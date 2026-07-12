"""BCP 47 回退链 — 参考 Fabric v1.4.317 locale 规范化"""
from __future__ import annotations

import os
from typing import Sequence

from ai_prompt_toolkit.i18n.types import Locale

_DEFAULT_FALLBACK_CHAIN: dict[str, list[str]] = {
    "zh-CN": ["zh-CN", "zh-Hans", "zh", "en-US", "en"],
    "zh-TW": ["zh-TW", "zh-Hant", "zh", "en-US", "en"],
    "en-US": ["en-US", "en", "zh-CN", "zh"],
    "ja-JP": ["ja-JP", "ja", "en-US", "en", "zh-CN", "zh"],
    "ko-KR": ["ko-KR", "ko", "en-US", "en", "zh-CN", "zh"],
    "pt-BR": ["pt-BR", "pt", "en-US", "en"],
    "pt-PT": ["pt-PT", "pt", "en-US", "en"],
    "de-DE": ["de-DE", "de", "en-US", "en"],
    "fr-FR": ["fr-FR", "fr", "en-US", "en"],
    "it-IT": ["it-IT", "it", "en-US", "en"],
}


class FallbackChain:
    def __init__(self, chains: dict[str, list[str]] | None = None):
        self._chains = chains or dict(_DEFAULT_FALLBACK_CHAIN)

    def resolve(self, locale: str, available: Sequence[str]) -> tuple[str, bool]:
        chain = self._build_chain(locale)
        available_set = set(available)
        for candidate in chain:
            if candidate in available_set:
                fallback = candidate != locale
                return candidate, fallback
        return "en-US", True

    def _build_chain(self, locale: str) -> list[str]:
        if locale in self._chains:
            return self._chains[locale]
        loc = Locale.from_bcp47(locale)
        chain = [locale]
        if loc.territory:
            chain.append(loc.language)
        parent_chain = self._chains.get(loc.language, [])
        for item in parent_chain:
            if item not in chain:
                chain.append(item)
        for default in ["en-US", "en", "zh-CN", "zh"]:
            if default not in chain:
                chain.append(default)
        return chain

    def add_chain(self, locale: str, chain: list[str]) -> None:
        self._chains[locale] = chain

    def get_chain(self, locale: str) -> list[str]:
        return self._build_chain(locale)

    @classmethod
    def from_env(cls) -> FallbackChain:
        instance = cls()
        env_lang = os.environ.get("PROMPT_LANGUAGE", "")
        if env_lang:
            for tag in env_lang.split(","):
                tag = tag.strip()
                if tag and tag not in instance._chains:
                    loc = Locale.from_bcp47(tag)
                    instance._chains[tag] = [tag, loc.language, "en-US", "en"]
        return instance
