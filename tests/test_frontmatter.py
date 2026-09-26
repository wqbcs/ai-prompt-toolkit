"""Front Matter v3 Schema与升级工具单元测试"""

from __future__ import annotations

from ai_prompt_toolkit.frontmatter import (
    FrontMatterV3,
    I18nStatus,
    MarketStatus,
    parse_front_matter,
    serialize_front_matter,
    upgrade_front_matter_v2_to_v3,
    upgrade_markdown_file,
)


class TestI18nStatus:
    def test_all_values(self):
        assert I18nStatus.UNTRANSLATED.value == "untranslated"
        assert I18nStatus.PUBLISHED.value == "published"
        assert len(I18nStatus) == 6


class TestMarketStatus:
    def test_all_values(self):
        assert MarketStatus.DRAFT.value == "draft"
        assert MarketStatus.LIVE.value == "live"
        assert len(MarketStatus) == 7


class TestFrontMatterV3:
    def test_defaults(self):
        fm = FrontMatterV3()
        assert fm.version == "3.0.0"
        assert fm.i18n_status == "untranslated"
        assert fm.market_status == "draft"
        assert fm.lint_score == 0.0

    def test_validate_valid(self):
        fm = FrontMatterV3(i18n_status="reviewed", market_status="approved", lint_score=85.5)
        errors = fm.validate()
        assert len(errors) == 0

    def test_validate_invalid_i18n(self):
        fm = FrontMatterV3(i18n_status="invalid")
        errors = fm.validate()
        assert len(errors) > 0

    def test_validate_invalid_market(self):
        fm = FrontMatterV3(market_status="invalid")
        errors = fm.validate()
        assert len(errors) > 0

    def test_validate_lint_score_out_of_range(self):
        fm = FrontMatterV3(lint_score=150)
        errors = fm.validate()
        assert any("lint_score" in e for e in errors)

    def test_validate_negative_lint_score(self):
        fm = FrontMatterV3(lint_score=-10)
        errors = fm.validate()
        assert any("lint_score" in e for e in errors)

    def test_validate_invalid_locale(self):
        fm = FrontMatterV3(locale="invalid locale!!")
        errors = fm.validate()
        assert any("locale" in e for e in errors)

    def test_validate_valid_locale_zh_cn(self):
        fm = FrontMatterV3(locale="zh-CN")
        assert len(fm.validate()) == 0

    def test_validate_valid_locale_en_us(self):
        fm = FrontMatterV3(locale="en-US")
        assert len(fm.validate()) == 0

    def test_validate_published_at_without_live(self):
        fm = FrontMatterV3(published_at="2026-01-01", market_status="draft")
        errors = fm.validate()
        assert any("published_at" in e for e in errors)

    def test_to_dict(self):
        fm = FrontMatterV3(i18n_status="reviewed", market_status="live", lint_score=90)
        d = fm.to_dict()
        assert d["i18n_status"] == "reviewed"
        assert d["market_status"] == "live"
        assert d["lint_score"] == 90
        assert "lint_last_checked" not in d

    def test_to_dict_optional_fields(self):
        fm = FrontMatterV3(
            lint_last_checked="2026-07-13",
            translation_key="e1_arkts",
            reviewed_at="2026-07-01",
        )
        d = fm.to_dict()
        assert d["lint_last_checked"] == "2026-07-13"
        assert d["translation_key"] == "e1_arkts"
        assert d["reviewed_at"] == "2026-07-01"


class TestParseFrontMatter:
    def test_valid_front_matter(self):
        text = "---\nversion: 1.0.0\nauthor: test\n---\nBody content"
        data, body = parse_front_matter(text)
        assert data is not None
        assert data["version"] == "1.0.0"
        assert body == "Body content"

    def test_no_front_matter(self):
        text = "Just body content"
        data, _body = parse_front_matter(text)
        assert data is None

    def test_unclosed_front_matter(self):
        text = "---\nversion: 1.0.0\nauthor: test\nBody without closing"
        data, _body = parse_front_matter(text)
        assert data is None

    def test_invalid_yaml(self):
        text = "---\n: : invalid\n---\nBody"
        data, _body = parse_front_matter(text)
        assert data is None


class TestUpgradeV2ToV3:
    def test_basic_upgrade(self):
        v2 = {
            "version": "1.0.0",
            "author": "test",
            "updated_at": "2026-07-01",
            "tags": ["harmonyos"],
        }
        fm = upgrade_front_matter_v2_to_v3(v2)
        assert fm.version == "3.0.0"
        assert fm.i18n_status == "untranslated"
        assert fm.market_status == "draft"
        assert fm.tags == ["harmonyos"]

    def test_preserves_existing_i18n_status(self):
        v2 = {"version": "2.0", "i18n_status": "reviewed"}
        fm = upgrade_front_matter_v2_to_v3(v2)
        assert fm.i18n_status == "reviewed"

    def test_infers_market_status_from_published(self):
        v2 = {"version": "2.0", "published_at": "2026-01-01"}
        fm = upgrade_front_matter_v2_to_v3(v2)
        assert fm.market_status == "live"

    def test_infers_i18n_from_locale(self):
        v2 = {"version": "2.0", "locale": "en-US"}
        fm = upgrade_front_matter_v2_to_v3(v2)
        assert fm.i18n_status == "human_translated"


class TestSerializeFrontMatter:
    def test_round_trip(self):
        fm = FrontMatterV3(author="test", i18n_status="reviewed", lint_score=85)
        yaml_str = serialize_front_matter(fm)
        assert yaml_str.startswith("---\n")
        assert "i18n_status: reviewed" in yaml_str
        assert "---\n" in yaml_str[4:]

    def test_dict_serialize(self):
        data = {"version": "3.0.0", "author": "test"}
        yaml_str = serialize_front_matter(data)
        assert "version: 3.0.0" in yaml_str


class TestUpgradeMarkdownFile:
    def test_upgrade_file(self):
        text = "---\nversion: 1.0.0\nauthor: test\ntags: [harmonyos]\n---\nBody"
        new_text, _errors = upgrade_markdown_file(text)
        assert "i18n_status" in new_text
        assert "market_status" in new_text
        assert "lint_score" in new_text
        assert "Body" in new_text

    def test_no_front_matter(self):
        text = "Just body"
        new_text, errors = upgrade_markdown_file(text)
        assert new_text == text
        assert any("No front matter" in e for e in errors)

    def test_preserves_body(self):
        text = "---\nversion: 1.0.0\n---\n# Title\n\nContent here"
        new_text, _errors = upgrade_markdown_file(text)
        assert "# Title" in new_text
        assert "Content here" in new_text
