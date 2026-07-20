"""测试 P051-P055 安全合规+可维护性+鸿蒙适配规则"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules_p051_p055 import (
    check_p051, check_p052, check_p053, check_p054, check_p055,
    run_checks_p051_p055,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestP051HardcodedCredentials:
    def test_pass_no_credentials(self):
        text = "你是一个翻译助手，请将以下内容翻译为英文。"
        assert check_p051(text) is None

    def test_pass_placeholder(self):
        text = "使用API_KEY环境变量获取密钥。"
        assert check_p051(text) is None

    def test_fail_hardcoded_password(self):
        text = "password=MySecret123456"
        result = check_p051(text)
        assert result is not None
        assert result.rule_id == "P051"
        assert result.severity == Severity.HIGH

    def test_fail_hardcoded_api_key(self):
        text = "api_key=AKIAIOSFODNN7EXAMPLE123456"
        result = check_p051(text)
        assert result is not None
        assert result.rule_id == "P051"

    def test_fail_hardcoded_token(self):
        text = "bearer=eyJhbGciOiJIUzI1NiIsInR5cCI6Ik"
        result = check_p051(text)
        assert result is not None
        assert result.rule_id == "P051"


class TestP052MissingOutputFormat:
    def test_pass_short_prompt(self):
        text = "翻译以下内容"
        assert check_p052(text) is None

    def test_pass_with_format(self):
        text = "请分析以下数据，输出JSON格式的结果。" + "详细描述分析方法和步骤。" * 20
        assert check_p052(text) is None

    def test_fail_long_no_format(self):
        text = "请分析以下数据，详细描述分析方法和步骤。" * 20
        result = check_p052(text)
        assert result is not None
        assert result.rule_id == "P052"
        assert result.severity == Severity.MEDIUM


class TestP053AmbiguousInstructions:
    def test_pass_clear_text(self):
        text = "请将以下5个句子翻译为英文，使用正式语气。"
        assert check_p053(text) is None

    def test_fail_ambiguous_etc(self):
        text = "请处理数据、清洗数据、等等"
        result = check_p053(text)
        assert result is not None
        assert result.rule_id == "P053"

    def test_fail_ambiguous_vague_words(self):
        text = "可能需要大概三个步骤来处理"
        result = check_p053(text)
        assert result is not None
        assert result.rule_id == "P053"
        assert len(result.details["ambiguous"]) >= 1

    def test_fail_ambiguous_quantifiers(self):
        text = "适当增加合理的内容，满足一定条件"
        result = check_p053(text)
        assert result is not None
        assert result.rule_id == "P053"


class TestP054HarmonyOSCompat:
    def test_pass_no_android(self):
        text = "你是一个鸿蒙应用开发助手，使用ArkTS编写。"
        assert check_p054(text) is None

    def test_fail_android_api(self):
        text = "使用android.os.Bundle传递数据"
        result = check_p054(text)
        assert result is not None
        assert result.rule_id == "P054"
        assert result.severity == Severity.MEDIUM

    def test_fail_android_components(self):
        text = "创建Android应用中的Activity和Fragment来管理界面"
        result = check_p054(text)
        assert result is not None
        assert result.rule_id == "P054"

    def test_pass_service_no_context(self):
        text = "请提供优质的Service给客户"
        assert check_p054(text) is None

    def test_fail_java_import(self):
        text = "import java.util.ArrayList"
        result = check_p054(text)
        assert result is not None
        assert result.rule_id == "P054"


class TestP055VersionTag:
    def test_pass_with_version(self):
        text = "---\nversion: 1.0\nname: test\n---\n你是一个助手。"
        assert check_p055(text) is None

    def test_pass_short_prompt(self):
        text = "翻译以下内容"
        assert check_p055(text) is None

    def test_fail_long_no_version(self):
        text = "你是一个专业的数据分析助手，请按照以下步骤处理数据。" * 20
        result = check_p055(text)
        assert result is not None
        assert result.rule_id == "P055"
        assert result.severity == Severity.LOW

    def test_fail_front_matter_no_version(self):
        text = "---\nname: test\nauthor: dev\n---\n你是一个助手。"
        result = check_p055(text)
        assert result is not None
        assert result.rule_id == "P055"


class TestRunChecksP051P055:
    def test_clean_prompt(self):
        text = "你是一个专业的翻译助手。请将用户输入的中文文本翻译为英文，输出JSON格式。版本:1.0"
        findings = run_checks_p051_p055(text)
        non_low = [f for f in findings if f.severity >= Severity.MEDIUM]
        assert len(non_low) == 0

    def test_multiple_issues(self):
        text = (
            "password=secret123456\n"
            "请处理数据、清洗数据、等等，可能需要适当调整\n"
            "使用android.os.Bundle传递数据\n"
            "这是一个长Prompt但没有版本标记，" * 30
        )
        findings = run_checks_p051_p055(text)
        assert len(findings) >= 3
