"""R212-5: 四维健康分 — Security/Quality/Completeness/Cost, A–F 总评级

参考 promptlint 的四维健康分设计(思路复用, 非代码复用): 单维安全评分无法支撑
"能不能上线"的决策 — 用户需要同时看到质量/完整性/成本面。

反指标膨胀纪律(奥卡姆剃刀): 四维分数全部机械派生自现有组件, 无新启发式、
无手调权重:
- Security     = PromptScorecard.overall_score (五维扣分制, 见 prompt_scorecard)
- Quality      = linter 的 lint_score (既有评分体系)
- Completeness = 6条关键结构规则(P001/P002/P003/P005/P025/P026)违反比例
                 → 100 * (1 - 违反数/总数); 该6条集合复用 scorecard 的
                 _STRUCTURE_RULE_IDS, 不新造规则集
- Cost         = token_analyzer 估算(default模型) → 单次调用成本 → 千次成本
                 → 分档打分(档位表见下, 文档化可审计, 非连续手调权重)

总评级 = 四维中最低档字母级(A–F): 短板决定可用性, 不平均(平均会掩盖短板)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_prompt_toolkit.types import Finding

# 分档表: 千次调用成本(USD)上限 → 分数。档位=离散审计点, 边界值取上限档。
# R212-5修正: 按实测千次成本分布校准(56干净样本+28内置模板: $1.24–$28.73,
# 中位$3.09, p25≈$1.5/p50≈$3.2/p75≈$14.3)。原表(≤$1全≥40分)是按错误量纲
# (单次成本误当千次)定的, 导致所有prompt恒落高档 → Cost维无区分度。
_COST_BANDS: list[tuple[float, int]] = [
    (2.00, 100),  # ≤$2/1k calls — 短prompt(<~130 tokens), 几乎可忽略
    (5.00, 80),  # ≤$5/1k — 常规prompt(至~320 tokens)
    (10.00, 60),  # ≤$10/1k — 中长(至~640 tokens)
    (20.00, 40),  # ≤$20/1k — 长模板(至~1280 tokens)
    (float("inf"), 20),  # >$20/1k — 超长prompt, 成本已成显著决策因素
]

# 关键结构规则集: 与 prompt_scorecard._STRUCTURE_RULE_IDS 同集合(单一事实源)
from ai_prompt_toolkit.security.prompt_scorecard import _STRUCTURE_RULE_IDS  # noqa: E402

_KEY_STRUCTURE_IDS: tuple[str, ...] = tuple(sorted(_STRUCTURE_RULE_IDS))


def letter_grade(score: int) -> str:
    """分数→字母级, 与 PromptScorecard 的 A–F 边界一致(90/75/60/40)"""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _cost_score(cost_per_1k_calls_usd: float) -> int:
    for ceiling, score in _COST_BANDS:
        if cost_per_1k_calls_usd <= ceiling:
            return score
    return 20


def _completeness_score(findings: list[Finding]) -> tuple[int, list[str]]:
    violated = [f.rule_id for f in findings if f.rule_id in _KEY_STRUCTURE_IDS]
    total = len(_KEY_STRUCTURE_IDS)
    score = round(100 * (1 - len(violated) / total))
    return max(0, score), sorted(set(violated))


def _security_score(findings: list[Finding], lint_score: float | None) -> int:
    """安全分: 从 findings 直接跑 scorecard 扣分制(与 score 命令同源)"""
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard

    card = compute_scorecard(findings, lint_score=lint_score)
    return card.overall_score


def compute_health_score(
    findings: list[Finding],
    lint_score: float | None,
    text: str,
    model: str = "default",
) -> dict[str, Any]:
    """计算四维健康分。返回:
    {
      "security": {"score": int, "grade": str},
      "quality": {"score": int, "grade": str},
      "completeness": {"score": int, "grade": str, "violated": [rule_ids]},
      "cost": {"score": int, "grade": str, "tokens": int,
               "cost_per_call_usd": float, "cost_per_1k_calls_usd": float, "model": str},
      "overall_grade": str,  # 四维最低档(短板决定)
    }
    """
    from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens

    security = _security_score(findings, lint_score)
    quality = round(max(0.0, min(100.0, lint_score))) if lint_score is not None else security
    completeness, violated = _completeness_score(findings)

    est = analyze_prompt_tokens(text, model).estimate
    # R212-5修正: token_analyzer的 estimated_input/output_cost_usd = tokens×单token单价,
    # 本身就是"单次调用"成本(非"每1K tokens成本")。原实现误除1000再乘1000,
    # 净效果把单次成本当千次成本, 千次成本低估1000倍 → Cost维恒100分(失真)。
    cost_per_call = est.estimated_input_cost_usd + est.estimated_output_cost_usd
    cost_per_1k_calls = cost_per_call * 1000.0
    cost = _cost_score(cost_per_1k_calls)

    dims = {
        "security": security,
        "quality": quality,
        "completeness": completeness,
        "cost": cost,
    }
    grades = {name: letter_grade(score) for name, score in dims.items()}
    # R212-5修正: 短板决定 — 取四维最低档(最小字母级)。原用max取最高档,
    # 与docstring/输出标签"短板决定总评级"矛盾(成本D+其余A会误判总评A)。
    # 弱环决定可用性: 任一维(尤其安全/成本)有致命短板, 整体不应评为A。
    order = ["F", "D", "C", "B", "A"]
    overall = order[min(order.index(grades[name]) for name in dims)]

    return {
        "security": {"score": security, "grade": grades["security"]},
        "quality": {"score": quality, "grade": grades["quality"]},
        "completeness": {"score": completeness, "grade": grades["completeness"], "violated": violated},
        "cost": {
            "score": cost,
            "grade": grades["cost"],
            "tokens": est.estimated_tokens,
            "cost_per_call_usd": round(cost_per_call, 8),
            "cost_per_1k_calls_usd": round(cost_per_1k_calls, 6),
            "model": model,
        },
        "overall_grade": overall,
    }
