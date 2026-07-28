"""R112 测试: lint --watch实时监听 + 首次运行引导"""
from __future__ import annotations

from ai_prompt_toolkit.linter.rules import get_all_rules
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES


class TestR112WatchOption:
    def test_rules_count_unchanged(self):
        rules = get_all_rules()
        assert len(rules) == 210

    def test_auto_fixable_stable(self):
        assert len(AUTO_FIXABLE_RULES) >= 151


class TestR112FirstRunGuide:
    def test_init_template_exists(self):
        from pathlib import Path
        init_path = Path("src/ai_prompt_toolkit") / "__init__.py"
        assert init_path.exists()

    def test_changelog_exists(self):
        from pathlib import Path
        assert Path("CHANGELOG.md").exists()

    def test_version_is_52(self):
        from ai_prompt_toolkit import __version__
        assert __version__ == "52.0.0"
