"""R118 测试: P211-P215 鸿蒙NEXT API 16规则"""

from __future__ import annotations

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules, run_all_checks
from ai_prompt_toolkit.types import Severity


class TestR118RuleCount:
    def test_total_rules_215(self):
        assert len(get_all_rules()) == 264

    def test_auto_fixable_count(self):
        assert len(AUTO_FIXABLE_RULES) >= 156


class TestR118P211P215Registration:
    def test_in_rule_map(self):
        for rid in ("P211", "P212", "P213", "P214", "P215"):
            assert rid in _RULE_MAP

    def test_category(self):
        for rid in ("P211", "P212", "P213", "P214", "P215"):
            assert _RULE_MAP[rid].category == "harmonyos_v16"

    def test_severity(self):
        assert _RULE_MAP["P211"].severity == Severity.HIGH
        assert _RULE_MAP["P212"].severity == Severity.MEDIUM
        assert _RULE_MAP["P213"].severity == Severity.HIGH
        assert _RULE_MAP["P214"].severity == Severity.MEDIUM
        assert _RULE_MAP["P215"].severity == Severity.HIGH

    def test_bilingual(self):
        for rid in ("P211", "P212", "P213", "P214", "P215"):
            rule = _RULE_MAP[rid]
            assert rule.description_en
            assert rule.remediation_en


class TestR118P211LazyLoad:
    def test_foreach_trigger(self):
        text = "ForEach(items, item => Text(item))"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P211" for f in findings)

    def test_lazy_foreach_pass(self):
        text = "LazyForEach(dataSource, item => ListItem)"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P211" for f in findings)


class TestR118P213NAPI:
    def test_napi_no_check_trigger(self):
        text = "napi_get_value_string_utf8(env, args[0])"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P213" for f in findings)

    def test_napi_with_check_pass(self):
        text = "napi_typeof(env, args[0]); napi_get_value_string_utf8(env, args[0])"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P213" for f in findings)


class TestR118P215Distributed:
    def test_distributed_no_encrypt_trigger(self):
        text = "distributedDB跨设备同步数据"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P215" for f in findings)

    def test_distributed_with_encrypt_pass(self):
        text = "distributedDB: {encrypt: true, algorithm: 'AES-256'}"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P215" for f in findings)
