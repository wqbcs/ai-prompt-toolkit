"""SARIF 2.1输出增强 — 对齐GitHub Advanced Security完整规范

参考:
- SARIF Specification 2.1 (OASIS Standard)
- GitHub Code Scanning SARIF format
- Microsoft SARIF SDK

增强字段(对比基础版):
- ruleIndex: 结果引用规则索引
- fullDescription: 规则完整描述
- helpUri: 规则帮助链接
- rank: 严重性排序权重(0.0-100.0)
- columnKind: 位置列类型
- lineNumber: 行号(从details提取)
- endTimeUtc: 调用结束时间
- exitCode: 退出码(语义化0/1/2/3)
- automationDetails: 运行标识
- metricValues: 统计指标
- taxonomy: CWE/OWASP分类映射
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_prompt_toolkit import __version__  # R236-P2-19: 版本单一真源(同 R174 先例)
from ai_prompt_toolkit.sarif_report import REPO_URL
from ai_prompt_toolkit.types import Finding, Severity

_SEVERITY_TO_SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "none",
}

_SEVERITY_TO_RANK = {
    Severity.CRITICAL: 90.0,
    Severity.HIGH: 70.0,
    Severity.MEDIUM: 40.0,
    Severity.LOW: 15.0,
    Severity.INFO: 5.0,
}

_RULE_TAXONOMY: dict[str, list[dict[str, str]]] = {
    "INJ-006": [{"id": "CWE-74", "name": "OWASP LLM01 - Prompt Injection"}],
    "INJ-007": [{"id": "CWE-74", "name": "OWASP LLM02 - Sensitive Info Disclosure"}],
    "INJ-008": [{"id": "CWE-74", "name": "OWASP LLM06 - Excessive Agency"}],
    "INJ-009": [{"id": "CWE-74", "name": "OWASP LLM02 - Sensitive Info Disclosure"}],
    "INJ-011": [{"id": "CWE-200", "name": "OWASP LLM07 - System Prompt Leak"}],
    "INJ-013": [{"id": "CWE-269", "name": "OWASP LLM08 - Supply Chain"}],
    "INJ-014": [{"id": "CWE-1357", "name": "OWASP LLM03 - Supply Chain"}],
    "PII001": [{"id": "CWE-359", "name": "OWASP LLM06 - PII Exposure"}],
    "PII002": [{"id": "CWE-359", "name": "OWASP LLM06 - PII Exposure"}],
    "PII003": [{"id": "CWE-359", "name": "OWASP LLM06 - PII Exposure"}],
}


def _severity_to_sarif_level(severity: Severity) -> str:
    return _SEVERITY_TO_SARIF_LEVEL.get(severity, "warning")


def findings_to_sarif(
    findings: list[Finding],
    source_file: str = "",
    tool_version: str = __version__,
    *,
    run_id: str = "",
    exit_code: int = 0,
) -> dict[str, Any]:
    rules_map: dict[str, dict[str, Any]] = {}
    rules_list: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    start_time = datetime.now(timezone.utc)

    for finding in findings:
        if finding.rule_id not in rules_map:
            rule_entry: dict[str, Any] = {
                "id": finding.rule_id,
                "name": finding.rule_id,
                "shortDescription": {"text": finding.description[:80]},
                "fullDescription": {"text": finding.description},
                "helpUri": f"https://ai-prompt-toolkit.dev/rules/{finding.rule_id}",
                "properties": {
                    "tags": ["security"] if finding.severity in (Severity.HIGH, Severity.CRITICAL) else ["quality"],
                },
            }

            rank = _SEVERITY_TO_RANK.get(finding.severity, 30.0)
            rule_entry["properties"]["rank"] = rank

            if finding.rule_id in _RULE_TAXONOMY:
                rule_entry["relationships"] = [
                    {"target": {"id": t["id"], "toolComponent": {"name": "CWE/OWASP"}}, "kinds": ["superset"]}
                    for t in _RULE_TAXONOMY[finding.rule_id]
                ]

            rules_map[finding.rule_id] = rule_entry
            rules_list.append(rule_entry)

        rule_index = list(rules_map.keys()).index(finding.rule_id)

        result_entry: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "ruleIndex": rule_index,
            "level": _severity_to_sarif_level(finding.severity),
            "message": {"text": finding.description},
            "rank": _SEVERITY_TO_RANK.get(finding.severity, 30.0),
        }

        loc: dict[str, Any] = {}
        if source_file:
            loc["artifactLocation"] = {"uri": source_file}
        line_number = finding.details.get("line_number", 0) if finding.details else 0
        if line_number:
            loc["region"] = {"startLine": line_number}
        if loc:
            result_entry["locations"] = [
                {"physicalLocation": loc, "contextRegion": {"startLine": max(1, line_number - 2)}}
            ]

        if finding.remediation:
            result_entry["fixes"] = [
                {
                    "description": {"text": finding.remediation},
                    "artifactChanges": [],
                }
            ]

        if finding.details:
            result_entry["properties"] = {"details": finding.details}

        results.append(result_entry)

    end_time = datetime.now(timezone.utc)

    invocation: dict[str, Any] = {
        "executionSuccessful": exit_code == 0,
        "startTimeUtc": start_time.isoformat(),
        "endTimeUtc": end_time.isoformat(),
        "exitCode": exit_code,
        "exitCodeDescription": {0: "PASS", 1: "WARN", 2: "FAIL", 3: "ERROR"}.get(exit_code, "UNKNOWN"),
    }

    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "ai-prompt-toolkit",
                "version": tool_version,
                "semanticVersion": tool_version,
                "informationUri": REPO_URL,
                "rules": rules_list,
                "columnKind": "unicodeCodePoints",
            }
        },
        "results": results,
        "invocations": [invocation],
    }

    if run_id:
        run["automationDetails"] = {"id": run_id}

    metric_values: list[dict[str, Any]] = []
    critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high_count = sum(1 for f in findings if f.severity == Severity.HIGH)
    medium_count = sum(1 for f in findings if f.severity == Severity.MEDIUM)
    low_count = sum(1 for f in findings if f.severity in (Severity.LOW, Severity.INFO))
    if findings:
        metric_values = [
            {"metric": {"id": "totalFindings"}, "value": len(findings)},
            {"metric": {"id": "criticalCount"}, "value": critical_count},
            {"metric": {"id": "highCount"}, "value": high_count},
            {"metric": {"id": "mediumCount"}, "value": medium_count},
            {"metric": {"id": "lowCount"}, "value": low_count},
        ]
        run["metricValues"] = metric_values

    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [run],
    }

    return sarif


def write_sarif_report(
    findings: list[Finding],
    output_path: str | Path,
    source_file: str = "",
    *,
    run_id: str = "",
    exit_code: int = 0,
) -> None:
    sarif = findings_to_sarif(findings, source_file=source_file, run_id=run_id, exit_code=exit_code)
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
            entry: dict[str, Any] = {
                "rule_id": finding.rule_id,
                "severity": finding.severity.value,
                "description": finding.description,
                "remediation": finding.remediation or "",
                "source": source_file,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if finding.details:
                entry["details"] = finding.details
            if finding.location:
                entry["location"] = finding.location
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
