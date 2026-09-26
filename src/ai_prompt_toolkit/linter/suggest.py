"""修复建议智能推荐 — 根据Lint结果生成优先级排序的修复建议

功能:
- generate_suggestions: 从findings生成结构化修复建议
- Suggestion: 优先级+操作步骤+预估影响+相关规则
- 按严重度和出现频率排序
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.linter.rules import _RULE_MAP

if TYPE_CHECKING:
    from ai_prompt_toolkit.types import Finding

_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Suggestion:
    priority: int
    rule_id: str
    rule_name: str
    severity: str
    category: str
    remediation: str
    hit_count: int
    estimated_impact: str
    action_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "category": self.category,
            "remediation": self.remediation,
            "hit_count": self.hit_count,
            "estimated_impact": self.estimated_impact,
            "action_steps": self.action_steps,
        }


def _estimate_impact(severity: str, hit_count: int) -> str:
    if severity in ("critical", "high") and hit_count >= 3:
        return "高(关键安全问题, 多次触发)"
    elif severity in ("critical", "high"):
        return "高(关键安全问题)"
    elif severity == "medium" and hit_count >= 3:
        return "中(多次触发的质量问题)"
    elif severity == "medium":
        return "中(建议修复)"
    else:
        return "低(可选优化)"


def _extract_steps(remediation: str) -> list[str]:
    steps = []
    for part in remediation.split("，"):
        part = part.strip()
        if part:
            steps.append(part)
    if not steps:
        for part in remediation.split(","):
            part = part.strip()
            if part:
                steps.append(part)
    return steps[:5]


def generate_suggestions(findings: list[Finding], lang: str = "zh") -> list[Suggestion]:
    rule_counts: dict[str, int] = {}
    for f in findings:
        rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1
    suggestions = []
    for rid, count in rule_counts.items():
        rule = _RULE_MAP.get(rid)
        if not rule:
            continue
        sev = rule.severity.value
        cat = rule.category
        if lang == "en":
            rem = rule.remediation_en or rule.remediation
            name = rule.description_en or rule.name
        else:
            rem = rule.remediation
            name = rule.name
        priority = _PRIORITY_ORDER.get(sev, 3) * 100 - min(count, 10)
        suggestions.append(
            Suggestion(
                priority=priority,
                rule_id=rid,
                rule_name=name,
                severity=sev,
                category=cat,
                remediation=rem,
                hit_count=count,
                estimated_impact=_estimate_impact(sev, count),
                action_steps=_extract_steps(rem),
            )
        )
    suggestions.sort(key=lambda s: s.priority)
    return suggestions
