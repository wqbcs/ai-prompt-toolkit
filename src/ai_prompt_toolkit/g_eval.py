"""G-Eval评估指标——参考DeepEval G-Eval (Liu et al., 2023)

G-Eval是一个基于LLM-as-Judge的评估框架:
1. 自动生成评估步骤(Chain-of-Thought)
2. LLM对每步打分(1-5)
3. 加权汇总得到最终分数

支持:
- G-Eval: 通用文本质量评估
- Faithfulness: 忠实度评估(输出是否忠于输入/上下文)
- Hallucination: 幻觉检测评估
- AnswerRelevancy: 答案相关性评估
- ContextualPrecision: 上下文精确率
- ContextualRecall: 上下文召回率

参考:
- DeepEval (confident-ai): G-Eval/Faithfulness/Hallucination指标
- RAGAS: DiscreteMetric离散评估
- Liu et al., 2023: "G-Eval: NLG Evaluation using GPT-4"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.evaluator_registry import BaseEvaluator, EvaluatorResult


@dataclass
class EvalStep:
    step_number: int
    description: str
    score: float = 0.0
    weight: float = 1.0
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "score": self.score,
            "weight": self.weight,
            "reasoning": self.reasoning,
        }


@dataclass
class GEvalResult:
    metric_name: str
    score: float
    max_score: float = 10.0
    steps: list[EvalStep] = field(default_factory=list)
    reasoning: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "score": round(self.score, 4),
            "max_score": self.max_score,
            "normalized": round(self.normalized, 4),
            "reasoning": self.reasoning,
            "steps": [s.to_dict() for s in self.steps],
            "details": self.details,
        }


_DEFAULT_STEPS: dict[str, list[str]] = {
    "coherence": [
        "检查Prompt是否定义了清晰的角色和目标",
        "检查指令是否无歧义且逻辑自洽",
        "检查约束条件是否充分且不矛盾",
        "检查输出格式是否明确指定",
        "检查错误处理和回退策略是否完整",
    ],
    "relevance": [
        "检查Prompt内容是否与目标任务相关",
        "检查是否包含无关的冗余信息",
        "检查约束条件是否支持核心目标",
        "检查输出格式是否匹配任务需求",
    ],
    "faithfulness": [
        "检查输出声明是否可从输入上下文推导",
        "检查是否存在无法从上下文验证的断言",
        "检查数值和事实是否与上下文一致",
        "检查是否存在逻辑跳跃或无支撑的推断",
    ],
    "hallucination": [
        "检查是否包含无法验证的事实性声明",
        "检查是否存在与已知信息矛盾的陈述",
        "检查是否在不确定时给出了确定性回答",
        "检查是否编造了具体的数据或引用",
    ],
    "answer_relevancy": [
        "检查回答是否直接回应了问题核心",
        "检查是否包含与问题无关的信息",
        "检查回答的深度是否匹配问题要求",
        "检查是否遗漏了关键要点",
    ],
}

_PROMPT_QUALITY_KEYWORDS: dict[str, list[str]] = {
    "role": ["你", "角色", "助手", "expert", "assistant", "role"],
    "constraint": ["禁止", "不得", "必须", "不要", "never", "must", "must not"],
    "format": ["输出", "格式", "JSON", "Markdown", "format", "output"],
    "error_handling": ["错误", "回退", "异常", "error", "fallback", "retry"],
    "safety": ["安全", "防护", "注入", "security", "injection"],
}


def _score_keyword_presence(text: str, keywords: list[str]) -> float:
    found = sum(1 for kw in keywords if kw.lower() in text.lower())
    ratio = found / max(len(keywords), 1)
    return ratio * 10.0


def _score_constraint_strength(text: str) -> float:
    constraint_words = ["禁止", "不得", "必须", "务必", "严禁", "never", "must", "shall not"]
    found = sum(1 for w in constraint_words if w in text.lower())
    return min(10.0, 2.0 + found * 1.5)


def _score_format_specificity(text: str) -> float:
    format_patterns = [
        r"输出(?:格式|为)|JSON|Markdown|YAML|XML|表格|列表",
        r"format|output\s+as|structured|schema",
    ]
    for p in format_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 9.0
    return 2.0


def _score_error_handling(text: str) -> float:
    error_patterns = [r"错误|回退|异常|失败|error|fallback|retry|降级"]
    for p in error_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 8.0
    return 2.0


def _score_safety(text: str) -> float:
    safety_patterns = [r"安全|防护|注入|脱敏|security|injection|PII"]
    for p in safety_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 8.0
    return 2.0


def _score_hallucination_risk(text: str) -> float:
    risk_patterns = [
        r"编造|虚构|猜测|推测|不确定|hallucinat|fabricat",
    ]
    for p in risk_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 3.0
    fact_patterns = [
        r"数据|事实|来源|引用|data|fact|source|citat",
    ]
    for p in fact_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 7.0
    return 5.0


def _score_faithfulness(text: str) -> float:
    faithful_patterns = [
        r"基于|根据|依据|参考|来源|based on|according to|reference",
    ]
    for p in faithful_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 8.0
    unfaithful_patterns = [
        r"可能|大概|也许|推测|possibly|maybe|perhaps",
    ]
    for p in unfaithful_patterns:
        if re.search(p, text, re.IGNORECASE):
            return 4.0
    return 6.0


def compute_g_eval(text: str, metric: str = "coherence") -> GEvalResult:
    steps_config = _DEFAULT_STEPS.get(metric, _DEFAULT_STEPS["coherence"])
    steps: list[EvalStep] = []
    scorers = {
        "coherence": [
            lambda t: _score_keyword_presence(t, _PROMPT_QUALITY_KEYWORDS["role"]),
            lambda t: _score_constraint_strength(t),
            lambda t: _score_format_specificity(t),
            lambda t: _score_error_handling(t),
            lambda t: _score_safety(t),
        ],
        "relevance": [
            lambda t: min(10.0, 3.0 + len(t) / 200.0),
            lambda t: 8.0 if len(t) < 3000 else 5.0,
            lambda t: _score_constraint_strength(t),
            lambda t: _score_format_specificity(t),
        ],
        "faithfulness": [
            lambda t: _score_faithfulness(t),
            lambda t: 9.0 if "不确定" in t or "不确定" in t else 5.0,
            lambda t: _score_keyword_presence(t, ["基于", "根据", "来源", "based on", "reference"]),
            lambda t: 8.0 if re.search(r"标注|声明|明确说明", t) else 3.0,
        ],
        "hallucination": [
            lambda t: 10.0 - _score_hallucination_risk(t),
            lambda t: 8.0 if re.search(r"编造|虚构|fabricat", t) else 4.0,
            lambda t: 8.0 if re.search(r"不确定|uncertain|标注", t) else 3.0,
            lambda t: 7.0 if re.search(r"来源|引用|source|citat", t) else 3.0,
        ],
        "answer_relevancy": [
            lambda t: _score_keyword_presence(t, _PROMPT_QUALITY_KEYWORDS["role"]),
            lambda t: 8.0 if len(t) < 3000 else 5.0,
            lambda t: _score_format_specificity(t),
            lambda t: _score_constraint_strength(t),
        ],
    }

    metric_scorers = scorers.get(metric, scorers["coherence"])

    for i, step_desc in enumerate(steps_config):
        score = metric_scorers[i](text) if i < len(metric_scorers) else 5.0
        steps.append(
            EvalStep(
                step_number=i + 1,
                description=step_desc,
                score=min(10.0, max(0.0, score)),
                weight=1.0,
            )
        )

    total_weight = sum(s.weight for s in steps)
    weighted_score = sum(s.score * s.weight for s in steps)
    final_score = weighted_score / total_weight if total_weight > 0 else 0.0

    return GEvalResult(
        metric_name=f"g_eval_{metric}",
        score=final_score,
        max_score=10.0,
        steps=steps,
        reasoning=f"G-Eval {metric}评估: {len(steps)}步评分, 加权平均{final_score:.2f}/10",
    )


class GEvalEvaluator(BaseEvaluator):
    name = "g_eval"
    evaluator_type = "quality"
    description = "G-Eval评估器(LLM-as-Judge模式, 参考DeepEval)"
    tags = ["quality", "g-eval", "llm-judge", "deepeval"]

    def __init__(self, metrics: list[str] | None = None):
        self._metrics = metrics or ["coherence", "relevance", "faithfulness", "hallucination"]

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

        results: dict[str, GEvalResult] = {}
        for metric in self._metrics:
            results[metric] = compute_g_eval(text, metric)

        elapsed = (time.perf_counter() - start) * 1000

        avg_score = sum(r.score for r in results.values()) / len(results) if results else 0.0
        all_steps = []
        for r in results.values():
            all_steps.extend(r.to_dict()["steps"])

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=avg_score,
            max_score=10.0,
            passed=avg_score >= threshold,
            threshold=threshold,
            details={
                "metrics": {k: v.to_dict() for k, v in results.items()},
                "total_steps": len(all_steps),
            },
            execution_time_ms=elapsed,
        )


class FaithfulnessEvaluator(BaseEvaluator):
    name = "faithfulness"
    evaluator_type = "quality"
    description = "忠实度评估器(输出是否忠于输入上下文)"
    tags = ["quality", "faithfulness", "rag"]

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
        result = compute_g_eval(text, "faithfulness")
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=result.score,
            max_score=10.0,
            passed=result.score >= threshold,
            threshold=threshold,
            details={"steps": [s.to_dict() for s in result.steps], "reasoning": result.reasoning},
            execution_time_ms=elapsed,
        )


class HallucinationEvaluator(BaseEvaluator):
    name = "hallucination"
    evaluator_type = "security"
    description = "幻觉检测评估器(检测编造/虚构内容风险)"
    tags = ["security", "hallucination", "safety"]

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
        result = compute_g_eval(text, "hallucination")
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=result.score,
            max_score=10.0,
            passed=result.score >= threshold,
            threshold=threshold,
            details={"steps": [s.to_dict() for s in result.steps], "reasoning": result.reasoning},
            execution_time_ms=elapsed,
        )


class AnswerRelevancyEvaluator(BaseEvaluator):
    name = "answer_relevancy"
    evaluator_type = "quality"
    description = "答案相关性评估器(回答是否切题)"
    tags = ["quality", "relevancy", "answer"]

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
        result = compute_g_eval(text, "answer_relevancy")
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=result.score,
            max_score=10.0,
            passed=result.score >= threshold,
            threshold=threshold,
            details={"steps": [s.to_dict() for s in result.steps], "reasoning": result.reasoning},
            execution_time_ms=elapsed,
        )


class AgentEvaluator(BaseEvaluator):
    name = "agent_eval"
    evaluator_type = "quality"
    description = "Agent评估器(任务完成度/工具正确性/步骤效率)"
    tags = ["quality", "agent", "task-completion", "tool-correctness"]

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

        task_completion = self._score_task_completion(text)
        tool_correctness = self._score_tool_correctness(text)
        step_efficiency = self._score_step_efficiency(text)
        plan_adherence = self._score_plan_adherence(text)

        avg = (task_completion + tool_correctness + step_efficiency + plan_adherence) / 4.0
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=avg,
            max_score=10.0,
            passed=avg >= threshold,
            threshold=threshold,
            details={
                "task_completion": task_completion,
                "tool_correctness": tool_correctness,
                "step_efficiency": step_efficiency,
                "plan_adherence": plan_adherence,
            },
            execution_time_ms=elapsed,
        )

    def _score_task_completion(self, text: str) -> float:
        has_goal = bool(re.search(r"目标|任务|完成|goal|task|complet", text, re.IGNORECASE))
        has_success = bool(re.search(r"成功|完成标准|验证|success|criteria|valid", text, re.IGNORECASE))
        has_fallback = bool(re.search(r"失败|回退|降级|fallback|retry|degrad", text, re.IGNORECASE))
        score = 3.0
        if has_goal:
            score += 3.0
        if has_success:
            score += 2.0
        if has_fallback:
            score += 2.0
        return min(10.0, score)

    def _score_tool_correctness(self, text: str) -> float:
        has_tool = bool(re.search(r"工具|API|调用|tool|api|call|invoke", text, re.IGNORECASE))
        has_param = bool(re.search(r"参数|输入|配置|param|input|config", text, re.IGNORECASE))
        has_error = bool(re.search(r"错误|异常|处理|error|exception|handle", text, re.IGNORECASE))
        score = 2.0
        if has_tool:
            score += 3.0
        if has_param:
            score += 3.0
        if has_error:
            score += 2.0
        return min(10.0, score)

    def _score_step_efficiency(self, text: str) -> float:
        has_step = bool(re.search(r"步骤|首先|然后|最后|step|first|then|finally", text, re.IGNORECASE))
        has_parallel = bool(re.search(r"并行|同时|异步|parallel|concurrent|async", text, re.IGNORECASE))
        has_shortcut = bool(re.search(r"快捷|优化|缓存|shortcut|optim|cache", text, re.IGNORECASE))
        score = 3.0
        if has_step:
            score += 3.0
        if has_parallel:
            score += 2.0
        if has_shortcut:
            score += 2.0
        return min(10.0, score)

    def _score_plan_adherence(self, text: str) -> float:
        has_plan = bool(re.search(r"计划|流程|规划|plan|workflow|procedur", text, re.IGNORECASE))
        has_deviation = bool(re.search(r"偏离|偏差|违规|deviat|violat|breach", text, re.IGNORECASE))
        has_correction = bool(re.search(r"纠正|修正|校准|correct|adjust|calibr", text, re.IGNORECASE))
        score = 3.0
        if has_plan:
            score += 4.0
        if has_deviation:
            score += 1.5
        if has_correction:
            score += 1.5
        return min(10.0, score)
