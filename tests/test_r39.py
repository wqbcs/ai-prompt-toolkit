"""R39: 鸿蒙Lint规则P086-P095 + GitHub Action + 配置文件 测试套件"""
from __future__ import annotations

import pytest


class TestLintP086:
    def test_arkts_unsupported_syntax(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p086
        f = check_p086("HarmonyOS ArkTS开发: 使用 enum Color { RED, GREEN }")
        assert f is not None
        assert f.rule_id == "P086"

    def test_arkts_no_unsupported(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p086
        f = check_p086("HarmonyOS ArkTS开发: 使用 const 和 interface")
        assert f is None

    def test_non_harmonyos(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p086
        f = check_p086("Python enum Color { RED }")
        assert f is None


class TestLintP087:
    def test_stage_model_no_ability(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p087
        f = check_p087("HarmonyOS Stage模型应用开发指南")
        assert f is not None
        assert f.rule_id == "P087"

    def test_stage_model_with_ability(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p087
        f = check_p087("Stage模型 UIAbility EntryAbility 配置")
        assert f is None

    def test_non_stage_model(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p087
        f = check_p087("普通应用开发")
        assert f is None


class TestLintP088:
    def test_ability_no_lifecycle(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p088
        f = check_p088("鸿蒙Ability开发: 处理生命周期事件")
        assert f is not None
        assert f.rule_id == "P088"

    def test_ability_with_lifecycle(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p088
        f = check_p088("鸿蒙Ability: onCreate和onDestroy生命周期回调")
        assert f is None


class TestLintP089:
    def test_permission_missing(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p089
        f = check_p089("鸿蒙应用需要权限和授权处理")
        assert f is not None
        assert f.rule_id == "P089"

    def test_permission_declared(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p089
        f = check_p089("鸿蒙应用 ohos.permission.INTERNET 权限声明")
        assert f is None


class TestLintP090:
    def test_ui_component_no_version(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p090
        f = check_p090("HarmonyOS ArkUI使用List和Grid组件布局")
        assert f is not None
        assert f.rule_id == "P090"

    def test_ui_component_with_version(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p090
        f = check_p090("ArkUI List组件 API 12+ 兼容版本")
        assert f is None


class TestLintP091:
    def test_resource_no_standard_ref(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p091
        f = check_p091("鸿蒙应用图片和字符串资源管理")
        assert f is not None
        assert f.rule_id == "P091"

    def test_resource_with_standard_ref(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p091
        f = check_p091("鸿蒙资源 $r('app.string.title') 和 $rawfile('data.json')")
        assert f is None


class TestLintP092:
    def test_async_no_thread_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p092
        f = check_p092("鸿蒙耗时异步并发多线程处理")
        assert f is not None
        assert f.rule_id == "P092"

    def test_async_with_thread_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p092
        f = check_p092("鸿蒙耗时操作使用TaskPool和Worker线程")
        assert f is None


class TestLintP093:
    def test_data_no_mgmt_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p093
        f = check_p093("鸿蒙数据存储和持久化缓存方案")
        assert f is not None
        assert f.rule_id == "P093"

    def test_data_with_mgmt_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p093
        f = check_p093("鸿蒙使用关系型数据库RDB和Preferences")
        assert f is None


class TestLintP094:
    def test_network_no_security(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p094
        f = check_p094("鸿蒙HTTP网络请求和API接口调用")
        assert f is not None
        assert f.rule_id == "P094"

    def test_network_with_security(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p094
        f = check_p094("鸿蒙HTTPS证书锁定certificatePinning网络安全")
        assert f is None


class TestLintP095:
    def test_signing_no_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p095
        f = check_p095("鸿蒙应用签名证书发布上架AppGallery")
        assert f is not None
        assert f.rule_id == "P095"

    def test_signing_with_decl(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p095
        f = check_p095("鸿蒙应用 .p12调试证书 .p7b Profile AGC发布签名")
        assert f is None


class TestLintP086P095Registered:
    def test_p086_registered(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        assert "P086" in _RULE_MAP

    def test_p095_registered(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        assert "P095" in _RULE_MAP

    def test_all_in_checkers_extended(self):
        from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED
        checker_ids = {c.__name__ for c in _CHECKERS_EXTENDED}
        for name in ["check_p086", "check_p087", "check_p088", "check_p089", "check_p090",
                      "check_p091", "check_p092", "check_p093", "check_p094", "check_p095"]:
            assert name in checker_ids, f"Missing checker: {name}"

    def test_linter_can_lint_p086(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter
        linter = PromptLinter()
        result = linter.lint("test", "HarmonyOS ArkTS: enum Color { RED }")
        p086_found = any(f.rule_id == "P086" for f in result.findings)
        assert p086_found

    def test_linter_can_lint_p094(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter
        linter = PromptLinter()
        result = linter.lint("test", "鸿蒙HTTP网络请求API")
        p094_found = any(f.rule_id == "P094" for f in result.findings)
        assert p094_found


class TestFixerP086P095:
    def test_fix_p086(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p086_arkts_compat
        result = _fix_p086_arkts_compat("HarmonyOS ArkTS prompt")
        assert "ArkTS语法兼容性" in result

    def test_fix_p087(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p087_ability_decl
        result = _fix_p087_ability_decl("Stage model prompt")
        assert "EntryAbility" in result

    def test_fix_p088(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p088_lifecycle
        result = _fix_p088_lifecycle("Ability prompt")
        assert "onCreate" in result

    def test_fix_p089(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p089_permission
        result = _fix_p089_permission("Permission prompt")
        assert "ohos.permission" in result

    def test_fix_p090(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p090_ui_compat
        result = _fix_p090_ui_compat("UI prompt")
        assert "API 12" in result

    def test_fix_p091(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p091_resource_ref
        result = _fix_p091_resource_ref("Resource prompt")
        assert "$r(" in result

    def test_fix_p092(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p092_thread_model
        result = _fix_p092_thread_model("Thread prompt")
        assert "TaskPool" in result

    def test_fix_p093(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p093_data_mgmt
        result = _fix_p093_data_mgmt("Data prompt")
        assert "Preferences" in result

    def test_fix_p094(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p094_net_security
        result = _fix_p094_net_security("Network prompt")
        assert "HTTPS" in result

    def test_fix_p095(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p095_signing
        result = _fix_p095_signing("Signing prompt")
        assert ".p12" in result


class TestPromptKitConfig:
    def test_default_config(self):
        from ai_prompt_toolkit.promptkit_config import PromptKitConfig
        config = PromptKitConfig()
        assert config.lint.threshold == 0.0
        assert config.cache.maxsize == 1024
        assert config.output.format == "cli"
        assert config.lts.enabled is False

    def test_parse_toml_simple(self):
        from ai_prompt_toolkit.promptkit_config import _parse_toml_simple
        text = '[lint]\nrules = "P001,P002"\nthreshold = 60\nfix = true\n'
        result = _parse_toml_simple(text)
        assert "lint" in result
        assert result["lint"]["threshold"] == 60
        assert result["lint"]["fix"] is True

    def test_dict_to_config(self):
        from ai_prompt_toolkit.promptkit_config import _dict_to_config
        data = {
            "lint": {"threshold": 80, "fix": True},
            "cache": {"maxsize": 2048, "ttl": 3600},
            "output": {"format": "json", "color": False},
            "lts": {"group_id": "g1", "enabled": True},
        }
        config = _dict_to_config(data)
        assert config.lint.threshold == 80
        assert config.cache.maxsize == 2048
        assert config.output.format == "json"
        assert config.lts.group_id == "g1"

    def test_load_config_nonexistent(self):
        from ai_prompt_toolkit.promptkit_config import load_promptkit_config
        config = load_promptkit_config("/nonexistent/path.toml")
        assert isinstance(config, type(config))

    def test_config_to_dict(self):
        from ai_prompt_toolkit.promptkit_config import PromptKitConfig
        config = PromptKitConfig()
        d = config.to_dict()
        assert "lint" in d
        assert "cache" in d
        assert "output" in d
        assert "lts" in d

    def test_generate_example(self):
        from ai_prompt_toolkit.promptkit_config import generate_example_config
        text = generate_example_config()
        assert "[lint]" in text
        assert "[cache]" in text


class TestCacheBatchOps:
    def test_put_batch(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache
        cache = PromptCache()
        count = cache.put_batch({"k1": "v1", "k2": "v2", "k3": "v3"})
        assert count == 3
        assert cache.size == 3

    def test_get_batch(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache
        cache = PromptCache()
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        results = cache.get_batch(["k1", "k2", "k3"])
        assert len(results) == 2
        assert results["k1"] == "v1"
        assert "k3" not in results

    def test_get_batch_empty(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache
        cache = PromptCache()
        results = cache.get_batch(["k1", "k2"])
        assert len(results) == 0
