"""R71测试: OWASP LLM Top 10映射 — P001-P150规则到LLM01-LLM10对照"""

from __future__ import annotations

from ai_prompt_toolkit.linter.owasp_mapping import (
    get_owasp_coverage,
    get_rules_by_owasp,
)
from ai_prompt_toolkit.linter.rules import _RULE_MAP


class TestOWASPMapping:
    def test_all_owasp_refs_have_rules(self):
        for ref in ("LLM01", "LLM02", "LLM03", "LLM04", "LLM05", "LLM06", "LLM07", "LLM08", "LLM09", "LLM10"):
            rules = get_rules_by_owasp(ref)
            assert len(rules) > 0, f"{ref} has no mapped rules"

    def test_mapped_rules_exist_in_rule_map(self):
        for ref, rule_ids in [
            ("LLM01", get_rules_by_owasp("LLM01")),
            ("LLM06", get_rules_by_owasp("LLM06")),
            ("LLM09", get_rules_by_owasp("LLM09")),
        ]:
            for rid in rule_ids:
                assert rid in _RULE_MAP, f"{rid} (mapped to {ref}) not in _RULE_MAP"

    def test_security_rules_mapped(self):
        security_rules = [r for r in _RULE_MAP.values() if r.category == "security"]
        with_owasp = [r for r in security_rules if r.owasp_refs]
        assert len(with_owasp) >= 15

    # R228: 2025 LLM06 (Excessive Agency) → 2026 LLM03（换位 #6→#3）
    def test_agent_rules_mapped_to_llm03(self):
        llm03_rules = get_rules_by_owasp("LLM03")
        for rid in ("P141", "P142", "P143", "P144", "P145"):
            assert rid in llm03_rules, f"{rid} should map to LLM03"

    def test_injection_rules_mapped_to_llm01(self):
        llm01_rules = get_rules_by_owasp("LLM01")
        for rid in ("P006", "P007", "P031", "P032"):
            assert rid in llm01_rules, f"{rid} should map to LLM01"

    def test_owasp_coverage_complete(self):
        coverage = get_owasp_coverage()
        assert len(coverage) == 10
        for ref in ("LLM01", "LLM02", "LLM03", "LLM04", "LLM05", "LLM06", "LLM07", "LLM08", "LLM09", "LLM10"):
            assert ref in coverage
            assert "name" in coverage[ref]
            assert "lint_rules" in coverage[ref]
            assert "lint_coverage" in coverage[ref]
            assert coverage[ref]["lint_coverage"] > 0

    def test_to_dict_includes_owasp_refs(self):
        p006 = _RULE_MAP["P006"]
        d = p006.to_dict()
        assert "owasp_refs" in d
        assert "LLM01" in d["owasp_refs"]

    def test_no_owasp_refs_not_in_dict(self):
        from ai_prompt_toolkit.linter.rules import LintRule, Severity

        rule = LintRule("TEST", "test", "test", Severity.LOW, "test", "test")
        d = rule.to_dict()
        assert "owasp_refs" not in d
