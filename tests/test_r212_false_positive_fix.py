"""R212-6: 误报第六批处置回归测试 — Top7高误报清零 (1.35%→0.96%)

处置9条规则(56样本口径, 高误报>10%全部清零):
- P107 条件分支覆盖: 触发收窄到真条件词(如果/假如/若/假设非否定/if|else|otherwise独立词),
  异常处理声明扩面(不确定/联系人工/I don't know/不假设等边界处理措辞)
- P119 能力边界声明: 纯长度门(len≥300)→加能力承诺声明门(全能/任何…/保证/100%)
- P039/P040 多模态安全/降级: 移除裸"文件/file/attach", 英文媒体词加\\b词边界
- P038 多模态校验: 同P039/P040(共用输入模式)
- P110 工具链恢复: 链式信号分强弱(强=首先…然后/pipeline, 弱=步骤/流程须工具语境门)
- P036/P037 幻觉检查/引用标注: 加RAG语境门(同P035/R180, 裸"查询"是SQL词汇)
- P109 RAG置信度: 移除裸"文档"触发

负样本断言: 9条规则 × 56干净样本 = 0命中(高误报清零)
正样本断言: 真场景保留命中(检测能力未被门削弱)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
# 本批收窄后应完全清零的规则
_ZERO_RULES = ["P036", "P037", "P038", "P039", "P040", "P107", "P109", "P110", "P119"]

# R211定位的误报根因样本(处置后必须不触发)
_NEG_SAMPLES: dict[str, str] = {
    # 裸"查询"是SQL/业务词汇, 不构成RAG面
    "sql_query": "查询数据库中2026年的订单记录",
    # "写文档"不是检索面
    "write_doc": "编写技术白皮书文档，介绍产品架构",
    # 标识符子串不是多模态输入(imageUrl≠image独立词)
    "identifier_substr": "React组件props包含imageUrl字段，点击缩略图打开预览窗口",
    # "diff文件"是代码审查语境, 非多模态输入
    "diff_file": "代码审查：阅读diff文件并给出改进建议",
    # 通用流程词无工具语境, 非工具链面
    "plain_pipeline": "日志处理流程：解析、过滤、聚合",
    # "触发条件"是SQL领域词, 非条件分支
    "sql_condition": "当触发条件满足时更新状态",
}


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR212NegativeSamples:
    """9条清零规则 × 56干净样本 = 0命中"""

    def test_zero_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 60, f"干净样本数应为60, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _ZERO_RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"

    def test_r211_root_cause_samples_no_longer_trigger(self):
        """R211逐样本定位的根因样本, 处置后对应规则不再触发"""
        rule_map = {
            "sql_query": ["P036", "P037"],
            "write_doc": ["P037", "P109"],
            "identifier_substr": ["P038", "P039", "P040"],
            "diff_file": ["P038", "P039", "P040"],
            "plain_pipeline": ["P110"],
            "sql_condition": ["P107"],
        }
        for name, text in _NEG_SAMPLES.items():
            r = lint_template(f"r212_neg_{name}", text)
            got = {f.rule_id for f in r.findings}
            for rule in rule_map[name]:
                assert rule not in got, f"{rule} 仍在根因样本 {name} 上误报"


class TestR212PositiveSamples:
    """正样本: 真场景保留命中 — 门收窄未削弱检测能力"""

    # --- P107 条件分支覆盖 ---
    def test_p107_if_without_exception_handling(self):
        r = lint_template("r212_p107_pos1", "如果用户输入为空，提示重新输入")
        assert any(f.rule_id == "P107" for f in r.findings)

    def test_p107_boundary_declaration_passes(self):
        # 客服边界处理: 不确定→引导联系人工, 是真实异常分支
        r = lint_template("r212_p107_ok1", "如果不确定→引导联系人工")
        assert not any(f.rule_id == "P107" for f in r.findings)

    def test_p107_rag_i_dont_know_passes(self):
        r = lint_template("r212_p107_ok2", "if the answer is not found, respond I don't know")
        assert not any(f.rule_id == "P107" for f in r.findings)

    # --- P119 能力边界声明 ---
    def test_p119_capability_claim_still_triggers(self):
        text = (
            "你是全能助手，能回答任何领域的任何问题。你负责撰写产品周报，汇总本周进展、数据指标与下周计划。"
            "输出包含摘要、亮点、风险与行动项四个部分，语言简洁，使用要点列表，总长度不超过五百字。"
            "摘要部分概括本周最重要的三件事；亮点部分列出取得进展的项目；风险部分说明可能影响进度的事项；"
            "行动项部分给出负责人和时间。周报完成后，检查格式是否完整、四个部分是否齐全、数字是否准确、"
            "语言是否通顺，再提交给项目负责人审阅归档。如果某项工作本周没有进展，请如实说明原因，不要夸大成绩。"
            "所有数据必须来自本周的统计报表，引用具体数字，不要使用模糊表述。对于跨部门协作的项目，"
            "需要分别说明产品、研发、运营三方的投入与产出，并指出下一步的衔接事项。最终输出使用Markdown格式。"
        )
        assert len(text) >= 300, "P119正样本须≥300字以越过长度门"
        r = lint_template("r212_p119_pos", text)
        assert any(f.rule_id == "P119" for f in r.findings)

    def test_p119_long_prompt_without_claim_not_required(self):
        # 无能力承诺声明的长prompt不构成过高期望风险(纯长度门误报根因)
        text = (
            "编写SQL查询：从orders表中统计2026年每月各品类的销售额，按月份升序排列。"
            "字段包括月份、品类名称、销售额合计、订单数。注意处理空值，使用COALESCE将空值转为0。"
            "如果某个品类当月没有订单，仍然保留该品类行，销售额显示为0。结果用于月度经营分析报表，"
            "导出为CSV格式。查询执行前请确认表结构包含category、amount、created_at三个字段。"
            "输出前先对数据进行清洗，去除测试账号的记录。最终结果按销售额降序取前二十名，并附上占比。"
            "本报表每周一上午自动生成，接收人为运营团队。如数据出现异常波动，在备注列标注原因。"
            "报表同时生成上月对比列，便于观察趋势。所有查询语句需通过慢查询审查，避免全表扫描；"
            "大表关联时必须使用索引字段。统计口径以财务系统为准，与业务系统存在差异时在备注中说明。"
            "最终脚本存入数据仓库的报表目录，并登记到报表清单。"
        )
        assert len(text) >= 300, "P119负样本须≥300字以证明长度门不再单独触发"
        r = lint_template("r212_p119_neg", text)
        assert not any(f.rule_id == "P119" for f in r.findings)

    # --- P110 工具链恢复 ---
    def test_p110_strong_chain_no_recovery(self):
        r = lint_template("r212_p110_pos1", "首先调用搜索API获取资料，然后整理成摘要")
        assert any(f.rule_id == "P110" for f in r.findings)

    def test_p110_weak_chain_with_tool_ctx(self):
        # 弱信号(步骤)+工具语境(调用工具)组合仍构成工具链面
        r = lint_template("r212_p110_pos2", "按以下步骤调用工具：第一步获取数据，第二步清洗，第三步输出")
        assert any(f.rule_id == "P110" for f in r.findings)

    def test_p110_recovery_declaration_passes(self):
        r = lint_template("r212_p110_ok", "首先调用搜索API获取资料，然后汇总；调用超时则重试3次，仍失败则跳过")
        assert not any(f.rule_id == "P110" for f in r.findings)

    # --- P036 幻觉检查 ---
    def test_p036_rag_without_hallucination_check(self):
        r = lint_template("r212_p036_pos", "基于知识库检索的内容回答用户问题")
        assert any(f.rule_id == "P036" for f in r.findings)

    def test_p036_missing_info_declaration_passes(self):
        r = lint_template("r212_p036_ok", "基于知识库检索回答；资料中没有相关信息时，明确告知用户")
        assert not any(f.rule_id == "P036" for f in r.findings)

    # --- P037 引用标注 ---
    def test_p037_rag_without_citation(self):
        r = lint_template("r212_p037_pos", "基于知识库检索结果撰写回答")
        assert any(f.rule_id == "P037" for f in r.findings)

    def test_p037_citation_declaration_passes(self):
        r = lint_template("r212_p037_ok", "基于知识库检索回答，并标注来源段落编号")
        assert not any(f.rule_id == "P037" for f in r.findings)

    # --- P038 多模态校验 ---
    def test_p038_image_without_validation(self):
        r = lint_template("r212_p038_pos", "用户提供图片，请描述内容")
        assert any(f.rule_id == "P038" for f in r.findings)

    def test_p038_validation_declaration_passes(self):
        r = lint_template("r212_p038_ok", "上传图片需校验格式为PNG或JPG，大小不超过5MB")
        assert not any(f.rule_id == "P038" for f in r.findings)

    # --- P039 多模态安全 ---
    def test_p039_upload_without_safety(self):
        r = lint_template("r212_p039_pos", "用户上传视频，请生成摘要")
        assert any(f.rule_id == "P039" for f in r.findings)

    def test_p039_safety_declaration_passes(self):
        r = lint_template("r212_p039_ok", "用户上传视频后先做内容审核，过滤违规内容再处理")
        assert not any(f.rule_id == "P039" for f in r.findings)

    # --- P040 多模态降级 ---
    def test_p040_upload_without_fallback(self):
        r = lint_template("r212_p040_pos", "用户上传音频，请转写为文字")
        assert any(f.rule_id == "P040" for f in r.findings)

    def test_p040_fallback_declaration_passes(self):
        r = lint_template("r212_p040_ok", "上传音频转写失败时降级为纯文本提示")
        assert not any(f.rule_id == "P040" for f in r.findings)

    # --- P109 RAG置信度 ---
    def test_p109_rag_without_confidence(self):
        r = lint_template("r212_p109_pos", "基于知识库检索结果回答")
        assert any(f.rule_id == "P109" for f in r.findings)

    def test_p109_confidence_declaration_passes(self):
        r = lint_template("r212_p109_ok", "基于知识库检索回答，给出置信度并引用来源")
        assert not any(f.rule_id == "P109" for f in r.findings)
