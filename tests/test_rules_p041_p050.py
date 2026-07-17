"""测试 P041-P050 lintlang参考检测器 + 中文特有规则"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules_p041_p050 import (
    check_p041, check_p042, check_p043, check_p044, check_p045,
    check_p046, check_p047, check_p048, check_p049, check_p050,
    run_checks_p041_p050,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestP041ToolDescriptionAmbiguity:
    def test_pass_no_tool(self):
        text = "你是一个翻译助手，请将以下内容翻译为英文。"
        assert check_p041(text) is None

    def test_pass_clear_description(self):
        text = """工具说明：翻译工具
        功能：将中文文本翻译为英文
        参数：text(中文文本，type:string)
        返回：英文翻译结果"""
        assert check_p041(text) is None

    def test_fail_vague_description(self):
        text = "工具说明：处理数据\n函数描述：do stuff"
        result = check_p041(text)
        assert result is not None
        assert result.rule_id == "P041"


class TestP042MissingConstraintScaffold:
    def test_pass_no_tool(self):
        text = "你是一个翻译助手。"
        assert check_p042(text) is None

    def test_pass_with_constraint(self):
        text = """工具函数：search
        当搜索无结果时，返回空列表
        如果API不可用，使用缓存数据"""
        assert check_p042(text) is None

    def test_fail_no_constraint(self):
        text = "可用的工具函数：search, translate, summarize"
        result = check_p042(text)
        assert result is not None
        assert result.rule_id == "P042"


class TestP043SchemaIntentMismatch:
    def test_pass_no_schema(self):
        text = "你是一个翻译助手。"
        assert check_p043(text) is None

    def test_pass_schema_with_intent(self):
        text = """参数：query(type:string)
        目的：用于搜索相关文档
        返回：搜索结果列表"""
        assert check_p043(text) is None

    def test_fail_schema_no_intent(self):
        text = """参数：query(type:string)
        参数：limit(type:integer)
        返回：搜索结果列表"""
        result = check_p043(text)
        assert result is not None
        assert result.rule_id == "P043"


class TestP044ContextBoundaryErosion:
    def test_pass_no_context(self):
        text = "你是一个翻译助手。"
        assert check_p044(text) is None

    def test_pass_with_boundary(self):
        text = "将上下文传递给工具时，禁止传递敏感字段，需要对数据脱敏。"
        assert check_p044(text) is None

    def test_fail_no_boundary(self):
        text = "将上下文信息和会话历史传递给工具函数。"
        result = check_p044(text)
        assert result is not None
        assert result.rule_id == "P044"


class TestP045ImplicitInstruction:
    def test_pass_no_implicit(self):
        text = "你是一个翻译助手。"
        assert check_p045(text) is None

    def test_pass_explicit(self):
        text = "必须明确告知用户结果，不要假设任何前提条件。"
        assert check_p045(text) is None

    def test_fail_implicit(self):
        text = "默认用户已经了解基本概念，隐含地认为用户同意条款。"
        result = check_p045(text)
        assert result is not None
        assert result.rule_id == "P045"


class TestP046TemplateFormatContract:
    def test_pass_no_template_vars(self):
        text = "你是一个翻译助手。"
        assert check_p046(text) is None

    def test_pass_with_format_spec(self):
        text = "格式：请使用{{name}}和{{age}}变量，格式模板如下。"
        assert check_p046(text) is None

    def test_fail_no_format_spec(self):
        text = "你好{{name}}，你的年龄是{{age}}，欢迎${company}。"
        result = check_p046(text)
        assert result is not None
        assert result.rule_id == "P046"


class TestP047RoleConfusion:
    def test_pass_single_role(self):
        text = "你是一个翻译助手。"
        assert check_p047(text) is None

    def test_pass_separated_roles(self):
        text = """角色一：翻译专家
        ---
        角色二：审核专家"""
        assert check_p047(text) is None

    def test_fail_confused_roles(self):
        text = "你是一个翻译专家，同时你又是审核专家，兼具两种角色。"
        result = check_p047(text)
        assert result is not None
        assert result.rule_id == "P047"


class TestP048ChinesePunctuationMixing:
    def test_pass_pure_chinese(self):
        text = "你是一个翻译助手，请将以下内容翻译为英文。"
        assert check_p048(text) is None

    def test_pass_pure_english(self):
        text = "You are a translator, please translate the following."
        assert check_p048(text) is None

    def test_fail_mixed_punctuation(self):
        text = "你好,请将内容翻译为英文.谢谢！"
        result = check_p048(text)
        assert result is not None
        assert result.rule_id == "P048"


class TestP049TokenEstimate:
    def test_pass_short_text(self):
        text = "你是一个翻译助手。"
        assert check_p049(text) is None

    def test_fail_long_text(self):
        text = "你是一个助手。" * 2000
        result = check_p049(text)
        assert result is not None
        assert result.rule_id == "P049"
        assert result.details["estimated_tokens"] > 4000

    def test_critical_long_text(self):
        text = "你是一个助手。" * 5000
        result = check_p049(text)
        assert result is not None
        assert result.severity == Severity.HIGH


class TestP050ChineseRedundancy:
    def test_pass_clean_text(self):
        text = "你是一个翻译助手，请翻译以下内容。"
        assert check_p050(text) is None

    def test_fail_redundant(self):
        text = "这是很重要的的了，的话的话请注意您您。"
        result = check_p050(text)
        assert result is not None
        assert result.rule_id == "P050"


class TestRunChecksP041P050:
    def test_clean_prompt(self):
        text = "你是一个专业的翻译助手。请将用户输入的中文文本翻译为英文，输出JSON格式。"
        findings = run_checks_p041_p050(text)
        non_low = [f for f in findings if f.severity >= Severity.MEDIUM]
        assert len(non_low) == 0

    def test_multiple_issues(self):
        text = "你好,这是测试.工具说明：处理数据。将上下文传递给工具。默认用户了解基本概念。你好{{name}}。你是一个翻译专家，同时你又是审核专家。"
        findings = run_checks_p041_p050(text)
        assert len(findings) > 0
