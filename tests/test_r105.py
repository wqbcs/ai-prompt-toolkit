"""R105: CHANGELOG v51.0.0 + 自定义Lint规则YAML DSL"""
from __future__ import annotations

from pathlib import Path

from ai_prompt_toolkit.linter.custom_rules import (
    CustomRuleDef, check_custom_rule, load_custom_rules, register_custom_rules,
)
from ai_prompt_toolkit.types import Severity


class TestR105CustomRulesDSL:
    def test_load_custom_rules_from_dir(self):
        rules = load_custom_rules(".prompt-toolkit-rules")
        assert len(rules) >= 3
        ids = {r.rule_id for r in rules}
        assert "CUSTOM001" in ids
        assert "CUSTOM002" in ids
        assert "CUSTOM003" in ids

    def test_custom_rule_regex_check(self):
        cr = CustomRuleDef(rule_id="CR01", name="test", category="custom",
                           severity=Severity.HIGH, pattern="禁止|forbidden",
                           message="包含禁止词", check_type="regex")
        result = check_custom_rule("这是禁止的内容", cr)
        assert result is not None
        assert result.rule_id == "CR01"

    def test_custom_rule_regex_pass(self):
        cr = CustomRuleDef(rule_id="CR01", name="test", category="custom",
                           severity=Severity.HIGH, pattern="禁止",
                           message="包含禁止词", check_type="regex")
        result = check_custom_rule("这是正常的内容", cr)
        assert result is None

    def test_custom_rule_keyword_check(self):
        cr = CustomRuleDef(rule_id="CR02", name="test", category="custom",
                           severity=Severity.MEDIUM, keywords=["OpenAI", "ChatGPT"],
                           message="提及竞品", check_type="keyword")
        result = check_custom_rule("使用OpenAI的API", cr)
        assert result is not None

    def test_custom_rule_not_contains_check(self):
        cr = CustomRuleDef(rule_id="CR03", name="test", category="custom",
                           severity=Severity.HIGH, keywords=["version", "版本"],
                           message="缺版本", check_type="not_contains")
        result = check_custom_rule("你是一个AI助手", cr)
        assert result is not None

    def test_custom_rule_min_length_check(self):
        cr = CustomRuleDef(rule_id="CR04", name="test", category="custom",
                           severity=Severity.LOW, pattern="100",
                           message="过短", check_type="min_length")
        result = check_custom_rule("短", cr)
        assert result is not None

    def test_register_custom_rules(self):
        cr = CustomRuleDef(rule_id="CR_REG1", name="test", category="custom",
                           severity=Severity.MEDIUM, pattern="test",
                           message="test", check_type="regex")
        registered = register_custom_rules([cr])
        assert registered == ["CR_REG1"]
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        assert "CR_REG1" in _RULE_MAP

    def test_changelog_v51(self):
        changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
        assert "v51.0.0" in changelog
        assert "P191" in changelog
