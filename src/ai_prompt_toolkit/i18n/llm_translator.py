"""LLM翻译器 — 利用Provider系统进行Prompt i18n翻译

P2-03: LLM辅助翻译+术语一致性
- 术语表优先: glossary命中直接使用，标记HUMAN_REVIEWED
- LLM翻译: 构建翻译Prompt，包含术语表上下文
- 一致性检查: 检测翻译结果与术语表冲突
- 批量翻译: 支持batch_translate_with_llm()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.i18n.glossary import Glossary
from ai_prompt_toolkit.i18n.types import TranslationEntry, TranslationStatus
from ai_prompt_toolkit.i18n.translation import TranslationEngine

logger = logging.getLogger(__name__)

_TRANSLATION_PROMPT_TEMPLATE = """你是一个专业的AI提示词翻译专家。

任务: 将以下{source_lang}文本翻译为{target_lang}

术语表(必须使用以下翻译):
{glossary_section}

翻译规则:
1. 术语表中的术语必须使用指定翻译，不可更改
2. 保持原文的语气和风格
3. 保持Markdown格式不变
4. 保留变量占位符(如{{variable}})不变
5. 保留代码块不变
6. 如果原文是系统提示词，翻译后仍需保持指令性

原文:
{source_text}

请直接输出翻译结果，不要添加任何解释:"""

_CONSISTENCY_CHECK_PROMPT = """检查以下翻译是否与术语表一致:

术语表:
{glossary_section}

源文本: {source}
翻译结果: {translation}

如果不一致，请输出修正后的翻译。如果一致，输出OK:"""


@dataclass
class LLMTranslationResult:
    entry: TranslationEntry
    glossary_hit: bool = False
    consistency_ok: bool = True
    consistency_issue: str = ""


class LLMTranslator:
    def __init__(
        self,
        glossary: Glossary | None = None,
        engine: TranslationEngine | None = None,
        provider: Any = None,
    ):
        self._glossary = glossary or Glossary.default()
        self._engine = engine or TranslationEngine()
        self._provider = provider

    def _build_glossary_section(self, target_locale: str) -> str:
        lines = []
        for term in self._glossary.terms():
            target_val = self._glossary.lookup(term, target_locale)
            if target_val:
                source_val = self._glossary.lookup(term, "zh-CN") or term
                lines.append(f"- {source_val} → {target_val}")
        return "\n".join(lines[:30])

    def _locale_to_lang(self, locale: str) -> str:
        mapping = {
            "zh-CN": "简体中文", "en-US": "English",
            "ja-JP": "日本語", "ko-KR": "한국어",
            "de-DE": "Deutsch", "fr-FR": "Français",
            "es-ES": "Español", "pt-BR": "Português",
            "ru-RU": "Русский", "zh-TW": "繁體中文",
            "it-IT": "Italiano",
        }
        return mapping.get(locale, locale)

    def translate_with_llm(
        self,
        text: str,
        source_locale: str,
        target_locale: str,
    ) -> LLMTranslationResult:
        glossary_value = self._glossary.lookup(text, target_locale)
        if glossary_value:
            return LLMTranslationResult(
                entry=TranslationEntry(
                    key="",
                    locale=target_locale,
                    value=glossary_value,
                    status=TranslationStatus.HUMAN_REVIEWED,
                    source="glossary",
                ),
                glossary_hit=True,
                consistency_ok=True,
            )

        existing = self._engine.translate(text, source_locale, target_locale)
        if existing.value and existing.status != TranslationStatus.MISSING:
            consistency = self._check_consistency(text, existing.value, target_locale)
            return LLMTranslationResult(
                entry=existing,
                glossary_hit=False,
                consistency_ok=consistency,
            )

        if self._provider:
            translated_text = self._call_llm(text, source_locale, target_locale)
            if translated_text:
                return LLMTranslationResult(
                    entry=TranslationEntry(
                        key="",
                        locale=target_locale,
                        value=translated_text,
                        status=TranslationStatus.MACHINE,
                        source="llm",
                    ),
                    glossary_hit=False,
                    consistency_ok=True,
                )

        return LLMTranslationResult(
            entry=TranslationEntry(
                key="",
                locale=target_locale,
                value="",
                status=TranslationStatus.MISSING,
                source="unavailable",
            ),
            glossary_hit=False,
            consistency_ok=False,
        )

    def _call_llm(self, text: str, source_locale: str, target_locale: str) -> str | None:
        if not self._provider:
            return None

        prompt = _TRANSLATION_PROMPT_TEMPLATE.format(
            source_lang=self._locale_to_lang(source_locale),
            target_lang=self._locale_to_lang(target_locale),
            glossary_section=self._build_glossary_section(target_locale),
            source_text=text,
        )

        try:
            result = self._provider.invoke(prompt)
            if hasattr(result, "text"):
                return result.text.strip()
            return str(result).strip()
        except Exception as e:
            logger.error("LLM翻译调用失败: %s", e)
            return None

    def _check_consistency(self, source: str, translation: str, target_locale: str) -> bool:
        for term in self._glossary.terms():
            expected = self._glossary.lookup(term, target_locale)
            if not expected:
                continue
            source_val = self._glossary.lookup(term, "zh-CN") or term
            if source_val in source and expected not in translation:
                return False
        return True

    def batch_translate_with_llm(
        self,
        entries: list[TranslationEntry],
        source_locale: str,
        target_locale: str,
    ) -> list[LLMTranslationResult]:
        results: list[LLMTranslationResult] = []
        for entry in entries:
            if self._engine.protect_reviewed(entry):
                results.append(LLMTranslationResult(entry=entry, glossary_hit=False, consistency_ok=True))
                continue
            result = self.translate_with_llm(entry.value, source_locale, target_locale)
            result.entry.key = entry.key
            results.append(result)
        return results

    def translate_template(
        self,
        template_text: str,
        source_locale: str,
        target_locale: str,
    ) -> dict[str, Any]:
        import re
        var_pattern = re.compile(r"\{\{(\w+)\}\}")
        variables = var_pattern.findall(template_text)
        placeholder_map = {f"__VAR_{i}__": f"{{{{{v}}}}}" for i, v in enumerate(variables)}
        protected_text = template_text
        for placeholder, var in placeholder_map.items():
            protected_text = protected_text.replace(var, placeholder)

        result = self.translate_with_llm(protected_text, source_locale, target_locale)

        translated = result.entry.value
        for placeholder, var in placeholder_map.items():
            if translated:
                translated = translated.replace(placeholder, var)

        return {
            "source_locale": source_locale,
            "target_locale": target_locale,
            "original": template_text,
            "translated": translated,
            "status": result.entry.status.value,
            "glossary_hit": result.glossary_hit,
            "consistency_ok": result.consistency_ok,
            "variables_preserved": len(variables),
        }
