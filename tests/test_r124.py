"""R124 测试: lint --profile性能分析"""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.rules import run_all_checks_profiled


class TestR124Profile:
    def test_run_all_checks_profiled(self):
        text = "你是一个专业的翻译助手，请将中文翻译为英文。"
        findings, profile_data = run_all_checks_profiled(text)
        assert len(findings) >= 0
        assert len(profile_data) > 0
        assert "checker" in profile_data[0]
        assert "elapsed_ms" in profile_data[0]
        assert "findings" in profile_data[0]
        assert all(p["elapsed_ms"] >= 0 for p in profile_data)

    def test_profile_data_count(self):
        text = "简单的prompt"
        _findings, profile_data = run_all_checks_profiled(text)
        assert len(profile_data) == 260  # R164扩容后实际值

    def test_lint_profile_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个翻译助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--profile"])
            assert "性能分析" in result.output or "Profile" in result.output

    def test_lint_profile_top10(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个翻译助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--profile"])
            assert "Top10" in result.output or "ms" in result.output
