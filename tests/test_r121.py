"""R121 测试: eval --format markdown + MCP prompt_version_diff"""
from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


class TestR121EvalMarkdown:
    def test_eval_format_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个专业的翻译助手，请将中文翻译为英文。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["evaluate", "-t", str(fpath), "--format", "markdown", "--quick"])
            assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
            assert "评估" in result.output or "均分" in result.output

    def test_eval_format_markdown_has_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("你是一个专业的翻译助手。", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["evaluate", "-t", str(fpath), "--format", "markdown", "--quick"])
            assert result.exit_code == 0
            assert "| 维度 |" in result.output
            assert "|------|" in result.output


class TestR121MCPVersionDiff:
    def test_prompt_version_diff_registered(self):
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        dispatch = _get_tool_dispatch()
        assert "prompt_version_diff" in dispatch

    def test_prompt_version_diff_in_tools_list(self):
        import json as _json
        from ai_prompt_toolkit.mcp_server import _handle_tools_list
        resp = _handle_tools_list(1)
        data = _json.loads(resp)
        tool_names = [t["name"] for t in data["result"]["tools"]]
        assert "prompt_version_diff" in tool_names

    def test_prompt_version_diff_execution(self):
        from ai_prompt_toolkit.mcp_server import _tool_prompt_version_diff
        result = _tool_prompt_version_diff({
            "template_id": "nonexistent",
            "version_id_1": "v1",
            "version_id_2": "v2",
        })
        assert "error" in result or "template_id" in result
