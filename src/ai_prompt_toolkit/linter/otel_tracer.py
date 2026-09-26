"""OpenTelemetry可观测性集成 — 标准化追踪Lint/Eval执行

借鉴Langfuse的OpenTelemetry集成 + OpenTelemetry GenAI语义约定
(open-telemetry/semantic-conventions-genai):
- Tracer协议 + NoopTracer/file/memory三实现: CLI/MCP不感知具体后端(A2)
- setup_otel: 创建OTelTracer; get_tracer: 按环境变量选择实现
- trace_lint/trace_eval: Lint/Eval执行追踪(span+attributes+metrics)
- to_otlp_json: 导出OTLP-JSON格式(可被Langfuse/Jaeger/Grafana消费)

GenAI语义约定属性(F1, 对齐gen_ai.*命名空间):
- gen_ai.system: 工具标识("ai-prompt-toolkit")
- gen_ai.operation.name: 操作名("lint"/"eval")
- gen_ai.request.model: 请求模型(可选)
- gen_ai.usage.input_tokens / gen_ai.usage.output_tokens: Token用量(可选)
- prompt.template.id / prompt.lint.* / prompt.eval.*: 本工具域扩展属性
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

GEN_AI_SYSTEM = "ai-prompt-toolkit"

# F1: GenAI语义约定属性名常量表 — 禁止散落硬编码属性名
GENAI_ATTR_OPERATION_NAME = "gen_ai.operation.name"
GENAI_ATTR_REQUEST_MODEL = "gen_ai.request.model"
GENAI_ATTR_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GENAI_ATTR_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"


@dataclass
class OTelConfig:
    service_name: str = "ai-prompt-toolkit"
    endpoint: str = ""
    enabled: bool = False
    export_format: str = "otlp"  # otlp | json | none

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "enabled": self.enabled,
            "export_format": self.export_format,
        }


@dataclass
class TraceSpan:
    name: str = ""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"  # ok | error

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time > self.start_time else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "attributes": self.attributes,
            "status": self.status,
        }


class OTelTracer:
    """轻量Tracer实现 — 零硬依赖，OTel语义约定对齐

    设计原则(奥卡姆剃刀):
    - 不引入opentelemetry-sdk硬依赖; span属性命名对齐GenAI语义约定,
      导出OTLP-JSON后可直接被Langfuse OTel端点/Jaeger/Grafana消费
    - 嵌套span: start_span支持parent参数, end_span恢复父span
    """

    def __init__(self, config: OTelConfig | None = None):
        self.config = config or OTelConfig()
        self._spans: list[TraceSpan] = []
        self._span_stack: list[TraceSpan] = []
        self._metrics: dict[str, list[float]] = {}

    @property
    def current_span(self) -> TraceSpan | None:
        return self._span_stack[-1] if self._span_stack else None

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent: TraceSpan | None = None,
    ) -> TraceSpan:
        parent = parent or self.current_span
        span = TraceSpan(
            name=name,
            start_time=time.time(),
            attributes={"gen_ai.system": GEN_AI_SYSTEM, **(attributes or {})},
            parent_span_id=parent.span_id if parent else "",
        )
        if parent:
            span.trace_id = parent.trace_id
        self._spans.append(span)
        self._span_stack.append(span)
        return span

    def end_span(self, span: TraceSpan | None = None, status: str = "ok", attributes: dict[str, Any] | None = None) -> TraceSpan | None:
        target = span or self.current_span
        if target is None:
            return None
        target.end_time = time.time()
        target.status = status
        if attributes:
            target.attributes.update(attributes)
        if self._span_stack and self._span_stack[-1] is target:
            self._span_stack.pop()
        return target

    def record_metric(self, name: str, value: float) -> None:
        self._metrics.setdefault(name, []).append(value)

    def trace_lint(self, template_id: str, findings_count: int, score: float, duration_ms: float,
                   model: str | None = None,
                   token_usage: tuple[int, int] | None = None) -> TraceSpan:
        """Lint执行追踪 — 单次执行作为一个已完成span

        model/token_usage为可选: lint本身零LLM调用, 但A/B评测链路上的lint可挂载模型上下文。
        """
        now = time.time()
        attrs: dict[str, Any] = {
            "gen_ai.system": GEN_AI_SYSTEM,
            GENAI_ATTR_OPERATION_NAME: "lint",
            "prompt.template.id": template_id,
            "prompt.lint.findings.count": findings_count,
            "prompt.lint.score": score,
            "prompt.lint.duration_ms": duration_ms,
        }
        if model:
            attrs[GENAI_ATTR_REQUEST_MODEL] = model
        if token_usage is not None:
            attrs[GENAI_ATTR_USAGE_INPUT_TOKENS] = token_usage[0]
            attrs[GENAI_ATTR_USAGE_OUTPUT_TOKENS] = token_usage[1]
        span = TraceSpan(
            name="prompt.lint",
            start_time=now - duration_ms / 1000,
            end_time=now,
            attributes=attrs,
            status="ok" if findings_count == 0 else "error" if score < 50 else "ok",
        )
        self._spans.append(span)
        self.record_metric("prompt.lint.findings", float(findings_count))
        self.record_metric("prompt.lint.score", score)
        self.record_metric("prompt.lint.duration_ms", duration_ms)
        return span

    def trace_eval(self, template_id: str, overall_score: float, grade: str, duration_ms: float,
                   model: str | None = None,
                   token_usage: tuple[int, int] | None = None) -> TraceSpan:
        """Eval执行追踪 — 单次执行作为一个已完成span"""
        now = time.time()
        attrs: dict[str, Any] = {
            "gen_ai.system": GEN_AI_SYSTEM,
            GENAI_ATTR_OPERATION_NAME: "eval",
            "prompt.template.id": template_id,
            "prompt.eval.score": overall_score,
            "prompt.eval.grade": grade,
            "prompt.eval.duration_ms": duration_ms,
        }
        if model:
            attrs[GENAI_ATTR_REQUEST_MODEL] = model
        if token_usage is not None:
            attrs[GENAI_ATTR_USAGE_INPUT_TOKENS] = token_usage[0]
            attrs[GENAI_ATTR_USAGE_OUTPUT_TOKENS] = token_usage[1]
        span = TraceSpan(
            name="prompt.eval",
            start_time=now - duration_ms / 1000,
            end_time=now,
            attributes=attrs,
            status="ok" if overall_score >= 80 else "error",
        )
        self._spans.append(span)
        self.record_metric("prompt.eval.score", overall_score)
        self.record_metric("prompt.eval.duration_ms", duration_ms)
        return span

    @property
    def spans(self) -> list[TraceSpan]:
        return list(self._spans)

    @property
    def metrics_summary(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for name, values in self._metrics.items():
            result[name] = {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values) if values else 0.0,
                "min": min(values) if values else 0.0,
                "max": max(values) if values else 0.0,
            }
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "spans": [s.to_dict() for s in self._spans],
            "metrics": self.metrics_summary,
        }

    def to_otlp_json(self) -> str:
        """导出OTLP-JSON格式(ExportTraceServiceRequest结构)

        可直接POST到Langfuse OTel端点(/api/public/otel)或OTLP collector。
        """
        resources = [{
            "attributes": [
                {"key": "service.name", "value": {"stringValue": self.config.service_name}},
                {"key": "gen_ai.system", "value": {"stringValue": GEN_AI_SYSTEM}},
            ]
        }]
        scope_spans = []
        for s in self._spans:
            attrs = []
            for k, v in s.attributes.items():
                if isinstance(v, bool):
                    val: dict[str, Any] = {"boolValue": v}
                elif isinstance(v, (int, float)):
                    val = {"doubleValue": float(v)}
                else:
                    val = {"stringValue": str(v)}
                attrs.append({"key": k, "value": val})
            scope_spans.append({
                "traceId": s.trace_id,
                "spanId": s.span_id,
                "parentSpanId": s.parent_span_id,
                "name": s.name,
                "kind": 1,  # SPAN_KIND_INTERNAL
                "startTimeUnixNano": int(s.start_time * 1e9),
                "endTimeUnixNano": int(s.end_time * 1e9),
                "attributes": attrs,
                "status": {"code": 1 if s.status == "ok" else 2},
            })
        request = {
            "resourceSpans": [{
                "resource": resources[0],
                "scopeSpans": [{
                    "scope": {"name": GEN_AI_SYSTEM},
                    "spans": scope_spans,
                }],
            }]
        }
        return json.dumps(request, ensure_ascii=False)


def setup_otel(config: OTelConfig | None = None) -> OTelTracer:
    """工厂函数 — 创建Tracer实例"""
    return OTelTracer(config)


# ---------------------------------------------------------------------------
# A2: Tracer抽象 — 端层(CLI/MCP)面向协议编程, 不感知具体后端
# ---------------------------------------------------------------------------

@runtime_checkable
class Tracer(Protocol):
    """可观测性最小协议 — OTelTracer/NoopTracer均满足"""

    def start_span(self, name: str, attributes: dict[str, Any] | None = None,
                   parent: Any = None) -> Any: ...

    def end_span(self, span: Any = None, status: str = "ok",
                 attributes: dict[str, Any] | None = None) -> Any: ...

    def to_dict(self) -> dict[str, Any]: ...


class NoopTracer:
    """零开销空实现 — 默认后端(不追踪, 不落盘)"""

    def __init__(self) -> None:
        self._noop_span: TraceSpan | None = None

    @property
    def current_span(self) -> TraceSpan | None:
        return self._noop_span

    def start_span(self, name: str, attributes: dict[str, Any] | None = None,
                   parent: TraceSpan | None = None) -> TraceSpan:
        self._noop_span = TraceSpan(name=name)
        return self._noop_span

    def end_span(self, span: TraceSpan | None = None, status: str = "ok",
                 attributes: dict[str, Any] | None = None) -> TraceSpan | None:
        target = span or self._noop_span
        self._noop_span = None
        return target

    def record_metric(self, name: str, value: float) -> None:  # 协议兼容
        return None

    def trace_lint(self, template_id: str, findings_count: int, score: float, duration_ms: float,
                   model: str | None = None, token_usage: tuple[int, int] | None = None) -> TraceSpan:
        return TraceSpan(name="prompt.lint")

    def trace_eval(self, template_id: str, overall_score: float, grade: str, duration_ms: float,
                   model: str | None = None, token_usage: tuple[int, int] | None = None) -> TraceSpan:
        return TraceSpan(name="prompt.eval")

    def to_dict(self) -> dict[str, Any]:
        return {"backend": "noop", "spans": []}


def get_tracer() -> Tracer:
    """按环境变量选择Tracer实现 — 端层唯一入口

    PROMPT_TOOLKIT_TRACING:
        off/noop(默认) → NoopTracer;  memory/otel → OTelTracer(内存span, 可OTLP导出)
    """
    backend = os.environ.get("PROMPT_TOOLKIT_TRACING", "noop").strip().lower()
    if backend in ("memory", "otel", "otlp"):
        return OTelTracer()
    return NoopTracer()
