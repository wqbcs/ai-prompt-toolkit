"""Prompt Linter 引擎。"""

from prompt_toolkit.linter.rules import LintRule, get_all_rules, get_rule, run_all_checks
from prompt_toolkit.linter.linter import FixAction, LintResult, PromptLinter


def lint_template(
    template_id: str,
    text: str,
    *,
    fix: bool = False,
    rules: list[str] | None = None,
    exclude: list[str] | None = None,
) -> LintResult:
    """SDK 便捷入口：检查单个模板。"""
    linter = PromptLinter(rules=rules, exclude=exclude)
    return linter.lint(template_id, text, fix=fix)
