"""i18n 类型定义 — BCP 47 locale 标准"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TranslationStatus(str, Enum):
    MISSING = "missing"
    MACHINE = "machine"
    HUMAN_REVIEWED = "human_reviewed"
    NATIVE = "native"


@dataclass
class Locale:
    language: str
    territory: str = ""
    script: str = ""

    @classmethod
    def from_bcp47(cls, tag: str) -> Locale:
        parts = tag.replace("-", "_").split("_")
        language = parts[0].lower() if parts else ""
        territory = parts[1].upper() if len(parts) > 1 else ""
        script = parts[2] if len(parts) > 2 else ""
        return cls(language=language, territory=territory, script=script)

    def to_bcp47(self) -> str:
        parts = [self.language]
        if self.script:
            parts.append(self.script.title())
        if self.territory:
            parts.append(self.territory)
        return "-".join(parts)

    @property
    def parent(self) -> Locale | None:
        if self.territory:
            return Locale(language=self.language)
        return None

    def __str__(self) -> str:
        return self.to_bcp47()


@dataclass
class TranslationEntry:
    key: str
    locale: str
    value: str
    status: TranslationStatus = TranslationStatus.MACHINE
    source: str = ""
    reviewed_by: str = ""
    reviewed_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "locale": self.locale,
            "value": self.value,
            "status": self.status.value,
            "source": self.source,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranslationEntry:
        return cls(
            key=data["key"],
            locale=data["locale"],
            value=data["value"],
            status=TranslationStatus(data.get("status", "machine")),
            source=data.get("source", ""),
            reviewed_by=data.get("reviewed_by", ""),
            reviewed_at=data.get("reviewed_at", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CoverageReport:
    locale: str
    total_keys: int = 0
    translated: int = 0
    human_reviewed: int = 0
    native: int = 0
    missing: int = 0
    fallback_used: int = 0

    @property
    def coverage_pct(self) -> float:
        return (self.translated / max(self.total_keys, 1)) * 100

    @property
    def quality_pct(self) -> float:
        return ((self.human_reviewed + self.native) / max(self.translated, 1)) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "locale": self.locale,
            "total_keys": self.total_keys,
            "translated": self.translated,
            "human_reviewed": self.human_reviewed,
            "native": self.native,
            "missing": self.missing,
            "fallback_used": self.fallback_used,
            "coverage_pct": round(self.coverage_pct, 1),
            "quality_pct": round(self.quality_pct, 1),
        }
