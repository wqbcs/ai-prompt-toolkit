"""新增模块测试 — schema验证 + output + npu_adapter + tracing + playground"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.schema import (
    validate_finding,
    validate_report,
    validate_scan_summary,
    _HAS_PYDANTIC,
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
        from ai_prompt_toolkit.output import finding, console
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
        with pytest.raises(ValueError):
            with tracer.span("bad_op") as s:
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


class TestPlaygroundServerAPIs:
    def test_server_import(self):
        from ai_prompt_toolkit.playground.server import app
        assert app.title == "AI Prompt Toolkit Playground"

    def test_traces_api_exists(self):
        from ai_prompt_toolkit.playground.server import app
        routes = [r.path for r in app.routes]
        assert "/api/traces" in routes
        assert "/api/traces/summary" in routes
        assert "/api/traces/export" in routes

    def test_market_router_included(self):
        from ai_prompt_toolkit.playground.server import app
        routes = [r.path for r in app.routes]
        assert "/api/market/templates" in routes
