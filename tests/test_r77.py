"""R77测试: lint类别统计 + glitch probes + MCP描述更新"""

from __future__ import annotations


class TestGlitchProbes:
    def test_glitch_token_probe(self):
        from ai_prompt_toolkit.redteam.probes.glitch import GlitchTokenProbe

        probe = GlitchTokenProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) > 0
        assert probe.name == "glitch_token"
        assert "LLM01" in probe.owasp_refs

    def test_glitch_repeat_probe(self):
        from ai_prompt_toolkit.redteam.probes.glitch import GlitchRepeatProbe

        probe = GlitchRepeatProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) >= 4
        assert probe.name == "glitch_repeat"

    def test_glitch_zerowidth_probe(self):
        from ai_prompt_toolkit.redteam.probes.glitch import GlitchZeroWidthProbe

        probe = GlitchZeroWidthProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) >= 4
        assert probe.name == "glitch_zerowidth"

    def test_glitch_separator_probe(self):
        from ai_prompt_toolkit.redteam.probes.glitch import GlitchSeparatorProbe

        probe = GlitchSeparatorProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) >= 5
        assert probe.name == "glitch_separator"

    def test_glitch_probes_in_registry(self):
        from ai_prompt_toolkit.redteam.registry import list_all_probes

        probes = list_all_probes()
        for name in ("glitch_token", "glitch_repeat", "glitch_zerowidth", "glitch_separator"):
            assert name in probes, f"{name} not in registry"


class TestLintCategoryStats:
    def test_category_counts_logic(self):
        from collections import Counter

        from ai_prompt_toolkit.linter import lint_template
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        text = "你是一个AI助手，请生成输出内容。根据数据报告提供统计信息。"
        result = lint_template("test_cat", text)
        if result.findings:
            category_counts = Counter()
            for f in result.findings:
                rule = _RULE_MAP.get(f.rule_id)
                if rule:
                    category_counts[rule.category] += 1
            assert len(category_counts) > 0


class TestMCPDescriptionUpdated:
    def test_mcp_lint_description_170(self):
        import json

        from ai_prompt_toolkit.mcp_server import _handle_tools_list

        response = _handle_tools_list(1)
        data = json.loads(response)
        tools = data["result"]["tools"]
        lint_tool = next(t for t in tools if t["name"] == "prompt_lint")
        assert "255" in lint_tool["description"]  # R164扩容后实际值
        assert "P001-P255" in lint_tool["description"]  # R164扩容后实际值

    def test_output_scan_tool_exists(self):
        import json

        from ai_prompt_toolkit.mcp_server import _handle_tools_list

        response = _handle_tools_list(1)
        data = json.loads(response)
        tools = data["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "output_scan" in names
        assert "deveco_config" in names
