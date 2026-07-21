"""测试SARIF/JSONL报告输出"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.report.sarif_reporter import (
    findings_to_sarif, write_sarif_report, write_jsonl_report,
)


@pytest.fixture
def sample_findings() -> list[Finding]:
    return [
        Finding(rule_id="INJ-001", severity=Severity.HIGH, description="注入攻击检测", remediation="移除注入指令"),
        Finding(rule_id="P001", severity=Severity.MEDIUM, description="缺少角色定义", remediation="添加角色定义"),
        Finding(rule_id="PII011", severity=Severity.CRITICAL, description="API密钥泄露", remediation="撤销密钥"),
    ]


class TestFindingsToSarif:
    def test_basic_structure(self, sample_findings: list[Finding]):
        sarif = findings_to_sarif(sample_findings)
        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif
        assert len(sarif["runs"]) == 1

    def test_tool_info(self, sample_findings: list[Finding]):
        sarif = findings_to_sarif(sample_findings)
        driver = sarif["runs"][0]["tool"]["driver"]
        assert driver["name"] == "ai-prompt-toolkit"
        assert "version" in driver

    def test_results_count(self, sample_findings: list[Finding]):
        sarif = findings_to_sarif(sample_findings)
        results = sarif["runs"][0]["results"]
        assert len(results) == 3

    def test_severity_mapping(self, sample_findings: list[Finding]):
        sarif = findings_to_sarif(sample_findings)
        results = sarif["runs"][0]["results"]
        levels = [r["level"] for r in results]
        assert "error" in levels
        assert "warning" in levels

    def test_with_source_file(self, sample_findings: list[Finding]):
        sarif = findings_to_sarif(sample_findings, source_file="test.md")
        for r in sarif["runs"][0]["results"]:
            assert "locations" in r

    def test_rules_deduplicated(self, sample_findings: list[Finding]):
        extra = Finding(rule_id="INJ-001", severity=Severity.LOW, description="another")
        sarif = findings_to_sarif(sample_findings + [extra])
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]
        assert rule_ids.count("INJ-001") == 1

    def test_empty_findings(self):
        sarif = findings_to_sarif([])
        assert sarif["runs"][0]["results"] == []


class TestWriteSarifReport:
    def test_writes_file(self, sample_findings: list[Finding], tmp_path: Path):
        out = tmp_path / "report.sarif"
        write_sarif_report(sample_findings, out, source_file="test.md")
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["version"] == "2.1.0"


class TestWriteJsonlReport:
    def test_writes_file(self, sample_findings: list[Finding], tmp_path: Path):
        out = tmp_path / "report.jsonl"
        write_jsonl_report(sample_findings, out, source_file="test.md")
        assert out.exists()
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert "rule_id" in entry
            assert "severity" in entry

    def test_empty_findings(self, tmp_path: Path):
        out = tmp_path / "empty.jsonl"
        write_jsonl_report([], out)
        assert out.exists()
        content = out.read_text(encoding="utf-8").strip()
        assert content == ""
