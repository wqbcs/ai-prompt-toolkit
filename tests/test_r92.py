"""R92: scan --explain + MCP工具扩展 + __init__.py版本"""
from __future__ import annotations

from ai_prompt_toolkit import __version__
from ai_prompt_toolkit.evaluator import list_weight_presets
from ai_prompt_toolkit.prompt_diff import rollback_safety_check
from ai_prompt_toolkit.html_report import generate_html_report


def test_version_50():
    assert __version__ == "67.0.0"  # R164扩容后实际值(原R92快照50.0.0已过期)


def test_weight_preset_list_callable():
    presets = list_weight_presets()
    assert len(presets) == 7


def test_rollback_safety_mcp_style():
    old = "禁止SQL注入。验证所有输入。"
    new = "你是一个助手。"
    result = rollback_safety_check(old, new)
    d = result.to_dict()
    assert "is_safe" in d
    assert d["risk_level"] == "dangerous"


def test_html_report_mcp_style():
    findings = [{"rule_id": "P001", "severity": "HIGH", "category": "structure", "name": "test", "message": "msg"}]
    html = generate_html_report(findings, "test.md")
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html


def test_mcp_dispatch_has_new_tools():
    from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
    dispatch = _get_tool_dispatch()
    assert "rollback_safety_check" in dispatch
    assert "html_report_generate" in dispatch
    assert "weight_preset_list" in dispatch


def test_mcp_tools_list_has_new_tools():
    import json
    from ai_prompt_toolkit.mcp_server import _handle_tools_list
    response = _handle_tools_list(1)
    data = json.loads(response)
    tool_names = [t["name"] for t in data["result"]["tools"]]
    assert "rollback_safety_check" in tool_names
    assert "html_report_generate" in tool_names
    assert "weight_preset_list" in tool_names
