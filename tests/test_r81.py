"""R81测试: P171-P175鸿蒙NEXT API 14规则 + CONTRIBUTING/CHANGELOG"""

from __future__ import annotations


class TestP171P175Rules:
    def test_p171_builder(self):
        from ai_prompt_toolkit.linter import lint_template

        result = lint_template("test_p171", "@Builder myBuilder() { Text('hello') }")
        p171 = [f for f in result.findings if f.rule_id == "P171"]
        assert len(p171) > 0

    def test_p172_lazy(self):
        from ai_prompt_toolkit.linter import lint_template

        result = lint_template("test_p172", "LazyForEach(data, item => Text(item))")
        p172 = [f for f in result.findings if f.rule_id == "P172"]
        assert len(p172) > 0

    def test_p173_reusable(self):
        from ai_prompt_toolkit.linter import lint_template

        result = lint_template("test_p173", "@Reusable @Component struct MyComp { build() {} }")
        p173 = [f for f in result.findings if f.rule_id == "P173"]
        assert len(p173) > 0

    def test_p174_uiability(self):
        from ai_prompt_toolkit.linter import lint_template

        result = lint_template("test_p174", "class MyAbility extends UIAbility { onCreate() {} }")
        p174 = [f for f in result.findings if f.rule_id == "P174"]
        assert len(p174) > 0

    def test_p175_distributed(self):
        from ai_prompt_toolkit.linter import lint_template

        result = lint_template("test_p175", "使用分布式数据同步")
        p175 = [f for f in result.findings if f.rule_id == "P175"]
        assert len(p175) > 0

    def test_total_rules_185(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules

        rules = get_all_rules()
        assert len(rules) == 261

    def test_p171_p175_bilingual(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        for rid in ("P171", "P172", "P173", "P174", "P175"):
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"

    def test_p171_p175_auto_fixable(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES

        for rid in ("P171", "P172", "P173", "P174", "P175"):
            assert rid in AUTO_FIXABLE_RULES

    def test_p171_p175_owasp(self):
        from ai_prompt_toolkit.linter.owasp_mapping import _OWASP_RULE_MAPPING

        # R228: harmonyos 平台安全规则原 2025 LLM06 → 2026 LLM03 (Excessive Agency 换位)
        llm03_rules = _OWASP_RULE_MAPPING.get("LLM03", [])
        for rid in ("P171", "P172", "P173", "P174", "P175"):
            assert rid in llm03_rules, f"{rid} not in LLM03"
