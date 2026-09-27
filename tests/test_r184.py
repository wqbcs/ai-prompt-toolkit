"""R184测试: quality_score扣分制质量分(score v2 RFC方案C)"""

from __future__ import annotations

from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.types import Finding, Severity


def _lint(text: str):
    return PromptLinter().lint("t", text)


class TestQualityScore:
    def test_clean_text_full_score(self):
        result = _lint(
            "version: 1.0.0\n# 角色\n你是测试工程师。\n# 任务\n编写用例。\n"
            "# 输出格式\nMarkdown。\n# 约束\n不编造。\n# 示例\n输入: 登录\n输出: 表格。\n"
        )
        assert result.quality_score >= 80.0

    def test_per_severity_deductions(self):
        from ai_prompt_toolkit.linter.linter import LintResult

        findings = [
            Finding("X001", Severity.CRITICAL, "c", 1, 1),
            Finding("X002", Severity.HIGH, "h", 1, 1),
            Finding("X003", Severity.MEDIUM, "m", 1, 1),
            Finding("X004", Severity.LOW, "l", 1, 1),
        ]
        lr = LintResult(template_id="t", findings=findings)
        assert lr.quality_score == round(100.0 - (12.0 + 6.0 + 1.0 + 0.1), 1)

    def test_same_rule_deduped(self):
        """R180: 同规则多次触发只计一次(防长文本刷屏叠加惩罚)"""
        from ai_prompt_toolkit.linter.linter import LintResult

        one = LintResult(template_id="t", findings=[Finding("P003", Severity.MEDIUM, "m", 1, 1)])
        many = LintResult(template_id="t", findings=[Finding("P003", Severity.MEDIUM, "m", i, 1) for i in range(10)])
        assert many.quality_score == one.quality_score

    def test_floors_at_zero(self):
        from ai_prompt_toolkit.linter.linter import LintResult

        findings = [Finding(f"X{i}", Severity.CRITICAL, "c", 1, 1) for i in range(20)]
        lr = LintResult(template_id="t", findings=findings)
        assert lr.quality_score == 0.0

    def test_included_in_to_dict(self):
        result = _lint("你是一名助手。")
        assert "quality_score" in result.to_dict()

    def test_semantics_absolute_quality(self):
        """quality_score语义: 绝对质量的粗粒度指示(跨长度不可直接比较) —
        极短prompt缺角色(HIGH)应扣6分以上"""
        short = _lint("处理数据")
        assert short.quality_score <= 94.0, f"缺角色未扣分: {short.quality_score}"
        assert short.quality_score >= 0.0
