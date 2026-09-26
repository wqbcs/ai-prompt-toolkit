"""i18n框架单元测试"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ai_prompt_toolkit.i18n.fallback import FallbackChain
from ai_prompt_toolkit.i18n.glossary import Glossary
from ai_prompt_toolkit.i18n.manager import EXTENSIBLE_LOCALES, SUPPORTED_LOCALES, I18nManager
from ai_prompt_toolkit.i18n.resource import ResourceManager
from ai_prompt_toolkit.i18n.translation import TranslationEngine
from ai_prompt_toolkit.i18n.types import Locale, TranslationEntry, TranslationStatus


class TestLocale:
    def test_from_bcp47_full(self):
        loc = Locale.from_bcp47("zh-Hans-CN")
        assert loc.language == "zh"
        parts = loc.to_bcp47()
        assert "zh" in parts

    def test_from_bcp47_simple(self):
        loc = Locale.from_bcp47("en-US")
        assert loc.language == "en"
        assert loc.territory == "US"

    def test_parent(self):
        loc = Locale.from_bcp47("pt-BR")
        assert loc.parent is not None
        assert loc.parent.language == "pt"
        assert loc.parent.territory == ""

    def test_parent_no_territory(self):
        loc = Locale(language="en")
        assert loc.parent is None


class TestFallbackChain:
    def test_exact_match(self):
        fb = FallbackChain()
        resolved, fallback = fb.resolve("zh-CN", ["zh-CN", "en-US"])
        assert resolved == "zh-CN"
        assert not fallback

    def test_fallback_to_parent(self):
        fb = FallbackChain()
        resolved, fallback = fb.resolve("zh-CN", ["zh"])
        assert resolved == "zh"
        assert fallback

    def test_fallback_to_en(self):
        fb = FallbackChain()
        resolved, fallback = fb.resolve("ja-JP", ["en-US"])
        assert resolved == "en-US"
        assert fallback

    def test_unknown_locale(self):
        fb = FallbackChain()
        resolved, fallback = fb.resolve("xx-YY", ["en-US"])
        assert resolved == "en-US"
        assert fallback

    def test_custom_chain(self):
        fb = FallbackChain({"xx-YY": ["xx-YY", "xx", "en-US"]})
        resolved, fallback = fb.resolve("xx-YY", ["en-US"])
        assert resolved == "en-US"
        assert fallback


class TestGlossary:
    def test_default_glossary(self):
        g = Glossary.default()
        assert g.lookup("华为云", "en-US") == "Huawei Cloud"

    def test_missing_term(self):
        g = Glossary.default()
        assert g.lookup("不存在的术语", "en-US") is None

    def test_add_term(self):
        g = Glossary()
        g.add("测试术语", "en-US", "Test Term")
        assert g.lookup("测试术语", "en-US") == "Test Term"

    def test_yaml_save_load(self):
        g = Glossary.default()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "glossary.yaml"
            g.save(path)
            g2 = Glossary()
            g2.load(path)
            assert g2.lookup("华为云", "en-US") == "Huawei Cloud"


class TestResourceManager:
    def test_load_locale(self):
        with tempfile.TemporaryDirectory() as td:
            locale_dir = Path(td) / "zh-CN"
            locale_dir.mkdir()
            data = {"locale": "zh-CN", "templates": {"k1": {"value": "v1", "status": "native"}}}
            with open(locale_dir / "templates.json", "w", encoding="utf-8") as f:
                json.dump(data, f)
            mgr = ResourceManager(td)
            entries = mgr.load_locale("zh-CN")
            assert "k1" in entries
            assert entries["k1"].value == "v1"

    def test_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            for locale in ["zh-CN", "en-US"]:
                d = Path(td) / locale
                d.mkdir()
                data = {"locale": locale, "templates": {"k1": {"value": f"v1-{locale}", "status": "native"}}}
                with open(d / "templates.json", "w", encoding="utf-8") as f:
                    json.dump(data, f)
            mgr = ResourceManager(td)
            cov = mgr.get_coverage("en-US", "zh-CN")
            assert cov.total_keys == 1
            assert cov.coverage_pct == 100.0


class TestTranslationEngine:
    def test_cache_hit(self):
        engine = TranslationEngine(cache_dir=tempfile.mkdtemp())
        entry1 = engine.translate("hello world test", "en", "zh-CN")
        entry2 = engine.translate("hello world test", "en", "zh-CN")
        assert entry2.source in ("cache", "unavailable")

    def test_protect_reviewed(self):
        engine = TranslationEngine()
        entry = TranslationEntry(key="k1", locale="zh-CN", value="v1", status=TranslationStatus.HUMAN_REVIEWED)
        assert engine.protect_reviewed(entry)

    def test_machine_not_protected(self):
        engine = TranslationEngine()
        entry = TranslationEntry(key="k1", locale="zh-CN", value="v1", status=TranslationStatus.MACHINE)
        assert not engine.protect_reviewed(entry)


class TestI18nManager:
    def test_supported_locales(self):
        assert "zh-CN" in SUPPORTED_LOCALES
        assert "en-US" in SUPPORTED_LOCALES

    def test_extensible_locales(self):
        assert len(EXTENSIBLE_LOCALES) >= 8

    def test_get_translation(self):
        mgr = I18nManager(base_dir="_i18n")
        val = mgr.get_translation("basic_role", "en-US")
        assert "AI assistant" in val

    def test_get_coverage(self):
        mgr = I18nManager(base_dir="_i18n")
        cov = mgr.get_coverage("en-US", "zh-CN")
        assert cov.coverage_pct == 100.0
