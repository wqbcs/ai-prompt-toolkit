"""YAML Front Matter v3 Schema定义与验证

参考:
- Hugo: draft/publishDate/expiryDate/translationKey/cascade
- Docusaurus: draft/slug/tags/i18n文件命名
- Astro: Zod schema + defineCollection + Content Collections
- gray-matter: 多格式解析+stringify回写
- SchemaStore: JSON Schema注册

v3新增字段:
- i18n_status: 枚举(untranslated/machine_translated/human_translated/reviewed/approved/published)
- market_status: 枚举(draft/staging/review/approved/live/archived/expired)
- lint_score: 0-100数字
- lint_last_checked: ISO8601时间戳
- locale: BCP 47语言标签
- translation_key: 关联同一内容不同语言版本的key
- reviewed_at: ISO8601时间戳
- published_at: ISO8601时间戳
- expires_at: ISO8601时间戳(可选)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import yaml


class I18nStatus(str, Enum):
    UNTRANSLATED = "untranslated"
    MACHINE_TRANSLATED = "machine_translated"
    HUMAN_TRANSLATED = "human_translated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"


class MarketStatus(str, Enum):
    DRAFT = "draft"
    STAGING = "staging"
    REVIEW = "review"
    APPROVED = "approved"
    LIVE = "live"
    ARCHIVED = "archived"
    EXPIRED = "expired"


@dataclass
class FrontMatterV3:
    version: str = "3.0.0"
    author: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)
    applicable_models: list[str] = field(default_factory=list)
    inheritance: dict[str, Any] = field(default_factory=dict)
    locale: str = "zh-CN"
    i18n_status: str = "untranslated"
    market_status: str = "draft"
    lint_score: float = 0.0
    lint_last_checked: str = ""
    translation_key: str = ""
    reviewed_at: str = ""
    published_at: str = ""
    expires_at: str = ""

    _VALID_I18N = {s.value for s in I18nStatus}
    _VALID_MARKET = {s.value for s in MarketStatus}

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.i18n_status not in self._VALID_I18N:
            errors.append(f"Invalid i18n_status: {self.i18n_status}, expected one of {sorted(self._VALID_I18N)}")
        if self.market_status not in self._VALID_MARKET:
            errors.append(f"Invalid market_status: {self.market_status}, expected one of {sorted(self._VALID_MARKET)}")
        if not (0 <= self.lint_score <= 100):
            errors.append(f"Invalid lint_score: {self.lint_score}, expected 0-100")
        if self.locale and not re.match(r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$", self.locale):
            errors.append(f"Invalid locale BCP 47: {self.locale}")
        if self.published_at and self.market_status not in ("live", "archived", "expired"):
            errors.append(f"published_at set but market_status={self.market_status}, expected live/archived/expired")
        return errors

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "author": self.author,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "applicable_models": self.applicable_models,
            "inheritance": self.inheritance,
            "locale": self.locale,
            "i18n_status": self.i18n_status,
            "market_status": self.market_status,
            "lint_score": self.lint_score,
        }
        if self.lint_last_checked:
            d["lint_last_checked"] = self.lint_last_checked
        if self.translation_key:
            d["translation_key"] = self.translation_key
        if self.reviewed_at:
            d["reviewed_at"] = self.reviewed_at
        if self.published_at:
            d["published_at"] = self.published_at
        if self.expires_at:
            d["expires_at"] = self.expires_at
        return d


def parse_front_matter(text: str) -> tuple[dict[str, Any] | None, str]:
    if not text.startswith("---"):
        return None, text
    end = text.find("---", 3)
    if end == -1:
        return None, text
    fm_text = text[3:end].strip()
    body = text[end + 3 :].lstrip("\n")
    try:
        data = yaml.safe_load(fm_text)
        if not isinstance(data, dict):
            return None, text
        return data, body
    except yaml.YAMLError:
        return None, text


def upgrade_front_matter_v2_to_v3(data: dict[str, Any]) -> FrontMatterV3:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fm = FrontMatterV3(
        version="3.0.0",
        author=data.get("author", ""),
        updated_at=data.get("updated_at", now),
        tags=data.get("tags", []),
        applicable_models=data.get("applicable_models", []),
        inheritance=data.get("inheritance", {"enabled": False}),
        locale=data.get("locale", "zh-CN"),
        i18n_status=_infer_i18n_status(data),
        market_status=_infer_market_status(data),
        lint_score=data.get("lint_score", 0.0),
        lint_last_checked=data.get("lint_last_checked", ""),
        translation_key=data.get("translation_key", ""),
        reviewed_at=data.get("reviewed_at", ""),
        published_at=data.get("published_at", ""),
        expires_at=data.get("expires_at", ""),
    )
    return fm


def _infer_i18n_status(data: dict[str, Any]) -> str:
    if data.get("i18n_status"):
        return data["i18n_status"]
    locale = data.get("locale", "")
    if locale and locale != "zh-CN":
        return "human_translated"
    return "untranslated"


def _infer_market_status(data: dict[str, Any]) -> str:
    if data.get("market_status"):
        return data["market_status"]
    if data.get("published_at"):
        return "live"
    if data.get("reviewed_at"):
        return "approved"
    if data.get("version"):
        return "draft"
    return "draft"


def serialize_front_matter(fm: FrontMatterV3 | dict[str, Any]) -> str:
    if isinstance(fm, FrontMatterV3):
        data = fm.to_dict()
    else:
        data = fm
    fm_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_yaml}---\n"


def upgrade_markdown_file(text: str) -> tuple[str, list[str]]:
    parsed, body = parse_front_matter(text)
    if parsed is None:
        return text, ["No front matter found, skipping"]
    fm = upgrade_front_matter_v2_to_v3(parsed)
    errors = fm.validate()
    new_text = serialize_front_matter(fm) + body
    return new_text, errors
