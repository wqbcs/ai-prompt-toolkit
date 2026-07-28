"""R97: P186-P190 鸿蒙NEXT API 15 Lint规则"""
from __future__ import annotations

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules import get_all_rules, _RULE_MAP
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.types import Severity


class TestP186P190Rules:
    def test_p186_arkui_migration_needed(self):
        text = "使用ArkUI的@Component和命令式API构建界面。"
        result = lint_template("test_p186", text)
        p186 = [f for f in result.findings if f.rule_id == "P186"]
        assert len(p186) > 0

    def test_p186_arkui_v15_pass(self):
        text = "使用ArkUI API 15声明式范式, @Builder和@Styles构建界面。"
        result = lint_template("test_p186_pass", text)
        p186 = [f for f in result.findings if f.rule_id == "P186"]
        assert len(p186) == 0

    def test_p187_napi_thread_unsafe(self):
        text = "使用Node-API的napi_env和napi_value进行跨线程调用。"
        result = lint_template("test_p187", text)
        p187 = [f for f in result.findings if f.rule_id == "P187"]
        assert len(p187) > 0

    def test_p188_sandbox_v1(self):
        text = "通过文件访问读取用户数据文件。"
        result = lint_template("test_p188", text)
        p188 = [f for f in result.findings if f.rule_id == "P188"]
        assert len(p188) > 0

    def test_p189_hsp_no_dep(self):
        text = "使用HSP模块化和HAP模块构建应用。"
        result = lint_template("test_p189", text)
        p189 = [f for f in result.findings if f.rule_id == "P189"]
        assert len(p189) > 0

    def test_p190_atomic_service_no_constraint(self):
        text = "开发免安装的元服务(Atomic Service)应用。"
        result = lint_template("test_p190", text)
        p190 = [f for f in result.findings if f.rule_id == "P190"]
        assert len(p190) > 0

    def test_p186_p190_in_rule_map(self):
        for rid in ("P186", "P187", "P188", "P189", "P190"):
            assert rid in _RULE_MAP

    def test_p186_p190_auto_fixable(self):
        for rid in ("P186", "P187", "P188", "P189", "P190"):
            assert rid in AUTO_FIXABLE_RULES

    def test_total_rules_190(self):
        rules = get_all_rules()
        assert len(rules) == 210

    def test_p186_p190_category(self):
        for rid in ("P186", "P187", "P188", "P189", "P190"):
            assert _RULE_MAP[rid].category == "harmonyos"

    def test_p186_p190_owasp(self):
        for rid in ("P186", "P187", "P188", "P189", "P190"):
            assert len(_RULE_MAP[rid].owasp_refs) > 0
