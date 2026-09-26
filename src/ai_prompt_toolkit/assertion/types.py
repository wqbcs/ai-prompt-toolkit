"""断言系统类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssertType(Enum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not-contains"
    REGEX = "regex"
    JSON_SCHEMA = "json_schema"
    SIMILARITY = "similarity"
    LLM_RUBRIC = "llm-rubric"
    LATENCY = "latency"
    COST = "cost"


@dataclass
class AssertionConfig:
    assert_type: AssertType
    value: str | dict[str, Any] | list[str] | float = ""
    threshold: float = 0.8
    weight: float = 1.0
    provider: str = ""
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "assert_type": self.assert_type.value,
            "value": self.value,
            "threshold": self.threshold,
            "weight": self.weight,
        }


@dataclass
class AssertionResult:
    assert_type: AssertType
    passed: bool
    score: float = 0.0
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assert_type": self.assert_type.value,
            "passed": self.passed,
            "score": self.score,
            "reason": self.reason,
            "details": self.details,
        }
