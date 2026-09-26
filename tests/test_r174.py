"""R174测试: 入口一致性 — prompt别名 + prompt-cli mcp stdio + 版本动态化"""

from __future__ import annotations

import json
import subprocess
import sys

from ai_prompt_toolkit import __version__
from ai_prompt_toolkit.cli_core import main


class TestCommandRegistry:
    """文档引用的命令必须真实注册(新用户第一分钟体验守护)"""

    def test_doc_referenced_commands_exist(self):
        # README/示例中引用的命令(历史漂移修复: scorecard→score, diff→prompt-diff)
        for cmd in (
            "lint",
            "scan",
            "evaluate",
            "score",
            "prompt-diff",
            "mcp",
            "serve",
            "badge",
            "doctor",
            "wizard",
            "trace",
            "judge",
            "redteam",
        ):
            assert cmd in main.commands, f"命令 {cmd} 未注册"

    def test_mcp_tools_count_is_73(self):
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch

        assert len(_get_tool_dispatch()) == 73


class TestMcpCommand:
    """prompt-cli mcp — MCP Server stdio入口"""

    def test_validate_only(self, capsys):
        from click.testing import CliRunner

        result = CliRunner().invoke(main, ["mcp", "--validate-only"])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_initialize_response(self):
        """端到端: stdin喂initialize请求, stdout返回JSON-RPC响应"""
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.argv = ['prompt-cli', 'mcp']; from ai_prompt_toolkit.cli_core import main; main()",
            ],
            input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n',
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        line = (proc.stdout or "").strip().split("\n")[0]
        assert line, f"无响应: {proc.stderr[-300:]}"
        resp = json.loads(line)
        assert resp["result"]["serverInfo"]["name"] == "ai-prompt-toolkit"
        # R174: 版本动态取包版本(修复硬编码42.0.0漂移)
        assert resp["result"]["serverInfo"]["version"] == __version__

    def test_server_version_matches_package(self):
        from ai_prompt_toolkit.mcp_server import _SERVER_VERSION

        assert __version__ == _SERVER_VERSION
