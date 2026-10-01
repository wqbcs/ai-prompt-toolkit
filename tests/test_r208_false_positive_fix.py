"""R208: 误报第二批处置回归测试

处置6条高误报规则(P003/P167/P117/P068/P067/P111):
1. 每条规则在32个干净样本上0命中(负样本断言)
2. 强语义词正样本保留命中(检测能力未削弱)
3. DECL补强回归: do not invent/仅依据上下文 等真实防护声明被识别

全局误报率: 3.17% -> 2.22% (高误报规则27->21)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
_RULES = ["P003", "P167", "P117", "P068", "P067", "P111"]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR208NegativeSamples:
    """6条规则 x 32干净样本 = 0命中"""

    def test_all_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 58, f"干净样本数应为58, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"


class TestR208PositiveSamples:
    """正样本: 强语义词场景保留命中"""

    def test_p003_constraint_heading_pass(self):
        # 裸"约束"章节标题识别(R208修复点)
        r = lint_template("r208_p003_pos", "# 角色\n你是助手。\n# 任务\n处理数据。\n# 约束\n只读操作。")
        assert not any(f.rule_id == "P003" for f in r.findings)

    def test_p003_no_constraint_still_reports(self):
        # 无任何约束声明仍报(检测能力未削弱)
        r = lint_template("r208_p003_neg", "# 角色\n你是一个数据分析助手。\n# 任务\n处理给定的数据并给出结论。")
        assert any(f.rule_id == "P003" for f in r.findings)

    def test_p003_english_constraint_heading(self):
        r = lint_template("r208_p003_en", "# Role\nYou are an assistant.\n# Constraints\nRead-only.")
        assert not any(f.rule_id == "P003" for f in r.findings)

    def test_p167_hallucination_risk_still_reports(self):
        # 引用/事实性风险面 + 无防护声明 仍报
        r = lint_template("r208_p167_pos", "请引用权威来源回答这个问题，事实要准确")
        assert any(f.rule_id == "P167" for f in r.findings)

    def test_p167_hallucination_decl_pass(self):
        r = lint_template("r208_p167_neg", "回答引用来源, 不确定的地方明确标注uncertain")
        assert not any(f.rule_id == "P167" for f in r.findings)

    def test_p167_do_not_invent_decl(self):
        # R208 DECL补强: 英文"Do not invent"是事实性防护声明
        r = lint_template("r208_p167_inv", "Reference the diff when reviewing. Do not invent changes that are not in the diff.")
        assert not any(f.rule_id == "P167" for f in r.findings)

    def test_p117_knowledge_intensive_still_reports(self):
        r = lint_template("r208_p117_pos", "基于最新的科学研究和医学报告回答")
        assert any(f.rule_id == "P117" for f in r.findings)

    def test_p117_factual_decl_pass(self):
        r = lint_template("r208_p117_neg", "基于科学研究回答, 不确定时声明不确定性")
        assert not any(f.rule_id == "P117" for f in r.findings)

    def test_p067_fact_still_reports(self):
        r = lint_template("r208_p067_pos", "请根据最新的统计数据和事实回答问题。")
        assert any(f.rule_id == "P067" for f in r.findings)

    def test_p067_cutoff_pass(self):
        r = lint_template("r208_p067_neg", "请根据截至2026年的知识回答。知识截止: 2026-01")
        assert not any(f.rule_id == "P067" for f in r.findings)

    def test_p068_fact_source_still_reports(self):
        r = lint_template("r208_p068_pos", "请根据事实和数据回答，提供引用来源。")
        assert any(f.rule_id == "P068" for f in r.findings)

    def test_p068_grounding_decl_pass(self):
        # R208 DECL补强: RAG grounding声明("仅依据上下文")是防编造声明
        r = lint_template(
            "r208_p068_neg",
            "仅依据下方上下文回答问题，引用来源编号。上下文未覆盖时明确说资料中没有相关信息。",
        )
        assert not any(f.rule_id == "P068" for f in r.findings)

    def test_p068_do_not_invent_decl(self):
        r = lint_template("r208_p068_inv", "根据事实回答。Do not invent information that is not provided.")
        assert not any(f.rule_id == "P068" for f in r.findings)

    def test_p111_strong_reasoning_still_reports(self):
        # 强推理(原因归因)仍要求CoT
        r = lint_template("r208_p111_pos", "请分析问题的原因并做出判断")
        assert any(f.rule_id == "P111" for f in r.findings)

    def test_p111_cot_decl_pass(self):
        r = lint_template("r208_p111_neg", "请逐步推理，展示思维链(Chain-of-Thought)过程")
        assert not any(f.rule_id == "P111" for f in r.findings)

    def test_p111_numbered_steps_decl(self):
        # R208: "编号步骤"是结构化推理声明
        r = lint_template("r208_p111_num", "定位错误根因, 输出根因说明 + 建议排查步骤（编号）。")
        assert not any(f.rule_id == "P111" for f in r.findings)

    def test_p111_data_analysis_not_required(self):
        # R208收窄: 数据分析(无因果归因)不要求CoT
        r = lint_template("r208_p111_data", "分析这组销售数据的趋势, 输出图表")
        assert not any(f.rule_id == "P111" for f in r.findings)

    def test_refactor_word_not_fact(self):
        # R208: "refactor"内嵌"fact"子串不再误配事实性
        r = lint_template("r208_refactor", "重构这段代码, refactor the function")
        assert not any(f.rule_id in ("P067", "P068", "P117") for f in r.findings)
