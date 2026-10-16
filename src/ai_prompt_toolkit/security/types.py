"""安全扫描专用类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from ai_prompt_toolkit.types import Finding, Severity

# 显式再导出(R297/strict no_implicit_reexport): Finding/Severity 定义于顶层
# ai_prompt_toolkit.types, 本模块是其安全域再导出面
__all__ = ["Finding", "Severity"]


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    _RANK: ClassVar[dict[RiskLevel, int]]

    def __ge__(self, other: RiskLevel) -> bool:
        return self._RANK[self] >= self._RANK[other]

    def __gt__(self, other: RiskLevel) -> bool:
        return self._RANK[self] > self._RANK[other]

    def __le__(self, other: RiskLevel) -> bool:
        return not self.__gt__(other)

    def __lt__(self, other: RiskLevel) -> bool:
        return not self.__ge__(other)


RiskLevel._RANK = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


@dataclass
class InjectionRule:
    rule_id: str
    name: str
    pattern: str
    severity: Severity
    description: str
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "pattern": self.pattern,
            "severity": self.severity.value,
            "description": self.description,
            "remediation": self.remediation,
        }


@dataclass
class InheritanceFinding:
    template_id: str
    parent_id: str
    chain: list[str]
    depth: int
    risk_level: RiskLevel
    issue_type: str
    description: str
    remediation: str = ""

    def to_finding(self) -> Finding:
        severity_map = {
            RiskLevel.NONE: Severity.INFO,
            RiskLevel.LOW: Severity.LOW,
            RiskLevel.MEDIUM: Severity.MEDIUM,
            RiskLevel.HIGH: Severity.HIGH,
            RiskLevel.CRITICAL: Severity.CRITICAL,
        }
        return Finding(
            rule_id=f"INH-{self.issue_type}",
            severity=severity_map[self.risk_level],
            description=self.description,
            location=f"{self.template_id} -> {self.parent_id}",
            remediation=self.remediation,
            details={
                "chain": self.chain,
                "depth": self.depth,
                "risk_level": self.risk_level.value,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "parent_id": self.parent_id,
            "chain": self.chain,
            "depth": self.depth,
            "risk_level": self.risk_level.value,
            "issue_type": self.issue_type,
            "description": self.description,
            "remediation": self.remediation,
        }


@dataclass
class ScanResult:
    template_id: str
    risk_level: RiskLevel
    injection_findings: list[Finding] = field(default_factory=list)
    inheritance_findings: list[InheritanceFinding] = field(default_factory=list)
    template_hash: str = ""
    scan_time_ms: float = 0.0
    skipped: bool = False

    @property
    def all_findings(self) -> list[Finding]:
        results = list(self.injection_findings)
        for inh in self.inheritance_findings:
            results.append(inh.to_finding())
        return results

    @property
    def has_critical(self) -> bool:
        return any(f.severity == Severity.CRITICAL for f in self.all_findings)

    @property
    def has_high(self) -> bool:
        return any(f.severity == Severity.HIGH for f in self.all_findings)

    @property
    def finding_count(self) -> int:
        return len(self.all_findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "risk_level": self.risk_level.value,
            "injection_findings": [f.to_dict() for f in self.injection_findings],
            "inheritance_findings": [i.to_dict() for i in self.inheritance_findings],
            "template_hash": self.template_hash,
            "scan_time_ms": self.scan_time_ms,
            "skipped": self.skipped,
            "finding_count": self.finding_count,
        }
