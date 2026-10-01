"""R114 测试: P206-P210 RAG/知识库安全Lint规则"""

from __future__ import annotations

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules, run_all_checks
from ai_prompt_toolkit.types import Severity


class TestR114RuleCount:
    def test_total_rules_210(self):
        assert len(get_all_rules()) == 257

    def test_auto_fixable_count(self):
        assert len(AUTO_FIXABLE_RULES) >= 156


class TestR114P206P210Registration:
    def test_p206_p210_in_rule_map(self):
        for rid in ("P206", "P207", "P208", "P209", "P210"):
            assert rid in _RULE_MAP

    def test_p206_p210_category(self):
        for rid in ("P206", "P207", "P208", "P209", "P210"):
            assert _RULE_MAP[rid].category == "rag_security"

    def test_p206_p210_severity(self):
        assert _RULE_MAP["P206"].severity == Severity.HIGH
        assert _RULE_MAP["P207"].severity == Severity.HIGH
        assert _RULE_MAP["P208"].severity == Severity.MEDIUM

    def test_p206_p210_bilingual(self):
        for rid in ("P206", "P207", "P208", "P209", "P210"):
            rule = _RULE_MAP[rid]
            assert rule.description_en
            assert rule.remediation_en


class TestR114P206RetrievalInjection:
    def test_missing_sanitize_trigger(self):
        text = "RAG检索知识库 retrieval: {top_k: 5}"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P206" for f in findings)

    def test_has_sanitize_pass(self):
        text = "RAG检索 retrieval: {sanitize: true, top_k: 5}"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P206" for f in findings)


class TestR114P207Hallucination:
    def test_missing_faithfulness_trigger(self):
        text = "RAG知识库检索生成 retrieval: true"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P207" for f in findings)

    def test_has_faithfulness_pass(self):
        text = "RAG检索 faithfulness: true, source_verification: true"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P207" for f in findings)


class TestR114P209ContextWindow:
    def test_missing_max_tokens_trigger(self):
        text = "向量检索RAG embedding: true"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P209" for f in findings)

    def test_has_max_tokens_pass(self):
        text = "RAG检索 max_chunks: 5, max_tokens: 4096"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P209" for f in findings)


class TestR114P210EmbeddingDrift:
    def test_missing_version_lock_trigger(self):
        text = "使用embedding模型 vector_model: ada-002"
        findings = run_all_checks(text)
        assert any(f.rule_id == "P210" for f in findings)

    def test_has_version_lock_pass(self):
        text = "embedding模型 ada-002@v1, version_lock: true"
        findings = run_all_checks(text)
        assert not any(f.rule_id == "P210" for f in findings)
