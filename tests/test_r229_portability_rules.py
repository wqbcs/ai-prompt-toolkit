"""R229-P1-16: 跨模型可移植性规则族 P262-P264 回归测试。

对标 aiproof AIP016-018（08 需求信号：prompt 移植到异模型时静默劣化）。
三条规则均为静态可判定的可移植性缺陷，精度设计=强信号共现（非全 prompt
任意两处各一），反例断言锁死低误报。
"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.rules_p262_p264 import check_p262, check_p263, check_p264


def _ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


class TestRuleRegistration:
    def test_three_rules_registered(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        assert rules["P262"].category == "portability"
        assert rules["P263"].category == "portability"
        assert rules["P264"].category == "portability"
        assert rules["P262"].family == "cross_model_portability"

    def test_severities(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        assert rules["P262"].severity.value == "medium"
        assert rules["P263"].severity.value == "medium"
        assert rules["P264"].severity.value == "low"

    def test_bilingual_fields(self):
        rules = {r.rule_id: r for r in get_all_rules()}
        for rid in ("P262", "P263", "P264"):
            assert rules[rid].description_en
            assert rules[rid].remediation_en


class TestP262ModelBrandBinding:
    def test_chinese_identity_binding(self):
        f = check_p262("你是ChatGPT，一个专业的代码审查助手，请帮我审查代码。")
        assert f is not None
        assert f.details["brand"] == "ChatGPT"

    def test_english_identity_binding(self):
        f = check_p262("You are a GPT-4 assistant specialized in SQL optimization.")
        assert f is not None

    def test_as_a_identity(self):
        f = check_p262("作为Claude，你需要遵循以下规则处理输入内容并输出结果。")
        assert f is not None

    def test_brand_without_identity_no_hit(self):
        # 品牌名存在但无身份标记近邻 → 不报（文档引用/背景说明）
        f = check_p262("这是一段参考文档，介绍了 GPT-4 的技术细节，与当前任务无关。")
        assert f is None

    def test_identity_without_brand_no_hit(self):
        f = check_p262("你是一个专业的数据分析师，请分析这份报表并给出结论。")
        assert f is None

    def test_brand_far_from_identity_no_hit(self):
        # 身份标记与品牌相距 >40 字符 → 不报（非绑定语境）
        filler = "以下是需要处理的背景资料说明文字，包含若干历史细节与行业惯例的补充。"
        f = check_p262("你是一个助手。" + filler + "参考 GPT-4 的文档编号 12345 处理。")
        assert f is None

    # ── R229 收口: frontmatter 边界（20 个模板 C5 误报复现与修复） ──
    def test_frontmatter_brand_not_anchored(self):
        # 模板 frontmatter model_compatibility 品牌名跨 `---` 边界落入正文
        # 身份句 ±40 窗口 → 元数据是声明非正文, 不锚定（CI 21 处中 20 处形态）
        text = (
            "---\ntemplate_id: code-reviewer\nmodel_compatibility:\n  - qwen\n"
            '  - deepseek\n  - pangu\nversion: "3.0"\n---\n\n# 角色\n\n'
            "你是资深代码审查专家，擅长发现代码中的安全隐患。"
        )
        assert check_p262(text) is None

    def test_frontmatter_only_brand_no_hit(self):
        # 仅 frontmatter 有品牌、正文无身份绑定 → 不报
        text = "---\nmodel_compatibility:\n  - deepseek\n---\n\n你是通用助手。"
        assert check_p262(text) is None

    def test_body_binding_still_hits_with_frontmatter(self):
        # frontmatter 存在时正文真绑定仍报, 且 location 行号基于原文（不漂移）
        text = "---\nmodel_compatibility:\n  - deepseek\n---\n\n# 角色\n\n你是DeepSeek-R1推理专家，擅长深度推理。"
        f = check_p262(text)
        assert f is not None
        # location 契约: "line:col" 字符串, 消费端 parse_location 解析（R218 单一入口）
        from ai_prompt_toolkit.types import parse_location

        line, _col = parse_location(f.location)
        assert line == 8  # 原文第 8 行（location 基于原文偏移, 不随 frontmatter 剥离漂移）

    def test_no_frontmatter_behavior_unchanged(self):
        # 无 frontmatter 输入行为不变（fm_len=0 全量扫描）
        f = check_p262("你是Claude，你需要遵循以下规则处理输入。")
        assert f is not None


class TestP263DeterminismContradiction:
    def test_both_present_hits(self):
        f = check_p263("输出必须确定性一致且可复现，同时请发挥想象力和创意，让结果随机多样。")
        assert f is not None
        assert f.details["determinism_match"]
        assert f.details["randomness_match"]

    def test_determinism_only_no_hit(self):
        f = check_p263("输出必须严格一致，确保可复现，同一输入同一输出，便于回归验证。")
        assert f is None

    def test_randomness_only_no_hit(self):
        f = check_p263("请发挥想象力，写一首富有创意和随机趣味的短诗，风格要多样。")
        assert f is None

    def test_english_keywords_hit(self):
        # deterministic/reproducible ∈ 确定性词集; creative/random ∈ 随机性词集 → 矛盾命中
        f = check_p263("The output must be deterministic and reproducible, yet creative and random.")
        assert f is not None


class TestP264VendorFormat:
    def test_human_assistant_pair_hits(self):
        f = check_p264("Human: 你好，帮我翻译这句话到英文\nAssistant: 当然可以，请提供文本\nHuman: 谢谢")
        assert f is not None
        assert f.details["format"] == "human_assistant"

    def test_hash_instruction_response_hits(self):
        f = check_p264("### Instruction:\n把下面的文本改写成更正式的语气\n### Response:\n好的，改写如下")
        assert f is not None
        assert f.details["format"] == "hash_instruction_response"

    def test_llama_inst_hits(self):
        f = check_p264("[INST] 请将这段口语化文本整理成书面语 [/INST]")
        assert f is not None
        assert f.details["format"] == "llama_inst"

    def test_system_special_token_hits(self):
        f = check_p264("<|system|>你是一个助手</system>")
        assert f is None  # 缺闭合标签 <|/system|>

    def test_system_special_token_hits_closed(self):
        f = check_p264("<|system|>你是一个助手<|/system|>")
        assert f is not None
        assert f.details["format"] == "system_special_tok"

    def test_im_start_end_hits(self):
        f = check_p264("<|im_start|>system\n你是一个助手<|im_end|>\n<|im_start|>user\n你好<|im_end|>")
        assert f is not None
        assert f.details["format"] == "im_start_end"

    def test_single_human_no_hit(self):
        # 单个 Human: 不成对 → 不报（普通正文）
        f = check_p264("注意：日志里出现过 Human: 这个前缀，需要排查它的来源和上下文。")
        assert f is None


class TestTargetModelEscalation:
    """P1-16 验收: --target-model × P262 跨族升级（纯函数 + pipeline 双口径）。"""

    def _p262(self, findings):
        return [f for f in findings if f.rule_id == "P262"]

    def test_resolve_family_data_driven(self):
        from ai_prompt_toolkit.linter.target_model import resolve_family

        assert resolve_family("claude-3-5-sonnet") == "anthropic"
        assert resolve_family("gpt-4o-mini") == "openai"
        assert resolve_family("Qwen-Max") == "aliyun"
        assert resolve_family("ERNIE-4.5") == "baidu"
        assert resolve_family("totally-unknown-model") is None
        assert resolve_family("") is None

    def test_cross_family_escalates_high(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        r = PromptLinter().lint(
            "t", "你是ChatGPT，一个专业的代码审查助手，请审查并指出问题。", target_model="claude-3-5-sonnet"
        )
        p = self._p262(r.findings)
        assert len(p) == 1
        assert p[0].severity.value == "high"
        assert p[0].details["escalated"] is True
        assert "claude" in p[0].description

    def test_same_family_stays_medium(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        r = PromptLinter().lint("t", "你是ChatGPT，一个专业的代码审查助手，请审查并指出问题。", target_model="gpt-4o")
        p = self._p262(r.findings)
        assert p and p[0].severity.value == "medium"
        assert "escalated" not in p[0].details

    def test_unknown_target_conservative(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        r = PromptLinter().lint(
            "t", "你是ChatGPT，一个专业的代码审查助手，请审查并指出问题。", target_model="mystery-model-9000"
        )
        p = self._p262(r.findings)
        assert p and p[0].severity.value == "medium"

    def test_no_target_model_baseline_unchanged(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        r = PromptLinter().lint("t", "你是ChatGPT，一个专业的代码审查助手，请审查并指出问题。")
        p = self._p262(r.findings)
        assert p and p[0].severity.value == "medium"

    def test_non_p262_findings_unaffected(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        r = PromptLinter().lint("t", "你。", target_model="claude")
        # 无 P262 命中时行为与不传 target_model 完全一致
        r0 = PromptLinter().lint("t", "你。")
        assert [(f.rule_id, f.severity.value) for f in r.findings] == [
            (f.rule_id, f.severity.value) for f in r0.findings
        ]

    def test_escalate_is_pure_function(self):
        from ai_prompt_toolkit.linter.target_model import escalate_mismatched_brand
        from ai_prompt_toolkit.types import Finding, Severity

        f = Finding(
            rule_id="P262", severity=Severity.MEDIUM, description="d", location="L1:C1", details={"brand": "ChatGPT"}
        )
        orig = [f]
        out = escalate_mismatched_brand(orig, "claude")
        assert orig is not out
        assert orig[0] is f  # 输入列表/元素未被修改
        assert out[0].severity is Severity.HIGH


class TestPipelineIntegration:
    """规则经完整 pipeline（run_all_checks → CJK 归一化包装）可达。"""

    def test_run_all_checks_reaches_p262(self):
        findings = run_all_checks("你是ChatGPT，一个专业的代码审查助手，请审查并指出问题。")
        assert "P262" in _ids(findings)

    def test_run_all_checks_reaches_p263(self):
        findings = run_all_checks("结果必须确定性一致且可复现，同时请随机发挥创意，输出多样。")
        assert "P263" in _ids(findings)

    def test_run_all_checks_reaches_p264(self):
        findings = run_all_checks("Human: 开始对话\nAssistant: 我在，请说\nHuman: 结束")
        assert "P264" in _ids(findings)
