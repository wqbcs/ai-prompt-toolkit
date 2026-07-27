"""R70测试: Lint规则P141-P145 Agent/Tool-Use专项 + 评估维度D86-D90"""
from __future__ import annotations

import pytest


class TestP141AgentGoal:
    def test_triggers_on_agent_without_goal(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p141
        result = check_p141("你是一个Agent，根据用户请求调用工具完成任务")
        assert result is not None
        assert result.rule_id == "P141"

    def test_passes_with_goal(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p141
        result = check_p141("你是一个Agent，目标是帮助用户查询信息，禁止执行删除操作，完成查询后停止")
        assert result is None

    def test_not_triggered_without_agent(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p141
        result = check_p141("你是一个助手，帮助用户解决问题")
        assert result is None


class TestP142ToolPermission:
    def test_triggers_on_tool_without_permission(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p142
        result = check_p142("你是一个Agent，可以调用API和工具完成任务")
        assert result is not None
        assert result.rule_id == "P142"

    def test_passes_with_permission(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p142
        result = check_p142("你是一个Agent，仅可调用查询API，禁止执行删除和修改操作，遵循最小权限原则")
        assert result is None

    def test_not_triggered_without_agent(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p142
        result = check_p142("你可以使用API查询数据")
        assert result is None


class TestP143LoopGuard:
    def test_triggers_on_agent_without_loop_guard(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p143
        result = check_p143("你是一个Agent，反复尝试直到成功")
        assert result is not None
        assert result.rule_id == "P143"

    def test_passes_with_loop_guard(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p143
        result = check_p143("你是一个Agent，最大迭代次数为10次，超过限制时输出当前结果并停止")
        assert result is None


class TestP144ContextManagement:
    def test_triggers_on_agent_without_context_mgmt(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p144
        result = check_p144("你是一个智能体，持续处理用户请求并保持完整对话历史")
        assert result is not None
        assert result.rule_id == "P144"

    def test_passes_with_context_mgmt(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p144
        result = check_p144("你是一个智能体，上下文超过8K Token时采用滑动窗口策略，对历史对话进行摘要压缩")
        assert result is None


class TestP145MultiAgentConflict:
    def test_triggers_on_multi_agent_without_conflict_res(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p145
        result = check_p145("系统包含多个Agent协同工作，各Agent独立执行任务")
        assert result is not None
        assert result.rule_id == "P145"

    def test_passes_with_conflict_res(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p145
        result = check_p145("多Agent系统，Agent间通过协议通信，冲突时由协调者裁决，设置超时机制防止死锁")
        assert result is None

    def test_not_triggered_single_agent(self):
        from ai_prompt_toolkit.linter.rules_p141_p145 import check_p145
        result = check_p145("你是一个Agent，帮助用户完成任务")
        assert result is None


class TestRuleCount150:
    def test_rule_map_has_150(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        assert len(_RULE_MAP) == 170

    def test_p141_p145_in_rule_map(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        for rid in ("P141", "P142", "P143", "P144", "P145"):
            assert rid in _RULE_MAP

    def test_p141_p145_have_english_descriptions(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        for rid in ("P141", "P142", "P143", "P144", "P145"):
            rule = _RULE_MAP[rid]
            assert rule.description_en
            assert rule.remediation_en


class TestD86D90Dimensions:
    def test_dimensions_count_90(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        assert len(_DIMENSIONS) == 120

    def test_d86_d90_in_dimensions(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        dim_ids = {d["id"] for d in _DIMENSIONS}
        for did in ("D86", "D87", "D88", "D89", "D90"):
            assert did in dim_ids

    def test_d86_cache_reuse(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("你是一个缓存友好的助手，使用前缀缓存策略，TTL为24小时")
        score = ev._eval_r70_dimensions("D86")
        assert score > 3.0

    def test_d87_rag_precision(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("RAG检索系统，Top-K=5，相似度阈值0.85，使用FAISS向量索引")
        score = ev._eval_r70_dimensions("D87")
        assert score > 3.0

    def test_d88_streaming(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("流式输出，使用SSE格式，增量返回结果")
        score = ev._eval_r70_dimensions("D88")
        assert score > 3.0

    def test_d89_multi_tenant(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("多租户系统，租户ID隔离，RBAC权限控制，数据隔离")
        score = ev._eval_r70_dimensions("D89")
        assert score > 3.0

    def test_d90_domestic_chip(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("昇腾NPU推理适配，CANN ATC模型转换，FP16精度，MindSpore框架")
        score = ev._eval_r70_dimensions("D90")
        assert score > 3.0

    def test_d86_low_without_cache(self):
        from ai_prompt_toolkit.evaluator import _DimensionEvaluator
        ev = _DimensionEvaluator("你是一个普通的助手，帮助用户回答问题")
        score = ev._eval_r70_dimensions("D86")
        assert score <= 3.0


class TestMCPNewTools:
    def test_multimodal_token_estimate(self):
        from ai_prompt_toolkit.mcp_server import _tool_multimodal_token_estimate
        result = _tool_multimodal_token_estimate({"text": "Hello world", "image_width": 1024, "image_height": 768, "image_detail": "low"})
        assert "text_tokens" in result
        assert result["image_tokens"] == 85

    def test_config_hot_reload_status(self):
        from ai_prompt_toolkit.mcp_server import _tool_config_hot_reload_status
        result = _tool_config_hot_reload_status({})
        assert "running" in result
        assert "watch_count" in result

    def test_badge_generate_themed(self):
        from ai_prompt_toolkit.mcp_server import _tool_badge_generate_themed
        result = _tool_badge_generate_themed({"score": 90, "grade": "A", "theme": "huawei"})
        assert "svg" in result
        assert result["theme"] == "huawei"

    def test_badge_generate_invalid_theme(self):
        from ai_prompt_toolkit.mcp_server import _tool_badge_generate_themed
        result = _tool_badge_generate_themed({"score": 80, "grade": "B", "theme": "invalid"})
        assert result["theme"] == "light"

    def test_harmonyos_arkui_check(self):
        from ai_prompt_toolkit.mcp_server import _tool_harmonyos_arkui_check
        result = _tool_harmonyos_arkui_check({"text": "使用ArkUI开发鸿蒙应用，包含Row和Column布局"})
        assert "has_arkui_context" in result
        assert result["has_arkui_context"] is True

    def test_harmonyos_arkui_check_empty(self):
        from ai_prompt_toolkit.mcp_server import _tool_harmonyos_arkui_check
        result = _tool_harmonyos_arkui_check({"text": ""})
        assert "error" in result

    def test_harmonyos_stage_model_check(self):
        from ai_prompt_toolkit.mcp_server import _tool_harmonyos_stage_model_check
        result = _tool_harmonyos_stage_model_check({"text": "使用Stage模型开发UIAbility，声明onCreate和onDestroy生命周期，通过Context和want进行Ability间交互"})
        assert "has_stage_context" in result
        assert result["pass"] is True

    def test_harmonyos_distributed_check(self):
        from ai_prompt_toolkit.mcp_server import _tool_harmonyos_distributed_check
        result = _tool_harmonyos_distributed_check({"text": "鸿蒙分布式能力，设备发现和数据迁移"})
        assert "has_distributed_context" in result
        assert result["has_distributed_context"] is True

    def test_mcp_dispatch_has_new_tools(self):
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        dispatch = _get_tool_dispatch()
        assert "multimodal_token_estimate" in dispatch
        assert "config_hot_reload_status" in dispatch
        assert "badge_generate_themed" in dispatch
        assert "harmonyos_arkui_check" in dispatch
        assert "harmonyos_stage_model_check" in dispatch
        assert "harmonyos_distributed_check" in dispatch


class TestHuaweiCloudSecurityBaseline:
    def test_security_baseline_exists(self):
        from ai_prompt_toolkit.compliance_report import _HWCLOUD_SECURITY_BASELINE
        assert len(_HWCLOUD_SECURITY_BASELINE) == 4

    def test_security_baseline_ids(self):
        from ai_prompt_toolkit.compliance_report import _HWCLOUD_SECURITY_BASELINE
        ids = [item.requirement_id for item in _HWCLOUD_SECURITY_BASELINE]
        assert "HWC-SEC-01" in ids
        assert "HWC-SEC-02" in ids
        assert "HWC-SEC-03" in ids
        assert "HWC-SEC-04" in ids

    def test_compliance_report_includes_security_baseline(self):
        from ai_prompt_toolkit.compliance_report import generate_compliance_report
        report = generate_compliance_report(project_name="test")
        sec_ids = [item.requirement_id for item in report.items if item.category == "hwcloud_security"]
        assert len(sec_ids) == 4
