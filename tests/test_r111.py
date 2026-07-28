"""R111 测试: P201-P205 Prompt合规Lint规则"""
from __future__ import annotations

from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.types import Severity


class TestR111RuleCount:
    def test_total_rules_205(self):
        rules = get_all_rules()
        assert len(rules) == 205

    def test_auto_fixable_count(self):
        assert len(AUTO_FIXABLE_RULES) >= 146


class TestR111P201P205Registration:
    def test_p201_p205_in_rule_map(self):
        for rid in ("P201", "P202", "P203", "P204", "P205"):
            assert rid in _RULE_MAP

    def test_p201_p205_category(self):
        for rid in ("P201", "P202", "P203", "P204", "P205"):
            assert _RULE_MAP[rid].category == "compliance"

    def test_p201_p205_severity(self):
        assert _RULE_MAP["P201"].severity == Severity.HIGH
        assert _RULE_MAP["P202"].severity == Severity.HIGH
        assert _RULE_MAP["P203"].severity == Severity.MEDIUM
        assert _RULE_MAP["P204"].severity == Severity.MEDIUM
        assert _RULE_MAP["P205"].severity == Severity.HIGH

    def test_p201_p205_bilingual(self):
        for rid in ("P201", "P202", "P203", "P204", "P205"):
            rule = _RULE_MAP[rid]
            assert rule.description_en
            assert rule.remediation_en


class TestR111P201ComplianceDeclaration:
    def test_missing_compliance_trigger(self):
        text = "收集用户数据进行分析 data_processing: true"
        findings = run_all_checks(text)
        p201 = [f for f in findings if f.rule_id == "P201"]
        assert len(p201) == 1

    def test_has_compliance_pass(self):
        text = "收集用户数据 compliance: {gdpr: true}"
        findings = run_all_checks(text)
        p201 = [f for f in findings if f.rule_id == "P201"]
        assert len(p201) == 0


class TestR111P202Consent:
    def test_missing_consent_trigger(self):
        text = "存储用户数据 user.data: true"
        findings = run_all_checks(text)
        p202 = [f for f in findings if f.rule_id == "P202"]
        assert len(p202) == 1

    def test_has_consent_pass(self):
        text = "存储用户数据 consent: {required: true}"
        findings = run_all_checks(text)
        p202 = [f for f in findings if f.rule_id == "P202"]
        assert len(p202) == 0


class TestR111P203AILabel:
    def test_missing_ai_label_trigger(self):
        text = "生成回复内容 generate: true"
        findings = run_all_checks(text)
        p203 = [f for f in findings if f.rule_id == "P203"]
        assert len(p203) == 1

    def test_has_ai_label_pass(self):
        text = "生成回复 ai_generated: true, 本内容由AI生成"
        findings = run_all_checks(text)
        p203 = [f for f in findings if f.rule_id == "P203"]
        assert len(p203) == 0


class TestR111P204Fairness:
    def test_missing_fairness_trigger(self):
        text = "模型推理 predict: true"
        findings = run_all_checks(text)
        p204 = [f for f in findings if f.rule_id == "P204"]
        assert len(p204) == 1

    def test_has_fairness_pass(self):
        text = "模型推理 fairness: {bias_audit: true}"
        findings = run_all_checks(text)
        p204 = [f for f in findings if f.rule_id == "P204"]
        assert len(p204) == 0


class TestR111P205Retention:
    def test_missing_retention_trigger(self):
        text = "存储用户数据 user.data: true"
        findings = run_all_checks(text)
        p205 = [f for f in findings if f.rule_id == "P205"]
        assert len(p205) == 1

    def test_has_retention_pass(self):
        text = "存储用户数据 retention: {max_days: 30, auto_delete: true}"
        findings = run_all_checks(text)
        p205 = [f for f in findings if f.rule_id == "P205"]
        assert len(p205) == 0
