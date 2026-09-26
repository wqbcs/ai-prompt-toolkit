"""R136 测试: eval-multi多模板评估对比"""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


class TestR136Multi:
    def test_eval_multi_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a.md"
            f2 = Path(tmpdir) / "b.md"
            f1.write_text("你是一个专业翻译助手。", encoding="utf-8")
            f2.write_text("你是代码审查专家，请审查代码安全性。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["eval-multi", "-t", f"{f1},{f2}"])
            assert "评估对比" in result.output or "最优" in result.output

    def test_eval_multi_has_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a.md"
            f2 = Path(tmpdir) / "b.md"
            f1.write_text("你是一个翻译助手。", encoding="utf-8")
            f2.write_text("你是安全审计专家。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["eval-multi", "-t", f"{f1},{f2}"])
            assert "| 维度 |" in result.output
            assert "| **均分** |" in result.output

    def test_eval_multi_single_file_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a.md"
            f1.write_text("测试", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["eval-multi", "-t", str(f1)])
            assert "至少2" in result.output
