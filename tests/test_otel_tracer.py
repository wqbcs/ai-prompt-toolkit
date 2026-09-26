"""otel_tracer 单元测试 — OTel语义约定对齐 + OTLP-JSON导出"""

from __future__ import annotations

import json

from ai_prompt_toolkit.linter.otel_tracer import (
    GEN_AI_SYSTEM,
    OTelConfig,
    OTelTracer,
    setup_otel,
)


class TestOTelTracerBasics:
    def test_setup_otel_factory(self):
        t = setup_otel()
        assert isinstance(t, OTelTracer)
        assert t.config.service_name == "ai-prompt-toolkit"

    def test_custom_config(self):
        cfg = OTelConfig(service_name="my-svc", endpoint="http://localhost:4318", enabled=True)
        t = OTelTracer(cfg)
        assert t.config.to_dict()["endpoint"] == "http://localhost:4318"

    def test_span_has_genai_system_attr(self):
        t = OTelTracer()
        s = t.start_span("test.span")
        t.end_span(s)
        assert s.attributes["gen_ai.system"] == GEN_AI_SYSTEM

    def test_nested_spans_share_trace_id(self):
        t = OTelTracer()
        parent = t.start_span("parent")
        child = t.start_span("child")
        t.end_span(child)
        assert t.current_span is parent  # 栈式恢复父span
        t.end_span(parent)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert parent.parent_span_id == ""

    def test_end_span_updates_time_and_status(self):
        t = OTelTracer()
        s = t.start_span("s")
        assert s.duration_ms == 0.0
        t.end_span(s, status="error")
        assert s.status == "error"
        assert s.end_time >= s.start_time

    def test_end_span_unknown_target_returns_none(self):
        t = OTelTracer()
        assert t.end_span() is None

    def test_end_span_with_extra_attributes(self):
        t = OTelTracer()
        s = t.start_span("s")
        t.end_span(s, attributes={"extra": 1})
        assert s.attributes["extra"] == 1


class TestTraceLintEval:
    def test_trace_lint_attributes(self):
        t = OTelTracer()
        s = t.trace_lint("tpl-1", findings_count=3, score=60.0, duration_ms=150.0)
        assert s.name == "prompt.lint"
        assert s.attributes["prompt.template.id"] == "tpl-1"
        assert s.attributes["prompt.lint.findings.count"] == 3
        assert s.attributes["prompt.lint.score"] == 60.0
        assert s.attributes["prompt.lint.duration_ms"] == 150.0
        assert s.status == "ok"  # findings>0 但 score>=50 → ok

    def test_trace_lint_low_score_is_error(self):
        t = OTelTracer()
        s = t.trace_lint("tpl-1", 5, 30.0, 100.0)
        assert s.status == "error"

    def test_trace_eval_attributes(self):
        t = OTelTracer()
        s = t.trace_eval("tpl-2", overall_score=88.0, grade="A", duration_ms=900.0)
        assert s.name == "prompt.eval"
        assert s.attributes["prompt.eval.grade"] == "A"
        assert s.status == "ok"

    def test_trace_eval_low_score_is_error(self):
        t = OTelTracer()
        s = t.trace_eval("tpl-2", 55.0, "D", 900.0)
        assert s.status == "error"

    def test_metrics_recorded(self):
        t = OTelTracer()
        t.trace_lint("t", 1, 90.0, 10.0)
        t.trace_eval("t", 90.0, "A", 20.0)
        m = t.metrics_summary
        assert m["prompt.lint.findings"]["count"] == 1
        assert m["prompt.eval.score"]["avg"] == 90.0
        assert m["prompt.lint.duration_ms"]["max"] == 10.0


class TestOTLPExport:
    def _make_tracer(self) -> OTelTracer:
        t = OTelTracer()
        t.trace_lint("tpl-1", 2, 75.0, 120.0)
        parent = t.start_span("wrap")
        t.start_span("inner")
        t.end_span()
        t.end_span(parent)
        return t

    def test_otlp_json_structure(self):
        d = json.loads(self._make_tracer().to_otlp_json())
        rs = d["resourceSpans"][0]
        attrs = {a["key"]: a["value"] for a in rs["resource"]["attributes"]}
        assert attrs["service.name"]["stringValue"] == "ai-prompt-toolkit"
        spans = rs["scopeSpans"][0]["spans"]
        # 1个lint span + 2个手动span
        assert len(spans) == 3
        s0 = spans[0]
        assert s0["traceId"] and len(s0["spanId"]) == 16
        assert s0["kind"] == 1
        assert s0["startTimeUnixNano"] < s0["endTimeUnixNano"]

    def test_otlp_attribute_types(self):
        d = json.loads(self._make_tracer().to_otlp_json())
        spans = d["resourceSpans"][0]["scopeSpans"][0]["spans"]
        lint = spans[0]
        vals = {a["key"]: a["value"] for a in lint["attributes"]}
        assert "doubleValue" in vals["prompt.lint.score"]
        assert "stringValue" in vals["prompt.template.id"]

    def test_to_dict_roundtrip(self):
        t = self._make_tracer()
        d = t.to_dict()
        assert d["config"]["export_format"] == "otlp"
        assert len(d["spans"]) == 3
        assert "prompt.lint.score" in d["metrics"]

    def test_empty_tracer_export(self):
        d = json.loads(OTelTracer().to_otlp_json())
        assert d["resourceSpans"][0]["scopeSpans"][0]["spans"] == []


class TestTracerAbstraction:
    """A2: Tracer协议 + NoopTracer + 工厂选择"""

    def test_noop_tracer_zero_spans(self):
        from ai_prompt_toolkit.linter.otel_tracer import NoopTracer

        t = NoopTracer()
        s = t.start_span("x", attributes={"a": 1})
        t.end_span(s)
        assert t.to_dict()["spans"] == []
        assert t.to_dict()["backend"] == "noop"

    def test_noop_current_span_stack(self):
        from ai_prompt_toolkit.linter.otel_tracer import NoopTracer

        t = NoopTracer()
        s = t.start_span("x")
        assert t.current_span is s
        t.end_span(s)
        assert t.current_span is None

    def test_factory_default_noop(self, monkeypatch):
        from ai_prompt_toolkit.linter.otel_tracer import NoopTracer, get_tracer

        monkeypatch.delenv("PROMPT_TOOLKIT_TRACING", raising=False)
        assert isinstance(get_tracer(), NoopTracer)

    def test_factory_memory_selects_otel(self, monkeypatch):
        from ai_prompt_toolkit.linter.otel_tracer import OTelTracer, get_tracer

        monkeypatch.setenv("PROMPT_TOOLKIT_TRACING", "memory")
        assert isinstance(get_tracer(), OTelTracer)

    def test_otel_tracer_satisfies_protocol(self):
        from ai_prompt_toolkit.linter.otel_tracer import NoopTracer, Tracer

        assert isinstance(OTelTracer(), Tracer)
        assert isinstance(NoopTracer(), Tracer)


class TestGenAISemconvAttrs:
    """F1: gen_ai.*语义约定属性"""

    def test_lint_operation_name(self):
        t = OTelTracer()
        s = t.trace_lint("tpl", 0, 95.0, 12.0)
        assert s.attributes["gen_ai.operation.name"] == "lint"

    def test_eval_operation_name(self):
        t = OTelTracer()
        s = t.trace_eval("tpl", 88.0, "B", 20.0)
        assert s.attributes["gen_ai.operation.name"] == "eval"

    def test_optional_model_and_usage(self):
        t = OTelTracer()
        s = t.trace_lint("tpl", 1, 80.0, 10.0, model="gpt-4o", token_usage=(120, 30))
        assert s.attributes["gen_ai.request.model"] == "gpt-4o"
        assert s.attributes["gen_ai.usage.input_tokens"] == 120
        assert s.attributes["gen_ai.usage.output_tokens"] == 30

    def test_semconv_attr_names_exact(self):
        from ai_prompt_toolkit.linter.otel_tracer import (
            GENAI_ATTR_OPERATION_NAME,
            GENAI_ATTR_REQUEST_MODEL,
            GENAI_ATTR_USAGE_INPUT_TOKENS,
            GENAI_ATTR_USAGE_OUTPUT_TOKENS,
        )

        assert GENAI_ATTR_OPERATION_NAME == "gen_ai.operation.name"
        assert GENAI_ATTR_REQUEST_MODEL == "gen_ai.request.model"
        assert GENAI_ATTR_USAGE_INPUT_TOKENS == "gen_ai.usage.input_tokens"
        assert GENAI_ATTR_USAGE_OUTPUT_TOKENS == "gen_ai.usage.output_tokens"
