"""R230-P1-17: P265 cache-unfriendly 前缀动态内容回归测试。

对标 aiproof AIP009（R230 调研：prompt caching 前缀精确字节匹配，前缀动态
内容静默击溃缓存）。精度设计=前缀区（512 有效字符，frontmatter 豁免）×
运行时动态 token × 强信号共现（缓存意图词或长 prompt）。
反例断言锁死低误报：短 prompt 动态内容、动态内容后置、稳定占位符都不报。
"""

from __future__ import annotations

from ai_prompt_toolkit.baselines import lint_template
from ai_prompt_toolkit.linter.rules import get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.rules_p265 import (
    _PREFIX_EFF_LEN,
    _effective_len,
    check_p265,
)


def _ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


class TestRuleRegistration:
    def test_rule_registered(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        assert rules["P265"].category == "portability"
        assert rules["P265"].family == "prompt_caching"

    def test_severity(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        assert rules["P265"].severity.value == "medium"

    def test_bilingual_fields(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        assert rules["P265"].description_en
        assert rules["P265"].remediation_en


class TestP265TruePositives:
    def test_chinese_timestamp_label_long_prompt(self):
        """中文主力形态：'当前时间：{timestamp}' 在头部 + 长 prompt（缓存收益场景）"""
        text = "当前时间：{timestamp}。你是客服助手。" + "知识条目内容；" * 150
        f = check_p265(text)
        assert f is not None
        assert "timestamp" in f.details["dynamic_token"]
        assert f.details["signal"] == "long_prompt"

    def test_english_uuid_call_with_cache_intent(self):
        """函数调用形态 + 缓存意图词共现（短 prompt 也报——意图信号独立生效）"""
        text = (
            "You are a data analysis assistant. Session request_id={uuid}, "
            "started {datetime.now()}. We keep a cached prefix for all turns."
        )
        f = check_p265(text)
        assert f is not None
        assert f.details["signal"] == "cache_intent"

    def test_jinja_now_placeholder_prefix(self):
        """{{now}} 双花括号占位在前缀区 + 长 prompt"""
        text = "Report date: {{now}}. " + "Analysis guideline item. " * 60
        f = check_p265(text)
        assert f is not None
        assert f.details["dynamic_token"].lower().startswith("{{now}}")

    def test_single_brace_bare_placeholder(self):
        """str.format 形态 {timestamp} 裸占位（无中文标签）+ 缓存意图"""
        text = "Audit log entry {timestamp} for trace {trace_id}; prefix is cached across requests."
        f = check_p265(text)
        assert f is not None


class TestP265FalsePositiveGuards:
    def test_short_prompt_with_timestamp_no_hit(self):
        """短 prompt（<2×前缀区）无缓存意图 → 动态内容属正常用法，不报（TN 锚点）"""
        text = "当前时间：{timestamp}。请简洁回答用户问题。"
        assert check_p265(text) is None

    def test_dynamic_content_at_suffix_no_hit(self):
        """动态 token 在尾部（追加位置）——前缀区干净，缓存不被击溃，不报"""
        text = "你是资深代码审查助手。" + "审查维度与输出规范说明。" * 80 + "当前时间：{timestamp}。"
        assert check_p265(text) is None

    def test_stable_placeholders_no_hit(self):
        """稳定模板占位符 {{title}}/{{date}}/{{user_question}} 非运行时动态 token，不报"""
        text = (
            "公告标题：{{title}} 发布日期：{{date}} 更新内容：{{changes}}。"
            "这是每周更新公告的模板，请根据团队提供的稳定素材填充，"
            "不要新增模板外的段落，条目数不超过五条，没有对应信息时保留占位符原样。"
        )
        assert check_p265(text) is None

    def test_cache_word_alone_no_hit(self):
        """只有缓存意图词、无动态 token → 不报"""
        text = "本系统使用缓存策略降低延迟。" + "架构说明文字。" * 60
        assert check_p265(text) is None

    def test_frontmatter_exempt(self):
        """frontmatter 里的时间戳声明（元数据）不是正文前缀区，不报（R229 同惯例）"""
        text = "---\nlast_updated: {timestamp}\nmodel: any\n---\n" + "正文内容是稳定指令。" * 30
        assert check_p265(text) is None


class TestP265PrefixZoneSemantics:
    def test_effective_len_cjk_weighting(self):
        """CJK 2× 加权口径（与 inline_prompt._effective_len 同口径）"""
        assert _effective_len("汉字") == 4
        assert _effective_len("ab") == 2
        assert _effective_len("汉字ab") == 6

    def test_prefix_cut_respects_effective_chars(self):
        """切点按有效字符而非裸字符：256 汉字 = 512 有效 = 前缀区满"""
        from ai_prompt_toolkit.linter.rules_p265 import _prefix_cut

        text = "汉" * 256 + "TAIL_MARKER"
        cut = _prefix_cut(text, fm_len=0)
        assert text[cut:] == "TAIL_MARKER"

    def test_prefix_zone_boundary(self):
        """动态 token 恰在 512 有效字符之外 → 不在前缀区，不报"""
        # 256 汉字填满前缀区，token 在之后
        text = "稳" * 256 + "尾部动态 {timestamp}"
        text += "填充文字把长度推到门槛之上。" * 60
        assert check_p265(text) is None


class TestP265PipelineIntegration:
    def test_via_run_all_checks(self):
        text = "当前时间：{timestamp}。你是客服助手。" + "知识条目内容；" * 150
        findings = run_all_checks(text)
        assert "P265" in _ids(findings)

    def test_via_lint_template_no_waiver_leak(self):
        """探针文本经 lint_template 全管线（与漏检基线同路径）"""
        r = lint_template(
            "r230_p265_pipeline", "当前时间：{timestamp}。" + "知识库稳定条目；" * 150, apply_waivers=False
        )
        assert "P265" in _ids(r.findings)

    def test_determinism_byte_identical(self):
        """楔子不变量：同输入两次裁决逐字节一致"""
        text = "当前时间：{timestamp}。" + "稳定指令内容。" * 80
        a = _ids(run_all_checks(text))
        b = _ids(run_all_checks(text))
        assert a == b

    def test_prefix_len_constant_documented(self):
        """前缀区口径常量与 R230 设计文档一致（512 有效字符）"""
        assert _PREFIX_EFF_LEN == 512
