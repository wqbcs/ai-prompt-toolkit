"""Linter单元测试——P001-P020规则、自动修复。"""
from __future__ import annotations

import pytest

from prompt_toolkit.linter.linter import FixAction, LintResult, PromptLinter
from prompt_toolkit.linter.rules import (
    LintRule,
    check_p001,
    check_p002,
    check_p003,
    check_p004,
    check_p005,
    check_p006,
    check_p007,
    check_p008,
    check_p009,
    check_p010,
    check_p011,
    check_p012,
    check_p013,
    check_p014,
    check_p015,
    check_p016,
    check_p017,
    check_p018,
    check_p019,
    check_p020,
    get_all_rules,
    get_rule,
    run_all_checks,
)
from prompt_toolkit.types import Finding, Severity


class TestStructureRules:
    def test_p001_missing_role(self):
        result = check_p001("请帮我翻译这段文字")
        assert result is not None
        assert result.rule_id == "P001"

    def test_p001_has_role(self):
        result = check_p001("你是一个专业翻译，请帮我翻译这段文字")
        assert result is None

    def test_p001_has_role_english(self):
        result = check_p001("You are a professional translator. Translate this.")
        assert result is None

    def test_p002_missing_output_format(self):
        result = check_p002("请帮我总结这段文字")
        assert result is not None
        assert result.rule_id == "P002"

    def test_p002_has_output_format(self):
        result = check_p002("请以JSON格式输出结果")
        assert result is None

    def test_p003_missing_constraints(self):
        result = check_p003("请帮我写一篇文章")
        assert result is not None
        assert result.rule_id == "P003"

    def test_p003_has_constraints(self):
        result = check_p003("请帮我写一篇文章，不要超过500字")
        assert result is None

    def test_p004_too_long(self):
        long_text = "a" * 2500
        result = check_p004(long_text)
        assert result is not None
        assert result.rule_id == "P004"

    def test_p004_normal_length(self):
        result = check_p004("正常长度的Prompt")
        assert result is None

    def test_p005_too_short(self):
        result = check_p005("Hi")
        assert result is not None
        assert result.rule_id == "P005"

    def test_p005_normal_length(self):
        result = check_p005("这是一个正常长度的Prompt，包含了足够的上下文信息")
        assert result is None


class TestSecurityRules:
    def test_p006_sensitive_info(self):
        result = check_p006("api_key=sk-1234567890abcdef")
        assert result is not None
        assert result.rule_id == "P006"

    def test_p006_clean(self):
        result = check_p006("请帮我翻译这段文字")
        assert result is None

    def test_p007_injection_risk_no_escape(self):
        result = check_p007("处理用户输入：{{user_input}}")
        assert result is not None
        assert result.rule_id == "P007"

    def test_p007_injection_risk_with_escape(self):
        result = check_p007("处理用户输入：{{user_input}}，注意转义和校验")
        assert result is None

    def test_p008_broad_permission(self):
        result = check_p008("你可以做任何事情，允许所有操作")
        assert result is not None
        assert result.rule_id == "P008"

    def test_p009_no_audit(self):
        result = check_p009("请帮我处理数据")
        assert result is not None
        assert result.rule_id == "P009"

    def test_p009_has_audit(self):
        result = check_p009("请帮我处理数据，并记录审计日志")
        assert result is None

    def test_p010_no_fallback(self):
        result = check_p010("请帮我完成任务")
        assert result is not None
        assert result.rule_id == "P010"

    def test_p010_has_fallback(self):
        result = check_p010("如果失败请回退到默认方案")
        assert result is None


class TestPerformanceRules:
    def test_p011_token_waste(self):
        lines = ["", "  ", "a", "", "  ", "b", "", "  "]
        text = "\n".join(lines)
        result = check_p011(text)
        assert result is not None
        assert result.rule_id == "P011"

    def test_p012_redundancy(self):
        text = "请帮我翻译这段文字。请帮我翻译这段文字。"
        result = check_p012(text)
        assert result is not None
        assert result.rule_id == "P012"

    def test_p014_deep_nesting(self):
        text = "{{{{{{{{deep nesting}}}}}}}}"
        result = check_p014(text)
        assert result is not None
        assert result.rule_id == "P014"

    def test_p015_too_many_constraints(self):
        constraints = "不要X 不要Y 不要Z 不可A 不可B 禁止C 禁止D 不能E 不能F 不允许G 不得H 切勿I must not J do not K"
        result = check_p015(constraints)
        assert result is not None
        assert result.rule_id == "P015"


class TestQualityRules:
    def test_p016_ambiguous(self):
        result = check_p016("这可能大概也许是正确的结果")
        assert result is not None
        assert result.rule_id == "P016"

    def test_p016_clear(self):
        result = check_p016("请务必完成以下任务")
        assert result is None

    def test_p018_no_fewshot(self):
        result = check_p018("请帮我翻译这段文字")
        assert result is not None
        assert result.rule_id == "P018"

    def test_p018_has_fewshot(self):
        result = check_p018("示例：输入hello，输出你好。请帮我翻译。")
        assert result is None

    def test_p019_no_cot(self):
        result = check_p019("请分析和推理这个复杂问题，然后比较两种方案的优劣并做出判断")
        assert result is not None
        assert result.rule_id == "P019"

    def test_p019_has_cot(self):
        result = check_p019("请一步步分析这个复杂问题")
        assert result is None

    def test_p020_no_eval_criteria(self):
        result = check_p020("请帮我写一篇文章")
        assert result is not None
        assert result.rule_id == "P020"

    def test_p020_has_eval_criteria(self):
        result = check_p020("请帮我写一篇文章，评估标准为准确性和完整性")
        assert result is None


class TestPromptLinter:
    def test_lint_clean_template(self):
        linter = PromptLinter()
        text = (
            "你是一个专业的翻译助手。请将以下内容翻译为中文。"
            "输出格式为Markdown。不要遗漏任何内容。"
            "如果遇到无法翻译的内容，请保留原文。"
            "示例：输入Hello，输出你好。"
            "评估标准为翻译准确性和完整性。"
        )
        result = linter.lint("tpl-clean", text)
        assert isinstance(result, LintResult)
        assert result.template_id == "tpl-clean"

    def test_lint_problematic_template(self):
        linter = PromptLinter()
        text = "Hi"
        result = linter.lint("tpl-bad", text)
        assert result.failed_count > 0
        assert not result.is_clean

    def test_lint_with_rule_filter(self):
        linter = PromptLinter(rules=["P001", "P005"])
        text = "Hi"
        result = linter.lint("tpl-filter", text)
        finding_ids = {f.rule_id for f in result.findings}
        assert finding_ids.issubset({"P001", "P005"})

    def test_lint_with_exclude(self):
        linter = PromptLinter(exclude=["P005"])
        text = "Hi"
        result = linter.lint("tpl-exclude", text)
        finding_ids = {f.rule_id for f in result.findings}
        assert "P005" not in finding_ids

    def test_lint_batch(self):
        linter = PromptLinter()
        items = [
            ("tpl-1", "你是一个专业助手。请以JSON格式输出。不要超出范围。"),
            ("tpl-2", "Hi"),
        ]
        results = linter.lint_batch(items)
        assert len(results) == 2


class TestAutoFix:
    def test_fix_p005_too_short(self):
        linter = PromptLinter()
        text = "Hi"
        result = linter.lint("tpl-fix", text, fix=True)
        assert result.auto_fixed is True

    def test_fix_p016_ambiguous(self):
        linter = PromptLinter()
        text = "这可能大概也许是正确的结果"
        result = linter.lint("tpl-fix", text, fix=True)
        assert result.auto_fixed is True

    def test_fix_p006_sensitive(self):
        linter = PromptLinter()
        text = "使用api_key=sk-1234567890abcdef连接"
        result = linter.lint("tpl-fix", text, fix=True)
        assert result.auto_fixed is True


class TestRuleRegistry:
    def test_get_all_rules_count(self):
        rules = get_all_rules()
        assert len(rules) == 20

    def test_get_rule_exists(self):
        rule = get_rule("P001")
        assert rule is not None
        assert rule.rule_id == "P001"

    def test_get_rule_not_exists(self):
        rule = get_rule("P999")
        assert rule is None

    def test_run_all_checks(self):
        findings = run_all_checks("Hi")
        assert isinstance(findings, list)
        assert len(findings) > 0

    def test_lint_result_score(self):
        linter = PromptLinter()
        result = linter.lint("tpl-score", "Hi")
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 100.0

    def test_lint_result_has_errors(self):
        linter = PromptLinter()
        result = linter.lint("tpl-err", "Hi")
        assert isinstance(result.has_errors, bool)

    def test_lint_result_to_dict(self):
        linter = PromptLinter()
        result = linter.lint("tpl-dict", "Hi")
        d = result.to_dict()
        assert "template_id" in d
        assert "score" in d
        assert "findings" in d
