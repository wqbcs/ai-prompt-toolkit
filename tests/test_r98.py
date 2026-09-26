"""R98: 华为云FunctionGraph Prompt模板 + MCP工具"""

from __future__ import annotations

from ai_prompt_toolkit.huawei_cloud.fg_template import (
    FGTemplateType,
    get_fg_template,
    list_fg_templates,
)


class TestR98FGTemplate:
    def test_list_fg_templates(self):
        templates = list_fg_templates()
        assert len(templates) == 4
        types = {t["type"] for t in templates}
        assert "ai_inference" in types
        assert "conversation" in types
        assert "embedding" in types
        assert "content_moderation" in types

    def test_get_ai_inference_template(self):
        t = get_fg_template("ai_inference", name="my_inference", description="AI推理")
        assert t.name == "my_inference"
        assert t.template_type == FGTemplateType.AI_INFERENCE
        assert "handler" in t.code
        assert "MODEL_ENDPOINT" in t.code

    def test_get_conversation_template(self):
        t = get_fg_template("conversation")
        assert t.template_type == FGTemplateType.CONVERSATION
        assert "session_id" in t.code
        assert "HISTORY_BUCKET" in t.code or "OBS" in t.code

    def test_get_embedding_template(self):
        t = get_fg_template("embedding")
        assert t.template_type == FGTemplateType.EMBEDDING
        assert "EMBEDDING_ENDPOINT" in t.code

    def test_get_content_moderation_template(self):
        t = get_fg_template("content_moderation")
        assert t.template_type == FGTemplateType.CONTENT_MODERATION
        assert "moderation" in t.code.lower() or "Moderation" in t.code

    def test_template_has_env_vars(self):
        for tt in FGTemplateType:
            if tt == FGTemplateType.CUSTOM:
                continue
            t = get_fg_template(tt.value)
            assert len(t.env_vars) > 0, f"{tt.value} has no env_vars"

    def test_template_has_prompt_variables(self):
        for tt in FGTemplateType:
            if tt == FGTemplateType.CUSTOM:
                continue
            t = get_fg_template(tt.value)
            assert len(t.prompt_variables) > 0, f"{tt.value} has no prompt_variables"

    def test_template_version(self):
        t = get_fg_template("ai_inference")
        assert t.version == "1.0.0"

    def test_mcp_fg_template_list(self):
        from ai_prompt_toolkit.mcp_server import _tool_fg_template_list

        result = _tool_fg_template_list({})
        assert "templates" in result
        assert result["count"] == 4

    def test_mcp_fg_template_generate(self):
        from ai_prompt_toolkit.mcp_server import _tool_fg_template_generate

        result = _tool_fg_template_generate({"template_type": "ai_inference", "name": "test_fn"})
        assert result["name"] == "test_fn"
        assert "code" in result
        assert len(result["code"]) > 100
