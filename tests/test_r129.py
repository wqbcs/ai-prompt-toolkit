"""R129 测试: 规则搜索引擎"""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.rules import search_rules


class TestR129RulesSearch:
    def test_search_injection_en(self):
        results = search_rules("injection")
        assert len(results) > 0

    def test_search_injection_zh(self):
        results = search_rules("注入")
        assert len(results) > 0

    def test_search_owasp_ref(self):
        results = search_rules("LLM01")
        assert len(results) > 0

    def test_search_category(self):
        results = search_rules("security", category="security")
        assert len(results) > 0
        assert all(r["category"] == "security" for r in results)

    def test_search_owasp_filter(self):
        results = search_rules("prompt", owasp="LLM06")
        assert len(results) > 0
        assert all("LLM06" in r["owasp_refs"] for r in results)

    def test_search_no_result(self):
        results = search_rules("xyznonexistent123")
        assert len(results) == 0

    def test_search_limit(self):
        results = search_rules("prompt", limit=5)
        assert len(results) <= 5

    def test_search_result_fields(self):
        results = search_rules("注入", limit=1)
        assert len(results) == 1
        r = results[0]
        assert "rule_id" in r and "name" in r and "score" in r

    def test_lint_rules_search_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("测试", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--rules-search", "注入"])
            assert "规则搜索" in result.output
            assert "P176" in result.output or "注入" in result.output
