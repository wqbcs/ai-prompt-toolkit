"""国际化(i18n)框架 — 参考Fabric v1.4.356完整i18n模式

支持 BCP 47 locale 标准、回退链、术语表、翻译质量报告
"""

from ai_prompt_toolkit.i18n.fallback import FallbackChain
from ai_prompt_toolkit.i18n.glossary import Glossary
from ai_prompt_toolkit.i18n.manager import I18nManager, SUPPORTED_LOCALES, EXTENSIBLE_LOCALES
from ai_prompt_toolkit.i18n.messages import t, set_locale, get_current_locale, get_supported_locales, add_messages
from ai_prompt_toolkit.i18n.resource import ResourceManager
from ai_prompt_toolkit.i18n.translation import TranslationEngine
from ai_prompt_toolkit.i18n.types import (
    CoverageReport,
    Locale,
    TranslationEntry,
    TranslationStatus,
)

__all__ = [
    "FallbackChain",
    "Glossary",
    "I18nManager",
    "ResourceManager",
    "TranslationEngine",
    "CoverageReport",
    "Locale",
    "TranslationEntry",
    "TranslationStatus",
    "SUPPORTED_LOCALES",
    "EXTENSIBLE_LOCALES",
    "t",
    "set_locale",
    "get_current_locale",
    "get_supported_locales",
    "add_messages",
]
