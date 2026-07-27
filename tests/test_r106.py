"""R106: PromptVersionManager + MCP自定义规则工具"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager, PromptVersion


class TestR106VersionManager:
    def test_create_version(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm = PromptVersionManager(store)
            pv = vm.create_version("test.md", "你是一个AI助手。", author="test")
            assert pv.version_id == "v1"
            assert pv.change_type == "initial"

    def test_create_multiple_versions(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm = PromptVersionManager(store)
            vm.create_version("test.md", "版本1")
            pv2 = vm.create_version("test.md", "版本2", score=8.0, grade="A")
            assert pv2.version_id == "v2"
            assert pv2.parent_version == "v1"
            assert pv2.score == 8.0

    def test_get_versions(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm = PromptVersionManager(store)
            vm.create_version("test.md", "v1")
            vm.create_version("test.md", "v2")
            versions = vm.get_versions("test.md")
            assert len(versions) == 2

    def test_get_latest(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm = PromptVersionManager(store)
            vm.create_version("test.md", "第一版")
            vm.create_version("test.md", "第二版")
            latest = vm.get_latest("test.md")
            assert latest is not None
            assert latest.version_id == "v2"

    def test_list_templates(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm = PromptVersionManager(store)
            vm.create_version("a.md", "内容A")
            vm.create_version("b.md", "内容B")
            templates = vm.list_templates()
            assert "a.md" in templates
            assert "b.md" in templates

    def test_version_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "versions.json"
            vm1 = PromptVersionManager(store)
            vm1.create_version("test.md", "持久化测试", author="ci")
            vm2 = PromptVersionManager(store)
            versions = vm2.get_versions("test.md")
            assert len(versions) == 1
            assert versions[0].content == "持久化测试"

    def test_custom_rules_in_mcp_dispatch(self):
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        dispatch = _get_tool_dispatch()
        assert "fg_template_list" in dispatch
        assert "fg_template_generate" in dispatch
