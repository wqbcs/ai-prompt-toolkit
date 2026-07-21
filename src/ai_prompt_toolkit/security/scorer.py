"""安全严重性评分体系——CVSS-like评分，区分Critical/High/Medium/Low。

参考: prompt-guard (严重性评分)、AegisGate (审计日志)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


class AttackVector(str, Enum):
    NETWORK = "network"
    LOCAL = "local"
    CONTEXT = "context"
    USER_INPUT = "user_input"


class AttackComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PrivilegesRequired(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"


class UserInteraction(str, Enum):
    NONE = "none"
    REQUIRED = "required"


class ImpactScope(str, Enum):
    UNCHANGED = "unchanged"
    CHANGED = "changed"


@dataclass
class SecurityScore:
    base_score: float
    impact_score: float
    exploitability_score: float
    severity: Severity
    attack_vector: AttackVector
    attack_complexity: AttackComplexity
    privileges_required: PrivilegesRequired
    user_interaction: UserInteraction
    scope: ImpactScope
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_score": round(self.base_score, 1),
            "impact_score": round(self.impact_score, 1),
            "exploitability_score": round(self.exploitability_score, 1),
            "severity": self.severity.value,
            "attack_vector": self.attack_vector.value,
            "attack_complexity": self.attack_complexity.value,
            "privileges_required": self.privileges_required.value,
            "user_interaction": self.user_interaction.value,
            "scope": self.scope.value,
            "rationale": self.rationale,
        }

    @property
    def severity_label(self) -> str:
        if self.base_score >= 9.0:
            return "CRITICAL"
        elif self.base_score >= 7.0:
            return "HIGH"
        elif self.base_score >= 4.0:
            return "MEDIUM"
        elif self.base_score > 0.0:
            return "LOW"
        return "INFO"


_RULE_SCORING: dict[str, dict[str, Any]] = {
    "INJ-001": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.85, "exploit": 0.85},
    "INJ-002": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.9, "exploit": 0.8},
    "INJ-003": {"av": AttackVector.NETWORK, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.95, "exploit": 0.85},
    "INJ-004": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.LOW, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.7, "exploit": 0.6},
    "INJ-005": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.75, "exploit": 0.7},
    "INJ-006": {"av": AttackVector.CONTEXT, "ac": AttackComplexity.HIGH, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.9, "exploit": 0.5},
    "INJ-007": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.95, "exploit": 0.9},
    "INJ-008": {"av": AttackVector.CONTEXT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.REQUIRED, "scope": ImpactScope.UNCHANGED, "impact": 0.8, "exploit": 0.65},
    "INJ-009": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.HIGH, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.7, "exploit": 0.55},
    "INJ-010": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.85, "exploit": 0.8},
    "INJ-011": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.8, "exploit": 0.85},
    "INJ-012": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.5, "exploit": 0.7},
    "INJ-013": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.HIGH, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.85, "exploit": 0.5},
    "INJ-014": {"av": AttackVector.CONTEXT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.6, "exploit": 0.55},
    "INJ-015": {"av": AttackVector.CONTEXT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.REQUIRED, "scope": ImpactScope.UNCHANGED, "impact": 0.55, "exploit": 0.5},
    "PII001": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.9, "exploit": 0.7},
    "INJ-016": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.75, "exploit": 0.65},
    "INJ-017": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.HIGH, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.7, "exploit": 0.6},
    "PII002": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.85, "exploit": 0.75},
    "PII003": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.8, "exploit": 0.7},
    "PII004": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.6, "exploit": 0.5},
    "PII005": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.5, "exploit": 0.4},
    "PII006": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.45, "exploit": 0.35},
    "PII007": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.5, "exploit": 0.4},
    "PII008": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.55, "exploit": 0.45},
    "PII009": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.UNCHANGED, "impact": 0.4, "exploit": 0.3},
    "PII010": {"av": AttackVector.LOCAL, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.65, "exploit": 0.55},
    "PII011": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.85, "exploit": 0.7},
    "PII012": {"av": AttackVector.LOCAL, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.9, "exploit": 0.8},
    "STRUCT-001": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.7, "exploit": 0.6},
    "ANOMALY-001": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.HIGH, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.6, "exploit": 0.5},
    "INJ-ZH-016": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.7, "exploit": 0.65},
    "INJ-ZH-017": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.MEDIUM, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.REQUIRED, "scope": ImpactScope.UNCHANGED, "impact": 0.55, "exploit": 0.5},
    "INJ-ZH-018": {"av": AttackVector.USER_INPUT, "ac": AttackComplexity.LOW, "pr": PrivilegesRequired.NONE, "ui": UserInteraction.NONE, "scope": ImpactScope.CHANGED, "impact": 0.75, "exploit": 0.7},
}


class SecurityScorer:
    def score(self, finding: Finding) -> SecurityScore:
        rule_id = finding.rule_id
        config = _RULE_SCORING.get(rule_id)

        if not config:
            return self._default_score(finding)

        impact_score = config["impact"] * 10
        exploitability_score = config["exploit"] * 10
        base_score = (impact_score * 0.6 + exploitability_score * 0.4)

        if base_score >= 9.0:
            severity = Severity.CRITICAL
        elif base_score >= 7.0:
            severity = Severity.HIGH
        elif base_score >= 4.0:
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        rationale = (
            f"攻击向量: {config['av'].value}, "
            f"攻击复杂度: {config['ac'].value}, "
            f"权限要求: {config['pr'].value}, "
            f"影响范围: {config['scope'].value}"
        )

        return SecurityScore(
            base_score=base_score,
            impact_score=impact_score,
            exploitability_score=exploitability_score,
            severity=severity,
            attack_vector=config["av"],
            attack_complexity=config["ac"],
            privileges_required=config["pr"],
            user_interaction=config["ui"],
            scope=config["scope"],
            rationale=rationale,
        )

    def score_batch(self, findings: list[Finding]) -> list[SecurityScore]:
        return [self.score(f) for f in findings]

    def overall_score(self, findings: list[Finding]) -> dict[str, Any]:
        if not findings:
            return {
                "total": 0,
                "max_score": 0.0,
                "avg_score": 0.0,
                "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                "top_risks": [],
            }

        scores = self.score_batch(findings)
        severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for s in scores:
            severity_dist[s.severity.value] = severity_dist.get(s.severity.value, 0) + 1

        sorted_scores = sorted(scores, key=lambda s: s.base_score, reverse=True)
        top_risks = [
            {
                "rule_id": findings[i].rule_id,
                "score": round(sorted_scores[i].base_score, 1),
                "description": findings[i].description[:80],
            }
            for i in range(min(5, len(findings)))
        ]

        return {
            "total": len(findings),
            "max_score": round(max(s.base_score for s in scores), 1),
            "avg_score": round(sum(s.base_score for s in scores) / len(scores), 1),
            "severity_distribution": severity_dist,
            "top_risks": top_risks,
        }

    def _default_score(self, finding: Finding) -> SecurityScore:
        sev_to_score = {
            Severity.CRITICAL: 9.5,
            Severity.HIGH: 7.5,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.5,
            Severity.INFO: 0.5,
        }
        score = sev_to_score.get(finding.severity, 2.0)
        return SecurityScore(
            base_score=score,
            impact_score=score * 0.6,
            exploitability_score=score * 0.4,
            severity=finding.severity,
            attack_vector=AttackVector.USER_INPUT,
            attack_complexity=AttackComplexity.MEDIUM,
            privileges_required=PrivilegesRequired.NONE,
            user_interaction=UserInteraction.NONE,
            scope=ImpactScope.UNCHANGED,
            rationale=f"基于规则严重性 {finding.severity.value} 的默认评分",
        )
