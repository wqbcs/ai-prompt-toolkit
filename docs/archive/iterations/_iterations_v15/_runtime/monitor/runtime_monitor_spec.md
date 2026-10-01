# 运行时监控设计

> 版本：v1.0 | 日期：2026-05-29

---

## 1. 监控架构

```
┌────────────────────────────────────────────┐
│            Runtime Monitor                  │
├────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐        │
│  │  Execution   │  │  Performance │        │
│  │  Tracer      │  │  Metrics     │        │
│  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐        │
│  │  Exception   │  │  Health      │        │
│  │  Alerter     │  │  Checker     │        │
│  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────┘
```

## 2. 执行追踪

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import json

@dataclass
class TraceEntry:
    timestamp: str
    scenario_id: str
    phase: str
    event: str
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)

class ExecutionTracer:
    def __init__(self, max_entries: int = 10000):
        self._entries: list[TraceEntry] = []
        self._max_entries = max_entries
        self._active_traces: dict[str, list[TraceEntry]] = {}

    def start_trace(self, scenario_id: str) -> str:
        trace_id = f"{scenario_id}:{datetime.utcnow().isoformat()}"
        self._active_traces[trace_id] = []
        return trace_id

    def record(self, trace_id: str, phase: str, event: str,
               duration_ms: float = 0, details: dict = None) -> None:
        entry = TraceEntry(
            timestamp=datetime.utcnow().isoformat(),
            scenario_id=trace_id.split(":")[0],
            phase=phase, event=event,
            duration_ms=duration_ms, details=details or {}
        )
        if trace_id in self._active_traces:
            self._active_traces[trace_id].append(entry)
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def end_trace(self, trace_id: str) -> list[TraceEntry]:
        entries = self._active_traces.pop(trace_id, [])
        return entries

    def get_trace(self, trace_id: str) -> list[TraceEntry]:
        return self._active_traces.get(trace_id, [])

    def export_traces(self, format: str = "json") -> str:
        if format == "json":
            return json.dumps([vars(e) for e in self._entries], indent=2)
        raise ValueError(f"Unsupported format: {format}")
```

## 3. 性能指标

```python
@dataclass
class PerformanceMetrics:
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0
    by_scenario: dict[str, dict] = field(default_factory=dict)
    by_phase: dict[str, dict] = field(default_factory=dict)

    @property
    def avg_execution_time_ms(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_executions

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def p50_execution_time_ms(self) -> float:
        return self.avg_execution_time_ms

    def record_execution(self, scenario_id: str, duration_ms: float,
                         success: bool, phase_times: dict[str, float] = None) -> None:
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        self.total_execution_time_ms += duration_ms
        self.min_execution_time_ms = min(self.min_execution_time_ms, duration_ms)
        self.max_execution_time_ms = max(self.max_execution_time_ms, duration_ms)

        if scenario_id not in self.by_scenario:
            self.by_scenario[scenario_id] = {"count": 0, "total_time": 0, "success": 0}
        self.by_scenario[scenario_id]["count"] += 1
        self.by_scenario[scenario_id]["total_time"] += duration_ms
        if success:
            self.by_scenario[scenario_id]["success"] += 1

        if phase_times:
            for phase, time_ms in phase_times.items():
                if phase not in self.by_phase:
                    self.by_phase[phase] = {"count": 0, "total_time": 0}
                self.by_phase[phase]["count"] += 1
                self.by_phase[phase]["total_time"] += time_ms
```

## 4. 异常告警

```python
class AlertLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    scenario_id: str
    message: str
    timestamp: str
    details: dict = field(default_factory=dict)

class ExceptionAlerter:
    def __init__(self):
        self._alerts: list[Alert] = []
        self._callbacks: list[Callable] = []
        self._thresholds = {
            "error_rate": 0.1,        # 错误率阈值10%
            "timeout_rate": 0.05,     # 超时率阈值5%
            "avg_time_ms": 5000,      # 平均耗时阈值5s
            "consecutive_failures": 3, # 连续失败阈值
        }
        self._consecutive_failures = 0

    def add_callback(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def check_execution(self, result: RuntimeResult, metrics: PerformanceMetrics) -> None:
        if result.status != RuntimeStatus.SUCCESS:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._thresholds["consecutive_failures"]:
                self._fire_alert(AlertLevel.ERROR, result.scenario_id,
                    f"连续{self._consecutive_failures}次执行失败")
        else:
            self._consecutive_failures = 0

        if metrics.total_executions > 10:
            error_rate = metrics.failed_executions / metrics.total_executions
            if error_rate > self._thresholds["error_rate"]:
                self._fire_alert(AlertLevel.WARN, result.scenario_id,
                    f"错误率{error_rate:.1%}超过阈值{self._thresholds['error_rate']:.1%}")

        if metrics.avg_execution_time_ms > self._thresholds["avg_time_ms"]:
            self._fire_alert(AlertLevel.WARN, result.scenario_id,
                f"平均耗时{metrics.avg_execution_time_ms:.0f}ms超过阈值")

    def _fire_alert(self, level: AlertLevel, scenario_id: str, message: str) -> None:
        alert = Alert(
            level=level, scenario_id=scenario_id, message=message,
            timestamp=datetime.utcnow().isoformat()
        )
        self._alerts.append(alert)
        for cb in self._callbacks:
            cb(alert)
```

## 5. RuntimeMonitor整合

```python
class RuntimeMonitor:
    def __init__(self):
        self.tracer = ExecutionTracer()
        self.metrics = PerformanceMetrics()
        self.alerter = ExceptionAlerter()
        self._health_status = "healthy"

    def on_phase(self, ctx: ExecutionContext) -> None:
        self.tracer.record(
            trace_id=ctx.scenario_id,
            phase=ctx.phase.value,
            event="phase_complete",
        )

    def on_execution_complete(self, result: RuntimeResult) -> None:
        success = result.status == RuntimeStatus.SUCCESS
        self.metrics.record_execution(
            scenario_id=result.scenario_id,
            duration_ms=result.execution_time_ms,
            success=success,
        )
        self.alerter.check_execution(result, self.metrics)

    @property
    def health(self) -> dict:
        return {
            "status": self._health_status,
            "total_executions": self.metrics.total_executions,
            "success_rate": f"{self.metrics.success_rate:.1%}",
            "avg_time_ms": f"{self.metrics.avg_execution_time_ms:.0f}",
            "active_alerts": len([a for a in self.alerter._alerts if a.level in (AlertLevel.ERROR, AlertLevel.CRITICAL)]),
        }
```
