"""R79测试: lint --parallel并行 + lint类别统计验证"""

from __future__ import annotations


class TestLintParallelOption:
    def test_parallel_code_exists(self):
        # R187: 断言升级为行为级 — lint命令params含parallel(源码grep断言曾因命令搬家失效)
        from ai_prompt_toolkit.cli_core import main

        lint_cmd = main.commands["lint"]
        param_names = [p.name for p in lint_cmd.params]
        assert "parallel" in param_names


class TestLintCategoryStats:
    def test_category_counter_import(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        categories = set()
        for _rid, rule in _RULE_MAP.items():
            categories.add(rule.category)
        assert "security" in categories
        assert "structure" in categories
        assert len(categories) >= 5
