"""TranslationEngine — 翻译API调用和本地缓存，人工审校标记保护"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ai_prompt_toolkit.i18n.types import TranslationEntry, TranslationStatus

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class TranslationEngine:
    def __init__(
        self,
        cache_dir: str | Path | None = None,
        api_caller: Callable[[str, str, str], str] | None = None,
    ):
        self._cache_dir = Path(cache_dir) if cache_dir else Path.cwd() / "_i18n" / ".cache"
        self._api_caller = api_caller
        self._cache: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        cache_file = self._cache_dir / "translations.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def _save_cache(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_dir / "translations.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _cache_key(self, text: str, source_locale: str, target_locale: str) -> str:
        raw = f"{source_locale}:{target_locale}:{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def translate(
        self,
        text: str,
        source_locale: str,
        target_locale: str,
        use_cache: bool = True,
    ) -> TranslationEntry:
        key = self._cache_key(text, source_locale, target_locale)
        if use_cache and key in self._cache:
            return TranslationEntry(
                key=key,
                locale=target_locale,
                value=self._cache[key],
                status=TranslationStatus.MACHINE,
                source="cache",
            )
        if self._api_caller:
            try:
                result = self._api_caller(text, source_locale, target_locale)
                self._cache[key] = result
                self._save_cache()
                return TranslationEntry(
                    key=key,
                    locale=target_locale,
                    value=result,
                    status=TranslationStatus.MACHINE,
                    source="api",
                )
            except Exception as e:
                logger.error("翻译API调用失败: %s", e)
        env_key = f"TRANSLATE_{source_locale.upper()}_TO_{target_locale.upper()}"
        fallback = os.environ.get(env_key, "")
        if fallback:
            return TranslationEntry(
                key=key,
                locale=target_locale,
                value=fallback,
                status=TranslationStatus.MACHINE,
                source="env_fallback",
            )
        return TranslationEntry(
            key=key,
            locale=target_locale,
            value="",
            status=TranslationStatus.MISSING,
            source="unavailable",
        )

    def protect_reviewed(self, entry: TranslationEntry) -> bool:
        return entry.status in (TranslationStatus.HUMAN_REVIEWED, TranslationStatus.NATIVE)

    def batch_translate(
        self,
        entries: list[TranslationEntry],
        source_locale: str,
        target_locale: str,
    ) -> list[TranslationEntry]:
        results: list[TranslationEntry] = []
        for entry in entries:
            if self.protect_reviewed(entry):
                results.append(entry)
                continue
            translated = self.translate(entry.value, source_locale, target_locale)
            translated.key = entry.key
            results.append(translated)
        return results
