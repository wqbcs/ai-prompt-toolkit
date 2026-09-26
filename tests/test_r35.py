"""R35: 华为云鸿蒙赛事模板集 测试套件"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.builtin_templates import (
    HARMONY_OS_TEMPLATES,
    HUAWEI_CLOUD_TEMPLATES,
    get_harmonyos_template_names,
    get_huaweicloud_template_names,
    get_template_names,
    seed_builtin_templates,
)
from ai_prompt_toolkit.prompt_registry import PromptRegistry


class TestBuiltinTemplateIntegrity:
    def test_harmonyos_template_count(self):
        assert len(HARMONY_OS_TEMPLATES) == 10

    def test_huaweicloud_template_count(self):
        assert len(HUAWEI_CLOUD_TEMPLATES) == 5

    def test_total_template_count(self):
        assert len(get_template_names()) == 15

    def test_all_harmonyos_have_required_fields(self):
        for t in HARMONY_OS_TEMPLATES:
            assert t["name"], "Missing name"
            assert t["template"], f"Missing template for {t['name']}"
            assert len(t["template"]) > 100, f"Template too short: {t['name']}"
            assert t["description"], f"Missing description for {t['name']}"
            assert t["category"] == "harmonyos", f"Wrong category for {t['name']}"
            assert "harmonyos" in t["tags"], f"Missing harmonyos tag: {t['name']}"

    def test_all_huaweicloud_have_required_fields(self):
        for t in HUAWEI_CLOUD_TEMPLATES:
            assert t["name"], "Missing name"
            assert t["template"], f"Missing template for {t['name']}"
            assert len(t["template"]) > 100, f"Template too short: {t['name']}"
            assert t["description"], f"Missing description for {t['name']}"
            assert t["category"] == "huaweicloud", f"Wrong category for {t['name']}"
            assert "huaweicloud" in t["tags"], f"Missing huaweicloud tag: {t['name']}"

    def test_all_template_names_unique(self):
        names = get_template_names()
        assert len(names) == len(set(names)), "Duplicate template names found"

    def test_harmonyos_templates_contain_keywords(self):
        harmonyos_keywords = ["ArkTS", "Stage", "鸿蒙", "HarmonyOS", "@Component", "UIAbility"]
        for t in HARMONY_OS_TEMPLATES:
            has_keyword = any(kw.lower() in t["template"].lower() for kw in harmonyos_keywords)
            assert has_keyword, f"Template {t['name']} missing HarmonyOS keywords"

    def test_huaweicloud_templates_contain_keywords(self):
        hw_keywords = ["华为云", "huaweicloud", "IAM", "ModelArts", "OBS", "AK/SK", "cn-north-4"]
        for t in HUAWEI_CLOUD_TEMPLATES:
            has_keyword = any(kw.lower() in t["template"].lower() for kw in hw_keywords)
            assert has_keyword, f"Template {t['name']} missing HuaweiCloud keywords"

    def test_all_templates_have_author(self):
        for t in HARMONY_OS_TEMPLATES + HUAWEI_CLOUD_TEMPLATES:
            assert t.get("author"), f"Missing author for {t['name']}"


class TestGetTemplateNames:
    def test_get_harmonyos_names(self):
        names = get_harmonyos_template_names()
        assert len(names) == 10
        assert all(n.startswith("harmonyos-") for n in names)

    def test_get_huaweicloud_names(self):
        names = get_huaweicloud_template_names()
        assert len(names) == 5
        assert all(n.startswith("huaweicloud-") for n in names)

    def test_get_all_names(self):
        names = get_template_names()
        assert len(names) == 15


class TestSeedBuiltinTemplates:
    def test_seed_to_fresh_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            count = seed_builtin_templates(registry)
            assert count == 15
            registry.close()

    def test_seed_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            registry = PromptRegistry(db_path=db_path)
            count1 = seed_builtin_templates(registry)
            count2 = seed_builtin_templates(registry)
            assert count1 == 15
            assert count2 == 0
            registry.close()

    def test_seeded_templates_can_be_pulled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            seed_builtin_templates(registry)
            entry = registry.pull("harmonyos-arkts-component")
            assert entry is not None
            assert "ArkTS" in entry.template
            registry.close()

    def test_seeded_templates_searchable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            seed_builtin_templates(registry)
            results = registry.search("ArkTS")
            assert len(results) >= 1
            registry.close()

    def test_seeded_templates_categorized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            seed_builtin_templates(registry)
            harmonyos = registry.list_entries(category="harmonyos")
            huaweicloud = registry.list_entries(category="huaweicloud")
            assert len(harmonyos) == 10
            assert len(huaweicloud) == 5
            registry.close()

    def test_seeded_templates_tagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PromptRegistry(db_path=Path(tmpdir) / "test.db")
            seed_builtin_templates(registry)
            security_entries = registry.list_entries(tag="security")
            assert len(security_entries) >= 2
            registry.close()
