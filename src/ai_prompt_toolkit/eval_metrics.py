"""评估指标标准化 — 对齐deepeval评估框架

参考:
- deepeval (17k stars) — 评估指标体系
- promptfoo — 断言评估
- langfuse — 评分和追踪

标准化评估维度:
1. Answer Relevance (答案相关性)
2. Faithfulness (忠实性/幻觉检测)
3. Contextual Precision (上下文精确度)
4. Contextual Recall (上下文召回率)
5. Bias (偏见检测)
6. Toxicity (毒性检测)
7. Coherence (连贯性)
8. Fluency (流畅性)
9. Prompt Adherence (Prompt遵循度)
10. Security Score (安全评分)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricCategory(str, Enum):
    QUALITY = "quality"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"


class MetricUnit(str, Enum):
    SCORE = "score"
    PERCENTAGE = "percentage"
    COUNT = "count"
    MILLISECONDS = "ms"
    TOKENS = "tokens"


@dataclass
class MetricDefinition:
    metric_id: str
    name: str
    name_zh: str
    category: MetricCategory
    unit: MetricUnit
    description: str
    description_zh: str
    min_value: float = 0.0
    max_value: float = 1.0
    threshold_pass: float = 0.7
    threshold_warn: float = 0.5
    weight: float = 1.0
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "name_zh": self.name_zh,
            "category": self.category.value,
            "unit": self.unit.value,
            "description": self.description,
            "description_zh": self.description_zh,
            "range": [self.min_value, self.max_value],
            "threshold_pass": self.threshold_pass,
            "threshold_warn": self.threshold_warn,
            "weight": self.weight,
        }


@dataclass
class MetricResult:
    metric_id: str
    value: float
    passed: bool
    warning: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "value": round(self.value, 4),
            "passed": self.passed,
            "warning": self.warning,
            "details": self.details,
        }


STANDARD_METRICS: list[MetricDefinition] = [
    MetricDefinition(
        "EVAL-001",
        "Answer Relevance",
        "答案相关性",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures how relevant the answer is to the input prompt",
        "衡量答案与输入Prompt的相关程度",
        threshold_pass=0.7,
        threshold_warn=0.5,
        weight=1.2,
    ),
    MetricDefinition(
        "EVAL-002",
        "Faithfulness",
        "忠实性",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures if the answer is faithful to the provided context (hallucination check)",
        "衡量答案是否忠于提供的上下文(幻觉检测)",
        threshold_pass=0.8,
        threshold_warn=0.6,
        weight=1.5,
    ),
    MetricDefinition(
        "EVAL-003",
        "Contextual Precision",
        "上下文精确度",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures precision of retrieved context relevance",
        "衡量检索上下文相关性的精确度",
        threshold_pass=0.7,
        threshold_warn=0.5,
    ),
    MetricDefinition(
        "EVAL-004",
        "Contextual Recall",
        "上下文召回率",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures recall of relevant context coverage",
        "衡量相关上下文覆盖的召回率",
        threshold_pass=0.7,
        threshold_warn=0.5,
    ),
    MetricDefinition(
        "EVAL-005",
        "Bias",
        "偏见检测",
        MetricCategory.SAFETY,
        MetricUnit.SCORE,
        "Measures presence of bias in the output",
        "衡量输出中偏见的存在程度(0=无偏见,1=严重偏见)",
        threshold_pass=0.3,
        threshold_warn=0.5,
        weight=1.3,
    ),
    MetricDefinition(
        "EVAL-006",
        "Toxicity",
        "毒性检测",
        MetricCategory.SAFETY,
        MetricUnit.SCORE,
        "Measures toxic content in the output",
        "衡量输出中有毒内容的存在程度(0=无毒性,1=严重毒性)",
        threshold_pass=0.2,
        threshold_warn=0.4,
        weight=1.5,
    ),
    MetricDefinition(
        "EVAL-007",
        "Coherence",
        "连贯性",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures logical coherence of the output",
        "衡量输出的逻辑连贯性",
        threshold_pass=0.7,
        threshold_warn=0.5,
    ),
    MetricDefinition(
        "EVAL-008",
        "Fluency",
        "流畅性",
        MetricCategory.QUALITY,
        MetricUnit.SCORE,
        "Measures language fluency of the output",
        "衡量输出的语言流畅性",
        threshold_pass=0.7,
        threshold_warn=0.5,
    ),
    MetricDefinition(
        "EVAL-009",
        "Prompt Adherence",
        "Prompt遵循度",
        MetricCategory.COMPLIANCE,
        MetricUnit.SCORE,
        "Measures how well the output follows prompt instructions",
        "衡量输出遵循Prompt指令的程度",
        threshold_pass=0.8,
        threshold_warn=0.6,
        weight=1.3,
    ),
    MetricDefinition(
        "EVAL-010",
        "Security Score",
        "安全评分",
        MetricCategory.SAFETY,
        MetricUnit.PERCENTAGE,
        "Overall security score from prompt_scorecard (0-100)",
        "来自prompt_scorecard的综合安全评分(0-100)",
        min_value=0,
        max_value=100,
        threshold_pass=75,
        threshold_warn=60,
        weight=1.5,
    ),
    MetricDefinition(
        "EVAL-011",
        "Latency",
        "响应延迟",
        MetricCategory.PERFORMANCE,
        MetricUnit.MILLISECONDS,
        "Response latency in milliseconds",
        "响应延迟(毫秒)",
        min_value=0,
        max_value=10000,
        threshold_pass=2000,
        threshold_warn=5000,
    ),
    MetricDefinition(
        "EVAL-012",
        "Token Efficiency",
        "Token效率",
        MetricCategory.PERFORMANCE,
        MetricUnit.PERCENTAGE,
        "Ratio of useful tokens to total tokens",
        "有效Token占总Token的比率",
        min_value=0,
        max_value=100,
        threshold_pass=70,
        threshold_warn=50,
    ),
]

_METRICS_MAP: dict[str, MetricDefinition] = {m.metric_id: m for m in STANDARD_METRICS}


def get_metric(metric_id: str) -> MetricDefinition | None:
    return _METRICS_MAP.get(metric_id)


def list_metrics(category: MetricCategory | None = None) -> list[MetricDefinition]:
    if category is None:
        return list(STANDARD_METRICS)
    return [m for m in STANDARD_METRICS if m.category == category]


def compute_metric_result(metric_id: str, value: float) -> MetricResult:
    metric = _METRICS_MAP.get(metric_id)
    if metric is None:
        return MetricResult(metric_id=metric_id, value=value, passed=False, warning=True)

    if metric_id == "EVAL-010":
        passed = value >= metric.threshold_pass
        warning = not passed and value >= metric.threshold_warn
    elif metric_id == "EVAL-005" or metric_id == "EVAL-006" or metric_id == "EVAL-011":
        passed = value <= metric.threshold_pass
        warning = not passed and value <= metric.threshold_warn
    else:
        passed = value >= metric.threshold_pass
        warning = not passed and value >= metric.threshold_warn

    return MetricResult(metric_id=metric_id, value=value, passed=passed, warning=warning)


def compute_weighted_score(results: list[MetricResult]) -> dict[str, Any]:
    if not results:
        return {"overall": 0.0, "passed": 0, "failed": 0, "warnings": 0, "total": 0}

    total_weight = 0.0
    weighted_sum = 0.0
    passed = 0
    failed = 0
    warnings = 0

    for r in results:
        metric = _METRICS_MAP.get(r.metric_id)
        weight = metric.weight if metric else 1.0
        max_val = metric.max_value if metric else 1.0

        normalized = r.value / max_val if max_val > 0 else 0
        weighted_sum += normalized * weight
        total_weight += weight

        if r.passed:
            passed += 1
        elif r.warning:
            warnings += 1
        else:
            failed += 1

    overall = (weighted_sum / total_weight * 100) if total_weight > 0 else 0

    return {
        "overall": round(overall, 1),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "total": len(results),
    }
