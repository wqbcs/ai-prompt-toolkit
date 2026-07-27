"""R89: HTML报告交互式折叠"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.html_report import generate_html_report


def test_html_report_basic():
    results = [
        {"rule_id": "P001", "severity": "HIGH", "category": "structure",
         "name": "角色清晰度", "message": "缺少角色定义"},
        {"rule_id": "P011", "severity": "CRITICAL", "category": "security",
         "name": "注入防御", "message": "存在注入风险"},
    ]
    html = generate_html_report(results, "test.md")
    assert "<!DOCTYPE html>" in html
    assert "P001" in html
    assert "P011" in html
    assert "CRITICAL" in html
    assert "HIGH" in html


def test_html_report_interactive_elements():
    results = [{"rule_id": "P001", "severity": "MEDIUM", "category": "structure", "name": "test", "message": "msg"}]
    html = generate_html_report(results, "test.md")
    assert "toggleCategory" in html
    assert "toggleDetail" in html
    assert "toggleAll" in html
    assert "toggleTheme" in html
    assert "filterFindings" in html


def test_html_report_dark_theme():
    results = []
    html = generate_html_report(results, "test.md")
    assert 'data-theme="light"' in html
    assert "dark" in html


def test_html_report_save_to_file():
    results = [{"rule_id": "P001", "severity": "LOW", "category": "quality", "name": "test", "message": "msg"}]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "report.html")
        html = generate_html_report(results, "test.md", output_path=path)
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "P001" in content


def test_html_report_stats():
    results = [
        {"rule_id": "P001", "severity": "CRITICAL", "category": "security", "name": "a", "message": "a"},
        {"rule_id": "P002", "severity": "HIGH", "category": "structure", "name": "b", "message": "b"},
        {"rule_id": "P003", "severity": "MEDIUM", "category": "quality", "name": "c", "message": "c"},
        {"rule_id": "P004", "severity": "LOW", "category": "other", "name": "d", "message": "d"},
    ]
    html = generate_html_report(results, "test.md")
    assert ">1<" in html
    assert "Critical" in html
    assert "High" in html
    assert "Medium" in html
    assert "Low" in html
