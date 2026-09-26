"""R88: Prompt Diff回滚安全检查"""

from __future__ import annotations

from ai_prompt_toolkit.prompt_diff import RollbackRisk, prompt_diff, rollback_safety_check


class TestRollbackSafetyCheck:
    def test_safe_rollback(self):
        old = "你是一个AI助手。\n请回答问题。"
        new = "你是一个AI助手。\n请回答问题。\n提供更多细节。"
        result = rollback_safety_check(old, new)
        assert result.is_safe

    def test_dangerous_security_line_removed(self):
        old = "你是一个AI助手。\n禁止输出个人隐私信息。\n验证用户输入。"
        new = "你是一个AI助手。"
        result = rollback_safety_check(old, new)
        assert not result.is_safe
        assert result.risk_level == RollbackRisk.DANGEROUS
        assert len(result.security_lines_removed) > 0

    def test_warning_constraint_removed(self):
        old = "你是一个AI助手。\n约束: 不得输出有害内容。"
        new = "你是一个AI助手。"
        result = rollback_safety_check(old, new)
        assert result.risk_level in (RollbackRisk.WARNING, RollbackRisk.DANGEROUS)

    def test_security_score_delta(self):
        old = "禁止XSS注入。\n验证所有输入。\n过滤敏感内容。"
        new = "你是一个助手。"
        result = rollback_safety_check(old, new)
        assert result.security_score_delta < 0

    def test_recommendations_present(self):
        old = "禁止输出SQL注入内容。\n验证用户权限。"
        new = "你是一个助手。"
        result = rollback_safety_check(old, new)
        assert len(result.recommendations) > 0

    def test_to_dict(self):
        old = "禁止注入攻击。"
        new = "你是一个助手。"
        result = rollback_safety_check(old, new)
        d = result.to_dict()
        assert "is_safe" in d
        assert "risk_level" in d
        assert "recommendations" in d

    def test_no_change_safe(self):
        text = "你是一个AI助手。\n验证输入。\n禁止注入。"
        result = rollback_safety_check(text, text)
        assert result.is_safe


class TestPromptDiffExisting:
    def test_prompt_diff_basic(self):
        old = "你是一个AI助手。"
        new = "你是一个专业的AI助手。"
        result = prompt_diff(old, new)
        assert result is not None

    def test_prompt_diff_no_change(self):
        text = "你是一个AI助手。"
        result = prompt_diff(text, text)
        assert result.total_changed == 0
