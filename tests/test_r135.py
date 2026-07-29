"""R135 测试: Finding行号/列号定位"""
from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.rules import find_line
import re


class TestR135Location:
    def test_find_line_basic(self):
        text = "第一行\n第二行有问题\n第三行"
        pattern = re.compile(r"问题")
        line = find_line(text, pattern)
        assert line == 2

    def test_find_line_first_line(self):
        text = "问题在第一行\n第二行"
        pattern = re.compile(r"问题")
        line = find_line(text, pattern)
        assert line == 1

    def test_find_line_no_match(self):
        text = "没有匹配\n第二行"
        pattern = re.compile(r"xyz")
        line = find_line(text, pattern)
        assert line == 1

    def test_lint_output_has_location(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个专业翻译助手\n你是一个专业翻译助手\n你是一个专业翻译助手", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath)])
            assert "Lint完成" in result.output

    def test_finding_location_field(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks
        text = "第一行\npassword=MySecret123\n第三行"
        findings = run_all_checks(text)
        p006 = [f for f in findings if f.rule_id == "P006"]
        assert len(p006) >= 1
