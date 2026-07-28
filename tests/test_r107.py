"""R107: 评估Tracing增强 + MCP Prompt版本管理工具"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


class TestR107TracingAndVersionMCP:
    def test_eval_store_record_trace(self):
        from ai_prompt_toolkit.eval_store import EvalStore
        td = tempfile.mkdtemp()
        try:
            store = EvalStore(Path(td) / "test.db")
            from ai_prompt_toolkit.evaluator import evaluate_template
            report = evaluate_template("test", "你是一个AI助手。")
            snapshot = store.save(report)
            trace_id = store.record_trace(snapshot.snapshot_id, "evaluate", dimension_id="D01", latency_ms=150.5, token_count=200)
            assert trace_id > 0
            store.close()
        finally:
            try:
                os.unlink(str(Path(td) / "test.db"))
            except Exception:
                pass

    def test_eval_store_get_traces(self):
        from ai_prompt_toolkit.eval_store import EvalStore
        td = tempfile.mkdtemp()
        try:
            store = EvalStore(Path(td) / "test.db")
            from ai_prompt_toolkit.evaluator import evaluate_template
            report = evaluate_template("test", "你是一个AI助手。")
            snapshot = store.save(report)
            store.record_trace(snapshot.snapshot_id, "lint", latency_ms=50)
            store.record_trace(snapshot.snapshot_id, "scan", latency_ms=100)
            traces = store.get_traces(snapshot_id=snapshot.snapshot_id)
            assert len(traces) == 2
            store.close()
        finally:
            try:
                os.unlink(str(Path(td) / "test.db"))
            except Exception:
                pass

    def test_eval_store_trace_stats(self):
        from ai_prompt_toolkit.eval_store import EvalStore
        td = tempfile.mkdtemp()
        try:
            store = EvalStore(Path(td) / "test.db")
            stats = store.get_trace_stats()
            assert "count" in stats
            assert "avg_latency_ms" in stats
            store.close()
        finally:
            try:
                os.unlink(str(Path(td) / "test.db"))
            except Exception:
                pass

    def test_mcp_prompt_version_create(self):
        from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager
        td = tempfile.mkdtemp()
        vm = PromptVersionManager(Path(td) / "versions.json")
        pv = vm.create_version("mcp_test.md", "测试版本", author="ci", score=8.0, grade="A")
        assert pv.version_id == "v1"
        assert pv.change_type == "initial"

    def test_mcp_prompt_version_list(self):
        from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager
        td = tempfile.mkdtemp()
        vm = PromptVersionManager(Path(td) / "versions.json")
        vm.create_version("list_test.md", "v1内容")
        vm.create_version("list_test.md", "v2内容")
        versions = vm.get_versions("list_test.md")
        assert len(versions) == 2

    def test_mcp_dispatch_has_version_tools(self):
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        dispatch = _get_tool_dispatch()
        assert "prompt_version_create" in dispatch
        assert "prompt_version_list" in dispatch
