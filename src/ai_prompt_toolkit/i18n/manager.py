"""I18nManager — i18n框架主入口，参考Fabric v1.4.356完整i18n模式"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.i18n.fallback import FallbackChain
from ai_prompt_toolkit.i18n.glossary import Glossary
from ai_prompt_toolkit.i18n.resource import ResourceManager
from ai_prompt_toolkit.i18n.translation import TranslationEngine
from ai_prompt_toolkit.i18n.types import (
    CoverageReport,
    TranslationEntry,
    TranslationStatus,
)

logger = logging.getLogger(__name__)

SUPPORTED_LOCALES = ["zh-CN", "en-US"]
EXTENSIBLE_LOCALES = ["ja-JP", "ko-KR", "pt-BR", "de-DE", "fr-FR", "it-IT", "zh-TW", "es-ES", "ru-RU"]


class I18nManager:
    def __init__(
        self,
        base_dir: str | Path | None = None,
        glossary: Glossary | None = None,
        fallback_chain: FallbackChain | None = None,
        translation_engine: TranslationEngine | None = None,
    ):
        self._base_dir = Path(base_dir) if base_dir else Path.cwd() / "_i18n"
        self._glossary = glossary or Glossary.default()
        self._fallback = fallback_chain or FallbackChain.from_env()
        self._engine = translation_engine or TranslationEngine()
        self._resource_mgr = ResourceManager(self._base_dir / "locales")
        glossary_path = self._base_dir / "glossary.yaml"
        if glossary_path.exists():
            self._glossary.load(glossary_path)

    def generate(
        self,
        source_locale: str = "zh-CN",
        target_locale: str = "en-US",
        output_dir: str | Path | None = None,
    ) -> CoverageReport:
        source_entries = self._resource_mgr.load_locale(source_locale)
        if not source_entries:
            logger.warning("源语言 %s 无翻译资源", source_locale)
            return CoverageReport(locale=target_locale)
        target_entries: dict[str, TranslationEntry] = {}
        for key, entry in source_entries.items():
            glossary_value = self._glossary.lookup(entry.value, target_locale)
            if glossary_value:
                target_entries[key] = TranslationEntry(
                    key=key,
                    locale=target_locale,
                    value=glossary_value,
                    status=TranslationStatus.HUMAN_REVIEWED,
                    source="glossary",
                )
                continue
            existing = self._resource_mgr.get_entry(target_locale, key)
            if existing and self._engine.protect_reviewed(existing):
                target_entries[key] = existing
                continue
            translated = self._engine.translate(entry.value, source_locale, target_locale)
            translated.key = key
            target_entries[key] = translated
        out = Path(output_dir) if output_dir else self._base_dir / "locales" / target_locale
        out.mkdir(parents=True, exist_ok=True)
        output_data: dict[str, Any] = {
            "locale": target_locale,
            "source_locale": source_locale,
            "version": "1.0",
            "templates": {},
        }
        for key, entry in target_entries.items():
            output_data["templates"][key] = {
                "value": entry.value,
                "status": entry.status.value,
                "source": entry.source,
            }
        out_file = out / "templates.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        self._resource_mgr._resources[target_locale] = target_entries
        return self._resource_mgr.get_coverage(target_locale, source_locale)

    def get_translation(
        self,
        key: str,
        locale: str,
        default: str = "",
    ) -> str:
        available = self._resource_mgr.available_locales()
        resolved_locale, _used_fallback = self._fallback.resolve(locale, available)
        entry = self._resource_mgr.get_entry(resolved_locale, key)
        if entry and entry.value:
            return entry.value
        if resolved_locale != "en-US":
            entry = self._resource_mgr.get_entry("en-US", key)
            if entry and entry.value:
                return entry.value
        entry = self._resource_mgr.get_entry("zh-CN", key)
        if entry and entry.value:
            return entry.value
        return default or key

    def get_coverage(self, locale: str, reference: str = "zh-CN") -> CoverageReport:
        return self._resource_mgr.get_coverage(locale, reference)

    def list_locales(self) -> list[str]:
        supported = list(SUPPORTED_LOCALES)
        available = self._resource_mgr.available_locales()
        for loc in available:
            if loc not in supported:
                supported.append(loc)
        return supported

    def add_translation(
        self,
        key: str,
        locale: str,
        value: str,
        status: TranslationStatus = TranslationStatus.MACHINE,
        source: str = "manual",
    ) -> None:
        entry = TranslationEntry(
            key=key,
            locale=locale,
            value=value,
            status=status,
            source=source,
        )
        self._resource_mgr.set_entry(locale, entry)
