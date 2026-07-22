"""R31: Plugin系统升级 + CI/CD集成 + 通知系统 测试套件"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.ci_integration import (
    CITestCase,
    CITestSuite,
    JUnitReporter,
    extract_ci_tags,
    generate_github_actions_workflow,
)
from ai_prompt_toolkit.notification import (
    DingTalkAdapter,
    FeishuAdapter,
    NotificationConfig,
    NotificationManager,
    SlackAdapter,
    WebhookAdapter,
    render_template,
)
from ai_prompt_toolkit.plugin import (
    Plugin,
    PluginHook,
    PluginManager,
    PluginMeta,
)


# ═══════════════════════════════════════
# Plugin系统v2 测试
# ═══════════════════════════════════════

class DummyHook(PluginHook):
    def name(self) -> str:
        return "dummy"


class LintHook(PluginHook):
    def name(self) -> str:
        return "lint-hook"

    def on_lint(self, template: str, findings: list) -> list:
        findings.append({"rule_id": "CUSTOM-001", "severity": "info", "description": "custom hook"})
        return findings

    def before_lint(self, template: str) -> str:
        return template + " [pre-processed]"

    def after_lint(self, template: str, findings: list) -> list:
        return [f for f in findings if f.get("severity") != "info"]


class NotifyHook(PluginHook):
    def name(self) -> str:
        return "notify-hook"

    def on_notify(self, event: str, data: dict) -> dict:
        data["notified"] = True
        return data


class TestPluginMetaV2:
    def test_to_dict(self):
        meta = PluginMeta(name="test", version="1.0", hooks=["lint", "scan"])
        d = meta.to_dict()
        assert d["name"] == "test"
        assert d["hooks"] == ["lint", "scan"]


class TestPluginHookV2:
    def test_new_hooks_exist(self):
        hook = DummyHook()
        assert hasattr(hook, "on_gepa_optimize")
        assert hasattr(hook, "on_flow_run")
        assert hasattr(hook, "on_notify")
        assert hasattr(hook, "before_lint")
        assert hasattr(hook, "after_lint")
        assert hasattr(hook, "before_gepa_optimize")
        assert hasattr(hook, "after_flow_run")

    def test_on_gepa_optimize_default(self):
        hook = DummyHook()
        result = hook.on_gepa_optimize("prompt", {"score": 0.9})
        assert result == {"score": 0.9}

    def test_on_flow_run_default(self):
        hook = DummyHook()
        result = hook.on_flow_run("test-flow", {"status": "success"})
        assert result == {"status": "success"}

    def test_on_notify_default(self):
        hook = DummyHook()
        result = hook.on_notify("test_event", {"key": "value"})
        assert result == {"key": "value"}

    def test_before_after_hooks(self):
        hook = DummyHook()
        assert hook.before_lint("test") == "test"
        assert hook.after_lint("test", []) == []
        assert hook.before_scan("test") == "test"
        assert hook.after_evaluate("test", {}) == {}


class TestPluginManagerV2:
    def setup_method(self):
        PluginManager.reset()

    def test_register_and_get(self):
        pm = PluginManager.get_instance()
        plugin = Plugin(meta=PluginMeta(name="test-plugin"), hooks=[DummyHook()])
        pm.register(plugin)
        assert pm.get_plugin("test-plugin") is not None

    def test_fire_lint_hook(self):
        pm = PluginManager.get_instance()
        hook = LintHook()
        plugin = Plugin(meta=PluginMeta(name="lint-test"), hooks=[hook])
        pm.register(plugin)
        result = pm.fire_hook("lint", template="hello", findings=[])
        assert len(result["findings"]) == 1
        assert result["findings"][0]["rule_id"] == "CUSTOM-001"

    def test_fire_before_hook(self):
        pm = PluginManager.get_instance()
        hook = LintHook()
        plugin = Plugin(meta=PluginMeta(name="before-test"), hooks=[hook])
        pm.register(plugin)
        result = pm.fire_before_hook("lint", template="hello")
        assert "[pre-processed]" in result["template"]

    def test_fire_after_hook(self):
        pm = PluginManager.get_instance()
        hook = LintHook()
        plugin = Plugin(meta=PluginMeta(name="after-test"), hooks=[hook])
        pm.register(plugin)
        findings = [
            {"severity": "info", "description": "info item"},
            {"severity": "high", "description": "high item"},
        ]
        result = pm.fire_after_hook("lint", template="hello", findings=findings)
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "high"

    def test_fire_notification(self):
        pm = PluginManager.get_instance()
        hook = NotifyHook()
        plugin = Plugin(meta=PluginMeta(name="notify-test"), hooks=[hook])
        pm.register(plugin)
        data = pm.fire_notification("eval_passed", {"score": 95})
        assert data["notified"] is True

    def test_fire_gepa_optimize_hook(self):
        pm = PluginManager.get_instance()
        plugin = Plugin(meta=PluginMeta(name="gepa-test"), hooks=[DummyHook()])
        pm.register(plugin)
        result = pm.fire_hook("gepa_optimize", prompt="test", result={"best_score": 0.95})
        assert result["result"]["best_score"] == 0.95

    def test_fire_flow_run_hook(self):
        pm = PluginManager.get_instance()
        plugin = Plugin(meta=PluginMeta(name="flow-test"), hooks=[DummyHook()])
        pm.register(plugin)
        result = pm.fire_hook("flow_run", flow_name="test-flow", result={"status": "success"})
        assert result["result"]["status"] == "success"

    def test_disabled_plugin_skipped(self):
        pm = PluginManager.get_instance()
        plugin = Plugin(meta=PluginMeta(name="disabled-test"), hooks=[LintHook()])
        plugin.disable()
        pm.register(plugin)
        result = pm.fire_hook("lint", template="hello", findings=[])
        assert len(result["findings"]) == 0

    def test_load_from_entry_points_no_error(self):
        pm = PluginManager.get_instance()
        loaded = pm.load_from_entry_points("nonexistent.group")
        assert loaded == []

    def test_get_summary(self):
        pm = PluginManager.get_instance()
        pm.register(Plugin(meta=PluginMeta(name="s1")))
        pm.register(Plugin(meta=PluginMeta(name="s2")))
        summary = pm.get_summary()
        assert summary["total_plugins"] == 2


# ═══════════════════════════════════════
# CI/CD集成 测试
# ═══════════════════════════════════════

class TestCITestCase:
    def test_passed(self):
        tc = CITestCase(name="test1", classname="suite", status="passed")
        xml = tc.to_xml()
        assert xml.tag == "testcase"
        assert xml.get("name") == "test1"

    def test_failed(self):
        tc = CITestCase(name="test2", classname="suite", status="failed", message="Assertion failed")
        xml = tc.to_xml()
        assert xml.find("failure") is not None

    def test_error(self):
        tc = CITestCase(name="test3", classname="suite", status="error", message="RuntimeError")
        xml = tc.to_xml()
        assert xml.find("error") is not None

    def test_skipped(self):
        tc = CITestCase(name="test4", classname="suite", status="skipped", message="Not ready")
        xml = tc.to_xml()
        assert xml.find("skipped") is not None


class TestCITestSuite:
    def test_properties(self):
        suite = CITestSuite(name="test-suite")
        suite.tests = [
            CITestCase(name="a", status="passed"),
            CITestCase(name="b", status="failed"),
            CITestCase(name="c", status="error"),
            CITestCase(name="d", status="skipped"),
        ]
        assert suite.total == 4
        assert suite.failures == 1
        assert suite.errors == 1
        assert suite.skipped == 1

    def test_to_xml_with_properties(self):
        suite = CITestSuite(name="ci-suite", properties={"ci_sha": "abc123", "ci_ref": "main"})
        suite.tests = [CITestCase(name="t1", status="passed")]
        xml = suite.to_xml()
        assert xml.get("name") == "ci-suite"
        props = xml.find("properties")
        assert props is not None
        assert len(props) == 2


class TestJUnitReporter:
    def test_add_lint_result(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_lint_result("test.md", [{"severity": "high", "rule_id": "P001"}], 100)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 1

    def test_add_scan_result(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_scan_result("test.md", [], 50)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 0

    def test_add_eval_result(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_eval_result("test.md", 85.0, True, elapsed_ms=200)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 0

    def test_add_gepa_result(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_gepa_result("prompt1", 0.95, 0.25, 5000)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 0

    def test_add_gepa_result_no_improvement(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_gepa_result("prompt1", 0.70, 0.0, 3000)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 1

    def test_add_redteam_result(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_redteam_result("target", 3, False, 1000)
        assert reporter.suite.total == 1
        assert reporter.suite.failures == 1

    def test_to_xml_string(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_lint_result("test.md", [], 100)
        xml_str = reporter.to_xml_string()
        assert "<?xml" in xml_str
        assert "testsuites" in xml_str

    def test_write_file(self):
        reporter = JUnitReporter(suite_name="test")
        reporter.add_eval_result("test.md", 90.0, True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = reporter.write(str(Path(tmpdir) / "junit.xml"))
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "testsuites" in content

    def test_has_failures(self):
        reporter = JUnitReporter(suite_name="test")
        assert not reporter.has_failures
        reporter.add_lint_result("test.md", [{"severity": "high"}], 100)
        assert reporter.has_failures

    def test_ci_tags(self):
        reporter = JUnitReporter(suite_name="test", ci_tags={"ci_sha": "abc"})
        assert reporter.suite.properties["ci_sha"] == "abc"


class TestExtractCITags:
    def test_returns_dict(self):
        tags = extract_ci_tags()
        assert isinstance(tags, dict)


class TestGenerateGitHubActionsWorkflow:
    def test_default_workflow(self):
        workflow = generate_github_actions_workflow()
        assert "Prompt Quality Gate" in workflow
        assert "promptkit lint" in workflow
        assert "promptkit scan" in workflow
        assert "promptkit evaluate" in workflow
        assert "junit-report" in workflow or "junit" in workflow.lower()

    def test_with_redteam(self):
        workflow = generate_github_actions_workflow(redteam=True)
        assert "promptkit redteam" in workflow

    def test_custom_threshold(self):
        workflow = generate_github_actions_workflow(threshold=80.0)
        assert "80.0" in workflow


# ═══════════════════════════════════════
# 通知系统 测试
# ═══════════════════════════════════════

class TestRenderTemplate:
    def test_simple_substitution(self):
        result = render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self):
        result = render_template("{{a}} + {{b}} = {{c}}", {"a": "1", "b": "2", "c": "3"})
        assert result == "1 + 2 = 3"

    def test_missing_variable_kept(self):
        result = render_template("Hello {{name}}!", {})
        assert "{{name}}" in result


class TestNotificationConfig:
    def test_to_dict_masks_webhook(self):
        config = NotificationConfig(type="slack", webhook="https://hooks.slack.com/services/ABC123DEF456", secret="")
        d = config.to_dict()
        assert "..." in d["webhook"]
        assert d["type"] == "slack"

    def test_enabled_default(self):
        config = NotificationConfig()
        assert config.enabled is True

    def test_events_list(self):
        config = NotificationConfig(events=["lint_failed", "eval_failed"])
        assert len(config.events) == 2


class TestNotificationManager:
    def test_add_and_remove_config(self):
        manager = NotificationManager()
        config = NotificationConfig(type="webhook", webhook="http://example.com")
        manager.add_config(config)
        assert len(manager.configs) == 1
        assert manager.remove_config(0)
        assert len(manager.configs) == 0

    def test_remove_invalid_index(self):
        manager = NotificationManager()
        assert not manager.remove_config(99)

    def test_notify_no_configs(self):
        manager = NotificationManager()
        results = manager.notify("lint_failed", {"file_path": "test.md"})
        assert results == []

    def test_notify_disabled_config(self):
        manager = NotificationManager()
        config = NotificationConfig(type="webhook", webhook="http://example.com", enabled=False)
        manager.add_config(config)
        results = manager.notify("lint_failed", {"file_path": "test.md"})
        assert results == []

    def test_notify_event_filter(self):
        manager = NotificationManager()
        config = NotificationConfig(type="webhook", webhook="http://example.com", events=["eval_failed"])
        manager.add_config(config)
        results = manager.notify("lint_failed", {"file_path": "test.md"})
        assert results == []

    def test_notify_unknown_type(self):
        manager = NotificationManager()
        config = NotificationConfig(type="unknown_platform", webhook="http://example.com")
        manager.add_config(config)
        results = manager.notify("lint_failed", {"file_path": "test.md"})
        assert results == []

    def test_list_configs(self):
        manager = NotificationManager()
        manager.add_config(NotificationConfig(type="slack", webhook="http://slack.example.com"))
        configs = manager.list_configs()
        assert len(configs) == 1

    def test_from_yaml_config(self):
        data = {
            "notifications": {
                "on_failure": [
                    {"type": "dingtalk", "webhook": "http://dingtalk.example.com", "secret": "test"},
                    {"type": "feishu", "webhook": "http://feishu.example.com"},
                ],
                "on_success": [
                    {"type": "slack", "webhook": "http://slack.example.com"},
                ],
            }
        }
        manager = NotificationManager.from_yaml_config(data)
        assert len(manager.configs) == 3
        assert manager.configs[0].type == "dingtalk"
        assert manager.configs[2].type == "slack"

    def test_from_yaml_config_auto_events(self):
        data = {
            "notifications": {
                "on_failure": [{"type": "webhook", "webhook": "http://example.com"}],
            }
        }
        manager = NotificationManager.from_yaml_config(data)
        assert "lint_failed" in manager.configs[0].events
        assert "eval_failed" in manager.configs[0].events


class TestAdapters:
    def test_dingtalk_adapter_no_url(self):
        adapter = DingTalkAdapter()
        result = adapter.send("test", NotificationConfig())
        assert result is False

    def test_feishu_adapter_no_url(self):
        adapter = FeishuAdapter()
        result = adapter.send("test", NotificationConfig())
        assert result is False

    def test_slack_adapter_no_url(self):
        adapter = SlackAdapter()
        result = adapter.send("test", NotificationConfig())
        assert result is False

    def test_webhook_adapter_no_url(self):
        adapter = WebhookAdapter()
        result = adapter.send("test", NotificationConfig())
        assert result is False

    def test_default_templates_exist(self):
        from ai_prompt_toolkit.notification import _DEFAULT_TEMPLATES
        assert "lint_failed" in _DEFAULT_TEMPLATES
        assert "eval_passed" in _DEFAULT_TEMPLATES
        assert "gepa_improved" in _DEFAULT_TEMPLATES
        assert "redteam_vulnerability" in _DEFAULT_TEMPLATES
        assert "contest_ready" in _DEFAULT_TEMPLATES
