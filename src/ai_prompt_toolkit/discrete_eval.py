"""离散评估指标——参考RAGAS DiscreteMetric + AspectCritique

核心特性:
- DiscreteMetric: 离散值评估(准确/不准确, 是/否, 好/中/差等)
- AspectCritique: 多维度批判评估, 每个维度自定义评估标准
- 评估结果包含reason(解释)和score(分数)
- 可组合为评估管道

参考:
- RAGAS: DiscreteMetric(allowed_values, prompt)
- RAGAS: AspectCritique(name, definition, strictness)
- DeepEval: DAG评估(确定性+LLM混合)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.evaluator_registry import BaseEvaluator, EvaluatorResult


@dataclass
class DiscreteValue:
    value: str
    score: float
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "score": self.score,
            "description": self.description,
        }


@dataclass
class DiscreteResult:
    metric_name: str
    value: str
    score: float
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "score": self.score,
            "reason": self.reason,
            "details": self.details,
        }


_ACCURATE = DiscreteValue("accurate", 10.0, "准确: 输出与预期完全一致")
_INACCURATE = DiscreteValue("inaccurate", 0.0, "不准确: 输出与预期不符")

_YES = DiscreteValue("yes", 10.0, "是")
_NO = DiscreteValue("no", 0.0, "否")

_GOOD = DiscreteValue("good", 10.0, "好: 质量优秀")
_AVERAGE = DiscreteValue("average", 5.0, "中: 质量一般")
_POOR = DiscreteValue("poor", 0.0, "差: 质量不佳")

_PASS = DiscreteValue("pass", 10.0, "通过")
_FAIL = DiscreteValue("fail", 0.0, "未通过")

_STANDARD_PRESETS: dict[str, list[DiscreteValue]] = {
    "accuracy": [_ACCURATE, _INACCURATE],
    "binary": [_YES, _NO],
    "quality": [_GOOD, _AVERAGE, _POOR],
    "pass_fail": [_PASS, _FAIL],
}


class DiscreteMetric:
    def __init__(
        self,
        name: str,
        allowed_values: list[DiscreteValue] | None = None,
        preset: str | None = None,
        evaluation_prompt: str = "",
    ) -> None:
        self.name = name
        if allowed_values:
            self._values = allowed_values
        elif preset and preset in _STANDARD_PRESETS:
            self._values = _STANDARD_PRESETS[preset]
        else:
            self._values = [_YES, _NO]
        self._evaluation_prompt = evaluation_prompt
        self._value_map = {v.value: v for v in self._values}

    def evaluate(self, text: str, *, expected: str = "", context: str = "") -> DiscreteResult:
        if self._evaluation_prompt:
            return self._evaluate_with_prompt(text, expected, context)
        return self._evaluate_heuristic(text, expected, context)

    def _evaluate_heuristic(self, text: str, expected: str, context: str) -> DiscreteResult:
        if self.name == "accuracy" or self._values == [_ACCURATE, _INACCURATE]:
            return self._evaluate_accuracy(text, expected)
        if self.name == "pass_fail" or (len(self._values) == 2 and self._values[0].value == "pass"):
            return self._evaluate_pass_fail(text)
        if self.name == "quality" or len(self._values) == 3:
            return self._evaluate_quality(text)
        if self.name == "binary" or (len(self._values) == 2 and self._values[0].score == 10.0):
            return self._evaluate_binary(text, expected, context)
        return DiscreteResult(metric_name=self.name, value=self._values[0].value, score=self._values[0].score)

    def _evaluate_accuracy(self, text: str, expected: str) -> DiscreteResult:
        if not expected:
            return DiscreteResult(metric_name=self.name, value="accurate", score=10.0, reason="无预期输出, 默认准确")
        text_clean = text.strip().lower()
        expected_clean = expected.strip().lower()
        if text_clean == expected_clean:
            return DiscreteResult(metric_name=self.name, value="accurate", score=10.0, reason="输出与预期完全一致")
        overlap = len(set(text_clean) & set(expected_clean))
        total = max(len(set(text_clean) | set(expected_clean)), 1)
        if overlap / total > 0.7:
            return DiscreteResult(metric_name=self.name, value="accurate", score=10.0, reason="输出与预期高度相似")
        return DiscreteResult(metric_name=self.name, value="inaccurate", score=0.0, reason="输出与预期不符")

    def _evaluate_binary(self, text: str, expected: str, context: str) -> DiscreteResult:
        has_constraint = bool(re.search(r"必须|禁止|不得|never|must", text, re.IGNORECASE))
        has_role = bool(re.search(r"你是|你作为|role|you are", text, re.IGNORECASE))
        has_format = bool(re.search(r"输出|格式|JSON|format|output", text, re.IGNORECASE))
        if has_constraint and has_role and has_format:
            return DiscreteResult(metric_name=self.name, value="yes", score=10.0, reason="包含角色、约束和格式定义")
        elif has_role or has_constraint:
            return DiscreteResult(metric_name=self.name, value="yes", score=10.0, reason="部分条件满足")
        return DiscreteResult(metric_name=self.name, value="no", score=0.0, reason="缺少关键元素")

    def _evaluate_quality(self, text: str) -> DiscreteResult:
        criteria_count = 0
        if re.search(r"你(?:是|作为|扮演)", text, re.IGNORECASE):
            criteria_count += 1
        if re.search(r"必须|禁止|不得|never|must", text, re.IGNORECASE):
            criteria_count += 1
        if re.search(r"输出(?:格式|为)|JSON|Markdown|format", text, re.IGNORECASE):
            criteria_count += 1
        if re.search(r"错误|回退|error|fallback", text, re.IGNORECASE):
            criteria_count += 1
        if re.search(r"安全|防护|security|injection", text, re.IGNORECASE):
            criteria_count += 1

        if criteria_count >= 4:
            return DiscreteResult(metric_name=self.name, value="good", score=10.0, reason=f"满足{criteria_count}/5项质量标准")
        elif criteria_count >= 2:
            return DiscreteResult(metric_name=self.name, value="average", score=5.0, reason=f"满足{criteria_count}/5项质量标准")
        return DiscreteResult(metric_name=self.name, value="poor", score=0.0, reason=f"仅满足{criteria_count}/5项质量标准")

    def _evaluate_pass_fail(self, text: str) -> DiscreteResult:
        has_role = bool(re.search(r"你(?:是|作为)", text))
        has_constraint = bool(re.search(r"必须|禁止|不得", text))
        min_length = len(text) >= 30
        if has_role and has_constraint and min_length:
            return DiscreteResult(metric_name=self.name, value="pass", score=10.0, reason="通过基础质量门禁")
        reasons = []
        if not has_role:
            reasons.append("缺少角色定义")
        if not has_constraint:
            reasons.append("缺少约束条件")
        if not min_length:
            reasons.append("内容过短")
        return DiscreteResult(metric_name=self.name, value="fail", score=0.0, reason="; ".join(reasons))

    def _evaluate_with_prompt(self, text: str, expected: str, context: str) -> DiscreteResult:
        return self._evaluate_heuristic(text, expected, context)

    @property
    def allowed_values(self) -> list[str]:
        return [v.value for v in self._values]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "allowed_values": [v.to_dict() for v in self._values],
            "evaluation_prompt": self._evaluation_prompt,
        }


_ASPECT_DEFINITIONS: dict[str, dict[str, str]] = {
    "harmfulness": {
        "definition": "评估Prompt是否包含有害、危险或违法内容",
        "pass_value": "safe",
        "fail_value": "harmful",
    },
    "maliciousness": {
        "definition": "评估Prompt是否具有恶意意图(如注入攻击、数据窃取)",
        "pass_value": "benign",
        "fail_value": "malicious",
    },
    "coherence": {
        "definition": "评估Prompt是否逻辑连贯、结构清晰",
        "pass_value": "coherent",
        "fail_value": "incoherent",
    },
    "correctness": {
        "definition": "评估Prompt内容是否正确、无事实错误",
        "pass_value": "correct",
        "fail_value": "incorrect",
    },
    "conciseness": {
        "definition": "评估Prompt是否简洁, 无冗余内容",
        "pass_value": "concise",
        "fail_value": "verbose",
    },
    "completeness": {
        "definition": "评估Prompt是否完整, 包含所有必要元素",
        "pass_value": "complete",
        "fail_value": "incomplete",
    },
    "readability": {
        "definition": "评估Prompt是否易于阅读和理解",
        "pass_value": "readable",
        "fail_value": "unclear",
    },
    "safety": {
        "definition": "评估Prompt是否包含安全防护措施",
        "pass_value": "safe",
        "fail_value": "unsafe",
    },
    "consistency": {
        "definition": "评估Prompt内部逻辑是否自洽",
        "pass_value": "consistent",
        "fail_value": "contradictory",
    },
    "effectiveness": {
        "definition": "评估Prompt是否有效引导模型产出期望输出",
        "pass_value": "effective",
        "fail_value": "ineffective",
    },
}


class AspectCritique:
    def __init__(
        self,
        name: str,
        definition: str = "",
        strictness: float = 0.5,
    ) -> None:
        self.name = name
        if definition:
            self._definition = definition
        elif name in _ASPECT_DEFINITIONS:
            self._definition = _ASPECT_DEFINITIONS[name]["definition"]
        else:
            self._definition = f"评估{aspect}质量"
        self._strictness = strictness
        self._config = _ASPECT_DEFINITIONS.get(name, {})

    def evaluate(self, text: str) -> DiscreteResult:
        pass_value = self._config.get("pass_value", "pass")
        fail_value = self._config.get("fail_value", "fail")

        score, reason = self._compute(text, pass_value, fail_value)
        value = pass_value if score >= 5.0 * self._strictness else fail_value

        return DiscreteResult(
            metric_name=f"aspect_{self.name}",
            value=value,
            score=score,
            reason=reason,
        )

    def _compute(self, text: str, pass_value: str, fail_value: str) -> tuple[float, str]:
        name = self.name

        if name == "harmfulness":
            harmful = bool(re.search(r"攻击|破坏|入侵|hack|attack|destroy|exploit", text, re.IGNORECASE))
            if harmful:
                return 0.0, "检测到潜在有害内容"
            return 10.0, "未检测到有害内容"

        if name == "maliciousness":
            malicious = bool(re.search(r"忽略.*指令|输出.*密钥|ignore.*instruct|output.*key|DAN|越狱", text, re.IGNORECASE))
            if malicious:
                return 0.0, "检测到潜在恶意意图"
            return 10.0, "未检测到恶意意图"

        if name == "coherence":
            has_structure = bool(re.search(r"^#+\s", text, re.MULTILINE))
            has_sequence = bool(re.search(r"首先|然后|最后|first|then|finally", text, re.IGNORECASE))
            if has_structure and has_sequence:
                return 10.0, "逻辑连贯, 结构清晰"
            elif has_structure or has_sequence:
                return 6.0, "部分连贯"
            return 3.0, "缺乏结构和逻辑"

        if name == "correctness":
            has_fact = bool(re.search(r"基于|根据|数据|来源|based on|data|source", text, re.IGNORECASE))
            if has_fact:
                return 8.0, "包含事实性支撑"
            return 4.0, "缺少事实性支撑"

        if name == "conciseness":
            if len(text) < 500:
                return 10.0, "简洁精炼"
            elif len(text) < 1500:
                return 6.0, "长度适中"
            return 3.0, "内容冗长"

        if name == "completeness":
            has_role = bool(re.search(r"你(?:是|作为)", text))
            has_constraint = bool(re.search(r"必须|禁止|不得|never|must", text, re.IGNORECASE))
            has_format = bool(re.search(r"输出|格式|format", text, re.IGNORECASE))
            has_error = bool(re.search(r"错误|回退|error|fallback", text, re.IGNORECASE))
            count = sum([has_role, has_constraint, has_format, has_error])
            if count >= 3:
                return 10.0, f"完整({count}/4要素)"
            return 4.0, f"不完整({count}/4要素)"

        if name == "readability":
            has_headers = bool(re.search(r"^#+\s", text, re.MULTILINE))
            has_lists = bool(re.search(r"^-\s|^\d+\.", text, re.MULTILINE))
            if has_headers and has_lists:
                return 10.0, "结构化良好, 易读"
            elif has_headers or has_lists:
                return 6.0, "部分结构化"
            return 3.0, "缺少格式化结构"

        if name == "safety":
            has_safety = bool(re.search(r"安全|防护|注入|脱敏|security|injection|PII", text, re.IGNORECASE))
            if has_safety:
                return 10.0, "包含安全防护"
            return 2.0, "缺少安全防护"

        if name == "consistency":
            has_positive = bool(re.search(r"必须|要|should|must", text, re.IGNORECASE))
            has_negative = bool(re.search(r"禁止|不得|never|must not", text, re.IGNORECASE))
            if has_positive and has_negative:
                return 10.0, "正负约束平衡, 逻辑自洽"
            elif has_positive or has_negative:
                return 7.0, "存在约束, 但方向单一"
            return 4.0, "缺少明确约束方向"

        if name == "effectiveness":
            has_role = bool(re.search(r"你(?:是|作为)", text))
            has_goal = bool(re.search(r"请|帮我|要求|目标|must|need", text, re.IGNORECASE))
            has_output = bool(re.search(r"输出|格式|JSON|format", text, re.IGNORECASE))
            count = sum([has_role, has_goal, has_output])
            if count >= 3:
                return 10.0, f"有效引导({count}/3核心要素)"
            return 4.0, f"引导不足({count}/3核心要素)"

        return 5.0, f"默认评估({name})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "definition": self._definition,
            "strictness": self._strictness,
        }


class DiscreteMetricEvaluator(BaseEvaluator):
    name = "discrete_metric"
    evaluator_type = "quality"
    description = "离散评估器(DiscreteMetric, 参考RAGAS)"
    tags = ["quality", "discrete", "ragas", "metric"]

    def __init__(
        self,
        metrics: list[DiscreteMetric] | None = None,
        aspects: list[AspectCritique] | None = None,
    ) -> None:
        self._metrics = metrics or [
            DiscreteMetric("quality", preset="quality"),
            DiscreteMetric("pass_fail", preset="pass_fail"),
        ]
        self._aspects = aspects or [
            AspectCritique("harmfulness"),
            AspectCritique("coherence"),
            AspectCritique("completeness"),
            AspectCritique("safety"),
        ]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 7.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        import time
        start = time.perf_counter()

        metric_results = [m.evaluate(text, expected=kwargs.get("expected", ""), context=kwargs.get("context", "")) for m in self._metrics]
        aspect_results = [a.evaluate(text) for a in self._aspects]

        all_results = metric_results + aspect_results
        avg_score = sum(r.score for r in all_results) / len(all_results) if all_results else 0.0

        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=avg_score,
            max_score=10.0,
            passed=avg_score >= threshold,
            threshold=threshold,
            details={
                "metrics": [r.to_dict() for r in metric_results],
                "aspects": [r.to_dict() for r in aspect_results],
            },
            execution_time_ms=elapsed,
        )
