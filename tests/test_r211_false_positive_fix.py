"""R211: 误报第五批处置回归测试

处置6组高误报规则(R210扩样56样本下暴露):
- P151-P155: 生产服务面门(声明类规则仅生产语境强制, 沿用R207 P181先例)
- P161: 模板注入门收窄到"模板/渲染/变量"管道组合(裸{{变量/formart泛词去除)
- P183: 环境隔离门收窄到≥2个不同环境名+「环境」共现
- P244: 审计日志门收窄到"变更类操作作用于敏感对象"
- P182: 依赖声明门收窄到API实体+调用动作共现
- P084: 格式约束DECL扩充(表头行/内联JSON/章节结构/字段定义/仅输出/英文结构词)

负样本断言: 8条规则 x 56干净样本 = 0命中(P244残留1条SQL多语言样本, 1.8%低于阈值)
正样本断言: 强语义词场景保留命中(检测能力未削弱)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
# 本批收窄后应完全清零的规则
_ZERO_RULES = ["P151", "P152", "P153", "P154", "P155", "P161", "P183", "P084"]
# 残留低于阈值(≤2/56)的规则
_LOW_RULES = ["P244", "P182"]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR211NegativeSamples:
    """8条清零规则 x 56干净样本 = 0命中; 2条残留规则 ≤ 2命中"""

    def test_zero_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 58, f"干净样本数应为58, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _ZERO_RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"

    def test_low_rules_below_threshold(self):
        samples = _clean_samples()
        hits: dict[str, list[str]] = {r: [] for r in _LOW_RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert len(hit_names) <= 2, f"{rule} 在干净样本上误报超标(>2/58=3.4%): {hit_names}"


class TestR211PositiveSamples:
    """正样本: 生产/管道/多环境/敏感变更场景保留命中"""

    def test_p151_prod_api_no_validation(self):
        r = lint_template("r211_p151_pos", "生产环境API服务，接收用户输入并调用后端接口处理请求")
        assert any(f.rule_id == "P151" for f in r.findings)

    def test_p151_prod_api_with_validation_pass(self):
        r = lint_template("r211_p151_ok", "生产环境API服务，输入长度<=2000字符，仅允许中英文和数字，白名单校验")
        assert not any(f.rule_id == "P151" for f in r.findings)

    def test_p151_draft_api_not_required(self):
        # R211收窄: 本地草稿/文档类API prompt不强制输入校验声明
        r = lint_template("r211_p151_neg", "API接口设计草稿，本地开发用，描述请求和响应结构")
        assert not any(f.rule_id == "P151" for f in r.findings)

    def test_p153_prod_no_rate_limit(self):
        r = lint_template("r211_p153_pos", "生产环境API服务，处理用户调用请求")
        assert any(f.rule_id == "P153" for f in r.findings)

    def test_p153_prod_with_rate_limit_pass(self):
        r = lint_template("r211_p153_ok", "生产环境API服务，每用户每分钟最多10次调用，Token上限8192")
        assert not any(f.rule_id == "P153" for f in r.findings)

    def test_p154_prod_no_audit(self):
        r = lint_template("r211_p154_pos", "生产环境服务，接口调用处理用户数据")
        assert any(f.rule_id == "P154" for f in r.findings)

    def test_p154_prod_with_audit_pass(self):
        r = lint_template("r211_p154_ok", "生产环境服务，记录每次调用审计日志，保留90天")
        assert not any(f.rule_id == "P154" for f in r.findings)

    def test_p161_template_render_no_escape(self):
        # 模板+变量+渲染管道组合仍要求注入防护
        r = lint_template("r211_p161_pos", "使用模板渲染{{user_input}}变量，进行字符串替换和格式化")
        assert any(f.rule_id == "P161" for f in r.findings)

    def test_p161_template_render_with_escape_pass(self):
        r = lint_template("r211_p161_ok", "模板注入防护: 变量强制转义escaping, 沙箱sandbox渲染, 禁止原始渲染")
        assert not any(f.rule_id == "P161" for f in r.findings)

    def test_p161_plain_placeholder_not_required(self):
        # R211收窄: 数据提取类{{var}}占位符(无渲染/管道语义)不要求模板注入防护
        r = lint_template("r211_p161_neg", "从 {{user_input}} 中提取字段并输出 JSON，字段定义见下")
        assert not any(f.rule_id == "P161" for f in r.findings)

    def test_p183_multi_env_no_isolation(self):
        r = lint_template("r211_p183_pos", "开发环境用GPT-3.5，测试环境用GPT-4，生产环境用Claude。")
        assert any(f.rule_id == "P183" for f in r.findings)

    def test_p183_single_env_word_not_required(self):
        # R211收窄: 裸"测试/单元测试"文档语境不要求环境隔离
        r = lint_template("r211_p183_neg", "你是一名单元测试工程师，编写测试用例")
        assert not any(f.rule_id == "P183" for f in r.findings)

    def test_p244_sensitive_mutation_no_audit(self):
        r = lint_template("r211_p244_pos", "删除用户数据并修改权限")
        assert any(f.rule_id == "P244" for f in r.findings)

    def test_p244_sensitive_mutation_with_audit_pass(self):
        r = lint_template("r211_p244_ok", "删除用户数据(audit_log记录who/what/when/why)")
        assert not any(f.rule_id == "P244" for f in r.findings)

    def test_p244_sql_maintenance_not_required(self):
        # R211收窄: SQL维护/排障语境(查询/修改代码)不要求审计日志
        r = lint_template("r211_p244_neg", "审查SQL查询性能，修改索引和查询计划")
        assert not any(f.rule_id == "P244" for f in r.findings)

    def test_p182_api_call_no_dependency(self):
        r = lint_template("r211_p182_pos", "调用weather API获取天气信息。")
        assert any(f.rule_id == "P182" for f in r.findings)

    def test_p182_api_doc_writing_not_required(self):
        # R211收窄: 写API文档/审查API设计不构成外部依赖调用
        r = lint_template("r211_p182_neg", "审查 REST API 端点定义，给出规范化建议。")
        assert not any(f.rule_id == "P182" for f in r.findings)

    def test_p084_json_without_constraint(self):
        r = lint_template("r211_p084_pos", "请返回JSON格式的结果")
        assert any(f.rule_id == "P084" for f in r.findings)

    def test_p084_json_with_field_definition_pass(self):
        # R211: 字段定义段是格式约束
        r = lint_template("r211_p084_ok1", "从输入中提取字段并输出 JSON。# 字段定义 - name: 姓名(必填)")
        assert not any(f.rule_id == "P084" for f in r.findings)

    def test_p084_markdown_with_sections_pass(self):
        # R211: 章节结构声明是格式约束
        r = lint_template("r211_p084_ok2", "Output a markdown report with sections: Bugs, Security, Style.")
        assert not any(f.rule_id == "P084" for f in r.findings)

    def test_p084_markdown_with_header_row_pass(self):
        # R211: 表头行是格式约束
        r = lint_template("r211_p084_ok3", "输出Markdown表格：事项 | 负责人 | 截止日期")
        assert not any(f.rule_id == "P084" for f in r.findings)

    def test_p084_json_with_inline_example_pass(self):
        # R211: 内联JSON字面量是格式约束
        r = lint_template("r211_p084_ok4", '输出分类结果 JSON：{"category": "<类别>", "priority": "P1"}')
        assert not any(f.rule_id == "P084" for f in r.findings)
