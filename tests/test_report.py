"""HTML报告生成器单元测试"""
from __future__ import annotations

import re

import pytest

from ai_prompt_toolkit.report.html_reporter import (
    generate_scan_html,
    generate_lint_html,
    generate_html_report,
    _assess_overall_risk,
    _svg_donut,
    _svg_score_gauge,
)


class TestAssessOverallRisk:
    def test_no_findings(self):
        assert _assess_overall_risk([]) == "none"

    def test_critical(self):
        assert _assess_overall_risk([{"severity": "critical"}]) == "critical"

    def test_high(self):
        assert _assess_overall_risk([{"severity": "high"}]) == "high"

    def test_medium(self):
        assert _assess_overall_risk([{"severity": "medium"}]) == "medium"

    def test_low(self):
        assert _assess_overall_risk([{"severity": "low"}]) == "low"

    def test_mixed_takes_highest(self):
        assert _assess_overall_risk([
            {"severity": "low"}, {"severity": "high"}, {"severity": "medium"},
        ]) == "high"


class TestSvgDonut:
    def test_empty(self):
        svg = _svg_donut(0, 0, 0, 0)
        assert "安全" in svg

    def test_with_findings(self):
        svg = _svg_donut(1, 2, 3, 4)
        assert "10" in svg
        assert "发现项" in svg

    def test_single_category(self):
        svg = _svg_donut(0, 0, 5, 0)
        assert "5" in svg


class TestSvgScoreGauge:
    def test_perfect_score(self):
        svg = _svg_score_gauge(100, "#22c55e")
        assert "100" in svg

    def test_zero_score(self):
        svg = _svg_score_gauge(0, "#ef4444")
        assert "0" in svg

    def test_mid_score(self):
        svg = _svg_score_gauge(75, "#f59e0b")
        assert "75" in svg


class TestGenerateScanHtml:
    def test_basic_report(self):
        data = {
            "scan_target": "test_dir",
            "total_files": 3,
            "findings": [
                {"severity": "high", "rule_id": "INJ-001", "description": "注入风险",
                 "remediation": "请过滤用户输入"},
                {"severity": "medium", "rule_id": "INJ-002", "description": "中等问题"},
            ],
        }
        html = generate_scan_html(data)
        assert "安全扫描报告" in html
        assert "注入风险" in html
        assert "INJ-001" in html
        assert "请过滤用户输入" in html
        assert "高危" in html
        assert "中危" in html

    def test_no_findings(self):
        data = {"scan_target": "clean_dir", "total_files": 1, "findings": []}
        html = generate_scan_html(data)
        assert "安全扫描报告" in html
        assert "无风险" in html

    def test_critical_findings(self):
        data = {
            "scan_target": "danger",
            "findings": [
                {"severity": "critical", "rule_id": "INJ-CRIT", "description": "极高风险"},
            ],
        }
        html = generate_scan_html(data)
        assert "极高风险" in html
        assert "严重" in html

    def test_findings_with_details(self):
        data = {
            "scan_target": "test",
            "findings": [
                {"severity": "high", "rule_id": "R1", "description": "test",
                 "details": {"chain": ["a", "b"], "depth": 2}},
            ],
        }
        html = generate_scan_html(data)
        assert "chain" in html
        assert "depth" in html

    def test_risk_level_from_data(self):
        data = {
            "scan_target": "test",
            "risk_level": "high",
            "findings": [{"severity": "high", "rule_id": "R1", "description": "test"}],
        }
        html = generate_scan_html(data)
        assert "高风险" in html

    def test_html_escaping(self):
        data = {
            "scan_target": "<script>alert(1)</script>",
            "findings": [
                {"severity": "high", "rule_id": "R1",
                 "description": "<img onerror=alert(1)>"},
            ],
        }
        html = generate_scan_html(data)
        assert "<img onerror" not in html
        assert "&lt;img onerror" in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


class TestGenerateLintHtml:
    def test_basic_lint_report(self):
        data = {
            "lint_target": "test_dir",
            "total_files": 2,
            "average_score": 85.5,
            "total_findings": 3,
            "results": [
                {
                    "template_id": "a.md",
                    "score": 90,
                    "findings": [
                        {"severity": "medium", "rule_id": "P005", "description": "内容过短"},
                    ],
                },
            ],
        }
        html = generate_lint_html(data)
        assert "Lint质量报告" in html
        assert "85.5" in html
        assert "P005" in html

    def test_clean_lint(self):
        data = {
            "lint_target": "clean",
            "total_files": 1,
            "average_score": 100,
            "total_findings": 0,
            "results": [],
        }
        html = generate_lint_html(data)
        assert "100" in html

    def test_low_score(self):
        data = {
            "lint_target": "bad",
            "total_files": 1,
            "average_score": 30,
            "total_findings": 10,
            "results": [
                {
                    "template_id": "bad.md",
                    "score": 30,
                    "findings": [
                        {"severity": "high", "rule_id": "P001", "description": "严重问题"},
                    ],
                },
            ],
        }
        html = generate_lint_html(data)
        assert "30" in html
        assert "严重问题" in html


class TestGenerateHtmlReportDispatch:
    def test_dispatches_scan(self):
        data = {"findings": [], "scan_target": "x"}
        html = generate_html_report(data)
        assert "安全扫描报告" in html

    def test_dispatches_lint(self):
        data = {"_report_type": "lint", "findings": [], "results": [],
                "lint_target": "x", "average_score": 100, "total_findings": 0}
        html = generate_html_report(data)
        assert "Lint质量报告" in html


class TestHtmlOutputValidity:
    def test_valid_html_structure(self):
        data = {
            "scan_target": "test",
            "findings": [
                {"severity": "high", "rule_id": "R1", "description": "test"},
            ],
        }
        html = generate_scan_html(data)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert '<html lang="zh-CN">' in html

    def test_has_theme_toggle(self):
        data = {"scan_target": "test", "findings": []}
        html = generate_scan_html(data)
        assert "toggleTheme" in html
        assert "data-theme" in html

    def test_has_responsive_meta(self):
        data = {"scan_target": "test", "findings": []}
        html = generate_scan_html(data)
        assert "viewport" in html
