"""R93: P181-P185 Prompt运维Lint规则"""

from __future__ import annotations

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules


class TestP181P185Rules:
    def test_p181_version_missing(self):
        text = "你是一个生产环境部署的AI助手。"
        result = lint_template("test_p181", text)
        p181 = [f for f in result.findings if f.rule_id == "P181"]
        assert len(p181) > 0

    def test_p181_version_present(self):
        text = "version: 1.2.3\n你是一个D是一个AI助手。"
        result = lint_template("test_p181_pass", text)
        p181 = [f for f in result.findings if f.rule_id == "P181"]
        assert len(p181) == 0

    def test_p182_dependency_missing(self):
        text = "调用weather API获取天气信息。"
        result = lint_template("test_p182", text)
        p182 = [f for f in result.findings if f.rule_id == "P182"]
        assert len(p182) > 0

    def test_p183_env_isolation(self):
        text = "开发环境用GPT-3.5，测试环境用GPT-4，生产环境用Claude。"
        result = lint_template("test_p183", text)
        p183 = [f for f in result.findings if f.rule_id == "P183"]
        assert len(p183) > 0

    def test_p184_fallback_missing(self):
        text = "使用GPT-4模型回答用户问题。"
        result = lint_template("test_p184", text)
        p184 = [f for f in result.findings if f.rule_id == "P184"]
        assert len(p184) > 0

    def test_p185_canary_missing(self):
        text = "新版本部署上线，发布到生产环境。"
        result = lint_template("test_p185", text)
        p185 = [f for f in result.findings if f.rule_id == "P185"]
        assert len(p185) > 0

    def test_p181_p185_in_rule_map(self):
        for rid in ("P181", "P182", "P183", "P184", "P185"):
            assert rid in _RULE_MAP

    def test_p181_p185_auto_fixable(self):
        for rid in ("P181", "P182", "P183", "P184", "P185"):
            assert rid in AUTO_FIXABLE_RULES

    def test_total_rules_185(self):
        rules = get_all_rules()
        assert (
            len(rules) >= 264
        )  # R230-E: 精确总数由 test_rules_smoke_p021_p255.EXPECTED_TOTAL 单锚点锁, 此处只断言规则集未缩水

    def test_p181_p185_category(self):
        for rid in ("P181", "P182", "P183", "P184", "P185"):
            assert _RULE_MAP[rid].category == "operations"
