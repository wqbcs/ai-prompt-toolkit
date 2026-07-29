"""R147: lint --json-diff结构化对比输出"""
import json
import pytest
from ai_prompt_toolkit.linter.baseline import BaselineSnapshot, BaselineDiff, compare_baseline
from ai_prompt_toolkit.linter.structured_diff import generate_structured_diff, format_diff_json


def test_generate_structured_diff_improved():
    baseline_findings = [
        {"rule_id": "P001", "description": "d1", "severity": "high"},
        {"rule_id": "P006", "description": "d2", "severity": "high"},
    ]
    current_findings = [{"rule_id": "P001", "description": "d1", "severity": "high"}]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=2, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    result = generate_structured_diff(diff, baseline, current_findings, target="test.md")
    assert result["verdict"] == "IMPROVED"
    assert result["summary"]["delta"] == -1
    assert result["summary"]["fixed_count"] == 1


def test_generate_structured_diff_regression():
    baseline_findings = [{"rule_id": "P001", "description": "d1", "severity": "high"}]
    current_findings = [
        {"rule_id": "P001", "description": "d1", "severity": "high"},
        {"rule_id": "P006", "description": "d2", "severity": "high"},
    ]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=1, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    result = generate_structured_diff(diff, baseline, current_findings)
    assert result["verdict"] == "FAIL"
    assert result["summary"]["new_count"] == 1


def test_generate_structured_diff_unchanged():
    findings = [{"rule_id": "P001", "description": "d1", "severity": "high"}]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=1, findings=findings)
    diff = compare_baseline(findings, baseline)
    result = generate_structured_diff(diff, baseline, findings)
    assert result["verdict"] == "PASS"
    assert result["summary"]["delta"] == 0


def test_generate_structured_diff_rule_level():
    baseline_findings = [{"rule_id": "P001", "description": "d1", "severity": "high"}]
    current_findings = [
        {"rule_id": "P001", "description": "d1", "severity": "high"},
        {"rule_id": "P001", "description": "d2", "severity": "high"},
    ]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=1, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    result = generate_structured_diff(diff, baseline, current_findings)
    p001_stat = [r for r in result["rule_level"] if r["rule_id"] == "P001"][0]
    assert p001_stat["status"] == "regression"
    assert p001_stat["delta"] == 1


def test_format_diff_json():
    data = {"verdict": "PASS", "summary": {"delta": 0}}
    result = format_diff_json(data)
    parsed = json.loads(result)
    assert parsed["verdict"] == "PASS"
