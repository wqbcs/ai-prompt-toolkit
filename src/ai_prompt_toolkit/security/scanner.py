"""安全扫描器主入口——编排注入检测与继承审计。"""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.security.types import (
    InheritanceFinding,
    RiskLevel,
    ScanResult,
)
from ai_prompt_toolkit.security.injection_detector import InjectionDetector
from ai_prompt_toolkit.security.inheritance_auditor import InheritanceAuditor, TemplateProvider


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _assess_risk(injection_findings: list[Finding], inheritance_findings: list[InheritanceFinding]) -> RiskLevel:
    levels = [RiskLevel.NONE]

    for f in injection_findings:
        sev_to_risk = {
            Severity.INFO: RiskLevel.NONE,
            Severity.LOW: RiskLevel.LOW,
            Severity.MEDIUM: RiskLevel.MEDIUM,
            Severity.HIGH: RiskLevel.HIGH,
            Severity.CRITICAL: RiskLevel.CRITICAL,
        }
        levels.append(sev_to_risk[f.severity])

    for inh in inheritance_findings:
        levels.append(inh.risk_level)

    return max(levels)


class Scanner:
    def __init__(
        self,
        provider: TemplateProvider,
        *,
        detector: InjectionDetector | None = None,
        max_depth: int = 5,
        hash_cache: dict[str, str] | None = None,
    ) -> None:
        self._provider = provider
        self._detector = detector or InjectionDetector()
        self._auditor = InheritanceAuditor(provider, max_depth=max_depth)
        self._hash_cache: dict[str, str] = hash_cache or {}

    def scan(self, template_id: str, text: str, *, incremental: bool = False) -> ScanResult:
        start = time.perf_counter()

        template_hash = _compute_hash(text)

        if incremental and self._hash_cache.get(template_id) == template_hash:
            return ScanResult(
                template_id=template_id,
                risk_level=RiskLevel.NONE,
                template_hash=template_hash,
                skipped=True,
            )

        preprocessed = self._preprocess(text)

        injection_findings = self._detector.detect(preprocessed, template_id=template_id)
        inheritance_findings = self._auditor.audit(template_id)

        risk_level = _assess_risk(injection_findings, inheritance_findings)

        elapsed = (time.perf_counter() - start) * 1000

        self._hash_cache[template_id] = template_hash

        return ScanResult(
            template_id=template_id,
            risk_level=risk_level,
            injection_findings=injection_findings,
            inheritance_findings=inheritance_findings,
            template_hash=template_hash,
            scan_time_ms=round(elapsed, 2),
        )

    def scan_batch(
        self,
        items: Iterable[tuple[str, str]],
        *,
        incremental: bool = False,
        max_workers: int = 4,
    ) -> list[ScanResult]:
        items_list = list(items)
        if not items_list:
            return []

        results: list[ScanResult] = [None] * len(items_list)  # type: ignore[list-item]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.scan, tid, text, incremental=incremental): idx
                for idx, (tid, text) in enumerate(items_list)
            }
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()

        return results

    @staticmethod
    def _preprocess(text: str) -> str:
        lines = text.splitlines()
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)
