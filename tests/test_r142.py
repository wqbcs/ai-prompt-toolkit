"""R142: lint --baseline基线管理"""
import json
import pytest
from pathlib import Path
from ai_prompt_toolkit.linter.baseline import (
    BaselineSnapshot, BaselineDiff,
    save_baseline, load_baseline, compare_baseline,
)


def test_save_and_load_baseline(tmp_path):
    findings = [{"rule_id": "P001", "description": "desc1", "severity": "high"}]
    path = tmp_path / "baseline.json"
    save_baseline(findings, path, template_id="test.md", score=85.0)
    assert path.exists()
    loaded = load_baseline(path)
    assert loaded.total_findings == 1
    assert loaded.template_id == "test.md"
    assert loaded.score == 85.0
    assert len(loaded.findings) == 1


def test_compare_baseline_no_change():
    findings = [
        {"rule_id": "P001", "description": "desc1", "severity": "high"},
        {"rule_id": "P006", "description": "desc2", "severity": "high"},
    ]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=2, findings=findings)
    diff = compare_baseline(findings, baseline)
    assert diff.baseline_total == 2
    assert diff.current_total == 2
    assert diff.delta == 0
    assert diff.is_regression is False
    assert len(diff.new_findings) == 0
    assert len(diff.fixed_findings) == 0
    assert len(diff.unchanged_findings) == 2


def test_compare_baseline_new_finding():
    baseline_findings = [{"rule_id": "P001", "description": "desc1", "severity": "high"}]
    current_findings = [
        {"rule_id": "P001", "description": "desc1", "severity": "high"},
        {"rule_id": "P006", "description": "desc2", "severity": "high"},
    ]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=1, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    assert len(diff.new_findings) == 1
    assert diff.delta == 1
    assert diff.is_regression is True


def test_compare_baseline_fixed_finding():
    baseline_findings = [
        {"rule_id": "P001", "description": "desc1", "severity": "high"},
        {"rule_id": "P006", "description": "desc2", "severity": "high"},
    ]
    current_findings = [{"rule_id": "P001", "description": "desc1", "severity": "high"}]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=2, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    assert len(diff.fixed_findings) == 1
    assert diff.delta == -1
    assert diff.is_regression is False


def test_compare_baseline_regression():
    baseline_findings = [{"rule_id": "P001", "description": "desc1", "severity": "high"}]
    current_findings = [
        {"rule_id": "P001", "description": "desc1", "severity": "high"},
        {"rule_id": "P001", "description": "desc2", "severity": "high"},
    ]
    baseline = BaselineSnapshot(created_at="2025-01-01", total_findings=1, findings=baseline_findings)
    diff = compare_baseline(current_findings, baseline)
    assert len(diff.regressions) >= 1
    assert diff.is_regression is True


def test_baseline_snapshot_serialization():
    snapshot = BaselineSnapshot(
        created_at="2025-01-01T00:00:00",
        total_findings=3,
        findings=[{"rule_id": "P001", "description": "test", "severity": "high"}],
        template_id="test.md",
        score=90.0,
    )
    d = snapshot.to_dict()
    restored = BaselineSnapshot.from_dict(d)
    assert restored.total_findings == 3
    assert restored.score == 90.0
