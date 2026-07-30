"""成本追踪维度 - Token使用+成本+延迟追踪

借鉴Langfuse的成本追踪功能:
- CostRecord: 单次推理成本记录
- CostTracker: 累积成本追踪器
- 支持多模型定价(OpenAI/Claude/华为云鹏鹏等)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


_MODEL_PRICING: dict[str, dict[str, Any]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "unit": "1M_tokens"},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "unit": "1M_tokens"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "unit": "1M_tokens"},
    "claude-3-opus": {"input": 15.00, "output": 75.00, "unit": "1M_tokens"},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00, "unit": "1M_tokens"},
    "claude-3-haiku": {"input": 0.25, "output": 1.25, "unit": "1M_tokens"},
    "pangu-large": {"input": 8.00, "output": 24.00, "unit": "1M_tokens"},
    "pangu-medium": {"input": 2.00, "output": 6.00, "unit": "1M_tokens"},
    "deepseek-chat": {"input": 0.14, "output": 0.28, "unit": "1M_tokens"},
    "qwen-max": {"input": 4.00, "output": 12.00, "unit": "1M_tokens"},
}


@dataclass
class CostRecord:
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "cost_usd": round(self.cost_usd, 6),
            "timestamp": self.timestamp,
        }


@dataclass
class CostTracker:
    records: list[CostRecord] = field(default_factory=list)

    def record(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float = 0.0) -> CostRecord:
        pricing = _MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0, "unit": "1M_tokens"})
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0.0)
        cost_usd = input_cost + output_cost
        rec = CostRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            timestamp=time.time(),
        )
        self.records.append(rec)
        return rec

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def avg_latency_ms(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.latency_ms for r in self.records) / len(self.records)

    @property
    def by_model(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for r in self.records:
            if r.model not in result:
                result[r.model] = {"count": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "latency_ms": 0.0}
            m = result[r.model]
            m["count"] += 1
            m["input_tokens"] += r.input_tokens
            m["output_tokens"] += r.output_tokens
            m["cost_usd"] += r.cost_usd
            m["latency_ms"] += r.latency_ms
        for m in result.values():
            if m["count"] > 0:
                m["latency_ms"] = round(m["latency_ms"] / m["count"], 2)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "by_model": self.by_model,
            "records": [r.to_dict() for r in self.records],
        }
