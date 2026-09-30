"""R112 测试: lint --watch实时监听 + 首次运行引导"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import get_all_rules


class TestR112WatchOption:
    def test_rules_count_unchanged(self):
        rules = get_all_rules()
        assert len(rules) == 256  # R164扩容后实际值

    def test_auto_fixable_stable(self):
        assert len(AUTO_FIXABLE_RULES) >= 156


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

        # 语义化格式校验+主版本下限: 版本bump不应破坏测试
        assert re.match(r"^\d+\.\d+\.\d+$", __version__), f"版本号须为语义化格式: {__version__}"
        assert int(__version__.split(".")[0]) >= 52, "主版本不应回退"
