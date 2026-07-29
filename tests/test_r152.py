"""R152: lint --export-lcov覆盖率导出"""
import pytest
from ai_prompt_toolkit.linter.lcov_export import generate_lcov_report, generate_coverage_summary
from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import get_all_rules


def test_generate_lcov_empty():
    report = generate_lcov_report([])
    assert "TN:" in report
    assert "FN:0" in report
    assert "end_of_record" in report


def test_generate_lcov_with_findings():
    findings = [Finding("P001", "d1", Severity.HIGH), Finding("P006", "d2", Severity.HIGH)]
    report = generate_lcov_report(findings)
    assert "DA:P001,1,1" in report
    assert "DA:P006,1,1" in report
    assert "DA:P002,0,0" in report


def test_generate_lcov_hit_count():
    findings = [Finding("P001", "d1", Severity.HIGH), Finding("P001", "d2", Severity.HIGH)]
    report = generate_lcov_report(findings)
    assert "DA:P001,1,2" in report


def test_generate_coverage_summary():
    findings = [Finding("P001", "d1", Severity.HIGH), Finding("P006", "d2", Severity.HIGH)]
    summary = generate_coverage_summary(findings)
    assert summary["total_rules"] == len(get_all_rules())
    assert summary["hit_rules"] == 2
    assert summary["coverage_pct"] > 0


def test_generate_coverage_summary_by_category():
    findings = [Finding("P001", "d1", Severity.HIGH)]
    summary = generate_coverage_summary(findings)
    assert "structure" in summary["by_category"]
    assert summary["by_category"]["structure"]["hit"] >= 1
