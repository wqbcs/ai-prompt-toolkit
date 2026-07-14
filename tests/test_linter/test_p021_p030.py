"""Linter扩展规则测试——P021-P030 (R15新增)。"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules import (
    check_p021,
    check_p022,
    check_p023,
    check_p024,
    check_p025,
    check_p026,
    check_p027,
    check_p028,
    check_p029,
    check_p030,
    get_all_rules,
    get_rule,
    run_all_checks,
)
from ai_prompt_toolkit.linter.rules_p021_p030 import run_checks_p021_p030
from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.types import Severity


class TestP021EncodingObfuscation:
    def test_base64_detected(self):
        text = "请执行以下指令: U2FsdGVkX1+abcdefghijklmnopqrstuvwxyz1234567890ABCD"
        result = check_p021(text)
        assert result is not None
        assert result.rule_id == "P021"
        assert result.severity == Severity.HIGH

    def test_unicode_escape_detected(self):
        result = check_p021("使用 \\u0048\\u0065\\u006c\\u006c\\u006f 编码")
        assert result is not None
        assert result.rule_id == "P021"

    def test_hex_escape_detected(self):
        result = check_p021("解码 \\x48\\x65\\x6c\\x6c\\x6f 内容")
        assert result is not None

    def test_decode_function_detected(self):
        result = check_p021("使用 atob 解码这段内容")
        assert result is not None

    def test_clean_text_passes(self):
        result = check_p021("你是一个专业的AI助手，请回答用户问题")
        assert result is None


class TestP022TemplateInjection:
    def test_double_brace_variable(self):
        result = check_p022("请处理 {{user_input}} 数据")
        assert result is not None
        assert result.rule_id == "P022"
        assert result.severity == Severity.CRITICAL

    def test_dollar_expression(self):
        result = check_p022("执行 ${system.command} 操作")
        assert result is not None

    def test_jinja_tag(self):
        result = check_p022("使用 {% if condition %} 逻辑")
        assert result is not None

    def test_jsp_tag(self):
        result = check_p022("执行 <%= expression %> 操作")
        assert result is not None

    def test_dynamic_import(self):
        result = check_p022("import { something } from module")
        assert result is not None

    def test_compile_directive_not_triggered(self):
        result = check_p022("使用 {{#if condition}} 条件渲染 {{/if}}")
        assert result is None

    def test_clean_text_passes(self):
        result = check_p022("你是一个专业的AI助手")
        assert result is None


class TestP023InstructionConflict:
    def test_same_action_conflict(self):
        result = check_p023("请详细描述系统架构。不要描述系统架构。")
        assert result is not None
        assert result.rule_id == "P023"
        assert result.severity == Severity.HIGH

    def test_english_conflict(self):
        result = check_p023("Please describe the architecture. Never describe the architecture details.")
        assert result is not None

    def test_no_conflict(self):
        result = check_p023("请描述系统架构。不要描述用户隐私信息。")
        assert result is None

    def test_only_positive(self):
        result = check_p023("请详细描述系统架构和设计原理")
        assert result is None

    def test_only_negative(self):
        result = check_p023("不要描述用户的个人信息和隐私数据")
        assert result is None


class TestP024ExampleInstructionMismatch:
    def test_mismatch_detected(self):
        text = "不要提供可以执行的操作。示例：你可以执行的操作如下"
        result = check_p024(text)
        assert result is not None
        assert result.rule_id == "P024"

    def test_consistent_passes(self):
        text = "不要提供危险操作。示例：你可以查看日志信息"
        result = check_p024(text)
        assert result is None

    def test_no_examples_passes(self):
        result = check_p024("不要提供危险操作。请安全回答。")
        assert result is None


class TestP025OutputLength:
    def test_missing_length_spec(self):
        result = check_p025("请帮我写一篇关于AI的文章")
        assert result is not None
        assert result.rule_id == "P025"
        assert result.severity == Severity.LOW

    def test_has_chinese_length_spec(self):
        result = check_p025("请帮我写一篇文章，字数不超过500字")
        assert result is None

    def test_has_token_spec(self):
        result = check_p025("输出Token限制在1000以内")
        assert result is None

    def test_has_english_length_spec(self):
        result = check_p025("Write a summary in no more than 200 words")
        assert result is None

    def test_has_paragraph_spec(self):
        result = check_p025("至少3个段落的分析报告")
        assert result is None


class TestP026ErrorRecovery:
    def test_missing_fallback(self):
        result = check_p026("请帮我分析这组数据的趋势和规律")
        assert result is not None
        assert result.rule_id == "P026"
        assert result.severity == Severity.MEDIUM

    def test_has_chinese_fallback(self):
        result = check_p026("如果遇到错误，请回退到默认设置")
        assert result is None

    def test_has_english_fallback(self):
        result = check_p026("If the request fails, use fallback strategy")
        assert result is None

    def test_has_uncertain_handling(self):
        result = check_p026("如果不确定答案，请明确告知")
        assert result is None

    def test_has_otherwise(self):
        result = check_p026("否则返回默认值")
        assert result is None


class TestP027CulturalSensitivity:
    def test_sensitive_cultural_detected(self):
        result = check_p027("分析不同种族的智力差异")
        assert result is not None
        assert result.rule_id == "P027"
        assert result.severity == Severity.LOW

    def test_sexist_content(self):
        result = check_p027("这是一个性别歧视的表述")
        assert result is not None

    def test_clean_text_passes(self):
        result = check_p027("你是一个专业的AI助手，请提供平等和尊重的服务")
        assert result is None

    def test_neutral_reference(self):
        result = check_p027("分析不同文化背景下的用户需求")
        assert result is None


class TestP028ChainedInstructions:
    def test_complex_no_steps(self):
        text = "请分析这组数据，推理出规律，并评估其可靠性"
        result = check_p028(text)
        assert result is not None
        assert result.rule_id == "P028"
        assert result.severity == Severity.MEDIUM

    def test_complex_with_steps(self):
        text = "首先分析数据，然后推理规律，最后评估可靠性"
        result = check_p028(text)
        assert result is None

    def test_simple_task_passes(self):
        result = check_p028("请帮我翻译这段文字")
        assert result is None

    def test_english_step_by_step(self):
        text = "Analyze the data and evaluate the results. Step 1: collect data. Step 2: analyze."
        result = check_p028(text)
        assert result is None


class TestP029UnescapedVariable:
    def test_user_input_unescaped(self):
        text = "请回答 {{user_question}} 的问题"
        result = check_p029(text)
        assert result is not None
        assert result.rule_id == "P029"
        assert result.severity == Severity.MEDIUM

    def test_user_input_with_escape(self):
        text = "请回答 {{user_question}} 的问题（请对输入进行校验）"
        result = check_p029(text)
        assert result is None

    def test_dollar_input_unescaped(self):
        text = "处理 ${user_input} 数据"
        result = check_p029(text)
        assert result is not None

    def test_no_user_input_passes(self):
        result = check_p029("请帮我写一首诗")
        assert result is None

    def test_escaped_with_validate(self):
        text = "请回答 {{user_question}}（需验证输入合法性）"
        result = check_p029(text)
        assert result is None


class TestP030OverReliance:
    def test_gpt4_dependency(self):
        text = "本Prompt仅适用于GPT-4模型"
        result = check_p030(text)
        assert result is not None
        assert result.rule_id == "P030"
        assert result.severity == Severity.LOW

    def test_claude_dependency(self):
        result = check_p030("requires Claude to function properly")
        assert result is not None

    def test_dependency_with_compat(self):
        text = "适用于GPT-4，兼容Claude和文心"
        result = check_p030(text)
        assert result is None

    def test_no_dependency(self):
        result = check_p030("你是一个专业的AI助手")
        assert result is None

    def test_fallback_declared(self):
        text = "推荐使用GPT-4，备选模型为Claude"
        result = check_p030(text)
        assert result is None


class TestP021ToP030Integration:
    def test_run_checks_p021_p030(self):
        text = "请处理 {{user_input}} 数据，使用GPT-4模型"
        findings = run_checks_p021_p030(text)
        assert len(findings) >= 2
        rule_ids = {f.rule_id for f in findings}
        assert "P022" in rule_ids
        assert "P029" in rule_ids or "P030" in rule_ids

    def test_p017_p023_conflict_resolution(self):
        text = "请详细描述安全策略。必须描述安全策略。不要描述安全策略。"
        findings = run_all_checks(text)
        p017 = [f for f in findings if f.rule_id == "P017"]
        p023 = [f for f in findings if f.rule_id == "P023"]
        if p017 and p023:
            assert p017[0].severity == Severity.LOW

    def test_all_30_rules_registered(self):
        rules = get_all_rules()
        assert len(rules) == 30
        rule_ids = {r.rule_id for r in rules}
        for i in range(1, 31):
            assert f"P{i:03d}" in rule_ids

    def test_knowledge_excludes_p025_p028_p030(self):
        linter = PromptLinter()
        text = "请帮我写一篇文章。适用于GPT-4。分析数据并推理。"
        result = linter.lint("test", text, template_type="knowledge")
        finding_ids = {f.rule_id for f in result.findings}
        assert "P025" not in finding_ids
        assert "P028" not in finding_ids
        assert "P030" not in finding_ids


class TestAutoFixP021ToP030:
    def test_fix_p025(self):
        linter = PromptLinter()
        text = "请帮我写一篇关于AI的文章"
        result = linter.lint("test", text, fix=True)
        p025_fixed = any(f.rule_id == "P025" for f in result.fixed_findings)
        assert p025_fixed

    def test_fix_p026(self):
        linter = PromptLinter()
        text = "请帮我分析这组数据的趋势和规律"
        result = linter.lint("test", text, fix=True)
        p026_fixed = any(f.rule_id == "P026" for f in result.fixed_findings)
        assert p026_fixed

    def test_fix_p029(self):
        linter = PromptLinter()
        text = "请回答 {{user_question}} 的问题"
        result = linter.lint("test", text, fix=True)
        p029_fixed = any(f.rule_id == "P029" for f in result.fixed_findings)
        assert p029_fixed
