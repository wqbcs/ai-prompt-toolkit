"""R100: CHANGELOG R95-R98 + lint --changed优化 + MCP同步校验"""
from __future__ import annotations

from pathlib import Path

from ai_prompt_toolkit.mcp_server import _get_tool_dispatch, _handle_tools_list


class TestR100ChangelogAndSync:
    def test_changelog_has_r95_r98(self):
        changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
        assert "R95" in changelog
        assert "R96" in changelog
        assert "R97" in changelog
        assert "R98" in changelog
        assert "FunctionGraph" in changelog
        assert "鸿蒙NEXT API 15" in changelog

    def test_mcp_tools_dispatch_sync(self):
        dispatch = _get_tool_dispatch()
        tools_list_str = str(_handle_tools_list(0))
        mismatched = [name for name in dispatch if name not in tools_list_str]
        assert len(mismatched) == 0, f"MCP工具不同步: {mismatched}"

    def test_mcp_tool_count(self):
        dispatch = _get_tool_dispatch()
        assert len(dispatch) >= 51

    def test_fg_tools_in_dispatch(self):
        dispatch = _get_tool_dispatch()
        assert "fg_template_list" in dispatch
        assert "fg_template_generate" in dispatch
