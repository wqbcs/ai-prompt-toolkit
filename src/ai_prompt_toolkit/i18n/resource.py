"""ResourceManager — JSON格式资源文件加载和保存"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.i18n.types import CoverageReport, TranslationEntry, TranslationStatus

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(self, base_dir: str | Path | None = None):
        self._base_dir = Path(base_dir) if base_dir else Path.cwd() / "_i18n" / "locales"
        self._resources: dict[str, dict[str, TranslationEntry]] = {}

    def load_locale(self, locale: str) -> dict[str, TranslationEntry]:
        if locale in self._resources:
            return self._resources[locale]
        path = self._base_dir / locale / "templates.json"
        if not path.exists():
            logger.warning("资源文件不存在: %s", path)
            self._resources[locale] = {}
            return {}
        entries: dict[str, TranslationEntry] = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                templates = data.get("templates", data)
                for key, value in templates.items():
                    if isinstance(value, dict):
                        entries[key] = TranslationEntry.from_dict({"key": key, "locale": locale, **value})
                    elif isinstance(value, str):
                        entries[key] = TranslationEntry(key=key, locale=locale, value=value)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("加载资源文件失败 %s: %s", path, e)
            self._resources[locale] = {}
            return {}
        self._resources[locale] = entries
        return entries

    def save_locale(self, locale: str, entries: dict[str, TranslationEntry] | None = None) -> None:
        data_to_save = entries or self._resources.get(locale, {})
        path = self._base_dir / locale / "templates.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        output: dict[str, Any] = {
            "locale": locale,
            "version": "1.0",
            "templates": {},
        }
        for key, entry in data_to_save.items():
            output["templates"][key] = {
                "value": entry.value,
                "status": entry.status.value,
                "source": entry.source,
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def get_entry(self, locale: str, key: str) -> TranslationEntry | None:
        entries = self._resources.get(locale) or self.load_locale(locale)
        return entries.get(key)

    def set_entry(self, locale: str, entry: TranslationEntry) -> None:
        if locale not in self._resources:
            self._resources[locale] = {}
        self._resources[locale][entry.key] = entry

    def get_coverage(self, locale: str, reference_locale: str = "zh-CN") -> CoverageReport:
        ref_entries = self._resources.get(reference_locale) or self.load_locale(reference_locale)
        target_entries = self._resources.get(locale) or self.load_locale(locale)
        total = len(ref_entries)
        translated = 0
        human_reviewed = 0
        native = 0
        missing = 0
        for key in ref_entries:
            entry = target_entries.get(key)
            if entry and entry.value:
                translated += 1
                if entry.status == TranslationStatus.HUMAN_REVIEWED:
                    human_reviewed += 1
                elif entry.status == TranslationStatus.NATIVE:
                    native += 1
            else:
                missing += 1
        return CoverageReport(
            locale=locale,
            total_keys=total,
            translated=translated,
            human_reviewed=human_reviewed,
            native=native,
            missing=missing,
        )

    def available_locales(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        return [d.name for d in self._base_dir.iterdir() if d.is_dir() and (d / "templates.json").exists()]
