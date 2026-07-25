"""R66测试: CLI错误友好化 + 3段式错误格式"""
import pytest
from ai_prompt_toolkit.cli_error_formatter import (
    format_three_part_error,
    format_finding_three_part,
    get_all_three_part_errors,
)


class TestThreePartError:
    def test_format_known_error(self):
        result = format_three_part_error("P001")
        assert "问题:" in result
        assert "原因:" in result
        assert "修复:" in result

    def test_format_injection_error(self):
        result = format_three_part_error("INJ-001")
        assert "指令注入" in result

    def test_format_pii_error(self):
        result = format_three_part_error("PII011")
        assert "API密钥" in result
        assert "撤销" in result

    def test_format_unknown_error(self):
        result = format_three_part_error("UNKNOWN_CODE", "原始错误信息")
        assert "原始错误信息" in result

    def test_format_unknown_no_message(self):
        result = format_three_part_error("UNKNOWN_CODE")
        assert "UNKNOWN_CODE" in result

    def test_all_errors_have_three_parts(self):
        for code, parts in get_all_three_part_errors().items():
            assert "problem" in parts, f"{code} missing 'problem'"
            assert "cause" in parts, f"{code} missing 'cause'"
            assert "fix" in parts, f"{code} missing 'fix'"

    def test_format_finding_with_rule_id(self):
        class FakeFinding:
            rule_id = "P001"
            description = "原始描述"
        result = format_finding_three_part(FakeFinding())
        assert "问题:" in result

    def test_format_finding_unknown(self):
        class FakeFinding:
            rule_id = "UNKNOWN"
            description = "原始描述"
        result = format_finding_three_part(FakeFinding())
        assert result == "原始描述"
