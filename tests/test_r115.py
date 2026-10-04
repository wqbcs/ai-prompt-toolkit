"""R115 测试: lint --ci + lint --diff"""

from __future__ import annotations

from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import get_all_rules


class TestR115CIAndDiff:
    def test_rules_count_stable(self):
        assert (
            len(get_all_rules()) >= 264
        )  # R230-E: 精确总数由 test_rules_smoke_p021_p255.EXPECTED_TOTAL 单锚点锁, 此处只断言规则集未缩水

    def test_auto_fixable_stable(self):
        assert len(AUTO_FIXABLE_RULES) >= 156

    def test_difflib_available(self):
        import difflib

        diff = list(difflib.unified_diff(["a\n", "b\n"], ["a\n", "c\n"], lineterm=""))
        assert len(diff) > 0
