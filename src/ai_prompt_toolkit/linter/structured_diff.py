"""结构化Lint对比输出 — JSON格式diff用于CI/CD集成

功能:
- generate_structured_diff: 生成结构化JSON diff报告
- 包含: 摘要/新增/修复/回归/规则级别统计/时间戳
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_prompt_toolkit.linter.baseline import BaselineDiff, BaselineSnapshot


def generate_structured_diff(
    diff: BaselineDiff,
    baseline: BaselineSnapshot,
    current_findings: list[dict[str, Any]],
    target: str = "",
) -> dict[str, Any]:
    current_rule_counts: dict[str, int] = {}
    for f in current_findings:
        rid = f.get("rule_id", "")
        current_rule_counts[rid] = current_rule_counts.get(rid, 0) + 1
    baseline_rule_counts: dict[str, int] = {}
    for f in baseline.findings:
        rid = f.get("rule_id", "")
        baseline_rule_counts[rid] = baseline_rule_counts.get(rid, 0) + 1
    all_rule_ids = sorted(set(current_rule_counts.keys()) | set(baseline_rule_counts.keys()))
    rule_level_stats = []
    for rid in all_rule_ids:
        bc = baseline_rule_counts.get(rid, 0)
        cc = current_rule_counts.get(rid, 0)
        rule_level_stats.append(
            {
                "rule_id": rid,
                "baseline_count": bc,
                "current_count": cc,
                "delta": cc - bc,
                "status": "fixed"
                if bc > 0 and cc == 0
                else "new"
                if bc == 0 and cc > 0
                else "regression"
                if cc > bc
                else "improved"
                if cc < bc
                else "unchanged",
            }
        )
    verdict = "PASS"
    if diff.is_regression:
        verdict = "FAIL"
    elif diff.delta < 0:
        verdict = "IMPROVED"
    elif diff.delta == 0:
        verdict = "PASS"
    return {
        "timestamp": datetime.now().isoformat(),
        "target": target,
        "verdict": verdict,
        "summary": {
            "baseline_total": diff.baseline_total,
            "current_total": diff.current_total,
            "delta": diff.delta,
            "new_count": len(diff.new_findings),
            "fixed_count": len(diff.fixed_findings),
            "regression_count": len(diff.regressions),
            "unchanged_count": len(diff.unchanged_findings),
        },
        "rule_level": rule_level_stats,
        "new_findings": diff.new_findings,
        "fixed_findings": diff.fixed_findings,
        "regressions": diff.regressions,
    }


def format_diff_json(diff_data: dict[str, Any], indent: int = 2) -> str:
    return json.dumps(diff_data, ensure_ascii=False, indent=indent)
