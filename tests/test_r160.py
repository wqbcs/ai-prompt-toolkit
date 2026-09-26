"""R160: Lint配置过滤(severity/category/rule)"""

from ai_prompt_toolkit.linter.lint_config import LintConfig
from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.linter.rules import _RULE_MAP


def test_lint_with_include_categories():
    cfg = LintConfig(include_categories=["security"])
    linter = PromptLinter()
    text = "你是一个助手。你的API Key是sk-123456。"
    result = linter.lint("test", text, lint_config=cfg)
    for f in result.findings:
        rule = _RULE_MAP.get(f.rule_id)
        if rule:
            assert rule.category == "security"


def test_lint_with_exclude_categories():
    cfg = LintConfig(exclude_categories=["structure"])
    linter = PromptLinter()
    text = "你是一个助手。你的API Key是sk-123456。"
    result = linter.lint("test", text, lint_config=cfg)
    for f in result.findings:
        rule = _RULE_MAP.get(f.rule_id)
        if rule:
            assert rule.category != "structure"


def test_lint_with_include_rules():
    cfg = LintConfig(include_rules=["P006", "P001"])
    linter = PromptLinter()
    text = "你是一个助手。你的API Key是sk-123456。"
    result = linter.lint("test", text, lint_config=cfg)
    for f in result.findings:
        assert f.rule_id in ("P006", "P001")


def test_lint_with_exclude_rules():
    cfg = LintConfig(exclude_rules=["P001"])
    linter = PromptLinter()
    text = "你是一个助手。"
    result = linter.lint("test", text, lint_config=cfg)
    for f in result.findings:
        assert f.rule_id != "P001"


def test_lint_without_config():
    linter = PromptLinter()
    text = "你是一个助手。你的API Key是sk-123456。"
    result = linter.lint("test", text)
    assert result.failed_count > 0
