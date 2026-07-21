"""SARIF 2.1输出增强 — 对齐GitHub Advanced Security

参考:
- SARIF Specification 2.1 (OASIS Standard)
- GitHub Code Scanning SARIF format
- Microsoft SARIF SDK

生成符合GitHub Code Scanning要求的SARIF报告
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


_SEVERITY_TO_SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "none",
}


def _severity_to_sarif_level(severity: Severity) -> str:
    return _SEVERITY_TO_SARIF_LEVEL.get(severity, "warning")


def findings_to_sarif(
    findings: list[Finding],
    source_file: str = "",
    tool_version: str = "42.0.0",
) -> dict[str, Any]:
    rules_map: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for finding in findings:
        if finding.rule_id not in rules_map:
            rules_map[finding.rule_id] = {
                "id": finding.rule_id,
                "name": finding.rule_id,
                "shortDescription": {"text": finding.description[:80]},
                "properties": {"tags": ["security"] if finding.severity in (Severity.HIGH, Severity.CRITICAL) else ["quality"]},
            }

        result_entry: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": _severity_to_sarif_level(finding.severity),
            "message": {"text": finding.description},
        }

        if source_file:
            result_entry["locations"] = [{
                "physicalLocation": {
                    "artifactLocation": {"uri": source_file},
                }
            }]

        if finding.remediation:
            result_entry["fixes"] = [{
                "description": {"text": finding.remediation},
            }]

        results.append(result_entry)

    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "ai-prompt-toolkit",
                    "version": tool_version,
                    "informationUri": "https://github.com/ai-prompt-toolkit",
                    "rules": list(rules_map.values()),
                }
            },
            "results": results,
            "invocations": [{
                "executionSuccessful": True,
                "startTimeUtc": datetime.now(timezone.utc).isoformat(),
            }],
        }],
    }

    return sarif


def write_sarif_report(
    findings: list[Finding],
    output_path: str | Path,
    source_file: str = "",
) -> None:
    sarif = findings_to_sarif(findings, source_file=source_file)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sarif, f, ensure_ascii=False, indent=2)


def write_jsonl_report(
    findings: list[Finding],
    output_path: str | Path,
    source_file: str = "",
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for finding in findings:
            entry = {
                "rule_id": finding.rule_id,
                "severity": finding.severity.value,
                "description": finding.description,
                "remediation": finding.remediation or "",
                "source": source_file,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if finding.details:
                entry["details"] = finding.details
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
