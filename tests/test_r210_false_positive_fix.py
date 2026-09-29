"""R210: 新样本(英文/长文/Agent/模板/代码块/多语言)暴露误报处置回归测试

扩样32→56后暴露5条新高误报规则(P083/P118/P165/P168/P101):
1. 每条规则在56个干净样本上0命中(负样本断言)
2. 强语义词正样本保留命中(检测能力未削弱)

根因:
- P083/P118: 纯长度门(>200字)对一切长prompt恒触发
- P165/P168: CTX泛词(时间/错误/日志、判断/推荐/分类)几乎恒触发
- P101: 字符级Jaccard对英文失真(字母表仅26, 任何两句英文>0.5)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
_RULES = ["P083", "P118", "P165", "P168", "P101"]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR210NegativeSamples:
    """5条规则 x 56干净样本 = 0命中"""

    def test_all_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 56, f"干净样本数应为56, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"


class TestR210PositiveSamples:
    """正样本: 强语义词场景保留命中"""

    def test_p083_production_prompt_still_reports(self):
        # 生产向长prompt(无doctor声明)仍建议诊断
        text = "你是客服Agent, 部署到production生产环境, 面向线上用户。" + "x" * 250
        r = lint_template("r210_p083_pos", text)
        assert any(f.rule_id == "P083" for f in r.findings)

    def test_p083_production_with_doctor_pass(self):
        text = "部署到production, 上线前运行prompt-doctor健康检查。" + "x" * 250
        r = lint_template("r210_p083_neg", text)
        assert not any(f.rule_id == "P083" for f in r.findings)

    def test_p083_non_production_not_required(self):
        # R210: 非生产向长prompt不要求doctor诊断
        r = lint_template("r210_p083_neg2", "把下面的技术笔记整理成结构化周报。" + "x" * 250)
        assert not any(f.rule_id == "P083" for f in r.findings)

    def test_p118_knowledge_prompt_still_reports(self):
        # 知识密集型长prompt(无截止声明)仍要求知识时效性
        text = "你是百科助手, 基于历史与科学知识回答用户问题。" + "x" * 250
        r = lint_template("r210_p118_pos", text)
        assert any(f.rule_id == "P118" for f in r.findings)

    def test_p118_knowledge_with_cutoff_pass(self):
        text = "基于历史与科学知识回答, 知识截止: 2026-01" + "x" * 250
        r = lint_template("r210_p118_neg", text)
        assert not any(f.rule_id == "P118" for f in r.findings)

    def test_p118_code_prompt_not_required(self):
        # R210: 代码/配置类长prompt无知识时效面
        r = lint_template("r210_p118_neg2", "根据给定的YAML配置, 解释每个字段的用途。" + "x" * 250)
        assert not any(f.rule_id == "P118" for f in r.findings)

    def test_p165_side_channel_still_reports(self):
        # 真实侧信道风险面(泄露+推断+时间)仍要求防护
        r = lint_template("r210_p165_pos", "接口返回登录结果, 注意防止通过响应时间推断账户是否存在, 避免泄露")
        assert any(f.rule_id == "P165" for f in r.findings)

    def test_p165_side_channel_with_decl_pass(self):
        r = lint_template(
            "r210_p165_neg", "接口返回登录结果, 防止通过响应时间推断账户, 统一错误提示, 恒定延迟±50ms"
        )
        assert not any(f.rule_id == "P165" for f in r.findings)

    def test_p165_error_handling_not_required(self):
        # R210: 普通错误处理/日志场景不构成侧信道风险面
        r = lint_template("r210_p165_neg2", "处理支付错误, 记录日志并返回统一错误码。")
        assert not any(f.rule_id == "P165" for f in r.findings)

    def test_p168_protected_attribute_still_reports(self):
        # 受保护属性区分(候选人评价)仍要求偏见防护
        r = lint_template("r210_p168_pos", "请对候选人进行评价、比较和分类判断。")
        assert any(f.rule_id == "P168" for f in r.findings)

    def test_p168_hiring_with_fairness_pass(self):
        r = lint_template("r210_p168_neg", "招聘筛选: 忽略性别/年龄/民族, 只依据技能匹配度评估")
        assert not any(f.rule_id == "P168" for f in r.findings)

    def test_p168_ticket_classification_not_required(self):
        # R210: 工单/日志/代码分类不构成群体偏见风险
        r = lint_template("r210_p168_neg2", "读取工单内容, 按类别分类并输出JSON。")
        assert not any(f.rule_id == "P168" for f in r.findings)

    def test_p101_redundant_chinese_still_reports(self):
        # 中文冗余表述仍检出(分词后CJK单字等价原字符级) — 3句确保句子数≥3
        text = (
            "你必须严格遵循上面的全部约束条件。"
            "你必须严格遵循上面的全部约束条件。"
            "你必须严格遵循上面的全部约束条件。"
        )
        r = lint_template("r210_p101_pos", text)
        assert any(f.rule_id == "P101" for f in r.findings)

    def test_p101_english_short_sentences_not_flagged(self):
        # R210: 英文短句不再因字符集天然重叠误报
        text = (
            "You are a code reviewer. "
            "Given a diff, identify potential bugs. "
            "Output a markdown report with sections."
        )
        r = lint_template("r210_p101_neg", text)
        assert not any(f.rule_id == "P101" for f in r.findings)

    def test_p101_english_redundant_still_reports(self):
        # 英文真冗余(重复同词群)仍检出
        text = (
            "Validate the input and reject malformed payloads. "
            "Validate the input and reject malformed payloads. "
            "Validate the input and reject malformed payloads."
        )
        r = lint_template("r210_p101_neg2", text)
        assert any(f.rule_id == "P101" for f in r.findings)

    def test_p002_english_output_colon_pass(self):
        # R210: "Output: xxx" 冒号式英文输出声明被识别(用不含强词的中性英文样本,
        # 避免JSON/Markdown等强词命中造成假阴性)
        text = "Review the diff. Output: a short memo with the key risks."
        r = lint_template("r210_p002_neg", text)
        assert not any(f.rule_id == "P002" for f in r.findings)
