"""R108 测试: P196-P200 LLM推理安全Lint规则"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.types import Severity


class TestR108RuleCount:
    def test_total_rules_200(self):
        rules = get_all_rules()
        assert len(rules) == 200

    def test_auto_fixable_count(self):
        assert len(AUTO_FIXABLE_RULES) >= 141


class TestR108P196P200Registration:
    def test_p196_p200_in_rule_map(self):
        for rid in ("P196", "P197", "P198", "P199", "P200"):
            assert rid in _RULE_MAP

    def test_p196_p200_auto_fixable(self):
        for rid in ("P196", "P197", "P198", "P199", "P200"):
            assert rid in AUTO_FIXABLE_RULES

    def test_p196_p200_category(self):
        assert _RULE_MAP["P196"].category == "inference_security"
        assert _RULE_MAP["P197"].category == "inference2security"
        assert _RULE_MAP["P198"].category == "inference_security"
        assert _RULE_MAP["P199"].category == "inference_security"
        assert _RULE_MAP["P200"].category == "inference_security"

    def test_p196_p200_severity(self):
        assert _RULE_MAP["P196"].severity == Severity.HIGH
        assert _RULE_MAP["P197"].severity == Severity.HIGH
        assert _RULE_MAP["P198"].severity == Severity.MEDIUM
        assert _RULE_MAP["P199"].severity == Severity.MEDIUM
        assert _RULE_MAP["P200"].severity == Severity.HIGH

    def test_p196_p200_bilingual(self):
        for rid in ("P196", "P197", "P198", "P199", "P200"):
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"


class TestR108P196InferenceTimeout:
    def test_no_timeout_trigger(self):
        text = "推理模型生成结果 inference: {model: gpt-4}"
        findings = run_all_checks(text)
        p196 = [f for f in findings if f.rule_id == "P196"]
        assert len(p196) == 1

    def test_has_timeout_pass(self):
        text = "推理模型生成结果 inference: {model: gpt-4, timeout: 30}"
        findings = run_all_checks(text)
        p196 = [f for f in findings if f.rule_id == "P196"]
        assert len(p196) == 0


class TestR108P197MaxTokens:
    def test_no_max_tokens_trigger(self):
        text = "调用模型生成 completion: {model: gpt-4}"
        findings = run_all_checks(text)
        p197 = [f for f in findings if f.rule_id == "P197"]
        assert len(p197) == 1

    def test_has_max_tokens_pass(self):
        text = "调用模型生成 completion: {model: gpt-4, max_tokens: 2048}"
        findings = run_all_checks(text)
        p197 = [f for f in findings if f.rule_id == "P197"]
        assert len(p197) == 0


class TestR108P198Temperature:
    def test_high_temperature_trigger(self):
        text = "生成文本 temperature: 2.0"
        findings = run_all_checks(text)
        p198 = [f for f in findings if f.rule_id == "P198"]
        assert len(p198) == 1

    def test_normal_temperature_pass(self):
        text = "生成文本 temperature: 0.7"
        findings = run_all_checks(text)
        p198 = [f for f in findings if f.rule_id == "P198"]
        assert len(p198) == 0


class TestR108P199SamplingConflict:
    def test_dual_sampling_trigger(self):
        text = "生成文本 top_p: 0.9 temperature: 0.7"
        findings = run_all_checks(text)
        p199 = [f for f in findings if f.rule_id == "P199"]
        assert len(p199) == 1

    def test_only_temperature_pass(self):
        text = "生成文本 temperature: 0.7"
        findings = run_all_checks(text)
        p199 = [f for f in findings if f.rule_id == "P199"]
        assert len(p199) == 0


class TestR108P200StreamingAudit:
    def test_stream_no_audit_trigger(self):
        text = "流式响应 streaming: true"
        findings = run_all_checks(text)
        p200 = [f for f in findings if f.rule_id == "P200"]
        assert len(p200) == 1

    def test_stream_with_audit_pass(self):
        text = "流式响应 streaming: true, audit: true, abort_on_violation: true"
        findings = run_all_checks(text)
        p200 = [f for f in findings if f.rule_id == "P200"]
        assert len(p200) == 0


class TestR108OWASPMapping:
    def test_p196_p200_owasp_refs(self):
        assert "LLM01" in _RULE_MAP["P196"].owasp_refs
        assert "LLM09" in _RULE_MAP["P196"].owasp_refs
        assert "LLM09" in _RULE_MAP["P197"].owasp_refs
        assert "LLM06" in _RULE_MAP["P198"].owasp_refs
        assert "LLM06" in _RULE_MAP["P199"].owasp_refs
        assert "LLM06" in _RULE_MAP["P200"].owasp_refs
