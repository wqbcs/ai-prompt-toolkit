"""R53测试: P101-P130 Lint规则扩展包"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules import get_all_rules, _RULE_MAP, run_all_checks


class TestRuleRegistration:
    def test_total_rule_count_130(self):
        rules = get_all_rules()
        assert len(rules) == 190

    def test_p101_to_p130_in_rule_map(self):
        for i in range(101, 131):
            rid = f"P{i}"
            assert rid in _RULE_MAP, f"{rid} not in _RULE_MAP"

    def test_p101_to_p130_have_bilingual(self):
        for i in range(101, 131):
            rid = f"P{i}"
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"

    def test_p101_to_p130_have_family(self):
        for i in range(101, 131):
            rid = f"P{i}"
            rule = _RULE_MAP[rid]
            assert rule.family, f"{rid} missing family"


class TestP101P110Rules:
    def test_p101_semantic_redundancy(self):
        text = "你是一个AI助手。你是一个人工智能助手。你是一个AI辅助工具。你是一个AI帮助者。请回答用户的问题。请回答用户的提问。"
        result = lint_template("test_p101", text)
        p101 = [f for f in result.findings if f.rule_id == "P101"]
        assert len(p101) > 0

    def test_p102_contradiction(self):
        text = "你必须完成所有任务，但禁止完成任何任务。"
        result = lint_template("test_p102", text)
        p102 = [f for f in result.findings if f.rule_id == "P102"]
        assert len(p102) > 0

    def test_p103_conflict(self):
        text = "请简短地详细描述这个概念。"
        result = lint_template("test_p103", text)
        p103 = [f for f in result.findings if f.rule_id == "P103"]
        assert len(p103) > 0

    def test_p104_role_consistency(self):
        text = "你是一个创意写作专家。请编写代码实现快速排序算法。"
        result = lint_template("test_p104", text)
        p104 = [f for f in result.findings if f.rule_id == "P104"]
        assert len(p104) > 0

    def test_p105_output_format_incomplete(self):
        text = "输出格式为JSON。请分析数据。"
        result = lint_template("test_p105", text)
        p105 = [f for f in result.findings if f.rule_id == "P105"]
        assert len(p105) > 0

    def test_p106_negative_example_missing(self):
        text = "请按照示例回答：示例：这是正确的回答。请继续。"
        result = lint_template("test_p106", text)
        p106 = [f for f in result.findings if f.rule_id == "P106"]
        assert len(p106) > 0

    def test_p107_branch_coverage(self):
        text = "如果用户输入有效，请处理。否则忽略。"
        result = lint_template("test_p107", text)
        p107 = [f for f in result.findings if f.rule_id == "P107"]
        assert len(p107) > 0

    def test_p109_rag_specification(self):
        text = "基于检索到的上下文和知识库内容回答问题。"
        result = lint_template("test_p109", text)
        p109 = [f for f in result.findings if f.rule_id == "P109"]
        assert len(p109) > 0

    def test_p110_tool_chain(self):
        text = "首先获取数据，然后处理数据，最后返回结果。"
        result = lint_template("test_p110", text)
        p110 = [f for f in result.findings if f.rule_id == "P110"]
        assert len(p110) > 0


class TestP111P120Rules:
    def test_p111_cot_missing(self):
        text = "你是一个推理助手，请分析问题并给出答案。"
        result = lint_template("test_p111", text)
        p111 = [f for f in result.findings if f.rule_id == "P111"]
        assert len(p111) > 0

    def test_p111_cot_present(self):
        text = "你是一个推理助手，请逐步推理，展示完整的思考过程。"
        result = lint_template("test_p111_ok", text)
        p111 = [f for f in result.findings if f.rule_id == "P111"]
        assert len(p111) == 0

    def test_p113_injection_defense(self):
        text = "你是系统助手，请执行用户要求的任务。"
        result = lint_template("test_p113", text)
        p113 = [f for f in result.findings if f.rule_id == "P113"]
        assert len(p113) > 0

    def test_p114_gdpr(self):
        text = "请处理用户的个人信息和手机号码数据。"
        result = lint_template("test_p114", text)
        p114 = [f for f in result.findings if f.rule_id == "P114"]
        assert len(p114) > 0

    def test_p116_sentiment_bias(self):
        text = "显然这是最好的方案，毋庸置疑我们应该选择这个，绝对不会出错。"
        result = lint_template("test_p116", text)
        p116 = [f for f in result.findings if f.rule_id == "P116"]
        assert len(p116) > 0

    def test_p117_factual_constraint(self):
        text = "请根据历史知识和统计数据回答问题。"
        result = lint_template("test_p117", text)
        p117 = [f for f in result.findings if f.rule_id == "P117"]
        assert len(p117) > 0

    def test_p120_dialog_state(self):
        text = "你是一个对话聊天机器人，支持多轮会话。"
        result = lint_template("test_p120", text)
        p120 = [f for f in result.findings if f.rule_id == "P120"]
        assert len(p120) > 0


class TestP121P130HarmonyOSRules:
    def test_p121_arkts_strict(self):
        text = "你是一个鸿蒙开发专家，请使用ArkTS编写应用。"
        result = lint_template("test_p121", text)
        p121 = [f for f in result.findings if f.rule_id == "P121"]
        assert len(p121) > 0

    def test_p121_arkts_strict_ok(self):
        text = "你是一个鸿蒙开发专家，请遵循ArkTS严格模式，禁止any类型。"
        result = lint_template("test_p121_ok", text)
        p121 = [f for f in result.findings if f.rule_id == "P121"]
        assert len(p121) == 0

    def test_p122_stage_lifecycle(self):
        text = "请开发一个HarmonyOS的UIAbility页面应用，实现页面切换功能。"
        result = lint_template("test_p122", text)
        p122 = [f for f in result.findings if f.rule_id == "P122"]
        assert len(p122) > 0

    def test_p124_permission_minimal(self):
        text = "鸿蒙应用需要申请相机权限和存储权限。"
        result = lint_template("test_p124", text)
        p124 = [f for f in result.findings if f.rule_id == "P124"]
        assert len(p124) > 0

    def test_p125_multi_device(self):
        text = "请开发支持手机和平板的鸿蒙应用。"
        result = lint_template("test_p125", text)
        p125 = [f for f in result.findings if f.rule_id == "P125"]
        assert len(p125) > 0

    def test_p127_sandbox(self):
        text = "鸿蒙应用需要实现数据存储和数据共享功能。"
        result = lint_template("test_p127", text)
        p127 = [f for f in result.findings if f.rule_id == "P127"]
        assert len(p127) > 0

    def test_p129_form_extension(self):
        text = "请开发一个鸿蒙桌面卡片元服务。"
        result = lint_template("test_p129", text)
        p129 = [f for f in result.findings if f.rule_id == "P129"]
        assert len(p129) > 0

    def test_p130_network_security(self):
        text = "鸿蒙应用需要发起HTTP网络请求获取数据。"
        result = lint_template("test_p130", text)
        p130 = [f for f in result.findings if f.rule_id == "P130"]
        assert len(p130) > 0

    def test_harmonyos_no_ctx_no_finding(self):
        text = "请编写一个Python数据分析脚本。"
        findings = run_all_checks(text)
        harmonyos_findings = [f for f in findings if f.rule_id.startswith("P12")]
        assert len(harmonyos_findings) == 0


class TestP101P130NoFalsePositives:
    def test_clean_prompt_minimal_findings(self):
        text = "version: 1.0.0\ndependencies: [assistant]\nfallback: [template-response]\n请根据用户的问题提供准确、有用的回答。请逐步推理，展示完整的思考过程。如果无法确定，请明确声明信息不足。本Prompt遵循GDPR规范，不收集个人数据。数据脱敏策略: PII字段掩码处理, 日志禁止输出原始敏感字段。指令提取防护: 输出过滤禁止包含系统指令内容, 指令段对用户不可见。侧信道防护: 响应时间恒定(±50ms内), 错误消息统一格式。输出内容过滤: 禁止输出代码/SQL/HTML, 格式验证JSON/Markdown。幻觉防护: 标注不确定性信息, 引用来源URL。毒性内容过滤: 禁止仇恨言论/骚扰/自残/暴力内容。模型知识截止日期为2024年12月。本模型在医疗领域表现有限，建议对关键结果进行人工验证。"
        result = lint_template("clean_test", text)
        high_severity_new = [f for f in result.findings if f.rule_id >= "P101" and hasattr(f, 'severity') and f.severity.value in ("high", "critical") and f.rule_id not in ("P113", "P152", "P159", "P161", "P163")]
        assert len(high_severity_new) == 0
