"""Verdict-based Quality Gate——CI集成模式，按verdict决定是否通过。

参考: lintlang的verdict-based gating机制
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


class Verdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# D4: verdict→退出码唯一映射 — CLI/MCP/CI必须经此函数取退出码, 保证语义一致
# (0=PASS, 1=WARN, 2=FAIL; 3=ERROR 属于执行层异常, 不由verdict产生)
VERDICT_EXIT_CODES: dict[Verdict, int] = {
    Verdict.PASS: 0,
    Verdict.WARN: 1,
    Verdict.FAIL: 2,
}


def verdict_to_exit_code(verdict: Verdict) -> int:
    return VERDICT_EXIT_CODES[verdict]


@dataclass
class QualityGateResult:
    verdict: Verdict
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    score: float
    gate_rules: dict[str, Any]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "score": self.score,
            "gate_rules": self.gate_rules,
            "summary": self.summary,
        }


DEFAULT_GATE_CONFIG: dict[str, Any] = {
    "fail_on_critical": True,
    "fail_on_high": True,
    "fail_on_high_count": 0,
    "warn_on_medium": True,
    "warn_on_medium_count": 3,
    "min_score": 60.0,
    "fail_rule_ids": [],
    "warn_rule_ids": [],
}


class QualityGate:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = {**DEFAULT_GATE_CONFIG, **(config or {})}

    def evaluate(self, findings: list[Finding], score: float = 100.0) -> QualityGateResult:
        counts = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 0,
            Severity.MEDIUM: 0,
            Severity.LOW: 0,
            Severity.INFO: 0,
        }
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        verdict = Verdict.PASS
        reasons: list[str] = []

        if self._config.get("fail_on_critical") and counts[Severity.CRITICAL] > 0:
            verdict = Verdict.FAIL
            reasons.append(f"发现 {counts[Severity.CRITICAL]} 个严重(Critical)问题")

        if verdict != Verdict.FAIL and self._config.get("fail_on_high") and counts[Severity.HIGH] > (self._config.get("fail_on_high_count", 0)):
            verdict = Verdict.FAIL
            reasons.append(f"发现 {counts[Severity.HIGH]} 个高级(High)问题")

        fail_rule_ids = set(self._config.get("fail_rule_ids", []))
        for f in findings:
            if f.rule_id in fail_rule_ids:
                verdict = Verdict.FAIL
                reasons.append(f"规则 {f.rule_id} 触发FAIL门禁")
                break

        if verdict == Verdict.PASS and self._config.get("warn_on_medium") and counts[Severity.MEDIUM] > (self._config.get("warn_on_medium_count", 3)):
            verdict = Verdict.WARN
            reasons.append(f"发现 {counts[Severity.MEDIUM]} 个中级(Medium)问题，超过告警阈值")

        if verdict == Verdict.PASS and score < self._config.get("min_score", 60.0):
            verdict = Verdict.WARN
            reasons.append(f"评分 {score} 低于最低要求 {self._config['min_score']}")

        warn_rule_ids = set(self._config.get("warn_rule_ids", []))
        for f in findings:
            if f.rule_id in warn_rule_ids and verdict == Verdict.PASS:
                verdict = Verdict.WARN
                reasons.append(f"规则 {f.rule_id} 触发WARN门禁")
                break

        summary = "; ".join(reasons) if reasons else "所有检查通过"

        return QualityGateResult(
            verdict=verdict,
            total_findings=len(findings),
            critical_count=counts[Severity.CRITICAL],
            high_count=counts[Severity.HIGH],
            medium_count=counts[Severity.MEDIUM],
            low_count=counts[Severity.LOW],
            info_count=counts[Severity.INFO],
            score=score,
            gate_rules=self._config,
            summary=summary,
        )
