"""通用类型定义"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, ClassVar


class Severity(Enum):
    """严重程度枚举"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    _RANK: ClassVar[dict[Severity, int]]

    def __ge__(self, other: Severity) -> bool:
        return self._RANK[self] >= self._RANK[other]

    def __gt__(self, other: Severity) -> bool:
        return self._RANK[self] > self._RANK[other]

    def __le__(self, other: Severity) -> bool:
        return not self.__gt__(other)

    def __lt__(self, other: Severity) -> bool:
        return not self.__ge__(other)


Severity._RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class ReportStatus(Enum):
    """报告状态枚举"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    PASSED = "passed"


@dataclass
class Finding:
    """通用发现项"""
    rule_id: str
    severity: Severity
    description: str
    location: str = ""
    remediation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "remediation": self.remediation,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        return cls(
            rule_id=data["rule_id"],
            severity=Severity(data["severity"]),
            description=data["description"],
            location=data.get("location", ""),
            remediation=data.get("remediation", ""),
            details=data.get("details", {}),
        )


@dataclass
class BaseReport:
    """通用报告基类"""
    timestamp: str
    template_id: str
    status: ReportStatus
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "template_id": self.template_id,
            "status": self.status.value,
            "details": self.details,
            "warnings": self.warnings,
            "findings": [f.to_dict() for f in self.findings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseReport":
        return cls(
            timestamp=data["timestamp"],
            template_id=data["template_id"],
            status=ReportStatus(data["status"]),
            details=data.get("details", {}),
            warnings=data.get("warnings", []),
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
        )
