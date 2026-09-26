"""A/B测试推荐器——胜率+显著性模式、综合评分模式、5条排除规则。"""

from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.statistics import auto_select_test
from ai_prompt_toolkit.ab_test.types import (
    ABTestConfig,
    EvaluationDimension,
    ModelResult,
    OptimalMatch,
    StatisticalReport,
    WinRateCell,
)


class Recommender:
    EXCLUSION_RULES = [
        {
            "id": "R001",
            "name": "成本超标排除",
            "description": "模型单次调用成本超过预算阈值时排除",
            "field": "cost",
            "threshold_key": "max_cost_per_call",
            "default_threshold": 0.5,
        },
        {
            "id": "R002",
            "name": "延迟超标排除",
            "description": "模型平均延迟超过阈值时排除",
            "field": "latency_ms",
            "threshold_key": "max_latency_ms",
            "default_threshold": 10000.0,
        },
        {
            "id": "R003",
            "name": "失败率过高排除",
            "description": "模型失败率超过阈值时排除",
            "field": "failure_rate",
            "threshold_key": "max_failure_rate",
            "default_threshold": 0.2,
        },
        {
            "id": "R004",
            "name": "效果不足排除",
            "description": "模型综合评分低于最低阈值时排除",
            "field": "overall_score",
            "threshold_key": "min_overall_score",
            "default_threshold": 5.0,
        },
        {
            "id": "R005",
            "name": "样本不足排除",
            "description": "有效测试样本数不足时排除该对比结果",
            "field": "sample_size",
            "threshold_key": "min_sample_size",
            "default_threshold": 10,
        },
    ]

    def __init__(
        self,
        config: ABTestConfig,
        *,
        thresholds: dict[str, Any] | None = None,
    ) -> None:
        self._config = config
        self._thresholds: dict[str, Any] = thresholds or {}
        self._excluded: list[dict[str, Any]] = []

    def _get_threshold(self, key: str, default: Any) -> Any:
        return self._thresholds.get(key, default)

    def _apply_exclusion_rules(
        self,
        model_stats: dict[str, dict[str, Any]],
    ) -> set[str]:
        excluded: set[str] = set()
        self._excluded = []

        for model_key, stats in model_stats.items():
            for rule in self.EXCLUSION_RULES:
                threshold = self._get_threshold(rule["threshold_key"], rule["default_threshold"])
                value = stats.get(rule["field"])

                if value is None:
                    continue

                if rule["id"] == "R003":
                    total = stats.get("total", 1)
                    failed = stats.get("failed", 0)
                    failure_rate = failed / max(total, 1)
                    if failure_rate > threshold:
                        excluded.add(model_key)
                        self._excluded.append(
                            {
                                "model": model_key,
                                "rule_id": rule["id"],
                                "reason": f"失败率 {failure_rate:.1%} > {threshold:.1%}",
                            }
                        )
                elif rule["id"] == "R005":
                    sample_size = stats.get("sample_size", 0)
                    if sample_size < threshold:
                        excluded.add(model_key)
                        self._excluded.append(
                            {
                                "model": model_key,
                                "rule_id": rule["id"],
                                "reason": f"样本量 {sample_size} < {threshold}",
                            }
                        )
                else:
                    if rule["field"] in ("cost", "latency_ms") and value > threshold:
                        excluded.add(model_key)
                        self._excluded.append(
                            {
                                "model": model_key,
                                "rule_id": rule["id"],
                                "reason": f"{rule['field']} {value} > {threshold}",
                            }
                        )
                    elif rule["field"] == "overall_score" and value < threshold:
                        excluded.add(model_key)
                        self._excluded.append(
                            {
                                "model": model_key,
                                "rule_id": rule["id"],
                                "reason": f"综合评分 {value} < {threshold}",
                            }
                        )

        return excluded

    def _build_model_stats(
        self,
        results: list[tuple[ModelResult, ModelResult]],
        dimensions: list[EvaluationDimension],
    ) -> dict[str, dict[str, Any]]:
        stats: dict[str, dict[str, Any]] = {}

        for result_a, result_b in results:
            for result in (result_a, result_b):
                key = f"{result.model_config.provider.value}:{result.model_config.model_name}"
                if key not in stats:
                    stats[key] = {
                        "total": 0,
                        "failed": 0,
                        "cost": 0.0,
                        "latency_ms": [],
                        "scores": {},
                        "sample_size": 0,
                        "model_config": result.model_config,
                        "overall_score": 0.0,
                    }

                entry = stats[key]
                entry["total"] += 1
                if result.status.value == "failed":
                    entry["failed"] += 1
                else:
                    entry["sample_size"] += 1
                    entry["cost"] += result.cost
                    entry["latency_ms"].append(result.latency_ms)
                    for dim_id, score in result.scores.items():
                        entry["scores"].setdefault(dim_id, []).append(score)

        for _key, entry in stats.items():
            avg_latency = sum(entry["latency_ms"]) / len(entry["latency_ms"]) if entry["latency_ms"] else 0.0
            entry["latency_ms"] = avg_latency

            weighted_sum = 0.0
            weight_total = 0.0
            for dim in dimensions:
                scores = entry["scores"].get(dim.dimension_id, [])
                if scores:
                    avg_score = sum(scores) / len(scores)
                    weighted_sum += avg_score * dim.weight
                    weight_total += dim.weight

            entry["overall_score"] = weighted_sum / weight_total if weight_total > 0 else 0.0

        return stats

    def recommend_by_win_rate(
        self,
        results: list[tuple[ModelResult, ModelResult]],
        dimensions: list[EvaluationDimension],
        *,
        significance_level: float = 0.05,
    ) -> list[OptimalMatch]:
        model_stats = self._build_model_stats(results, dimensions)
        excluded = self._apply_exclusion_rules(model_stats)

        win_counts: dict[str, dict[str, int]] = {}

        for result_a, result_b in results:
            key_a = f"{result_a.model_config.provider.value}:{result_a.model_config.model_name}"
            key_b = f"{result_b.model_config.provider.value}:{result_b.model_config.model_name}"

            if key_a in excluded and key_b in excluded:
                continue

            for dim in dimensions:
                score_a = result_a.scores.get(dim.dimension_id, 0.0)
                score_b = result_b.scores.get(dim.dimension_id, 0.0)

                dim_key = dim.dimension_id
                if key_a not in win_counts:
                    win_counts[key_a] = {}
                if key_b not in win_counts:
                    win_counts[key_b] = {}

                pair_key = f"{key_a}|{key_b}|{dim_key}"
                if pair_key not in win_counts[key_a]:
                    win_counts[key_a][pair_key] = 0
                if pair_key not in win_counts[key_b]:
                    win_counts[key_b][pair_key] = 0

                if score_a > score_b:
                    win_counts[key_a][pair_key] += 1
                elif score_b > score_a:
                    win_counts[key_b][pair_key] += 1

        model_wins: dict[str, int] = {}
        model_total: dict[str, int] = {}
        for key, pairs in win_counts.items():
            if key in excluded:
                continue
            for _pair_key, wins in pairs.items():
                model_wins[key] = model_wins.get(key, 0) + wins
                model_total[key] = model_total.get(key, 0) + max(wins, 1)

        recommendations: list[OptimalMatch] = []
        for key, stats in model_stats.items():
            if key in excluded:
                continue
            wins = model_wins.get(key, 0)
            total = model_total.get(key, 1)
            win_rate = wins / total if total > 0 else 0.0

            recommendations.append(
                OptimalMatch(
                    model_config=stats["model_config"],
                    prompt_template="",
                    scenario="win_rate",
                    dimensions=[d.dimension_id for d in dimensions],
                    overall_score=win_rate,
                    confidence=stats["overall_score"] / 10.0 if stats["overall_score"] <= 10 else 1.0,
                    reason=f"胜率 {win_rate:.1%}，综合评分 {stats['overall_score']:.2f}",
                )
            )

        recommendations.sort(key=lambda r: r.overall_score, reverse=True)
        return recommendations

    def recommend_by_score(
        self,
        results: list[tuple[ModelResult, ModelResult]],
        dimensions: list[EvaluationDimension],
        *,
        weights: dict[str, float] | None = None,
    ) -> list[OptimalMatch]:
        model_stats = self._build_model_stats(results, dimensions)
        excluded = self._apply_exclusion_rules(model_stats)

        recommendations: list[OptimalMatch] = []
        for key, stats in model_stats.items():
            if key in excluded:
                continue

            dim_scores: dict[str, float] = {}
            for dim in dimensions:
                scores = stats["scores"].get(dim.dimension_id, [])
                if scores:
                    dim_scores[dim.dimension_id] = sum(scores) / len(scores)

            overall = stats["overall_score"]
            cost_penalty = min(stats["cost"] * 10, 2.0)
            latency_penalty = min(stats["latency_ms"] / 10000.0, 1.0)
            adjusted = max(0.0, overall - cost_penalty - latency_penalty)

            recommendations.append(
                OptimalMatch(
                    model_config=stats["model_config"],
                    prompt_template="",
                    scenario="composite_score",
                    dimensions=list(dim_scores.keys()),
                    overall_score=round(adjusted, 4),
                    confidence=0.8 if stats["sample_size"] >= 30 else 0.5,
                    reason=(
                        f"综合评分 {overall:.2f}，成本扣减 {cost_penalty:.2f}，"
                        f"延迟扣减 {latency_penalty:.2f}，最终 {adjusted:.2f}"
                    ),
                )
            )

        recommendations.sort(key=lambda r: r.overall_score, reverse=True)
        return recommendations

    def recommend(
        self,
        results: list[tuple[ModelResult, ModelResult]],
        dimensions: list[EvaluationDimension] | None = None,
        *,
        mode: str = "win_rate",
        significance_level: float = 0.05,
    ) -> list[OptimalMatch]:
        dims = dimensions or self._config.dimensions

        if mode == "win_rate":
            return self.recommend_by_win_rate(results, dims, significance_level=significance_level)
        elif mode == "composite":
            return self.recommend_by_score(results, dims)
        else:
            raise ValueError(f"未知推荐模式: {mode!r}，可选: win_rate, composite")

    def build_report(
        self,
        results: list[tuple[ModelResult, ModelResult]],
        dimensions: list[EvaluationDimension] | None = None,
    ) -> StatisticalReport:
        dims = dimensions or self._config.dimensions
        model_stats = self._build_model_stats(results, dims)
        excluded = self._apply_exclusion_rules(model_stats)

        matrix: list[WinRateCell] = []
        model_keys = [k for k in model_stats if k not in excluded]

        for dim in dims:
            for i, key_a in enumerate(model_keys):
                for key_b in model_keys[i + 1 :]:
                    scores_a: list[float] = []
                    scores_b: list[float] = []

                    for result_a, result_b in results:
                        ra_key = f"{result_a.model_config.provider.value}:{result_a.model_config.model_name}"
                        rb_key = f"{result_b.model_config.provider.value}:{result_b.model_config.model_name}"

                        if ra_key == key_a and rb_key == key_b:
                            sa = result_a.scores.get(dim.dimension_id, 0.0)
                            sb = result_b.scores.get(dim.dimension_id, 0.0)
                            scores_a.append(sa)
                            scores_b.append(sb)
                        elif ra_key == key_b and rb_key == key_a:
                            sa = result_b.scores.get(dim.dimension_id, 0.0)
                            sb = result_a.scores.get(dim.dimension_id, 0.0)
                            scores_a.append(sa)
                            scores_b.append(sb)

                    if not scores_a:
                        continue

                    wins_a = sum(1 for a, b in zip(scores_a, scores_b) if a > b)
                    wins_b = sum(1 for a, b in zip(scores_a, scores_b) if b > a)
                    ties = len(scores_a) - wins_a - wins_b
                    total = len(scores_a)

                    stat_result = auto_select_test(scores_a, scores_b)

                    matrix.append(
                        WinRateCell(
                            model_a=key_a,
                            model_b=key_b,
                            dimension_id=dim.dimension_id,
                            wins_a=wins_a,
                            wins_b=wins_b,
                            ties=ties,
                            total=total,
                            win_rate_a=round(wins_a / total, 4) if total else 0.0,
                            win_rate_b=round(wins_b / total, 4) if total else 0.0,
                            significant=stat_result.get("significant", False),
                            p_value=stat_result.get("p_value", 1.0),
                        )
                    )

        import datetime

        win_rate_recs = self.recommend_by_win_rate(results, dims)
        score_recs = self.recommend_by_score(results, dims)

        recs_dicts = []
        for rec in win_rate_recs[:3]:
            recs_dicts.append({"mode": "win_rate", **rec.to_dict()})
        for rec in score_recs[:3]:
            recs_dicts.append({"mode": "composite", **rec.to_dict()})

        return StatisticalReport(
            test_id=self._config.test_id,
            total_tests=len(results),
            completed_tests=sum(
                1 for a, b in results if a.status.value == "completed" and b.status.value == "completed"
            ),
            failed_tests=sum(1 for a, b in results if a.status.value == "failed" or b.status.value == "failed"),
            win_rate_matrix=matrix,
            summary={
                "models_tested": len(model_keys),
                "models_excluded": len(excluded),
                "exclusion_details": self._excluded,
                "model_stats": {
                    k: {kk: vv for kk, vv in v.items() if kk != "model_config"} for k, v in model_stats.items()
                },
            },
            recommendations=recs_dicts,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
