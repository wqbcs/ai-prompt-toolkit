"""R140: lint --statistics 规则命中率统计"""
import pytest
from ai_prompt_toolkit.linter.rules import compute_rule_statistics
from ai_prompt_toolkit.types import Finding, Severity


def test_compute_rule_statistics_empty():
    stats = compute_rule_statistics([])
    assert stats["total_findings"] == 0
    assert stats["unique_rules"] == 0
    assert stats["rules"] == []


def test_compute_rule_statistics_basic():
    findings = [
        Finding("P001", "desc1", Severity.HIGH),
        Finding("P001", "desc2", Severity.HIGH),
        Finding("P006", "desc3", Severity.HIGH),
        Finding("P031", "desc4", Severity.HIGH),
        Finding("P006", "desc5", Severity.HIGH),
    ]
    stats = compute_rule_statistics(findings)
    assert stats["total_findings"] == 5
    assert stats["unique_rules"] == 3
    assert stats["rules"][0]["rule_id"] == "P001"
    assert stats["rules"][0]["hit_count"] == 2
    assert stats["rules"][1]["rule_id"] == "P006"
    assert stats["rules"][1]["hit_count"] == 2
    assert stats["rules"][2]["rule_id"] == "P031"
    assert stats["rules"][2]["hit_count"] == 1


def test_compute_rule_statistics_hit_rate():
    findings = [
        Finding("P001", "d1", Severity.HIGH),
        Finding("P001", "d2", Severity.HIGH),
        Finding("P001", "d3", Severity.HIGH),
        Finding("P006", "d4", Severity.HIGH),
    ]
    stats = compute_rule_statistics(findings)
    assert stats["rules"][0]["hit_rate"] == 75.0
    assert stats["rules"][1]["hit_rate"] == 25.0


def test_compute_rule_statistics_by_category():
    findings = [
        Finding("P001", "d1", Severity.HIGH),
        Finding("P006", "d2", Severity.HIGH),
        Finding("P031", "d3", Severity.HIGH),
    ]
    stats = compute_rule_statistics(findings)
    assert "structure" in stats["by_category"]
    assert "security" in stats["by_category"]


def test_compute_rule_statistics_by_severity():
    findings = [
        Finding("P001", "d1", Severity.HIGH),
        Finding("P002", "d2", Severity.MEDIUM),
        Finding("P005", "d3", Severity.LOW),
    ]
    stats = compute_rule_statistics(findings)
    assert "high" in stats["by_severity"]
    assert "medium" in stats["by_severity"]
    assert "low" in stats["by_severity"]
