"""Lint规则覆盖率导出 — lcov风格格式

功能:
- generate_lcov_report: 生成规则覆盖率lcov格式报告
- TN: 总规则数, FN: 命中(覆盖)数, DA: 每条规则命中详情
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.linter.rules import get_all_rules

if TYPE_CHECKING:
    from ai_prompt_toolkit.types import Finding


def generate_lcov_report(findings: list[Finding]) -> str:
    all_rules = get_all_rules()
    hit_rule_ids = set()
    rule_hit_counts: dict[str, int] = {}
    for f in findings:
        hit_rule_ids.add(f.rule_id)
        rule_hit_counts[f.rule_id] = rule_hit_counts.get(f.rule_id, 0) + 1
    total_rules = len(all_rules)
    hit_count = len(hit_rule_ids & {r.rule_id for r in all_rules})
    lines = []
    lines.append(f"TN:{total_rules}")
    lines.append(f"FN:{hit_count}")
    for rule in sorted(all_rules, key=lambda r: r.rule_id):
        rid = rule.rule_id
        is_hit = 1 if rid in hit_rule_ids else 0
        count = rule_hit_counts.get(rid, 0)
        lines.append(f"DA:{rid},{is_hit},{count}")
    lines.append("end_of_record")
    coverage_pct = hit_count / total_rules * 100 if total_rules > 0 else 0
    lines.append(f"# Coverage: {hit_count}/{total_rules} ({coverage_pct:.1f}%)")
    return "\n".join(lines)


def generate_coverage_summary(findings: list[Finding]) -> dict[str, Any]:
    all_rules = get_all_rules()
    hit_rule_ids = set()
    rule_hit_counts: dict[str, int] = {}
    for f in findings:
        hit_rule_ids.add(f.rule_id)
        rule_hit_counts[f.rule_id] = rule_hit_counts.get(f.rule_id, 0) + 1
    total = len(all_rules)
    hit = len(hit_rule_ids & {r.rule_id for r in all_rules})
    by_category: dict[str, dict[str, int]] = {}
    for rule in all_rules:
        cat = rule.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "hit": 0}
        by_category[cat]["total"] += 1
        if rule.rule_id in hit_rule_ids:
            by_category[cat]["hit"] += 1
    return {
        "total_rules": total,
        "hit_rules": hit,
        "coverage_pct": round(hit / total * 100, 1) if total > 0 else 0,
        "by_category": by_category,
    }
