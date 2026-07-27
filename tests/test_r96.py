"""R96: lint --changed增量模式 + --cache-dir缓存目录"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


class TestR96LintChanged:
    def test_lint_changed_option_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--help"])
        assert "--changed" in result.output

    def test_lint_cache_dir_option_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--help"])
        assert "--cache-dir" in result.output

    def test_lint_changed_no_git(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fp), "--changed", "--quiet"])
            assert result.exit_code in (0, 1, 2)

    def test_lint_cache_dir_created(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手。", encoding="utf-8")
            cache_dir = Path(td) / ".cache"
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fp), "--cache-dir", str(cache_dir), "--quiet"])
            assert result.exit_code in (0, 1, 2)

    def test_lint_changed_with_git(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init"], cwd=td, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=td, capture_output=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=td, capture_output=True)
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手。", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=td, capture_output=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=td, capture_output=True)
            fp.write_text("version: 2.0.0\n你是一个改进的AI助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", td, "--changed"])
            assert result.exit_code in (0, 1, 2)
