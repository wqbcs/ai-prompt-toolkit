"""R130 测试: lint --fix --dry-run干运行修复预览"""
from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


class TestR130DryRun:
    def test_dry_run_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你可能大概也许需要帮助。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--fix", "--dry-run"])
            assert "DRY-RUN" in result.output or "未实际修改" in result.output

    def test_dry_run_no_modify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            original = "你可能大概也许需要帮助。"
            fpath.write_text(original, encoding="utf-8")
            runner = CliRunner()
            runner.invoke(main, ["lint", "-t", str(fpath), "--fix", "--dry-run"])
            assert fpath.read_text(encoding="utf-8") == original

    def test_dry_run_shows_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你可能大概也许需要帮助。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--dry-run"])
            assert "DRY-RUN" in result.output or "可修复" in result.output or "预览" in result.output
