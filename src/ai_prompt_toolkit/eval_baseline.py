"""R204: 评估基线管理 — 维度级drift检测(Drift Sentinel)

与linter/baseline.py(findings级)互补: 本模块针对eval的130维度分数,
检测「行为漂移」— 同维度分数涨跌超阈值即为drift(信号而非故障)。

功能:
- save_eval_baseline: 保存评估快照(整体分+维度分+类别分)
- load_eval_baseline: 加载快照
- compare_eval_baseline: 维度级diff, 输出drifted维度(超阈值涨跌)
- EvalBaselineDiff: 整体/类别/维度三级对比统计
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# drift判定默认阈值: 维度分数(0-10)变化超过此值才报drift(降噪)
DEFAULT_DRIFT_THRESHOLD = 1.5
# 整体百分比变化阈值
DEFAULT_OVERALL_THRESHOLD = 2.0


@dataclass
class EvalBaselineSnapshot:
    created_at: str
    template_id: str
    overall_score: float
    percentage: float
    category_scores: dict[str, float] = field(default_factory=dict)
    # dimension_id -> score(0-10)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    preset: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "template_id": self.template_id,
            "overall_score": self.overall_score,
            "percentage": self.percentage,
            "category_scores": self.category_scores,
            "dimension_scores": self.dimension_scores,
            "preset": self.preset,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalBaselineSnapshot:
        return cls(
            created_at=data.get("created_at", ""),
            template_id=data.get("template_id", ""),
            overall_score=data.get("overall_score", 0.0),
            percentage=data.get("percentage", 0.0),
            category_scores=data.get("category_scores", {}),
            dimension_scores=data.get("dimension_scores", {}),
            preset=data.get("preset", "default"),
        )


@dataclass
class EvalBaselineDiff:
    baseline_overall: float = 0.0
    current_overall: float = 0.0
    overall_delta: float = 0.0
    overall_drift: bool = False
    # dimension_id -> {baseline, current, delta, direction: up|down}
    drifted_dimensions: dict[str, dict[str, Any]] = field(default_factory=dict)
    stable_dimensions: int = 0
    new_dimensions: list[str] = field(default_factory=list)
    removed_dimensions: list[str] = field(default_factory=list)
    category_deltas: dict[str, float] = field(default_factory=dict)
    is_regression: bool = False  # 整体下跌超阈值

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_overall": self.baseline_overall,
            "current_overall": self.current_overall,
            "overall_delta": self.overall_delta,
            "overall_drift": self.overall_drift,
            "drifted_dimensions": self.drifted_dimensions,
            "stable_dimensions": self.stable_dimensions,
            "new_dimensions": self.new_dimensions,
            "removed_dimensions": self.removed_dimensions,
            "category_deltas": self.category_deltas,
            "is_regression": self.is_regression,
        }


def _report_to_scores(reports: list[Any]) -> tuple[float, float, dict[str, float], dict[str, float]]:
    """从EvaluationReport列表聚合: 多文件时取均值"""
    if not reports:
        return 0.0, 0.0, {}, {}
    n = len(reports)
    overall = sum(r.overall_score for r in reports) / n
    percentage = sum(r.percentage for r in reports) / n
    dim_sums: dict[str, float] = {}
    for r in reports:
        for s in r.scores:
            dim_sums[s.dimension_id] = dim_sums.get(s.dimension_id, 0.0) + s.score
    dimension_scores = {k: v / n for k, v in dim_sums.items()}
    cat_sums: dict[str, float] = {}
    for r in reports:
        for k, v in r.category_scores.items():
            cat_sums[k] = cat_sums.get(k, 0.0) + v
    category_scores = {k: v / n for k, v in cat_sums.items()}
    return overall, percentage, category_scores, dimension_scores


def save_eval_baseline(
    reports: list[Any],
    path: str | Path,
    template_id: str = "",
    preset: str = "default",
) -> EvalBaselineSnapshot:
    overall, percentage, category_scores, dimension_scores = _report_to_scores(reports)
    snapshot = EvalBaselineSnapshot(
        created_at=datetime.now().isoformat(),
        template_id=template_id or (reports[0].template_id if reports else ""),
        overall_score=round(overall, 4),
        percentage=round(percentage, 2),
        category_scores={k: round(v, 4) for k, v in category_scores.items()},
        dimension_scores={k: round(v, 4) for k, v in dimension_scores.items()},
        preset=preset,
    )
    Path(path).write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def load_eval_baseline(path: str | Path) -> EvalBaselineSnapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return EvalBaselineSnapshot.from_dict(data)


def compare_eval_baseline(
    reports: list[Any],
    baseline: EvalBaselineSnapshot,
    drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
    overall_threshold: float = DEFAULT_OVERALL_THRESHOLD,
) -> EvalBaselineDiff:
    current_overall, _percentage, current_cats, current_dims = _report_to_scores(reports)
    overall_delta = round(current_overall - baseline.overall_score, 4)
    diff = EvalBaselineDiff(
        baseline_overall=baseline.overall_score,
        current_overall=round(current_overall, 4),
        overall_delta=overall_delta,
        overall_drift=abs(overall_delta) >= overall_threshold,
        is_regression=overall_delta <= -overall_threshold,
    )
    base_dims = baseline.dimension_scores
    for dim_id, cur_score in current_dims.items():
        base_score = base_dims.get(dim_id)
        if base_score is None:
            diff.new_dimensions.append(dim_id)
            continue
        delta = round(cur_score - base_score, 4)
        if abs(delta) > drift_threshold:
            diff.drifted_dimensions[dim_id] = {
                "baseline": base_score,
                "current": cur_score,
                "delta": delta,
                "direction": "down" if delta < 0 else "up",
            }
        else:
            diff.stable_dimensions += 1
    for dim_id in base_dims:
        if dim_id not in current_dims:
            diff.removed_dimensions.append(dim_id)
    for cat, cur_v in current_cats.items():
        base_v = baseline.category_scores.get(cat)
        if base_v is not None:
            diff.category_deltas[cat] = round(cur_v - base_v, 4)
    return diff
