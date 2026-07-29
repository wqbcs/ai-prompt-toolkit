"""R132 测试: eval --format csv输出"""
from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


class TestR132CSV:
    def test_eval_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个专业的翻译助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["evaluate", "-t", str(fpath), "--format", "csv", "--quick"])
            assert result.exit_code == 0, f"exit={result.exit_code}, out={result.output[:200]}"
            assert "template_id,dimension_id,name,category,score,weight" in result.output
            lines = result.output.strip().split("\n")
            assert len(lines) > 1

    def test_eval_csv_has_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个翻译助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["evaluate", "-t", str(fpath), "--format", "csv", "--quick"])
            assert result.exit_code == 0
            lines = result.output.strip().split("\n")
            assert len(lines) >= 2
            fields = lines[1].split(",")
            assert len(fields) >= 6
