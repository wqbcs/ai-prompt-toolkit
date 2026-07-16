"""可观测性Tracing — 参考Langfuse/OpenTelemetry

P3-03: Prompt编译/评估/红队操作的端到端Tracing
- Trace: 一次完整操作的追踪
- Span: Trace内的子操作(Lint/Evaluate/Compile等)
- 指标: 延迟/Token数/费用/评分
- 导出: JSON/OpenTelemetry格式
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


_DEFAULT_EXPORT_DIR = Path.home() / ".prompt-toolkit" / "traces"


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
