"""R78测试: 条件模板渲染 + NIST AI RMF映射"""

from __future__ import annotations


class TestConditionalRendering:
    def test_if_true(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        result = render_conditional("{% if verbose %}详细模式{% endif %}你好", {"verbose": True})
        assert "详细模式" in result

    def test_if_false(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        result = render_conditional("{% if verbose %}详细模式{% endif %}你好", {"verbose": False})
        assert "详细模式" not in result
        assert "你好" in result

    def test_if_else(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        result = render_conditional("{% if expert %}专家模式{% else %}普通模式{% endif %}", {"expert": False})
        assert "普通模式" in result
        assert "专家模式" not in result

    def test_if_else_true(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        result = render_conditional("{% if expert %}专家模式{% else %}普通模式{% endif %}", {"expert": True})
        assert "专家模式" in result

    def test_for_loop(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        template = "步骤:{% for step in steps %} {{step}}{% endfor %}"
        result = render_conditional(template, {"steps": ["准备", "执行", "验证"]})
        assert "准备" in result
        assert "执行" in result
        assert "验证" in result

    def test_i18n(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        template = "你是一个{% i18n role_desc %}"
        translations = {"role_desc": {"zh": "专业助手", "en": "professional assistant"}}
        result = render_conditional(template, {}, locale="zh", translations=translations)
        assert "专业助手" in result

    def test_i18n_en(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        template = "You are a {% i18n role_desc %}"
        translations = {"role_desc": {"zh": "专业助手", "en": "professional assistant"}}
        result = render_conditional(template, {}, locale="en", translations=translations)
        assert "professional assistant" in result

    def test_variable_with_conditional(self):
        from ai_prompt_toolkit.prompt_template import render_conditional

        template = "{% if show_name %}你好{{name}}{% endif %}"
        result = render_conditional(template, {"show_name": True, "name": "小明"})
        assert "你好小明" in result


class TestNISTRMFMapping:
    def test_mapping_exists(self):
        from ai_prompt_toolkit.linter.nist_rmf_mapping import get_nist_rmf_mapping

        mapping = get_nist_rmf_mapping()
        assert "GOVERN" in mapping
        assert "MAP" in mapping
        assert "MEASURE" in mapping
        assert "MANAGE" in mapping

    def test_get_rules_for_subcategory(self):
        from ai_prompt_toolkit.linter.nist_rmf_mapping import get_rules_for_nist_subcategory

        rules = get_rules_for_nist_subcategory("G1-01")
        assert len(rules) > 0
        assert "P001" in rules

    def test_nist_coverage(self):
        from ai_prompt_toolkit.linter.nist_rmf_mapping import get_nist_coverage_for_rules

        coverage = get_nist_coverage_for_rules(["P001", "P006", "P166"])
        assert "P001" in coverage
        assert "P006" in coverage

    def test_compliance_report(self):
        from ai_prompt_toolkit.linter.nist_rmf_mapping import generate_nist_compliance_report

        report = generate_nist_compliance_report(["P001", "P006", "P007", "P166"])
        assert report["framework"] == "NIST AI RMF 1.0"
        assert "function_coverage" in report
        assert report["total_subcategories_triggered"] > 0

    def test_eu_ai_act_mapping(self):
        from ai_prompt_toolkit.linter.nist_rmf_mapping import get_eu_ai_act_mapping

        mapping = get_eu_ai_act_mapping()
        assert "Article5-Prohibited" in mapping
        assert "Article9-Transparency" in mapping
        assert len(mapping["Article5-Prohibited"]) > 0
