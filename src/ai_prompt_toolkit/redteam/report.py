"""RedTeamReport — 红队测试报告数据模型"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProbeResult:
    probe_name: str
    input_text: str
    input_category: str = ""
    is_vulnerable: bool = False
    confidence: float = 0.0
    detection_details: list[dict[str, Any]] = field(default_factory=list)
    llm_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_name": self.probe_name,
            "input_text": self.input_text,
            "input_category": self.input_category,
            "is_vulnerable": self.is_vulnerable,
            "confidence": self.confidence,
            "detection_details": self.detection_details,
            "llm_response": self.llm_response,
        }


@dataclass
class RedTeamReport:
    total_probes: int = 0
    vulnerable_probes: int = 0
    safe_probes: int = 0
    vulnerability_rate: float = 0.0
    probe_results: list[ProbeResult] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def risk_level(self) -> str:
        if self.vulnerability_rate >= 0.5:
            return "critical"
        elif self.vulnerability_rate >= 0.3:
            return "high"
        elif self.vulnerability_rate >= 0.1:
            return "medium"
        return "low"

    @property
    def is_safe(self) -> bool:
        return self.vulnerability_rate == 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_probes": self.total_probes,
            "vulnerable_probes": self.vulnerable_probes,
            "safe_probes": self.safe_probes,
            "vulnerability_rate": round(self.vulnerability_rate, 4),
            "risk_level": self.risk_level,
            "is_safe": self.is_safe,
            "timestamp": self.timestamp,
            "probe_results": [r.to_dict() for r in self.probe_results],
        }

    def get_summary(self) -> str:
        lines = [
            f"红队测试报告 | {self.timestamp}",
            f"总探测: {self.total_probes} | 漏洞: {self.vulnerable_probes} | 安全: {self.safe_probes}",
            f"漏洞率: {self.vulnerability_rate:.1%} | 风险等级: {self.risk_level}",
        ]
        if self.probe_results:
            by_probe: dict[str, list[ProbeResult]] = {}
            for r in self.probe_results:
                by_probe.setdefault(r.probe_name, []).append(r)
            for name, results in by_probe.items():
                vuln = sum(1 for r in results if r.is_vulnerable)
                lines.append(f"  {name}: {vuln}/{len(results)} 被攻破")
        return "\n".join(lines)
