"""Prompt Linter 引擎。"""

from ai_prompt_toolkit.linter.linter import FixAction, LintResult, PromptLinter
from ai_prompt_toolkit.linter.rules import LintRule, get_all_rules, get_rule, run_all_checks


def lint_template(
    template_id: str,
    text: str,
    *,
    fix: bool = False,
    rules: list[str] | None = None,
    exclude: list[str] | None = None,
    apply_waivers: bool = True,
) -> LintResult:
    """SDK 便捷入口：检查单个模板。

    apply_waivers=False 绕过内联豁免(R213审查: 漏检率基线等检测能力度量
    不可被文件内 promptlint:ignore 注释抑制)。
    """
    linter = PromptLinter(rules=rules, exclude=exclude)
    return linter.lint(template_id, text, fix=fix, apply_waivers=apply_waivers)
