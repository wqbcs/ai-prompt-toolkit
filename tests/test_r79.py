"""R79测试: lint --parallel并行 + lint类别统计验证"""

from __future__ import annotations

import pytest


class TestLintParallelOption:
    @pytest.mark.xfail(reason="R177死代码手术移除inline并行lint; 恢复记档R187", strict=True)
    def test_parallel_code_exists(self):
        import inspect

        from ai_prompt_toolkit import cli_core

        source = inspect.getsource(cli_core)
        assert "--parallel" in source or "parallel" in source


class TestLintCategoryStats:
    def test_category_counter_import(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        categories = set()
        for _rid, rule in _RULE_MAP.items():
            categories.add(rule.category)
        assert "security" in categories
        assert "structure" in categories
        assert len(categories) >= 5
