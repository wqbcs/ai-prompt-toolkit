"""Prompt安全评分卡 — 0-100分综合评分系统

参考:
- OpenSSF Scorecard (开源项目安全评分)
- prompt-armor (决策引擎: ALLOW/WARN/BLOCK)
- NVIDIA garak (漏洞扫描评分)

评分维度:
1. Lint质量 (0-25分) — Prompt质量检查通过率
2. 注入防御 (0-25分) — 注入/越狱/角色切换检测
3. PII保护 (0-20分) — 个人隐私信息泄露检测
4. 结构健全性 (0-15分) — 角色定义/格式约束/回退策略
5. 供应链安全 (0-15分) — 外部引用/模板注入/编码绕过

评分等级:
- A (90-100): 生产级安全
- B (75-89): 良好, 少量改进
- C (60-74): 合格, 需要加固
- D (40-59): 不足, 存在风险
- F (0-39): 危险, 禁止上线
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class Decision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class DimensionScore:
    name: str
    max_points: int
    earned: int
    findings: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.earned / self.max_points if self.max_points > 0 else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "max_points": self.max_points,
            "earned": self.earned,
            "ratio": round(self.ratio, 2),
            "findings": self.findings[:5],
        }


@dataclass
class PromptScorecard:
    overall_score: int
    grade: Grade
    decision: Decision
    dimensions: list[DimensionScore]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "decision": self.decision.value,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "summary": self.summary,
        }


_SEVERITY_DEDUCTION = {
    Severity.CRITICAL: 15,
    Severity.HIGH: 8,
    Severity.MEDIUM: 4,
    Severity.LOW: 1,
    Severity.INFO: 0,
}

_LINT_RULE_IDS = {f"P{i:03d}" for i in range(1, 56)}
_INJECTION_RULE_PREFIXES = ("INJ-", "INJ-ZH-")
_PII_RULE_IDS = {"PII001", "PII002", "PII003"}
_STRUCTURE_RULE_IDS = {"P001", "P002", "P003", "P005", "P025", "P026"}
_SUPPLY_CHAIN_RULE_PREFIXES = ("SC", "UNI", "CANARY")


def _classify_rule(rule_id: str) -> str:
    if rule_id in _LINT_RULE_IDS:
        if rule_id in _STRUCTURE_RULE_IDS:
            return "structure"
        return "lint"
    if any(rule_id.startswith(p) for p in _INJECTION_RULE_PREFIXES):
        return "injection"
    if rule_id in _PII_RULE_IDS or "PII" in rule_id:
        return "pii"
    if any(rule_id.startswith(p) for p in _SUPPLY_CHAIN_RULE_PREFIXES):
        return "supply_chain"
    return "lint"


def compute_scorecard(
    findings: list[Finding],
    lint_score: float | None = None,
) -> PromptScorecard:
    buckets: dict[str, list[Finding]] = {
        "lint": [],
        "injection": [],
        "pii": [],
        "structure": [],
        "supply_chain": [],
    }
    for f in findings:
        category = _classify_rule(f.rule_id)
        buckets[category].append(f)

    dim_configs = [
        ("Lint质量", 25, "lint"),
        ("注入防御", 25, "injection"),
        ("PII保护", 20, "pii"),
        ("结构健全性", 15, "structure"),
        ("供应链安全", 15, "supply_chain"),
    ]

    dimensions: list[DimensionScore] = []
    total_earned = 0

    for name, max_pts, bucket_key in dim_configs:
        bucket_findings = buckets[bucket_key]
        deduction = sum(_SEVERITY_DEDUCTION.get(f.severity, 0) for f in bucket_findings)
        earned = max(0, max_pts - deduction)
        total_earned += earned
        finding_descs = [f"[{f.rule_id}] {f.description[:50]}" for f in bucket_findings[:5]]
        dimensions.append(DimensionScore(
            name=name, max_points=max_pts, earned=earned,
            findings=finding_descs,
        ))

    if lint_score is not None:
        lint_bonus = max(0, round(lint_score * 25 / 100))
        total_earned = total_earned - dimensions[0].earned + lint_bonus
        dimensions[0] = DimensionScore(
            name="Lint质量", max_points=25, earned=lint_bonus,
            findings=dimensions[0].findings,
        )

    overall = min(100, max(0, total_earned))

    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low = sum(1 for f in findings if f.severity in (Severity.LOW, Severity.INFO))

    if overall >= 90:
        grade = Grade.A
        decision = Decision.ALLOW
    elif overall >= 75:
        grade = Grade.B
        decision = Decision.ALLOW
    elif overall >= 60:
        grade = Grade.C
        decision = Decision.WARN
    elif overall >= 40:
        grade = Grade.D
        decision = Decision.WARN
    else:
        grade = Grade.F
        decision = Decision.BLOCK

    if critical > 0:
        decision = Decision.BLOCK
    elif high > 2:
        decision = Decision.WARN

    summary = f"评分 {overall}/100 ({grade.value}) — "
    if decision == Decision.ALLOW:
        summary += "可以安全上线"
    elif decision == Decision.WARN:
        summary += f"存在 {high}个高危+{medium}个中危问题，建议修复后上线"
    else:
        summary += f"存在 {critical}个严重+{high}个高危问题，禁止上线"

    return PromptScorecard(
        overall_score=overall,
        grade=grade,
        decision=decision,
        dimensions=dimensions,
        total_findings=len(findings),
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        summary=summary,
    )
