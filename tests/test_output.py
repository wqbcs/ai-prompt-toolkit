"""R30: CLI输出体验增强 测试套件"""
from __future__ import annotations

from io import StringIO

import pytest

from ai_prompt_toolkit.output import (
    ScanSummary,
    console,
    create_progress,
    error,
    finding,
    findings_list,
    info,
    print_contest_result,
    print_eval_matrix,
    print_flow_dag,
    print_gepa_result,
    print_table,
    print_version_tree,
    success,
    warning,
)


class TestBasicOutput:
    def test_success(self):
        console.print = lambda *a, **kw: None
        success("test ok")

    def test_warning(self):
        console.print = lambda *a, **kw: None
        warning("test warn")

    def test_error(self):
        console.print = lambda *a, **kw: None
        error("test err")

    def test_info(self):
        console.print = lambda *a, **kw: None
        info("test info")

    def test_finding_with_remediation(self):
        console.print = lambda *a, **kw: None
        finding("high", "P001", "constraint detected", "Add constraint word")

    def test_finding_without_remediation(self):
        console.print = lambda *a, **kw: None
        finding("low", "P002", "minor issue")

    def test_findings_list_empty(self):
        console.print = lambda *a, **kw: None
        findings_list([])

    def test_findings_list_with_data(self):
        console.print = lambda *a, **kw: None
        findings_list([
            {"severity": "high", "rule_id": "P001", "description": "test"},
            {"severity": "low", "rule_id": "P002", "description": "test2", "remediation": "fix"},
        ])


class TestCreateProgress:
    def test_returns_progress(self):
        progress = create_progress()
        assert progress is not None

    def test_progress_columns(self):
        progress = create_progress()
        col_types = [type(c).__name__ for c in progress.columns]
        assert "SpinnerColumn" in col_types
        assert "BarColumn" in col_types
        assert "TaskProgressColumn" in col_types
        assert "TimeElapsedColumn" in col_types
        assert "TimeRemainingColumn" in col_types


class TestPrintTable:
    def test_basic_table(self):
        console.print = lambda *a, **kw: None
        print_table("Test", ["Name", "Score"], [["a", "90"], ["b", "80"]])

    def test_empty_rows(self):
        console.print = lambda *a, **kw: None
        print_table("Empty", ["Col1"], [])


class TestPrintEvalMatrix:
    def test_basic_matrix(self):
        console.print = lambda *a, **kw: None
        cells = [
            {"prompt_name": "template1", "evaluator_name": "lint", "score": 9.0, "max_score": 10, "passed": True},
            {"prompt_name": "template1", "evaluator_name": "security", "score": 7.5, "max_score": 10, "passed": True},
            {"prompt_name": "template2", "evaluator_name": "lint", "score": 4.0, "max_score": 10, "passed": False},
        ]
        print_eval_matrix(
            "评估矩阵",
            ["template1", "template2"],
            ["lint", "security"],
            cells,
        )

    def test_empty_cells(self):
        console.print = lambda *a, **kw: None
        print_eval_matrix("Empty", ["t1"], ["ev1"], [])

    def test_score_color_high(self):
        console.print = lambda *a, **kw: None
        cells = [
            {"prompt_name": "t", "evaluator_name": "ev", "score": 9.5, "max_score": 10, "passed": True},
        ]
        print_eval_matrix("High", ["t"], ["ev"], cells)

    def test_score_color_low(self):
        console.print = lambda *a, **kw: None
        cells = [
            {"prompt_name": "t", "evaluator_name": "ev", "score": 3.0, "max_score": 10, "passed": False},
        ]
        print_eval_matrix("Low", ["t"], ["ev"], cells)


class TestPrintVersionTree:
    def test_basic_version_tree(self):
        console.print = lambda *a, **kw: None
        versions = [
            {"version_id": "abc123456789", "prompt_name": "test", "score": 92.5, "source": "gepa", "created_at": "2025-01-01"},
            {"version_id": "def123456789", "prompt_name": "test", "score": 65.0, "source": "manual", "created_at": "2025-01-02"},
        ]
        print_version_tree(versions)

    def test_empty_versions(self):
        console.print = lambda *a, **kw: None
        print_version_tree([])

    def test_version_without_optional_fields(self):
        console.print = lambda *a, **kw: None
        versions = [{"version_id": "abc", "prompt_name": "minimal", "score": 80}]
        print_version_tree(versions)


class TestPrintFlowDAG:
    def test_basic_flow(self):
        console.print = lambda *a, **kw: None
        flow_data = {
            "name": "test-flow",
            "nodes": {
                "input": {"node_type": "prompt"},
                "lint": {"node_type": "lint"},
                "scan": {"node_type": "security"},
            },
            "edges": [
                {"source": "input", "target": "lint"},
                {"source": "input", "target": "scan"},
            ],
        }
        print_flow_dag(flow_data)

    def test_flow_with_condition(self):
        console.print = lambda *a, **kw: None
        flow_data = {
            "name": "condition-flow",
            "nodes": {
                "start": {"node_type": "prompt"},
                "check": {"node_type": "condition"},
                "pass": {"node_type": "prompt"},
            },
            "edges": [
                {"source": "start", "target": "check"},
                {"source": "check", "target": "pass", "condition": "score > 80"},
            ],
        }
        print_flow_dag(flow_data)

    def test_empty_flow(self):
        console.print = lambda *a, **kw: None
        print_flow_dag({"name": "empty", "nodes": {}, "edges": []})


class TestPrintGepaResult:
    def test_positive_improvement(self):
        console.print = lambda *a, **kw: None
        result = {
            "best_score": 0.95,
            "initial_score": 0.70,
            "improvement": 0.25,
            "candidates_explored": 12,
            "generations": 5,
            "frontier_size": 3,
        }
        print_gepa_result(result)

    def test_zero_improvement(self):
        console.print = lambda *a, **kw: None
        result = {
            "best_score": 0.70,
            "initial_score": 0.70,
            "improvement": 0.0,
            "candidates_explored": 6,
            "generations": 3,
            "frontier_size": 1,
        }
        print_gepa_result(result)


class TestPrintContestResult:
    def test_excellent_level(self):
        console.print = lambda *a, **kw: None
        result = {
            "contest_score": 9.5,
            "readiness_level": "excellent",
            "pangu_integration": True,
            "harmonyos_integration": True,
        }
        print_contest_result(result)

    def test_insufficient_level(self):
        console.print = lambda *a, **kw: None
        result = {
            "contest_score": 3.0,
            "readiness_level": "insufficient",
            "pangu_integration": False,
            "harmonyos_integration": False,
        }
        print_contest_result(result)

    def test_moderate_level(self):
        console.print = lambda *a, **kw: None
        result = {
            "contest_score": 6.5,
            "readiness_level": "moderate",
            "pangu_integration": True,
            "harmonyos_integration": False,
        }
        print_contest_result(result)


class TestScanSummary:
    def test_passed_no_findings(self):
        s = ScanSummary(command="lint", total_files=5, total_findings=0)
        assert s.passed is True

    def test_failed_with_critical(self):
        s = ScanSummary(command="scan", total_files=3, total_findings=2, critical=1, high=1)
        assert s.passed is False

    def test_failed_with_high(self):
        s = ScanSummary(command="scan", total_files=1, total_findings=1, high=1)
        assert s.passed is False

    def test_passed_with_medium_only(self):
        s = ScanSummary(command="lint", total_files=2, total_findings=3, medium=2, low=1)
        assert s.passed is True

    def test_render_no_findings(self):
        console.print = lambda *a, **kw: None
        s = ScanSummary(command="lint", total_files=5, total_findings=0, elapsed_ms=1200)
        s.render()

    def test_render_with_findings(self):
        console.print = lambda *a, **kw: None
        s = ScanSummary(
            command="scan",
            total_files=10,
            total_findings=5,
            critical=1,
            high=1,
            medium=2,
            low=1,
            elapsed_ms=3500,
        )
        s.render()

    def test_render_with_extras(self):
        console.print = lambda *a, **kw: None
        s = ScanSummary(
            command="lint",
            total_files=3,
            total_findings=2,
            medium=2,
            elapsed_ms=500,
            extras={"avg_score": "85.5"},
        )
        s.render()
