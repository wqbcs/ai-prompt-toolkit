"""新增模块测试 — schema验证 + output + npu_adapter + tracing + playground"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.schema import (
    validate_finding,
    validate_report,
    validate_scan_summary,
)


class TestSchemaValidation:
    def test_valid_finding(self):
        data = {"rule_id": "P001", "severity": "high", "description": "问题1"}
        assert validate_finding(data) == []

    def test_finding_missing_rule_id(self):
        data = {"severity": "high", "description": "问题1"}
        errors = validate_finding(data)
        assert len(errors) > 0

    def test_finding_invalid_severity(self):
        data = {"rule_id": "P001", "severity": "extreme", "description": "问题1"}
        errors = validate_finding(data)
        assert len(errors) > 0

    def test_finding_missing_description(self):
        data = {"rule_id": "P001", "severity": "low"}
        errors = validate_finding(data)
        assert len(errors) > 0

    def test_valid_report(self):
        data = {"timestamp": "2024-01-01", "template_id": "test", "status": "success"}
        assert validate_report(data) == []

    def test_report_missing_timestamp(self):
        data = {"template_id": "test", "status": "success"}
        errors = validate_report(data)
        assert len(errors) > 0

    def test_report_invalid_status(self):
        data = {"timestamp": "2024-01-01", "template_id": "test", "status": "unknown"}
        errors = validate_report(data)
        assert len(errors) > 0

    def test_valid_scan_summary(self):
        data = {"total_files": 5, "total_findings": 3, "critical": 0, "high": 1}
        assert validate_scan_summary(data) == []

    def test_scan_summary_negative_count(self):
        data = {"total_files": -1, "total_findings": 0}
        errors = validate_scan_summary(data)
        assert len(errors) > 0


class TestOutputModule:
    def test_scan_summary_creation(self):
        from ai_prompt_toolkit.output import ScanSummary

        s = ScanSummary(command="lint", total_files=3, total_findings=5, high=2, medium=3)
        assert s.passed is False
        assert s.total_findings == 5

    def test_scan_summary_passed(self):
        from ai_prompt_toolkit.output import ScanSummary

        s = ScanSummary(command="scan", total_files=1, total_findings=2, low=1, info=1)
        assert s.passed is True

    def test_finding_output(self):
        from ai_prompt_toolkit.output import finding

        finding("high", "P001", "测试问题", "修复建议")

    def test_findings_list_empty(self):
        from ai_prompt_toolkit.output import findings_list

        findings_list([])


class TestNPUAdapter:
    def test_detect_npu_returns_info(self):
        from ai_prompt_toolkit.ab_test.npu_adapter import detect_npu

        info = detect_npu()
        assert hasattr(info, "available")
        assert hasattr(info, "npu_count")
        assert hasattr(info, "to_dict")

    def test_get_npu_config(self):
        from ai_prompt_toolkit.ab_test.npu_adapter import get_npu_config

        config = get_npu_config("pangu-large")
        assert "quantization" in config
        assert "batch_size" in config

    def test_should_use_npu_without_env(self):
        import os

        from ai_prompt_toolkit.ab_test.npu_adapter import should_use_npu

        old = os.environ.pop("PROMPT_CLI_USE_NPU", None)
        try:
            result = should_use_npu("pangu")
        finally:
            if old is not None:
                os.environ["PROMPT_CLI_USE_NPU"] = old
        assert result is False


class TestMarkdownReporter:
    def test_lint_report(self):
        from ai_prompt_toolkit.report.markdown_reporter import generate_markdown_report

        data = {
            "_report_type": "lint",
            "lint_target": "test.md",
            "findings": [
                {"rule_id": "P001", "severity": "high", "description": "问题1"},
            ],
        }
        md = generate_markdown_report(data)
        assert "Lint Report" in md
        assert "P001" in md
        assert "high" in md

    def test_scan_report(self):
        from ai_prompt_toolkit.report.markdown_reporter import generate_markdown_report

        data = {
            "_report_type": "scan",
            "scan_target": "test.md",
            "risk_level": "high",
            "findings": [],
        }
        md = generate_markdown_report(data)
        assert "Security Scan" in md
        assert "high" in md

    def test_eval_report(self):
        from ai_prompt_toolkit.report.markdown_reporter import generate_markdown_report

        data = {
            "_report_type": "evaluate",
            "reports": [
                {"template_id": "test", "scores": [{"dimension_id": "D01", "score": 8.5}]},
            ],
        }
        md = generate_markdown_report(data)
        assert "Evaluation" in md
        assert "D01" in md


class TestTracing:
    def test_tracer_create_trace(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        trace = tracer.start_trace("test_op")
        assert trace.name == "test_op"
        assert trace.trace_id

    def test_tracer_end_trace(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        tracer.start_trace("test_op")
        trace = tracer.end_trace()
        assert trace is not None
        assert trace.duration_ms >= 0

    def test_tracer_span(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        tracer.start_trace("test_op")
        with tracer.span("sub_op", {"key": "val"}) as s:
            assert s.name == "sub_op"
        trace = tracer.end_trace()
        assert len(trace.spans) == 1
        assert trace.spans[0].status == "ok"

    def test_tracer_span_error(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        tracer.start_trace("test_op")
        with pytest.raises(ValueError), tracer.span("bad_op") as s:
            raise ValueError("test")
        trace = tracer.end_trace()
        assert trace.spans[0].status == "error"

    def test_tracer_get_traces(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        for i in range(5):
            tracer.start_trace(f"op_{i}")
            tracer.end_trace()
        traces = tracer.get_traces(limit=3)
        assert len(traces) == 3

    def test_tracer_export_json(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        tracer.start_trace("test")
        tracer.end_trace()
        json_str = tracer.export_json()
        assert "test" in json_str
        assert "trace_id" in json_str

    def test_tracer_summary(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        tracer = Tracer()
        summary = tracer.get_summary()
        assert summary["total_traces"] == 0
        tracer.start_trace("test")
        tracer.end_trace()
        summary = tracer.get_summary()
        assert summary["total_traces"] == 1

    def test_tracer_singleton(self):
        from ai_prompt_toolkit.tracing import Tracer

        Tracer.reset()
        t1 = Tracer.get_instance()
        t2 = Tracer.get_instance()
        assert t1 is t2


def _collect_route_paths(app):
    """递归收集应用路由路径（兼容新版FastAPI的_IncludedRouter包装对象）"""
    paths = []

    def _walk(routes):
        for r in routes:
            if type(r).__name__ == "_IncludedRouter":
                inner = getattr(r, "original_router", None)
                if inner is not None:
                    _walk(getattr(inner, "routes", []))
            elif hasattr(r, "path"):
                paths.append(r.path)

    _walk(app.routes)
    return paths


class TestPlaygroundServerAPIs:
    def test_server_import(self):
        from ai_prompt_toolkit.playground.server import app

        assert app.title == "AI Prompt Toolkit Playground"

    def test_traces_api_exists(self):
        from ai_prompt_toolkit.playground.server import app

        routes = _collect_route_paths(app)
        assert "/api/traces" in routes
        assert "/api/traces/summary" in routes
        assert "/api/traces/export" in routes

    def test_market_router_included(self):
        from ai_prompt_toolkit.playground.server import app

        routes = _collect_route_paths(app)
        assert "/api/market/templates" in routes


class TestDatasetModule:
    def _make_store(self, td):
        import os

        from ai_prompt_toolkit.dataset import DatasetStore

        return DatasetStore(db_path=os.path.join(td, "test.db"))

    def test_create_dataset(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("test_ds", description="测试数据集", tags=["unit"])
        assert ds.dataset_id
        assert ds.name == "test_ds"
        assert ds.tags == ["unit"]
        store.close()

    def test_add_and_get_cases(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("test_ds")
        c = store.add_case(ds.dataset_id, "输入文本", "期望输出", tags=["t1"])
        assert c.case_id
        cases = store.get_cases(ds.dataset_id)
        assert len(cases) == 1
        assert cases[0].input_text == "输入文本"
        store.close()

    def test_list_datasets(self, tmp_path):
        store = self._make_store(tmp_path)
        store.create_dataset("ds1")
        store.create_dataset("ds2")
        _datasets, total = store.list_datasets()
        assert total == 2
        store.close()

    def test_delete_dataset(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("del_me")
        assert store.delete_dataset(ds.dataset_id)
        assert store.get_dataset(ds.dataset_id) is None
        store.close()

    def test_import_export_json(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("imp_ds")
        count = store.import_json(ds.dataset_id, [{"input": "hello", "expected": "hi"}])
        assert count == 1
        exported = store.export_json(ds.dataset_id)
        assert "hello" in exported
        store.close()

    def test_import_export_csv(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("csv_ds")
        csv_text = "input,expected\nhello,hi\nworld,earth"
        count = store.import_csv(ds.dataset_id, csv_text)
        assert count == 2
        store.close()

    def test_run_dataset(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("run_ds")
        store.add_case(ds.dataset_id, "你是一个专业助手", "帮助用户")
        results = store.run_dataset(ds.dataset_id, run_type="lint")
        assert len(results) == 1
        assert results[0].status == "completed"
        store.close()

    def test_delete_case(self, tmp_path):
        store = self._make_store(tmp_path)
        ds = store.create_dataset("dc_ds")
        c = store.add_case(ds.dataset_id, "text")
        assert store.delete_case(c.case_id)
        assert len(store.get_cases(ds.dataset_id)) == 0
        store.close()


class TestEvalMatrixAPI:
    def test_eval_matrix_api_exists(self):
        from ai_prompt_toolkit.playground.server import app

        routes = _collect_route_paths(app)
        assert "/api/eval-matrix" in routes
        assert "/api/eval-history" in routes
        assert "/api/eval-compare" in routes

    def test_dataset_router_included(self):
        from ai_prompt_toolkit.playground.server import app

        routes = _collect_route_paths(app)
        assert "/api/datasets" in routes


class TestI18nModule:
    def test_translate_zh(self):
        from ai_prompt_toolkit.i18n.messages import set_locale, t

        set_locale("zh-CN")
        assert "Lint" in t("cli.lint.start")

    def test_translate_en(self):
        from ai_prompt_toolkit.i18n.messages import set_locale, t

        set_locale("en-US")
        assert "lint" in t("cli.lint.start").lower()

    def test_translate_with_kwargs(self):
        from ai_prompt_toolkit.i18n.messages import set_locale, t

        set_locale("zh-CN")
        result = t("cli.lint.findings_count", count=5)
        assert "5" in result

    def test_fallback_to_key(self):
        from ai_prompt_toolkit.i18n.messages import t

        assert t("nonexistent.key") == "nonexistent.key"

    def test_supported_locales(self):
        from ai_prompt_toolkit.i18n.messages import get_supported_locales

        locales = get_supported_locales()
        assert "zh-CN" in locales
        assert "en-US" in locales

    def test_set_unsupported_locale(self):
        from ai_prompt_toolkit.i18n.messages import get_current_locale, set_locale

        set_locale("fr-FR")
        assert get_current_locale() == "zh-CN"

    def test_add_custom_messages(self):
        from ai_prompt_toolkit.i18n.messages import add_messages, set_locale, t

        set_locale("zh-CN")
        add_messages("zh-CN", {"custom.key": "自定义值"})
        assert t("custom.key") == "自定义值"

    def test_t_from_package(self):
        from ai_prompt_toolkit.i18n import t

        result = t("cli.lint.start")
        assert result

    def test_get_current_locale(self):
        from ai_prompt_toolkit.i18n.messages import get_current_locale

        loc = get_current_locale()
        assert loc in ("zh-CN", "en-US")


class TestPluginSystem:
    def test_register_plugin(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginManager, PluginMeta

        PluginManager.reset()
        mgr = PluginManager()
        meta = PluginMeta(name="test-plugin", version="1.0")
        p = Plugin(meta)
        mgr.register(p)
        assert mgr.get_plugin("test-plugin") is not None

    def test_unregister_plugin(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginManager, PluginMeta

        PluginManager.reset()
        mgr = PluginManager()
        meta = PluginMeta(name="rm-plugin")
        mgr.register(Plugin(meta))
        assert mgr.unregister("rm-plugin")
        assert mgr.get_plugin("rm-plugin") is None

    def test_enable_disable(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginManager, PluginMeta

        PluginManager.reset()
        mgr = PluginManager()
        meta = PluginMeta(name="toggle-plugin")
        p = Plugin(meta)
        mgr.register(p)
        assert p.enabled
        p.disable()
        assert not p.enabled
        assert len(mgr.get_enabled_plugins()) == 0
        p.enable()
        assert len(mgr.get_enabled_plugins()) == 1

    def test_list_plugins(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginManager, PluginMeta

        PluginManager.reset()
        mgr = PluginManager()
        mgr.register(Plugin(PluginMeta(name="p1")))
        mgr.register(Plugin(PluginMeta(name="p2")))
        assert len(mgr.list_plugins()) == 2

    def test_plugin_summary(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginManager, PluginMeta

        PluginManager.reset()
        mgr = PluginManager()
        mgr.register(Plugin(PluginMeta(name="s1", version="2.0")))
        summary = mgr.get_summary()
        assert summary["total_plugins"] == 1
        assert summary["plugins"][0]["meta"]["version"] == "2.0"

    def test_singleton(self):
        from ai_prompt_toolkit.plugin import PluginManager

        PluginManager.reset()
        a = PluginManager.get_instance()
        b = PluginManager.get_instance()
        assert a is b

    def test_plugin_to_dict(self):
        from ai_prompt_toolkit.plugin import Plugin, PluginMeta

        meta = PluginMeta(name="dict-test", version="3.0", description="测试")
        p = Plugin(meta)
        d = p.to_dict()
        assert d["meta"]["name"] == "dict-test"
        assert d["enabled"] is True
