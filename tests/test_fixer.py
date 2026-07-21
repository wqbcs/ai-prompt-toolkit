"""Fixer 模块测试 — 自动修复器 P005/P006/P016"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES, AMBIGUOUS_REPLACEMENTS, FixResult, Fixer
from ai_prompt_toolkit.types import Finding, Severity


class TestAutoFixableRules:
    def test_auto_fixable_rules_contains_expected(self):
        assert AUTO_FIXABLE_RULES == {"P005", "P006", "P016", "P003", "P010", "P025", "P053", "P048", "P061"}

    def test_ambiguous_replacements_keys(self):
        for key in AMBIGUOUS_REPLACEMENTS:
            assert isinstance(key, str)
            assert isinstance(AMBIGUOUS_REPLACEMENTS[key], str)


class TestFixResult:
    def test_diff_property_no_change(self):
        r = FixResult(rule_id="P005", original_text="hello", fixed_text="hello", description="test")
        assert r.diff == ""

    def test_diff_property_with_change(self):
        r = FixResult(rule_id="P005", original_text="line1\n", fixed_text="line2\n", description="test")
        diff = r.diff
        assert "-line1" in diff
        assert "+line2" in diff

    def test_to_dict(self):
        r = FixResult(rule_id="P006", original_text="abc", fixed_text="xyz", description="desc")
        d = r.to_dict()
        assert d["rule_id"] == "P006"
        assert d["description"] == "desc"
        assert d["original_length"] == 3
        assert d["fixed_length"] == 3


class TestFixer:
    def setup_method(self):
        self.fixer = Fixer()

    def test_fix_no_findings(self):
        text, results = self.fixer.fix("一些文本", [])
        assert text == "一些文本"
        assert results == []

    def test_fix_non_auto_fixable_finding_ignored(self):
        finding = Finding(rule_id="P001", severity=Severity.HIGH, description="test")
        text, results = self.fixer.fix("一些文本", [finding])
        assert text == "一些文本"
        assert results == []

    def test_fix_p005_short_prompt(self):
        short_text = "你好"
        finding = Finding(rule_id="P005", severity=Severity.LOW, description="过短")
        text, results = self.fixer.fix(short_text, [finding])
        assert len(text) > len(short_text)
        assert "请按照以上要求进行回答" in text
        assert len(results) == 1
        assert results[0].rule_id == "P005"

    def test_fix_p005_long_prompt_not_fixed(self):
        long_text = "这是一个很长的提示词" * 20
        finding = Finding(rule_id="P005", severity=Severity.LOW, description="过短")
        text, results = self.fixer.fix(long_text, [finding])
        assert text == long_text
        assert results == []

    def test_fix_p006_api_key_equals(self):
        text = "api_key=sk-1234567890abcdef"
        finding = Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息")
        fixed, results = self.fixer.fix(text, [finding])
        assert "sk-1234567890abcdef" not in fixed
        assert "***REDACTED***" in fixed
        assert len(results) == 1

    def test_fix_p006_password_colon(self):
        text = "password: mysecret123"
        finding = Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息")
        fixed, results = self.fixer.fix(text, [finding])
        assert "mysecret123" not in fixed
        assert "***REDACTED***" in fixed
        assert len(results) == 1

    def test_fix_p006_no_match(self):
        text = "这是一段正常的文本"
        finding = Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息")
        fixed, results = self.fixer.fix(text, [finding])
        assert fixed == text
        assert results == []

    def test_fix_p016_ambiguous_word(self):
        text = "你可能会得到结果"
        finding = Finding(rule_id="P016", severity=Severity.HIGH, description="歧义表述")
        fixed, results = self.fixer.fix(text, [finding])
        assert "可能" not in fixed
        assert "需要" in fixed
        assert len(results) == 1

    def test_fix_p016_english_maybe(self):
        text = "This maybe works"
        finding = Finding(rule_id="P016", severity=Severity.HIGH, description="歧义表述")
        fixed, results = self.fixer.fix(text, [finding])
        assert "maybe" not in fixed.lower() or "must" in fixed
        assert len(results) == 1

    def test_fix_p016_no_ambiguous_word(self):
        text = "请明确输出结果"
        finding = Finding(rule_id="P016", severity=Severity.HIGH, description="歧义表述")
        fixed, results = self.fixer.fix(text, [finding])
        assert fixed == text
        assert results == []

    def test_fix_dry_run(self):
        text = "api_key=sk-secret123"
        finding = Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息")
        result_text, results = self.fixer.fix(text, [finding], dry_run=True)
        assert result_text == text
        assert len(results) == 1

    def test_fix_multiple_findings(self):
        findings = [
            Finding(rule_id="P005", severity=Severity.LOW, description="过短"),
            Finding(rule_id="P016", severity=Severity.HIGH, description="歧义表述"),
        ]
        text = "可能会"
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) >= 1

    def test_fix_mixed_auto_and_non_auto(self):
        findings = [
            Finding(rule_id="P001", severity=Severity.HIGH, description="缺失角色"),
            Finding(rule_id="P005", severity=Severity.LOW, description="过短"),
        ]
        text = "短"
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) == 1
        assert results[0].rule_id == "P005"

    def test_fix_p048_mixed_punctuation(self):
        text = "你必须回答，不要编造。回复控制在500字以内！"
        finding = Finding(rule_id="P048", severity=Severity.LOW, description="标点混用")
        fixed, results = self.fixer.fix(text, [finding])
        assert "，" not in fixed
        assert "。" not in fixed
        assert len(results) == 1

    def test_fix_p061_blank_lines(self):
        text = "Line1\n\n\n\n\nLine2"
        finding = Finding(rule_id="P061", severity=Severity.LOW, description="空行过多")
        fixed, results = self.fixer.fix(text, [finding])
        assert fixed.count("\n") <= 3
        assert len(results) == 1

    def test_fix_p053_fuzzy_word(self):
        text = "回复应该适当控制在合理范围内等等"
        finding = Finding(rule_id="P053", severity=Severity.LOW, description="模糊表述")
        fixed, results = self.fixer.fix(text, [finding])
        assert len(results) >= 1

    def test_fix_p003_missing_constraints(self):
        text = "# 角色\n你是专家"
        finding = Finding(rule_id="P003", severity=Severity.MEDIUM, description="缺少约束")
        fixed, results = self.fixer.fix(text, [finding])
        assert "约束" in fixed
        assert len(results) == 1

    def test_fix_p010_missing_error_handling(self):
        text = "# 角色\n你是专家\n# 安全边界\n不执行代码"
        finding = Finding(rule_id="P010", severity=Severity.MEDIUM, description="缺少错误处理")
        fixed, results = self.fixer.fix(text, [finding])
        assert "错误处理" in fixed
        assert len(results) == 1

    def test_fix_p025_missing_length(self):
        text = "# 角色\n你是专家"
        finding = Finding(rule_id="P025", severity=Severity.MEDIUM, description="缺少长度约束")
        fixed, results = self.fixer.fix(text, [finding])
        assert "800字" in fixed
        assert len(results) == 1
