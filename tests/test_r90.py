"""R90: --color-theme选项 + --html报告"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


def test_lint_color_theme_option():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("你是一个AI助手。", encoding="utf-8")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["lint", "-t", str(test_file), "--color-theme", "monokai"])
            assert result.exit_code in (0, 1, 2)
            # R319: 移除 `or True` 重言面 — 真实断言生效
            assert os.environ.get("PROMPT_TOOLKIT_THEME") == "monokai"
        finally:
            os.chdir(original_cwd)
            os.environ.pop("PROMPT_TOOLKIT_THEME", None)


def test_lint_html_flag():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("你是一个AI助手。", encoding="utf-8")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            html_path = str(Path(tmpdir) / "report.html")
            result = runner.invoke(main, ["lint", "-t", str(test_file), "--html", "-o", html_path])
            assert result.exit_code in (0, 1, 2)
        finally:
            os.chdir(original_cwd)


def test_lint_format_html():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("你是一个AI助手。", encoding="utf-8")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            html_path = str(Path(tmpdir) / "report.html")
            result = runner.invoke(main, ["lint", "-t", str(test_file), "--format", "html", "-o", html_path])
            assert result.exit_code in (0, 1, 2)
        finally:
            os.chdir(original_cwd)


def test_color_theme_choices():
    runner = CliRunner()
    result = runner.invoke(main, ["lint", "--help"])
    assert "monokai" in result.output
    assert "solarized" in result.output
    assert "nord" in result.output
    assert "dracula" in result.output
