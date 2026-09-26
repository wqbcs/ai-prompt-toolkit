"""LLM-as-Judge评估模块

参考开源项目:
- FastChat/MT-Bench: 多维度评分rubric + 成对比较
- Prometheus(kaist-ai): 参考答案+Rubric绝对评分
- PairJudge: 位置去偏swap-debias
- Ragas: RAG专用评估维度

核心能力:
- 绝对评分(Absolute): 1-5分rubric评估
- 成对比较(Pairwise): A/B/Tie判断+位置去偏
- 多裁判(Multi-Judge): 多数投票+加权平均
- RAG专用维度: Faithfulness/Answer Relevancy/Context Precision/Recall
- 6大通用维度: Relevance/Accuracy/Fluency/Completeness/Safety/Helpfulness
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_prompt_toolkit.ab_test.provider import create_provider
from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType, TestStatus

logger = logging.getLogger(__name__)


class JudgeMode(Enum):
    ABSOLUTE = "absolute"
    PAIRWISE = "pairwise"


class AggregationMethod(Enum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    SWAP_DEBIAS = "swap_debias"


@dataclass
class JudgeDimension:
    dimension_id: str
    name: str
    description: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
        }


BUILTIN_DIMENSIONS: dict[str, JudgeDimension] = {
    "relevance": JudgeDimension("relevance", "相关性", "回答是否与问题相关", 1.0),
    "accuracy": JudgeDimension("accuracy", "准确性", "信息是否正确，有无幻觉", 1.5),
    "fluency": JudgeDimension("fluency", "流畅性", "语言是否自然流畅、逻辑连贯", 0.8),
    "completeness": JudgeDimension("completeness", "完整性", "是否全面覆盖了问题的各个方面", 1.0),
    "safety": JudgeDimension("safety", "安全性", "是否包含有害/偏见/不当内容", 2.0),
    "helpfulness": JudgeDimension("helpfulness", "有用性", "回答是否对用户有实际帮助", 1.2),
    "faithfulness": JudgeDimension("faithfulness", "忠实性", "RAG: 生成内容与检索上下文的一致性", 1.5),
    "answer_relevancy": JudgeDimension("answer_relevancy", "答案相关性", "RAG: 回答与问题的语义相关度", 1.0),
    "context_precision": JudgeDimension(
        "context_precision", "上下文精确度", "RAG: 检索上下文中相关信息的排名质量", 1.0
    ),
    "context_recall": JudgeDimension("context_recall", "上下文召回率", "RAG: 检索上下文对回答所需信息的覆盖度", 1.0),
}

_ABSOLUTE_RUBRIC = """请作为一名公正的评判者，评估AI助手对用户问题的回答质量。

[评估维度]: {dimension_name}
[评估标准]:
- 分数1（极差）: 完全不相关或存在严重事实错误
- 分数2（较差）: 部分相关但存在明显错误或遗漏
- 分数3（一般）: 基本相关但缺乏深度或细节
- 分数4（良好）: 相关且准确，仅有少量不足
- 分数5（优秀）: 完全相关、准确、全面、表达流畅

{reference_section}
[用户问题]: {question}
[AI回答]: {response}

请先给出分析理由，然后在最后一行输出分数，格式为: [[分数]]"""

_PAIRWISE_RUBRIC = """请比较两个AI助手对同一问题的回答，判断哪个更好。

[用户问题]: {question}
[助手A的回答]: {response_a}
[助手B的回答]: {response_b}

[评估标准]:
- 如果助手A明显更好，输出: [[A]]
- 如果助手B明显更好，输出: [[B]]
- 如果两者质量相当，输出: [[C]]

请从以下维度进行综合判断：相关性、准确性、完整性、流畅性、安全性。
注意：不要因为回答长度而偏好某一方，应关注回答的质量。
先给出分析理由，再输出判断结果。"""

_SCORE_PATTERN = re.compile(r"\[\[(\d+)\]\]")
_PAIR_PATTERN = re.compile(r"\[\[([ABC])\]\]", re.IGNORECASE)


@dataclass
class AbsoluteJudgeResult:
    dimension: JudgeDimension
    score: float
    reasoning: str = ""
    judge_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.to_dict(),
            "score": self.score,
            "reasoning": self.reasoning,
            "judge_model": self.judge_model,
        }


@dataclass
class PairwiseJudgeResult:
    winner: str
    confidence: float = 0.0
    reasoning: str = ""
    raw_scores_a: dict[str, float] = field(default_factory=dict)
    raw_scores_b: dict[str, float] = field(default_factory=dict)
    judge_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": self.winner,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "raw_scores_a": self.raw_scores_a,
            "raw_scores_b": self.raw_scores_b,
            "judge_model": self.judge_model,
        }


@dataclass
class MultiJudgeResult:
    mode: JudgeMode
    aggregation: AggregationMethod
    judge_count: int
    absolute_results: list[AbsoluteJudgeResult] = field(default_factory=list)
    pairwise_result: PairwiseJudgeResult | None = None
    aggregated_score: float = 0.0
    agreement_ratio: float = 0.0
    # F2: swap一致性 — 两个排列顺序下指向同一真实结论的裁判比例(1.0=完全一致)
    swap_consistency: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "aggregation": self.aggregation.value,
            "judge_count": self.judge_count,
            "absolute_results": [r.to_dict() for r in self.absolute_results],
            "pairwise_result": self.pairwise_result.to_dict() if self.pairwise_result else None,
            "aggregated_score": self.aggregated_score,
            "agreement_ratio": self.agreement_ratio,
            "swap_consistency": self.swap_consistency,
        }


class LLMJudge:
    def __init__(
        self,
        judge_config: ModelConfig,
        dimensions: list[JudgeDimension] | None = None,
        mode: JudgeMode = JudgeMode.ABSOLUTE,
        temperature: float = 0.0,
    ) -> None:
        self._judge_config = judge_config
        self._judge_config.temperature = temperature
        self._provider = create_provider(judge_config)
        self._dimensions = dimensions or list(BUILTIN_DIMENSIONS.values())[:6]
        self._mode = mode

    async def evaluate_absolute(
        self,
        question: str,
        response: str,
        reference_answer: str = "",
    ) -> list[AbsoluteJudgeResult]:
        results: list[AbsoluteJudgeResult] = []
        for dim in self._dimensions:
            ref_section = f"[参考答案]: {reference_answer}\n" if reference_answer else ""
            prompt = _ABSOLUTE_RUBRIC.format(
                dimension_name=dim.name,
                reference_section=ref_section,
                question=question,
                response=response,
            )
            model_result = await self._provider.invoke(prompt)
            if model_result.status != TestStatus.COMPLETED:
                results.append(
                    AbsoluteJudgeResult(
                        dimension=dim,
                        score=0.0,
                        reasoning=f"Judge调用失败: {model_result.error_message}",
                        judge_model=self._judge_config.model_name,
                    )
                )
                continue
            score, reasoning = self._parse_absolute(model_result.response)
            results.append(
                AbsoluteJudgeResult(
                    dimension=dim,
                    score=score,
                    reasoning=reasoning,
                    judge_model=self._judge_config.model_name,
                )
            )
        return results

    async def evaluate_pairwise(
        self,
        question: str,
        response_a: str,
        response_b: str,
    ) -> PairwiseJudgeResult:
        prompt = _PAIRWISE_RUBRIC.format(
            question=question,
            response_a=response_a,
            response_b=response_b,
        )
        model_result = await self._provider.invoke(prompt)
        if model_result.status != TestStatus.COMPLETED:
            return PairwiseJudgeResult(
                winner="C",
                confidence=0.0,
                reasoning=f"Judge调用失败: {model_result.error_message}",
                judge_model=self._judge_config.model_name,
            )
        winner, reasoning = self._parse_pairwise(model_result.response)
        return PairwiseJudgeResult(
            winner=winner,
            confidence=1.0,
            reasoning=reasoning,
            judge_model=self._judge_config.model_name,
        )

    def _parse_absolute(self, text: str) -> tuple[float, str]:
        match = _SCORE_PATTERN.search(text)
        if match:
            score = float(match.group(1))
            score = max(1.0, min(5.0, score))
        else:
            score = 3.0
        reasoning = text[: match.start()].strip() if match else text.strip()
        return score, reasoning

    def _parse_pairwise(self, text: str) -> tuple[str, str]:
        match = _PAIR_PATTERN.search(text)
        if match:
            winner = match.group(1).upper()
            if winner == "C":
                winner = "C"
        else:
            winner = "C"
        reasoning = text[: match.start()].strip() if match else text.strip()
        return winner, reasoning


class MultiJudgeEnsemble:
    def __init__(
        self,
        judge_configs: list[ModelConfig],
        dimensions: list[JudgeDimension] | None = None,
        mode: JudgeMode = JudgeMode.ABSOLUTE,
        aggregation: AggregationMethod = AggregationMethod.MAJORITY_VOTE,
        weights: list[float] | None = None,
    ) -> None:
        self._judges = [LLMJudge(cfg, dimensions, mode) for cfg in judge_configs]
        self._mode = mode
        self._aggregation = aggregation
        self._weights = weights or [1.0] * len(judge_configs)

    async def evaluate_absolute(
        self,
        question: str,
        response: str,
        reference_answer: str = "",
    ) -> MultiJudgeResult:
        all_results: list[list[AbsoluteJudgeResult]] = await asyncio.gather(
            *[judge.evaluate_absolute(question, response, reference_answer) for judge in self._judges]
        )

        dim_count = len(all_results[0]) if all_results else 0
        aggregated: list[AbsoluteJudgeResult] = []
        total_agreement = 0
        total_comparisons = 0

        for d in range(dim_count):
            dim_results = [r[d] for r in all_results if d < len(r)]
            if not dim_results:
                continue

            dim = dim_results[0].dimension
            scores = [r.score for r in dim_results]

            if self._aggregation == AggregationMethod.WEIGHTED_AVERAGE:
                weighted = sum(s * w for s, w in zip(scores, self._weights[: len(scores)]))
                avg = weighted / sum(self._weights[: len(scores)])
            else:
                rounded = [round(s) for s in scores]
                counts = Counter(rounded)
                mode_score = counts.most_common(1)[0][0]
                avg = mode_score

                total_comparisons += len(scores) * (len(scores) - 1) // 2
                for i in range(len(rounded)):
                    for j in range(i + 1, len(rounded)):
                        if rounded[i] == rounded[j]:
                            total_agreement += 1

            reasoning_combined = " | ".join(r.reasoning[:100] for r in dim_results[:3])
            aggregated.append(
                AbsoluteJudgeResult(
                    dimension=dim,
                    score=round(avg, 2),
                    reasoning=reasoning_combined,
                    judge_model=f"ensemble({len(self._judges)})",
                )
            )

        overall = (
            sum(r.score * r.dimension.weight for r in aggregated) / max(sum(r.dimension.weight for r in aggregated), 1)
            if aggregated
            else 0.0
        )

        agreement_ratio = total_agreement / max(total_comparisons, 1)

        return MultiJudgeResult(
            mode=self._mode,
            aggregation=self._aggregation,
            judge_count=len(self._judges),
            absolute_results=aggregated,
            aggregated_score=round(overall, 2),
            agreement_ratio=round(agreement_ratio, 2),
        )

    async def evaluate_pairwise(
        self,
        question: str,
        response_a: str,
        response_b: str,
    ) -> MultiJudgeResult:
        if self._aggregation == AggregationMethod.SWAP_DEBIAS:
            return await self._evaluate_pairwise_swap_debias(question, response_a, response_b)

        results = await asyncio.gather(
            *[judge.evaluate_pairwise(question, response_a, response_b) for judge in self._judges]
        )

        verdicts = [r.winner for r in results]
        if self._aggregation == AggregationMethod.MAJORITY_VOTE:
            counts = Counter(verdicts)
            winner = counts.most_common(1)[0][0]
        else:
            score_map = {"A": 1.0, "B": -1.0, "C": 0.0}
            weighted = sum(score_map.get(v, 0.0) * w for v, w in zip(verdicts, self._weights[: len(verdicts)]))
            if weighted > 0.5:
                winner = "A"
            elif weighted < -0.5:
                winner = "B"
            else:
                winner = "C"

        total = len(verdicts)
        agreement = sum(1 for v in verdicts if v == winner)
        agreement_ratio = agreement / max(total, 1)

        best_result = next((r for r in results if r.winner == winner), results[0])

        return MultiJudgeResult(
            mode=self._mode,
            aggregation=self._aggregation,
            judge_count=len(self._judges),
            pairwise_result=PairwiseJudgeResult(
                winner=winner,
                confidence=round(agreement_ratio, 2),
                reasoning=best_result.reasoning,
                judge_model=f"ensemble({len(self._judges)})",
            ),
            agreement_ratio=round(agreement_ratio, 2),
        )

    async def _evaluate_pairwise_swap_debias(
        self,
        question: str,
        response_a: str,
        response_b: str,
    ) -> MultiJudgeResult:
        ab_results = await asyncio.gather(
            *[judge.evaluate_pairwise(question, response_a, response_b) for judge in self._judges]
        )
        ba_results = await asyncio.gather(
            *[judge.evaluate_pairwise(question, response_b, response_a) for judge in self._judges]
        )

        score_map = {"A": 1.0, "B": -1.0, "C": 0.0}
        debiased_scores: list[float] = []
        inconsistent_count = 0

        for ab, ba in zip(ab_results, ba_results):
            ab_score = score_map.get(ab.winner, 0.0)
            ba_score = score_map.get(ba.winner, 0.0)
            debiased = (ab_score - ba_score) / 2.0
            debiased_scores.append(debiased)
            # F2 swap一致性过滤(Shi et al./Xu et al.): 两序同标签=裁判只偏好呈现位置
            # (如AB序选A且BA序也选A), 该判定是位置偏置伪影而非质量结论
            if ab_score != 0.0 and ab_score == ba_score:
                inconsistent_count += 1

        swap_consistency = 1.0 - inconsistent_count / max(len(debiased_scores), 1)
        avg_debiased = sum(debiased_scores) / max(len(debiased_scores), 1)
        if avg_debiased > 0.1:
            winner = "A"
        elif avg_debiased < -0.1:
            winner = "B"
        else:
            winner = "C"

        confidence = min(abs(avg_debiased) / 0.5, 1.0) * swap_consistency

        return MultiJudgeResult(
            mode=self._mode,
            aggregation=self._aggregation,
            judge_count=len(self._judges),
            pairwise_result=PairwiseJudgeResult(
                winner=winner,
                confidence=round(confidence, 2),
                reasoning=(
                    f"Swap-Debias平均偏移: {avg_debiased:.3f} | "
                    f"swap一致性: {swap_consistency:.0%}"
                    + (f" (位置偏置伪影: {inconsistent_count}个判定)" if inconsistent_count else "")
                ),
                judge_model=f"ensemble-swap({len(self._judges)})",
            ),
            agreement_ratio=round(confidence, 2),
            swap_consistency=round(swap_consistency, 2),
        )


class StableJudge:
    """F4: Flaky判定稳定性包装器 — 对方差大的LLM裁判判定自动重试取多数决

    借鉴DeepEval v4.1与promptfoo的flaky retry实践: LLM裁判对同一输入的判定存在
    随机方差, 单次判定不可靠; 对同一输入执行(1+retries)次, 多数决取结论,
    置信度=多数票占比。判定分歧严重(无多数)时降为C/中性并标注flaky。

    与LLMJudge/MultiJudgeEnsemble同接口(duck-typing), 可透明替换。
    """

    def __init__(self, judge: Any, retries: int = 2) -> None:
        self._judge = judge
        self._retries = max(retries, 0)

    @property
    def wrapped_judge(self) -> Any:
        return self._judge

    async def evaluate_pairwise(self, question: str, response_a: str, response_b: str) -> PairwiseJudgeResult:
        results = [
            await self._judge.evaluate_pairwise(question, response_a, response_b) for _ in range(1 + self._retries)
        ]
        winners = [r.winner for r in results]
        counts = Counter(winners)
        winner, votes = counts.most_common(1)[0]
        agreement = votes / len(winners)
        has_majority = votes > len(winners) / 2
        final = winner if has_majority else "C"
        best = next(r for r in results if r.winner == final) if has_majority else results[0]
        note = f"[stable {votes}/{len(winners)}]" if has_majority else f"[flaky 无多数: {winners}]"
        return PairwiseJudgeResult(
            winner=final,
            confidence=round(agreement, 2),
            reasoning=f"{note} {best.reasoning}".strip(),
            judge_model=getattr(best, "judge_model", "") or f"stable({1 + self._retries}x)",
        )

    async def evaluate_absolute(
        self,
        question: str,
        response: str,
        reference_answer: str = "",
    ) -> list[AbsoluteJudgeResult]:
        runs = [
            await self._judge.evaluate_absolute(question, response, reference_answer) for _ in range(1 + self._retries)
        ]
        if not runs:
            return []
        aggregated: list[AbsoluteJudgeResult] = []
        for d, dim_result in enumerate(runs[0]):
            scores = [r[d].score for r in runs if d < len(r)]
            rounded = [round(s) for s in scores]
            counts = Counter(rounded)
            majority_score, votes = counts.most_common(1)[0]
            note = f"[stable {votes}/{len(scores)}]" if votes > len(scores) / 2 else f"[flaky 分歧: {rounded}]"
            aggregated.append(
                AbsoluteJudgeResult(
                    dimension=dim_result.dimension,
                    score=round(sum(scores) / len(scores), 2) if votes <= len(scores) / 2 else float(majority_score),
                    reasoning=f"{note} {dim_result.reasoning[:80]}".strip(),
                    judge_model=f"stable({1 + self._retries}x)",
                )
            )
        return aggregated


def create_judge(
    judge_model: str = "gpt-4o-mini",
    provider: str = "openai",
    dimensions: list[str] | None = None,
    mode: str = "absolute",
    flaky_retries: int = 0,
) -> LLMJudge | StableJudge:
    try:
        pt = ProviderType(provider)
    except ValueError:
        pt = ProviderType.OPENAI
    config = ModelConfig(provider=pt, model_name=judge_model, temperature=0.0)
    dims = [BUILTIN_DIMENSIONS[d] for d in dimensions if d in BUILTIN_DIMENSIONS] if dimensions else None
    judge = LLMJudge(config, dims, JudgeMode(mode))
    return StableJudge(judge, flaky_retries) if flaky_retries > 0 else judge


def create_multi_judge(
    judge_models: list[dict[str, str]],
    dimensions: list[str] | None = None,
    mode: str = "absolute",
    aggregation: str = "majority_vote",
    weights: list[float] | None = None,
    flaky_retries: int = 0,
) -> MultiJudgeEnsemble | StableJudge:
    configs: list[ModelConfig] = []
    for m in judge_models:
        try:
            pt = ProviderType(m.get("provider", "openai"))
        except ValueError:
            pt = ProviderType.OPENAI
        configs.append(ModelConfig(provider=pt, model_name=m.get("model", "gpt-4o-mini"), temperature=0.0))

    dims = [BUILTIN_DIMENSIONS[d] for d in dimensions if d in BUILTIN_DIMENSIONS] if dimensions else None
    ensemble = MultiJudgeEnsemble(configs, dims, JudgeMode(mode), AggregationMethod(aggregation), weights)
    return StableJudge(ensemble, flaky_retries) if flaky_retries > 0 else ensemble
