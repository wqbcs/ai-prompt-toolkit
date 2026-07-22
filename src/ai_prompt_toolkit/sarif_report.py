"""SARIF输出格式 — 参考OASIS SARIF v2.1.0规范

核心特性:
- SarifReport: 顶级SARIF报告对象
- SarifRun: 单次工具执行结果
- SarifResult: 单条检查结果(对应一条Lint规则/安全发现)
- SarifRule: 规则定义
- GitHub Code Scanning兼容
- 零依赖纯Python实现

参考:
- OASIS SARIF v2.1.0 (https://docs.oasis-open.org/sarif/sarif/v2.1.0/)
- microsoft/sarif-python-om 对象模型设计
- GitHub Code Scanning SARIF上传规范

SARIF核心结构:
$schema + version → runs[] → results[] + tool → rules[]
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SARIF_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
_SARIF_VERSION = "2.1.0"


@dataclass
class SarifLocation:
    uri: str = ""
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0

    def to_dict(self) -> dict[str, Any]:
        physical = {"artifactLocation": {"uri": self.uri}}
        if self.start_line > 0:
            region: dict[str, Any] = {"startLine": self.start_line}
            if self.start_column > 0:
                region["startColumn"] = self.start_column
            if self.end_line > 0:
                region["endLine"] = self.end_line
            if self.end_column > 0:
                region["endColumn"] = self.end_column
            physical["region"] = region
        return physical


@dataclass
class SarifResult:
    rule_id: str = ""
    level: str = "note"
    message: str = ""
    uri: str = ""
    start_line: int = 0
    remediation: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ruleId": self.rule_id,
            "level": self.level,
            "message": {"text": self.message},
        }
        if self.uri:
            loc = SarifLocation(
                uri=self.uri,
                start_line=self.start_line,
            )
            d["locations"] = [loc.to_dict()]
        if self.remediation:
            d["fixes"] = [
                {
                    "description": {"text": self.remediation},
                    "artifactChanges": [],
                }
            ]
        if self.properties:
            d["properties"] = self.properties
        return d


@dataclass
class SarifRule:
    id: str = ""
    name: str = ""
    short_description: str = ""
    full_description: str = ""
    default_severity: str = "note"
    help_uri: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
        }
        if self.name:
            d["name"] = self.name
        if self.short_description:
            d["shortDescription"] = {"text": self.short_description}
        if self.full_description:
            d["fullDescription"] = {"text": self.full_description}
        level_map = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
        d["defaultConfiguration"] = {"level": level_map.get(self.default_severity, "note")}
        if self.help_uri:
            d["helpUri"] = self.help_uri
        if self.properties:
            d["properties"] = self.properties
        return d


@dataclass
class SarifRun:
    tool_name: str = "ai-prompt-toolkit"
    tool_version: str = "42.0.0"
    tool_info_uri: str = "https://github.com/ai-prompt-toolkit"
    results: list[SarifResult] = field(default_factory=list)
    rules: list[SarifRule] = field(default_factory=list)
    invocation_time: str = ""

    def __post_init__(self) -> None:
        if not self.invocation_time:
            self.invocation_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def add_result(self, result: SarifResult) -> None:
        self.results.append(result)

    def add_rule(self, rule: SarifRule) -> None:
        self.rules.append(rule)

    def add_lint_finding(
        self,
        rule_id: str,
        severity: str,
        description: str,
        uri: str = "",
        line: int = 0,
        remediation: str = "",
    ) -> None:
        level_map = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
        self.results.append(SarifResult(
            rule_id=rule_id,
            level=level_map.get(severity, "note"),
            message=description,
            uri=uri,
            start_line=line,
            remediation=remediation,
        ))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tool": {
                "driver": {
                    "name": self.tool_name,
                    "version": self.tool_version,
                    "informationUri": self.tool_info_uri,
                    "rules": [r.to_dict() for r in self.rules],
                }
            },
            "results": [r.to_dict() for r in self.results],
        }
        if self.invocation_time:
            d["invocations"] = [
                {
                    "executionSuccessful": True,
                    "startTimeUtc": self.invocation_time,
                    "endTimeUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ]
        return d


@dataclass
class SarifReport:
    runs: list[SarifRun] = field(default_factory=list)

    def add_run(self, run: SarifRun) -> None:
        self.runs.append(run)

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": _SARIF_SCHEMA,
            "version": _SARIF_VERSION,
            "runs": [r.to_dict() for r in self.runs],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def write(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @property
    def total_results(self) -> int:
        return sum(len(r.results) for r in self.runs)

    @property
    def error_count(self) -> int:
        return sum(
            1 for r in self.runs for res in r.results if res.level == "error"
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for r in self.runs for res in r.results if res.level == "warning"
        )


def lint_results_to_sarif(
    findings: list[dict[str, Any]],
    *,
    tool_name: str = "ai-prompt-toolkit",
    tool_version: str = "42.0.0",
    target_uri: str = "",
) -> SarifReport:
    report = SarifReport()
    run = SarifRun(tool_name=tool_name, tool_version=tool_version)

    seen_rules: set[str] = set()
    for f in findings:
        rule_id = f.get("rule_id", "")
        severity = f.get("severity", "info")
        description = f.get("description", "")
        remediation = f.get("remediation", "")

        if rule_id and rule_id not in seen_rules:
            run.add_rule(SarifRule(
                id=rule_id,
                name=rule_id,
                short_description=description[:80] if description else rule_id,
                default_severity=severity,
            ))
            seen_rules.add(rule_id)

        run.add_lint_finding(
            rule_id=rule_id,
            severity=severity,
            description=description,
            uri=f.get("file_path", target_uri),
            line=f.get("line", 0),
            remediation=remediation,
        )

    report.add_run(run)
    return report


def scan_results_to_sarif(
    findings: list[dict[str, Any]],
    *,
    tool_name: str = "ai-prompt-toolkit-security",
    target_uri: str = "",
) -> SarifReport:
    report = SarifReport()
    run = SarifRun(tool_name=tool_name, tool_version="42.0.0")

    seen_rules: set[str] = set()
    for f in findings:
        rule_id = f.get("rule_id", f.get("category", "SEC-UNKNOWN"))
        severity = f.get("severity", "medium")
        description = f.get("description", "")
        remediation = f.get("remediation", f.get("recommendation", ""))

        if rule_id and rule_id not in seen_rules:
            run.add_rule(SarifRule(
                id=rule_id,
                name=rule_id,
                short_description=description[:80] if description else rule_id,
                default_severity=severity,
                help_uri=f.get("reference", ""),
            ))
            seen_rules.add(rule_id)

        run.add_lint_finding(
            rule_id=rule_id,
            severity=severity,
            description=description,
            uri=f.get("file_path", target_uri),
            remediation=remediation,
        )

    report.add_run(run)
    return report


def eval_results_to_sarif(
    eval_data: list[dict[str, Any]],
    *,
    target_uri: str = "",
) -> SarifReport:
    report = SarifReport()
    run = SarifRun(tool_name="ai-prompt-toolkit-eval", tool_version="42.0.0")

    for item in eval_data:
        dimension = item.get("dimension", item.get("name", "UNKNOWN"))
        score = item.get("score", 0)
        threshold = item.get("threshold", 60)
        passed = score >= threshold

        rule_id = f"EVAL-{dimension}"
        if rule_id not in {r.id for r in run.rules}:
            run.add_rule(SarifRule(
                id=rule_id,
                name=dimension,
                short_description=f"Evaluation dimension: {dimension}",
                default_severity="note",
            ))

        run.add_result(SarifResult(
            rule_id=rule_id,
            level="note" if passed else "warning",
            message=f"Score: {score:.1f}/{threshold:.0f} ({'PASS' if passed else 'FAIL'})",
            uri=item.get("file_path", target_uri),
            properties={"score": score, "threshold": threshold, "passed": passed},
        ))

    report.add_run(run)
    return report
