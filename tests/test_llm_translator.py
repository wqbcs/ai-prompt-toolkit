"""LLM辅助i18n翻译测试 — P2-03"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.i18n.llm_translator import (
    LLMTranslator,
    LLMTranslationResult,
    _TRANSLATION_PROMPT_TEMPLATE,
)
from ai_prompt_toolkit.i18n.glossary import Glossary
from ai_prompt_toolkit.i18n.types import TranslationEntry, TranslationStatus
from ai_prompt_toolkit.i18n.translation import TranslationEngine


class TestLLMTranslatorBasic:
    def test_glossary_hit(self):
        glossary = Glossary.default()
        translator = LLMTranslator(glossary=glossary)
        result = translator.translate_with_llm("华为云", "zh-CN", "en-US")
        assert result.glossary_hit is True
        assert result.entry.value == "Huawei Cloud"
        assert result.entry.status == TranslationStatus.HUMAN_REVIEWED

    def test_glossary_hit_prompt(self):
        glossary = Glossary.default()
        translator = LLMTranslator(glossary=glossary)
        result = translator.translate_with_llm("提示词", "zh-CN", "en-US")
        assert result.glossary_hit is True
        assert result.entry.value == "Prompt"

    def test_no_glossary_no_provider(self):
        glossary = Glossary(data={})
        engine = TranslationEngine()
        translator = LLMTranslator(glossary=glossary, engine=engine)
        result = translator.translate_with_llm("Hello world", "en-US", "zh-CN")
        assert result.glossary_hit is False
        assert result.entry.status in (TranslationStatus.MISSING, TranslationStatus.MACHINE)

    def test_translate_with_cache(self, tmp_path):
        engine = TranslationEngine(cache_dir=str(tmp_path / "cache"))
        glossary = Glossary(data={})
        translator = LLMTranslator(glossary=glossary, engine=engine)
        result = translator.translate_with_llm("Hello", "en-US", "zh-CN")
        assert isinstance(result, LLMTranslationResult)


class TestConsistency:
    def test_consistent_translation(self):
        glossary = Glossary.default()
        translator = LLMTranslator(glossary=glossary)
        ok = translator._check_consistency("华为云服务", "Huawei Cloud Service", "en-US")
        assert ok is True

    def test_inconsistent_translation(self):
        glossary = Glossary.default()
        translator = LLMTranslator(glossary=glossary)
        ok = translator._check_consistency("华为云服务", "HUAWEI Cloud Service", "en-US")
        assert ok is False

    def test_no_glossary_terms_consistent(self):
        glossary = Glossary(data={})
        translator = LLMTranslator(glossary=glossary)
        ok = translator._check_consistency("hello", "你好", "zh-CN")
        assert ok is True


class TestBatchTranslate:
    def test_batch_with_glossary(self):
        glossary = Glossary.default()
        engine = TranslationEngine()
        translator = LLMTranslator(glossary=glossary, engine=engine)
        entries = [
            TranslationEntry(key="t1", locale="zh-CN", value="华为云", status=TranslationStatus.MACHINE),
            TranslationEntry(key="t2", locale="zh-CN", value="提示词", status=TranslationStatus.MACHINE),
        ]
        results = translator.batch_translate_with_llm(entries, "zh-CN", "en-US")
        assert len(results) == 2
        assert results[0].glossary_hit is True
        assert results[1].glossary_hit is True

    def test_batch_protects_reviewed(self):
        glossary = Glossary(data={})
        engine = TranslationEngine()
        translator = LLMTranslator(glossary=glossary, engine=engine)
        entries = [
            TranslationEntry(key="t1", locale="en-US", value="Reviewed", status=TranslationStatus.HUMAN_REVIEWED),
        ]
        results = translator.batch_translate_with_llm(entries, "zh-CN", "en-US")
        assert results[0].entry.status == TranslationStatus.HUMAN_REVIEWED


class TestTranslateTemplate:
    def test_preserves_variables(self):
        glossary = Glossary(data={})
        engine = TranslationEngine()
        translator = LLMTranslator(glossary=glossary, engine=engine)
        result = translator.translate_template(
            "你好{{name}}，欢迎使用华为云",
            "zh-CN", "en-US"
        )
        assert result["variables_preserved"] == 1
        assert "source_locale" in result
        assert "target_locale" in result

    def test_template_result_structure(self):
        glossary = Glossary.default()
        engine = TranslationEngine()
        translator = LLMTranslator(glossary=glossary, engine=engine)
        result = translator.translate_template("华为云", "zh-CN", "en-US")
        assert "original" in result
        assert "translated" in result
        assert "status" in result
        assert "glossary_hit" in result
        assert "consistency_ok" in result


class TestPromptTemplate:
    def test_prompt_includes_glossary(self):
        glossary = Glossary.default()
        section = ""
        for term in glossary.terms()[:5]:
            en = glossary.lookup(term, "en-US")
            if en:
                section += f"- {term} → {en}\n"
        prompt = _TRANSLATION_PROMPT_TEMPLATE.format(
            source_lang="简体中文",
            target_lang="English",
            glossary_section=section,
            source_text="测试文本",
        )
        assert "术语表" in prompt
        assert "翻译规则" in prompt


class TestLocaleMapping:
    def test_locale_to_lang(self):
        translator = LLMTranslator()
        assert translator._locale_to_lang("zh-CN") == "简体中文"
        assert translator._locale_to_lang("en-US") == "English"
        assert translator._locale_to_lang("ja-JP") == "日本語"
        assert translator._locale_to_lang("unknown") == "unknown"
