"""可观测性Tracing — 参考Langfuse/OpenTelemetry

P3-03: Prompt编译/评估/红队操作的端到端Tracing
- Trace: 一次完整操作的追踪
- Span: Trace内的子操作(Lint/Evaluate/Compile等)
- @observe装饰器: 自动追踪函数调用/耗时/输入输出(参考Langfuse)
- trace()上下文管理器: 追踪完整工作流
- 指标: 延迟/Token数/费用/评分
- 导出: JSON/OpenTelemetry格式
- 后端: 本地JSON + 华为云LTS
"""
from __future__ import annotations

import contextvars
import functools
import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Generator


_DEFAULT_EXPORT_DIR = Path.home() / ".prompt-toolkit" / "traces"

_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_current_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")


@dataclass
class Span:
    span_id: str
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "attributes": self.attributes,
        }


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
        return trace

    def end_trace(self) -> Trace | None:
        if not self._current_trace:
            return None
        self._current_trace.end_time = time.perf_counter()
        self._current_trace.duration_ms = (self._current_trace.end_time - self._current_trace.start_time) * 1000
        trace = self._current_trace
        self._traces.append(trace)
        self._current_trace = None
        return trace

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Generator[Span, None, None]:
        s = Span(
            span_id=uuid.uuid4().hex[:12],
            name=name,
            start_time=time.perf_counter(),
            attributes=attributes or {},
        )
        self._current_span = s
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
            if self._current_trace:
                self._current_trace.spans.append(s)
            self._current_span = None

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


class trace:
    def __init__(self, name: str, *, metadata: dict[str, Any] | None = None) -> None:
        self._name = name
        self._metadata = metadata

    def __enter__(self) -> Tracer:
        self._tracer = Tracer.get_instance()
        self._tracer.start_trace(self._name, self._metadata)
        _current_trace_id.set(self._tracer._current_trace.trace_id if self._tracer._current_trace else "")
        return self._tracer

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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
