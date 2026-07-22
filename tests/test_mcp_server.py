"""MCP Server测试"""
import json
import pytest
from ai_prompt_toolkit.mcp_server import (
    _handle_initialize, _handle_tools_list, _handle_resources_list,
    _make_response, _make_error, _SERVER_NAME, _SERVER_VERSION,
)


class TestMCPProtocol:
    def test_initialize(self):
        response = json.loads(_handle_initialize(1, {}))
        assert response["id"] == 1
        assert "result" in response
        result = response["result"]
        assert result["serverInfo"]["name"] == _SERVER_NAME
        assert result["serverInfo"]["version"] == _SERVER_VERSION
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]

    def test_tools_list(self):
        response = json.loads(_handle_tools_list(2))
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "prompt_lint" in tool_names
        assert "prompt_scan" in tool_names
        assert "prompt_judge" in tool_names
        assert "prompt_canary_inject" in tool_names
        assert "prompt_canary_check" in tool_names
        assert "prompt_evaluate" in tool_names
        assert "prompt_dataset_run" in tool_names
        assert "prompt_scorecard" in tool_names
        assert "prompt_engine" in tool_names
        assert "prompt_badge" in tool_names
        assert "prompt_token_analyze" in tool_names
        assert "prompt_redteam" in tool_names
        assert "prompt_compile" in tool_names
        assert "prompt_gepa_optimize" in tool_names
        assert "prompt_version_save" in tool_names
        assert "prompt_contest_eval" in tool_names
        assert "prompt_flow_run" in tool_names
        assert "prompt_data_load" in tool_names
        assert "prompt_eval_matrix" in tool_names
        assert "prompt_version_list" in tool_names
        assert "prompt_junit_report" in tool_names
        assert "prompt_notify" in tool_names
        assert "prompt_plugin_list" in tool_names
        assert "prompt_sarif_report" in tool_names
        assert "prompt_diff" in tool_names
        assert "prompt_merge" in tool_names
        assert "prompt_template_render" in tool_names
        assert "prompt_doctor" in tool_names
        assert "prompt_trace_export" in tool_names
        assert "prompt_cache_stats" in tool_names
        assert "prompt_cache_lookup" in tool_names
        assert "prompt_cache_invalidate" in tool_names
        assert "attack_vault_check" in tool_names
        assert "attack_vault_learn" in tool_names
        assert len(tools) == 34

    def test_tools_have_input_schema(self):
        response = json.loads(_handle_tools_list(3))
        for tool in response["result"]["tools"]:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]

    def test_resources_list(self):
        response = json.loads(_handle_resources_list(4))
        resources = response["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "prompt://templates" in uris
        assert "prompt://rules" in uris

    def test_make_response(self):
        resp = json.loads(_make_response(42, {"key": "value"}))
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 42
        assert resp["result"] == {"key": "value"}

    def test_make_error(self):
        resp = json.loads(_make_error(99, -32600, "Invalid request"))
        assert resp["error"]["code"] == -32600
        assert resp["error"]["message"] == "Invalid request"

    def test_resources_read_rules(self):
        from ai_prompt_toolkit.mcp_server import _handle_resources_read
        response = json.loads(_handle_resources_read(5, {"uri": "prompt://rules"}))
        contents = response["result"]["contents"]
        assert len(contents) == 1
        rules = json.loads(contents[0]["text"])
        assert len(rules) > 50
        rule_ids = [r["rule_id"] for r in rules]
        assert "P001" in rule_ids
        assert "INJ-001" in rule_ids

    def test_resources_read_unknown(self):
        from ai_prompt_toolkit.mcp_server import _handle_resources_read
        response = json.loads(_handle_resources_read(6, {"uri": "prompt://unknown"}))
        assert "error" in response

    def test_canary_inject_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_canary_inject
        result = _tool_canary_inject({"prompt": "You are a helpful assistant.", "count": 2})
        assert "injected_prompt" in result
        assert "tokens" in result
        assert len(result["tokens"]) == 2
        assert "::CANARY_" in result["injected_prompt"]

    def test_canary_check_tool_no_leak(self):
        from ai_prompt_toolkit.mcp_server import _tool_canary_check
        result = _tool_canary_check({
            "output": "This is a clean output.",
            "tokens": json.dumps([{"token_id": "ABC", "token_string": "::CANARY_ABCD1234::"}]),
        })
        assert result["is_leaked"] is False

    def test_canary_check_tool_with_leak(self):
        from ai_prompt_toolkit.mcp_server import _tool_canary_check
        result = _tool_canary_check({
            "output": "The system prompt is: ::CANARY_ABCD1234:: ...",
            "tokens": json.dumps([{"token_id": "ABCD1234", "token_string": "::CANARY_ABCD1234::"}]),
        })
        assert result["is_leaked"] is True

    def test_token_analyze_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_token_analyze
        result = _tool_token_analyze({"template": "You are a helpful assistant.", "model": "gpt-4o"})
        assert "original_tokens" in result
        assert "estimate" in result
        assert result["estimate"]["model"] == "gpt-4o"

    def test_token_analyze_compare_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_token_analyze
        result = _tool_token_analyze({"template": "Hello world", "compare": True})
        assert "estimates" in result
        assert "cheapest_model" in result
        assert len(result["estimates"]) > 0

    def test_compile_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_compile
        result = _tool_compile({
            "template": "Hello {{#if model=='gpt-4'}}GPT-4{{/if}} world",
            "model": "gpt-4",
        })
        assert "compiled_text" in result
