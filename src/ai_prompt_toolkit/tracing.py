"""可观测性Tracing — 参考Langfuse/OpenTelemetry/Traceloop

P3-03: Prompt编译/评估/红队操作的端到端Tracing
- Trace: 一次完整操作的追踪
- Span: Trace内的子操作(Lint/Evaluate/Compile等)
- @observe装饰器: 自动追踪函数调用/耗时/输入输出(参考Langfuse)
- @trace_workflow/@trace_task: 声明式装饰器(参考Traceloop)
- trace()上下文管理器: 追踪完整工作流
- 指标: 延迟/Token数/费用/评分
- 导出: JSON/OpenTelemetry OTLP格式(兼容GitHub/Jaeger/华为云AOM)
- 后端: 本地JSON + 华为云LTS/AOM
- gen_ai.*语义约定: 标准化LLM可观测性属性(参考OpenTelemetry GenAI Semantic Conventions)
"""

from __future__ import annotations

import contextvars
import functools
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ai_prompt_toolkit import __version__  # R236-P2-19: OTel 服务版本动态(原默认 42.0.0 漂移)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

logger = logging.getLogger(__name__)

_DEFAULT_EXPORT_DIR = Path.home() / ".prompt-toolkit" / "traces"

_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_current_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")

_W3C_VERSION = "00"
_SPAN_KIND_MAP = {"internal": 1, "server": 2, "client": 3, "producer": 4, "consumer": 5}
_STATUS_OTLP_MAP = {"ok": {"code": 1}, "error": {"code": 2, "message": ""}, "unset": {"code": 0}}


@dataclass
class Span:
    span_id: str
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    kind: str = "internal"
    parent_span_id: str = ""
    trace_id: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    start_time_ns: int = 0
    end_time_ns: int = 0

    def __post_init__(self) -> None:
        if not self.span_id:
            self.span_id = uuid.uuid4().hex[:16]
        if not self.trace_id:
            self.trace_id = _current_trace_id.get() or uuid.uuid4().hex[:32]
        if self.start_time_ns == 0:
            self.start_time_ns = time.time_ns()

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        self.attributes.update(attrs)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "timeUnixNano": str(time.time_ns()), "attributes": attributes or {}})

    def record_exception(self, exception: Exception) -> None:
        self.status = "error"
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )

    def w3c_traceparent(self) -> str:
        flags = "01" if self.status == "ok" else "00"
        return f"{_W3C_VERSION}-{self.trace_id}-{self.span_id}-{flags}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "attributes": self.attributes,
            "kind": self.kind,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
        }

    def to_otlp_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "name": self.name,
            "kind": _SPAN_KIND_MAP.get(self.kind, 1),
            "startTimeUnixNano": str(self.start_time_ns),
            "endTimeUnixNano": str(self.end_time_ns) if self.end_time_ns else str(time.time_ns()),
        }
        if self.parent_span_id:
            d["parentSpanId"] = self.parent_span_id
        if self.attributes:
            d["attributes"] = _attrs_to_otlp(self.attributes)
        if self.events:
            d["events"] = self.events
        d["status"] = _STATUS_OTLP_MAP.get(self.status, _STATUS_OTLP_MAP["unset"])
        return d


@dataclass
class Trace:
    trace_id: str
    name: str
    spans: list[Span] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_otlp_json(
        self, service_name: str = "ai-prompt-toolkit", service_version: str = __version__
    ) -> dict[str, Any]:
        scope_spans: list[dict[str, Any]] = [
            {
                "scope": {"name": service_name, "version": service_version},
                "spans": [s.to_otlp_dict() for s in self.spans],
            }
        ]
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service_name}},
                            {"key": "service.version", "value": {"stringValue": service_version}},
                            {"key": "telemetry.sdk.name", "value": {"stringValue": "promptkit-tracing"}},
                        ]
                    },
                    "scopeSpans": scope_spans,
                }
            ]
        }

    def w3c_traceparent(self) -> str:
        if not self.spans:
            return ""
        root = self.spans[0]
        flags = "01"
        return f"{_W3C_VERSION}-{self.trace_id}-{root.span_id}-{flags}"


class Tracer:
    _instance: Tracer | None = None

    def __init__(self, export_dir: str | Path | None = None):
        self._export_dir = Path(export_dir) if export_dir else _DEFAULT_EXPORT_DIR
        self._traces: list[Trace] = []
        self._current_trace: Trace | None = None
        self._current_span: Span | None = None

    @classmethod
    def get_instance(cls) -> Tracer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def start_trace(self, name: str, metadata: dict[str, Any] | None = None) -> Trace:
        trace = Trace(
            trace_id=uuid.uuid4().hex[:16],
            name=name,
            start_time=time.perf_counter(),
            metadata=metadata or {},
        )
        self._current_trace = trace
        _current_trace_id.set(trace.trace_id)
        return trace

    def end_trace(self) -> Trace | None:
        if not self._current_trace:
            return None
        self._current_trace.end_time = time.perf_counter()
        self._current_trace.duration_ms = (self._current_trace.end_time - self._current_trace.start_time) * 1000
        trace = self._current_trace
        self._traces.append(trace)
        self._current_trace = None
        _current_trace_id.set("")
        _current_span_id.set("")
        return trace

    @contextmanager
    def span(
        self, name: str, attributes: dict[str, Any] | None = None, kind: str = "internal"
    ) -> Generator[Span, None, None]:
        parent_id = _current_span_id.get()
        trace_id = _current_trace_id.get() or ""
        s = Span(
            span_id=uuid.uuid4().hex[:16],
            name=name,
            start_time=time.perf_counter(),
            attributes=attributes or {},
            kind=kind,
            parent_span_id=parent_id,
            trace_id=trace_id,
        )
        self._current_span = s
        prev_span_id = _current_span_id.set(s.span_id)
        try:
            yield s
            s.status = "ok"
        except Exception as e:
            s.status = "error"
            s.attributes["error"] = str(e)
            raise
        finally:
            s.end_time = time.perf_counter()
            s.duration_ms = (s.end_time - s.start_time) * 1000
            s.end_time_ns = time.time_ns()
            if self._current_trace:
                self._current_trace.spans.append(s)
            self._current_span = None
            _current_span_id.set(prev_span_id if isinstance(prev_span_id, str) else "")

    def get_traces(self, limit: int = 100) -> list[Trace]:
        return self._traces[-limit:]

    def export_json(self, trace: Trace | None = None) -> str:
        t = trace or (self._traces[-1] if self._traces else None)
        if not t:
            return "{}"
        return json.dumps(t.to_dict(), ensure_ascii=False, indent=2)

    def save_traces(self, export_dir: str | Path | None = None) -> int:
        d = Path(export_dir) if export_dir else self._export_dir
        d.mkdir(parents=True, exist_ok=True)
        count = 0
        for trace in self._traces:
            fname = f"{trace.trace_id}_{trace.name}.json"
            with open(d / fname, "w", encoding="utf-8") as f:
                json.dump(trace.to_dict(), f, ensure_ascii=False, indent=2)
            count += 1
        return count

    def get_summary(self) -> dict[str, Any]:
        if not self._traces:
            return {"total_traces": 0}
        total_duration = sum(t.duration_ms for t in self._traces)
        total_spans = sum(len(t.spans) for t in self._traces)
        return {
            "total_traces": len(self._traces),
            "total_spans": total_spans,
            "avg_duration_ms": round(total_duration / len(self._traces), 2),
            "max_duration_ms": round(max(t.duration_ms for t in self._traces), 2),
            "error_count": sum(1 for t in self._traces for s in t.spans if s.status == "error"),
        }

    def export_otlp_json(self, trace: Trace | None = None) -> str:
        t = trace or (self._traces[-1] if self._traces else None)
        if not t:
            return "{}"
        return json.dumps(t.to_otlp_json(), ensure_ascii=False, indent=2)

    def save_otlp(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {"resourceSpans": []}
        for t in self._traces:
            otlp = t.to_otlp_json()
            data["resourceSpans"].extend(otlp.get("resourceSpans", []))
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def trace_llm(self, system: str, model: str, **extra_attrs: Any) -> Generator[Span, None, None]:
        attrs: dict[str, Any] = {
            "gen_ai.system": system,
            "gen_ai.request.model": model,
            **extra_attrs,
        }
        return cast("Generator[Span, None, None]", self.span(f"{system}.chat", attributes=attrs))

    def get_trace_tree(self, trace_id: str = "") -> dict[str, Any]:
        traces = self._traces
        if trace_id:
            traces = [t for t in traces if t.trace_id == trace_id]
        if not traces:
            return {"traces": [], "total": 0}
        result: list[dict[str, Any]] = []
        for t in traces:
            spans_by_parent: dict[str, list[Span]] = {}
            roots: list[Span] = []
            for s in t.spans:
                if s.parent_span_id:
                    spans_by_parent.setdefault(s.parent_span_id, []).append(s)
                else:
                    roots.append(s)
            tree_nodes = [_build_span_tree_node(r, spans_by_parent) for r in roots]
            result.append(
                {
                    "trace_id": t.trace_id,
                    "name": t.name,
                    "duration_ms": round(t.duration_ms, 2),
                    "spans": tree_nodes,
                }
            )
        return {"traces": result, "total": len(result)}


def _build_span_tree_node(span: Span, spans_by_parent: dict[str, list[Span]]) -> dict[str, Any]:
    children = spans_by_parent.get(span.span_id, [])
    node: dict[str, Any] = {
        "name": span.name,
        "span_id": span.span_id,
        "duration_ms": round(span.duration_ms, 2),
        "status": span.status,
    }
    if children:
        node["children"] = [_build_span_tree_node(c, spans_by_parent) for c in children]
    return node


def _attrs_to_otlp(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key, value in attrs.items():
        kv: dict[str, Any] = {"key": key}
        if isinstance(value, bool):
            kv["value"] = {"boolValue": value}
        elif isinstance(value, int):
            kv["value"] = {"intValue": str(value)}
        elif isinstance(value, float):
            kv["value"] = {"doubleValue": value}
        elif isinstance(value, str):
            kv["value"] = {"stringValue": value}
        else:
            kv["value"] = {"stringValue": str(value)}
        result.append(kv)
    return result


@dataclass
class HuaweiAOMConfig:
    endpoint: str = ""
    project_id: str = ""
    ak: str = ""
    sk: str = ""
    domain_id: str = ""
    region: str = "cn-north-4"

    @classmethod
    def from_env(cls) -> HuaweiAOMConfig:
        return cls(
            endpoint=os.getenv("HUAWEI_AOM_ENDPOINT", ""),
            project_id=os.getenv("HUAWEI_AOM_PROJECT_ID", ""),
            ak=os.getenv("HUAWEI_AOM_AK", ""),
            sk=os.getenv("HUAWEI_AOM_SK", ""),
            domain_id=os.getenv("HUAWEI_AOM_DOMAIN_ID", ""),
            region=os.getenv("HUAWEI_AOM_REGION", "cn-north-4"),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.endpoint and self.ak and self.sk)


class HuaweiAOMExporter:
    def __init__(self, config: HuaweiAOMConfig | None = None):
        self.config = config or HuaweiAOMConfig.from_env()

    def export_trace(self, trace: Trace) -> dict[str, Any]:
        if not self.config.is_configured:
            return {"status": "skipped", "reason": "not_configured"}

        otlp_data = trace.to_otlp_json()
        payload = json.dumps(otlp_data, ensure_ascii=False)
        result: dict[str, Any] = {
            "status": "prepared",
            "endpoint": self.config.endpoint,
            "region": self.config.region,
            "span_count": len(trace.spans),
            "payload_size_bytes": len(payload.encode("utf-8")),
        }

        try:
            import urllib.error
            import urllib.request

            url = f"{self.config.endpoint}/v1/{self.config.project_id}/traces"
            req = urllib.request.Request(
                url,
                data=payload.encode("utf-8"),
                headers={"Content-Type": "application/json", "x-auth-token": f"{self.config.ak}:{self.config.sk}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result["http_status"] = resp.status
                result["status"] = "exported"
        except urllib.error.URLError as e:
            result["status"] = "export_failed"
            result["error"] = str(e)
            logger.warning(f"AOM export failed: {e}")
        except Exception as e:
            result["status"] = "export_failed"
            result["error"] = str(e)

        return result

    def export_all(self, tracer: Tracer) -> list[dict[str, Any]]:
        return [self.export_trace(t) for t in tracer.get_traces()]

    def build_payload(self, trace: Trace) -> str:
        return json.dumps(trace.to_otlp_json(), ensure_ascii=False, indent=2)


def print_trace_tree(tracer: Tracer, trace_id: str = "") -> str:
    tree = tracer.get_trace_tree(trace_id)
    if not tree.get("traces"):
        return "No traces found"
    lines: list[str] = []
    for t in tree["traces"]:
        lines.append(f"[{t['name']}] {t['duration_ms']:.1f}ms")
        for s in t.get("spans", []):
            _format_tree_node(s, lines, indent=1)
    return "\n".join(lines)


def _format_tree_node(node: dict[str, Any], lines: list[str], indent: int) -> None:
    prefix = "  " * indent
    status_icon = "+" if node.get("status") == "ok" else "x" if node.get("status") == "error" else "-"
    name = node.get("name", "?")
    duration = node.get("duration_ms", 0)
    lines.append(f"{prefix}{status_icon} {name} ({duration:.1f}ms)")
    for child in node.get("children", []):
        _format_tree_node(child, lines, indent + 1)


class trace:  # noqa: N801 — 公开API名(以with trace(...)使用), 保持小写
    def __init__(self, name: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._name = name
        self._metadata = metadata

    def __enter__(self) -> Tracer:
        self._tracer = Tracer.get_instance()
        self._tracer.start_trace(self._name, self._metadata)
        _current_trace_id.set(self._tracer._current_trace.trace_id if self._tracer._current_trace else "")
        return self._tracer

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self._tracer.end_trace()
        _current_trace_id.set("")
        _current_span_id.set("")


def observe(
    name: str | None = None,
    *,
    capture_input: bool = True,
    capture_output: bool = True,
) -> Callable:
    """@observe装饰器——参考Langfuse @observe模式, 自动追踪函数调用/耗时/输入输出"""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = Tracer.get_instance()
            if not tracer._current_trace:
                return func(*args, **kwargs)

            attributes: dict[str, Any] = {}
            if capture_input:
                try:
                    attributes["input_args"] = repr(args)[:200]
                    attributes["input_kwargs"] = repr(kwargs)[:200]
                except Exception:
                    pass

            with tracer.span(span_name, attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    if capture_output:
                        try:
                            span.attributes["output"] = repr(result)[:200]
                        except Exception:
                            pass
                    return result
                except Exception as e:
                    span.attributes["output_error"] = str(e)[:200]
                    raise

        return wrapper

    return decorator


def trace_workflow(name: str | None = None) -> Callable:
    """@trace_workflow装饰器——参考Traceloop, 标注顶层工作流(根Span)"""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with trace(span_name, metadata={"type": "workflow"}):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def trace_task(name: str | None = None) -> Callable:
    """@trace_task装饰器——参考Traceloop, 标注工作流内子任务(子Span)"""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = Tracer.get_instance()
            if not tracer._current_trace:
                return func(*args, **kwargs)
            with tracer.span(span_name, attributes={"traceloop.task.name": span_name}):
                return func(*args, **kwargs)

        return wrapper

    return decorator
