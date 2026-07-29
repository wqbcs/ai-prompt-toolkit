"""R156: MCP热重载(mcp_reload)"""
import pytest
from ai_prompt_toolkit.mcp_server import _tool_mcp_reload


def test_mcp_reload_default():
    result = _tool_mcp_reload({})
    assert result["status"] == "reloaded"
    assert result["rule_count"] > 0


def test_mcp_reload_rules_module():
    result = _tool_mcp_reload({"module": "ai_prompt_toolkit.linter.rules"})
    assert result["status"] == "reloaded"
    assert result["module"] == "ai_prompt_toolkit.linter.rules"


def test_mcp_reload_invalid_module():
    result = _tool_mcp_reload({"module": "nonexistent.module.xyz"})
    assert result["status"] == "error"


def test_mcp_reload_fixer_module():
    result = _tool_mcp_reload({"module": "ai_prompt_toolkit.linter.fixer"})
    assert result["status"] == "reloaded"
