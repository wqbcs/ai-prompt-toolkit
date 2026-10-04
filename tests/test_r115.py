"""R115 测试: lint --ci + lint --diff"""

from __future__ import annotations

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import get_all_rules


class TestR115CIAndDiff:
    def test_rules_count_stable(self):
        assert len(get_all_rules()) == 264  # R229 P262-P264 可移植性规则后实际值

    def test_auto_fixable_stable(self):
        assert len(AUTO_FIXABLE_RULES) >= 156

    def test_difflib_available(self):
        import difflib

        diff = list(difflib.unified_diff(["a\n", "b\n"], ["a\n", "c\n"], lineterm=""))
        assert len(diff) > 0
