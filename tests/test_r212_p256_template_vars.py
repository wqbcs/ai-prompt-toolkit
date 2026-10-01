"""R212: P256 模板变量完整性规则测试

正样本: 畸形占位符 / 显式声明段外的引用
负样本: 隐式变量风格(clean43-46形态) / |default回退 / handlebars指令 / 代码围栏内
零命中断言: 56干净样本 = 0命中 (沿用R206-R211纪律, 第一天建立)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"


def _rule_ids(result) -> list[str]:
    return [f.rule_id for f in result.findings]


class TestP256Positive:
    def test_malformed_placeholder_empty(self):
        r = lint_template("r212_p256_pos1", "把下面的内容翻译成英文：{{}}")
        # 空占位符不报(无内层内容), 但非空畸形必须报
        assert "P256" not in _rule_ids(r)

    def test_malformed_placeholder_hyphen(self):
        r = lint_template("r212_p256_pos2", "渲染模板: 标题为 {{my-title}}, 正文为 {{body}}")
        assert "P256" in _rule_ids(r)

    def test_malformed_placeholder_inner_space(self):
        # 注意: {{客户名}} 是渲染器合法变量(py3 \w+匹配CJK), 不在此列 —
        # 规则口径=与渲染引擎一致, 只报渲染器填不上的形态
        r = lint_template("r212_p256_pos3", "模板: 欢迎 {{客户 名}} 使用本服务")
        assert "P256" in _rule_ids(r)

    def test_valid_chinese_var_not_reported(self):
        # 与渲染引擎一致: 中文变量名是合法占位符
        r = lint_template("r212_p256_pos3b", "模板: 欢迎 {{客户名}} 使用本服务")
        assert "P256" not in _rule_ids(r)

    def test_undeclared_var_in_declared_style(self):
        text = (
            "# 变量\n"
            "- name: 客户姓名\n"
            "- date: 日期\n"
            "\n"
            "# 任务\n"
            "给 {{name}} 写一封 {{date}} 的跟进邮件，抄送 {{manager}}。"
        )
        r = lint_template("r212_p256_pos4", text)
        assert "P256" in _rule_ids(r)

    def test_default_fallback_not_reported(self):
        r = lint_template("r212_p256_pos5", "你是一个{{role|default('智能助手')}}。回答: {{question}}")
        # 无声明段(隐式风格) → 不报未声明; {{role|default(...)}} 合法语法
        assert "P256" not in _rule_ids(r)


class TestP256Negative:
    def test_implicit_style_no_declaration(self):
        """clean43-46形态: 变量只在正文出现, 无声明段 → 不报(隐式变量由调用方提供)"""
        text = "根据以下变量撰写邮件：\n- 客户姓名: {{customer_name}}\n- 事项: {{followup_item}}"
        r = lint_template("r212_p256_neg1", text)
        assert "P256" not in _rule_ids(r)

    def test_handlebars_directives_not_reported(self):
        r = lint_template("r212_p256_neg2", "模板: {{#if user}}已登录{{/if}}，用户 {{user}}")
        assert "P256" not in _rule_ids(r)

    def test_code_fence_placeholder_ignored(self):
        text = "说明文档：\n```\n{{broken-var}} 是示例\n```\n正文变量 {{ok}}。"
        r = lint_template("r212_p256_neg3", text)
        assert "P256" not in _rule_ids(r)

    def test_declared_all_referenced_ok(self):
        text = "# 变量\n- name: 姓名\n- city: 城市\n\n# 任务\n为 {{name}} 生成 {{city}} 的天气摘要。"
        r = lint_template("r212_p256_neg4", text)
        assert "P256" not in _rule_ids(r)

    def test_plain_text_no_braces(self):
        r = lint_template("r212_p256_neg5", "你是一名专业的技术写作助手，请优化以下文案。")
        assert "P256" not in _rule_ids(r)


class TestP256CleanSamples:
    """56干净样本零命中 — P256第一天建立的负样本基线"""

    def test_zero_hits_on_clean_prompts(self):
        hits: list[str] = []
        for p in sorted(_CLEAN_DIR.iterdir()):
            text = p.read_text(encoding="utf-8")
            r = lint_template(p.name, text)
            for f in r.findings:
                if f.rule_id == "P256":
                    hits.append(p.name)
        assert not hits, f"P256 在干净样本上误报: {hits}"
