"""术语表 — YAML格式术语管理，支持华为云领域术语"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from ai_prompt_toolkit.i18n.types import TranslationStatus

logger = logging.getLogger(__name__)

_DEFAULT_GLOSSARY: dict[str, dict[str, str]] = {
    "华为云": {
        "zh-CN": "华为云",
        "en-US": "Huawei Cloud",
    },
    "云容器引擎": {
        "zh-CN": "云容器引擎",
        "en-US": "Cloud Container Engine (CCE)",
    },
    "ModelArts": {
        "zh-CN": "ModelArts开发平台",
        "en-US": "ModelArts Development Platform",
    },
    "函数工作流": {
        "zh-CN": "函数工作流",
        "en-US": "FunctionGraph",
    },
    "云数据库": {
        "zh-CN": "云数据库 GaussDB",
        "en-US": "GaussDB Cloud Database",
    },
    "微服务引擎": {
        "zh-CN": "微服务引擎",
        "en-US": "Cloud Service Engine (CSE)",
    },
    "智能边缘": {
        "zh-CN": "智能边缘平台",
        "en-US": "Intelligent EdgeFabric (IEF)",
    },
    "虚拟私有云": {
        "zh-CN": "虚拟私有云",
        "en-US": "Virtual Private Cloud (VPC)",
    },
    "分布式缓存": {
        "zh-CN": "分布式缓存服务",
        "en-US": "Distributed Cache Service (DCS)",
    },
    "数据仓库": {
        "zh-CN": "数据仓库服务",
        "en-US": "Data Warehouse Service (DWS)",
    },
    "关系型数据库": {
        "zh-CN": "关系型数据库服务",
        "en-US": "Relational Database Service (RDS)",
    },
    "弹性云服务器": {
        "zh-CN": "弹性云服务器",
        "en-US": "Elastic Cloud Server (ECS)",
    },
    "对象存储": {
        "zh-CN": "对象存储服务",
        "en-US": "Object Storage Service (OBS)",
    },
    "弹性负载均衡": {
        "zh-CN": "弹性负载均衡",
        "en-US": "Elastic Load Balance (ELB)",
    },
    "裸金属服务器": {
        "zh-CN": "裸金属服务器",
        "en-US": "Bare Metal Server (BMS)",
    },
    "弹性伸缩": {
        "zh-CN": "弹性伸缩",
        "en-US": "Auto Scaling (AS)",
    },
    "专属主机": {
        "zh-CN": "专属主机",
        "en-US": "Dedicated Host (DeH)",
    },
    "提示词": {
        "zh-CN": "提示词",
        "en-US": "Prompt",
    },
    "条件编译": {
        "zh-CN": "条件编译",
        "en-US": "Conditional Compilation",
    },
    "模板继承": {
        "zh-CN": "模板继承",
        "en-US": "Template Inheritance",
    },
}


class Glossary:
    def __init__(self, data: dict[str, dict[str, str]] | None = None):
        self._entries: dict[str, dict[str, str]] = data or {}
        self._preferred: dict[str, str] = {}

    def load(self, path: str | Path) -> None:
        p = Path(path)
        if not p.exists():
            logger.warning("术语表文件不存在: %s", p)
            return
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return
        for term, translations in data.items():
            if isinstance(translations, dict):
                existing = self._entries.get(term, {})
                for locale, value in translations.items():
                    if term in existing and existing[locale] != value:
                        logger.warning("术语冲突: '%s' 在 %s 中有多个翻译，使用首选: %s",
                                       term, locale, self._preferred.get(term, value))
                    else:
                        existing[locale] = value
                self._entries[term] = existing

    def lookup(self, term: str, locale: str) -> str | None:
        entry = self._entries.get(term)
        if not entry:
            return None
        result = entry.get(locale)
        if result:
            return result
        for loc in sorted(entry.keys()):
            if loc != locale:
                return entry[loc]
        return None

    def add(self, term: str, locale: str, value: str, preferred: bool = False) -> None:
        if term not in self._entries:
            self._entries[term] = {}
        self._entries[term][locale] = value
        if preferred:
            self._preferred[term] = locale

    def terms(self) -> list[str]:
        return list(self._entries.keys())

    def to_dict(self) -> dict[str, dict[str, str]]:
        return dict(self._entries)

    @classmethod
    def default(cls) -> Glossary:
        return cls(data=dict(_DEFAULT_GLOSSARY))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(self._entries, f, allow_unicode=True, default_flow_style=False, sort_keys=True)
