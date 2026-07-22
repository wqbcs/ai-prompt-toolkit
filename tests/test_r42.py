"""R42测试 — 盘古P096-P100 Lint规则 + Fixer + MCP"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules_p096_p100 import (
    check_p096, check_p097, check_p098, check_p099, check_p100,
    run_checks_p096_p100,
)
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP, get_rule
from ai_prompt_toolkit.linter.fixer import Fixer, AUTO_FIXABLE_RULES
from ai_prompt_toolkit.types import Finding, Severity


class TestP096PanguFormat:
    def test_p096_chatml_format(self):
        text = "使用盘古大模型\n<|im_start|>system\n你是助手<|im_end|>"
        result = check_p096(text)
        assert result is not None
        assert result.rule_id == "P096"
        assert "ChatML" in result.details.get("non_pangu_formats", [])

    def test_p096_llama_format(self):
        text = "调用华为云MaaS推理\n[INST] 你好 [/INST]"
        result = check_p096(text)
        assert result is not None
        assert "Llama" in result.description

    def test_p096_alpaca_format(self):
        text = "盘古模型生成\n### Instruction:\n写一首诗\n### Response:"
        result = check_p096(text)
        assert result is not None
        assert "Alpaca" in result.description

    def test_p096_claude_format(self):
        text = "华为云MaaS部署\nHuman: 你好\nAssistant: 你好!"
        result = check_p096(text)
        assert result is not None
        formats = result.details.get("non_pangu_formats", [])
        assert any("Claude" in f for f in formats)

    def test_p096_no_pangu_context(self):
        text = "<|im_start|>system\n你是助手<|im_end|>"
        result = check_p096(text)
        assert result is None

    def test_p096_pangu_format_declared(self):
        text = "使用盘古大模型\n<|im_start|>system\n使用system role和assistant role对话"
        result = check_p096(text)
        assert result is None

    def test_p096_clean_pangu_prompt(self):
        text = "使用盘古大模型进行文本生成"
        result = check_p096(text)
        assert result is None

    def test_p096_multiple_formats(self):
        text = "盘古模型\n<|im_start|>system\n[INST] test [/INST]"
        result = check_p096(text)
        assert result is not None
        assert "ChatML" in result.description
        assert "Llama" in result.description


class TestP097PanguTokenLimit:
    def test_p097_long_prompt_no_decl(self):
        text = "使用盘古大模型\n" + "这是一段很长的提示词文字，用于测试token限制检测功能。" * 400
        result = check_p097(text)
        assert result is not None
        assert result.rule_id == "P097"

    def test_p097_short_prompt(self):
        text = "使用盘古大模型进行推理"
        result = check_p097(text)
        assert result is None

    def test_p097_token_declared(self):
        text = "使用盘古大模型，token限制8K上下文"
        result = check_p097(text)
        assert result is None

    def test_p097_context_window_declared(self):
        text = "盘古模型，上下文窗口32768"
        result = check_p097(text)
        assert result is None

    def test_p097_no_pangu_context(self):
        text = "这是一个很长的提示词" * 200
        result = check_p097(text)
        assert result is None

    def test_p097_8k_declared(self):
        text = "盘古模型推理，8K tokens限制"
        result = check_p097(text)
        assert result is None


class TestP098PanguToolCall:
    def test_p098_tool_call_no_decl(self):
        text = "使用盘古大模型，调用工具获取数据"
        result = check_p098(text)
        assert result is not None
        assert result.rule_id == "P098"

    def test_p098_api_tool_no_decl(self):
        text = "华为云MaaS模型，需要调用API插件plugin完成任务"
        result = check_p098(text)
        assert result is not None

    def test_p098_tool_declared(self):
        text = "使用盘古大模型，Function Calling格式定义tools参数"
        result = check_p098(text)
        assert result is None

    def test_p098_no_tool_call(self):
        text = "使用盘古大模型进行文本生成"
        result = check_p098(text)
        assert result is None

    def test_p098_no_pangu_context(self):
        text = "调用工具获取数据，使用function calling"
        result = check_p098(text)
        assert result is None

    def test_p098_maas_tool_use_decl(self):
        text = "盘古模型，Tool Use格式，MaaS function定义"
        result = check_p098(text)
        assert result is None


class TestP099PanguMultimodal:
    def test_p099_image_no_decl(self):
        text = "使用盘古大模型，分析图片中的内容，识别物体"
        result = check_p099(text)
        assert result is not None
        assert result.rule_id == "P099"

    def test_p099_multimodal_no_decl(self):
        text = "华为云MaaS多模态模型，处理图文输入"
        result = check_p099(text)
        assert result is not None

    def test_p099_multimodal_declared(self):
        text = "盘古多模态格式，图片使用base64编码输入"
        result = check_p099(text)
        assert result is None

    def test_p099_vision_declared(self):
        text = "盘古vision模型，image url格式输入"
        result = check_p099(text)
        assert result is None

    def test_p099_no_image_ref(self):
        text = "使用盘古大模型进行文本分类"
        result = check_p099(text)
        assert result is None

    def test_p099_no_pangu_context(self):
        text = "分析图片中的内容，识别物体"
        result = check_p099(text)
        assert result is None


class TestP100PanguSafety:
    def test_p100_safety_no_decl(self):
        text = "使用盘古大模型，需要内容安全审核，确保输出合规"
        result = check_p100(text)
        assert result is not None
        assert result.rule_id == "P100"

    def test_p100_guardrail_no_decl(self):
        text = "盘古模型需要安全护栏防止有害内容输出"
        result = check_p100(text)
        assert result is not None

    def test_p100_safety_declared(self):
        text = "盘古模型，启用ModelArts内容审核，安全评分阈值0.8"
        result = check_p100(text)
        assert result is None

    def test_p100_guardrail_declared(self):
        text = "盘古模型，配置安全护栏和敏感词过滤配置"
        result = check_p100(text)
        assert result is None

    def test_p100_no_safety_ref(self):
        text = "使用盘古大模型进行文本生成"
        result = check_p100(text)
        assert result is None

    def test_p100_no_pangu_context(self):
        text = "需要内容安全审核，确保输出合规"
        result = check_p100(text)
        assert result is None

    def test_p100_content_moderation_decl(self):
        text = "盘古模型，配置内容审核和敏感词过滤配置"
        result = check_p100(text)
        assert result is None


class TestRunChecksP096P100:
    def test_run_all_no_findings(self):
        text = "这是一个普通的文本"
        results = run_checks_p096_p100(text)
        assert results == []

    def test_run_all_multiple_findings(self):
        text = (
            "使用盘古大模型，调用工具获取数据\n"
            "分析图片内容\n"
            "需要内容安全审核\n"
            "安全护栏防止有害输出\n"
        ) + "很长的文本内容，用于测试token限制" * 500
        results = run_checks_p096_p100(text)
        rule_ids = [r.rule_id for r in results]
        assert "P097" in rule_ids
        assert "P098" in rule_ids
        assert "P099" in rule_ids
        assert "P100" in rule_ids


class TestP096P100RuleRegistration:
    def test_rules_in_rule_map(self):
        for rid in ["P096", "P097", "P098", "P099", "P100"]:
            rule = _RULE_MAP.get(rid)
            assert rule is not None, f"{rid} not in _RULE_MAP"
            assert rule.rule_id == rid

    def test_rules_have_english_descriptions(self):
        for rid in ["P096", "P097", "P098", "P099", "P100"]:
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"

    def test_get_rule_p096_p100(self):
        for rid in ["P096", "P097", "P098", "P099", "P100"]:
            rule = get_rule(rid)
            assert rule is not None
            assert rule.rule_id == rid

    def test_rule_to_dict_en(self):
        rule = _RULE_MAP["P096"]
        d = rule.to_dict(lang="en")
        assert d["description"] == rule.description_en

    def test_rule_to_dict_zh(self):
        rule = _RULE_MAP["P100"]
        d = rule.to_dict(lang="zh")
        assert d["description"] == rule.description


class TestP096P100Fixer:
    def setup_method(self):
        self.fixer = Fixer()

    def test_auto_fixable_includes_p096_p100(self):
        for rid in ["P096", "P097", "P098", "P099", "P100"]:
            assert rid in AUTO_FIXABLE_RULES

    def test_fix_p096_pangu_format(self):
        text = "使用盘古大模型\n<|im_start|>system\n你是助手"
        finding = Finding(rule_id="P096", severity=Severity.HIGH, description="盘古格式兼容性")
        fixed, results = self.fixer.fix(text, [finding])
        assert "盘古对话格式兼容性" in fixed
        assert "system/user/assistant" in fixed
        assert len(results) == 1

    def test_fix_p097_pangu_token_limit(self):
        text = "使用盘古大模型进行推理"
        finding = Finding(rule_id="P097", severity=Severity.HIGH, description="Token限制风险")
        fixed, results = self.fixer.fix(text, [finding])
        assert "盘古Token限制声明" in fixed
        assert "tokens" in fixed
        assert len(results) == 1

    def test_fix_p097_long_prompt(self):
        text = "使用盘古大模型\n" + "很长的内容" * 3000
        finding = Finding(rule_id="P097", severity=Severity.HIGH, description="Token限制风险")
        fixed, results = self.fixer.fix(text, [finding])
        assert "盘古" in fixed
        assert "Token" in fixed
        assert len(results) == 1

    def test_fix_p098_pangu_tool_call(self):
        text = "盘古模型调用工具获取数据"
        finding = Finding(rule_id="P098", severity=Severity.MEDIUM, description="工具调用规范缺失")
        fixed, results = self.fixer.fix(text, [finding])
        assert "Function Calling规范" in fixed
        assert "tools参数" in fixed
        assert len(results) == 1

    def test_fix_p099_pangu_multimodal(self):
        text = "盘古模型分析图片内容"
        finding = Finding(rule_id="P099", severity=Severity.MEDIUM, description="多模态兼容性风险")
        fixed, results = self.fixer.fix(text, [finding])
        assert "盘古多模态兼容性" in fixed
        assert "base64" in fixed
        assert len(results) == 1

    def test_fix_p100_pangu_safety(self):
        text = "盘古模型需要内容安全审核"
        finding = Finding(rule_id="P100", severity=Severity.HIGH, description="安全护栏缺失")
        fixed, results = self.fixer.fix(text, [finding])
        assert "盘古安全护栏声明" in fixed
        assert "ModelArts内容审核" in fixed
        assert "0.8" in fixed
        assert len(results) == 1

    def test_fix_multiple_p096_p100(self):
        findings = [
            Finding(rule_id="P096", severity=Severity.HIGH, description="格式兼容性"),
            Finding(rule_id="P098", severity=Severity.MEDIUM, description="工具调用规范"),
            Finding(rule_id="P100", severity=Severity.HIGH, description="安全护栏"),
        ]
        text = "使用盘古大模型"
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) == 3
        assert "盘古对话格式" in fixed
        assert "Function Calling" in fixed
        assert "安全护栏" in fixed


class TestF1VersionManagementEnhancement:
    def setup_method(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        from ai_prompt_toolkit.prompt_version import PromptVersionStore
        self.store = PromptVersionStore(db_path=f"{self.tmp}/test_versions.db")

    def teardown_method(self):
        self.store.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_with_auto_lint(self):
        v = self.store.save("test_prompt", "你是一个专业的AI助手", auto_lint=True)
        assert v.version_id
        assert v.prompt_name == "test_prompt"

    def test_save_without_auto_lint(self):
        v = self.store.save("test_prompt", "你是一个专业的AI助手", score=85.0)
        assert v.score == 85.0

    def test_add_tag(self):
        v = self.store.save("test_prompt", "内容")
        assert self.store.add_tag("test_prompt", v.version_id, "production")
        tags = self.store.list_tags("test_prompt")
        assert any(t["tag"] == "production" for t in tags)

    def test_add_tag_invalid_version(self):
        assert not self.store.add_tag("test_prompt", "nonexistent", "production")

    def test_remove_tag(self):
        v = self.store.save("test_prompt", "内容")
        self.store.add_tag("test_prompt", v.version_id, "staging")
        assert self.store.remove_tag("test_prompt", v.version_id, "staging")
        tags = self.store.list_tags("test_prompt")
        assert not any(t["tag"] == "staging" for t in tags)

    def test_get_by_tag(self):
        v1 = self.store.save("test_prompt", "版本1")
        v2 = self.store.save("test_prompt", "版本2")
        self.store.add_tag("test_prompt", v1.version_id, "production")
        self.store.add_tag("test_prompt", v2.version_id, "staging")
        prod = self.store.get_by_tag("test_prompt", "production")
        assert len(prod) == 1
        assert prod[0].content == "版本1"

    def test_create_branch(self):
        v = self.store.save("test_prompt", "初始版本")
        assert self.store.create_branch("test_prompt", "main", v.version_id)
        branches = self.store.list_branches("test_prompt")
        assert any(b["branch_name"] == "main" for b in branches)

    def test_update_branch_head(self):
        v1 = self.store.save("test_prompt", "版本1")
        v2 = self.store.save("test_prompt", "版本2")
        self.store.create_branch("test_prompt", "main", v1.version_id)
        assert self.store.update_branch_head("test_prompt", "main", v2.version_id)
        head = self.store.get_branch_head("test_prompt", "main")
        assert head is not None
        assert head.version_id == v2.version_id

    def test_get_branch_head_empty(self):
        self.store.create_branch("test_prompt", "dev")
        head = self.store.get_branch_head("test_prompt", "dev")
        assert head is None

    def test_get_branch_head_nonexistent(self):
        head = self.store.get_branch_head("test_prompt", "nonexistent")
        assert head is None

    def test_list_branches(self):
        v = self.store.save("test_prompt", "内容")
        self.store.create_branch("test_prompt", "main", v.version_id)
        self.store.create_branch("test_prompt", "dev")
        branches = self.store.list_branches("test_prompt")
        assert len(branches) == 2

    def test_version_tree(self):
        v1 = self.store.save("test_prompt", "版本1", score=80.0)
        v2 = self.store.save("test_prompt", "版本2", score=90.0)
        self.store.add_tag("test_prompt", v1.version_id, "stable")
        self.store.create_branch("test_prompt", "main", v2.version_id)
        tree = self.store.get_version_tree("test_prompt")
        assert tree["total_versions"] == 2
        assert tree["latest_score"] in (80.0, 90.0)
        assert len(tree["tags"]) == 1
        assert len(tree["branches"]) == 1

    def test_version_tree_empty(self):
        tree = self.store.get_version_tree("nonexistent")
        assert tree["total_versions"] == 0


class TestH2NewTemplates:
    def test_pangu_chat_template(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name
        t = get_template_by_name("pangu-chat")
        assert t is not None
        assert "盘古" in t.template
        assert "system/user/assistant" in t.template

    def test_pangu_function_call_template(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name
        t = get_template_by_name("pangu-function-call")
        assert t is not None
        assert "Function Calling" in t.template

    def test_harmonyos_ability_template(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name
        t = get_template_by_name("harmonyos-ability")
        assert t is not None
        assert "Ability" in t.template
        assert "Stage模型" in t.template

    def test_huaweicloud_maas_finetune_template(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name
        t = get_template_by_name("huaweicloud-maas-finetune")
        assert t is not None
        assert "ModelArts" in t.template
        assert "MindSpore" in t.template

    def test_huaweicloud_sec_audit_template(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name
        t = get_template_by_name("huaweicloud-sec-audit")
        assert t is not None
        assert "安全审计" in t.template
        assert "ModelArts" in t.template

    def test_all_new_templates_render(self):
        from ai_prompt_toolkit.prompt_template import get_template_by_name, PromptTemplate
        for name in ["pangu-chat", "pangu-function-call", "harmonyos-ability",
                      "huaweicloud-maas-finetune", "huaweicloud-sec-audit"]:
            t = get_template_by_name(name)
            assert t is not None, f"Template {name} not found"
            rendered = t.render()
            assert len(rendered) > 50, f"Template {name} rendered too short"

    def test_template_count(self):
        from ai_prompt_toolkit.prompt_template import get_builtin_templates
        assert len(get_builtin_templates()) == 9


class TestD1FixerConflictDetection:
    def setup_method(self):
        self.fixer = Fixer()

    def test_no_conflict_single_rule(self):
        text = "短文本"
        findings = [Finding(rule_id="P005", severity=Severity.LOW, description="过短")]
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) == 1

    def test_no_conflict_different_categories(self):
        text = "api_key=sk-123 你可能会得到结果"
        findings = [
            Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息"),
            Finding(rule_id="P016", severity=Severity.HIGH, description="歧义表述"),
        ]
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) == 2

    def test_sequential_fix_order(self):
        findings = [
            Finding(rule_id="P005", severity=Severity.LOW, description="过短"),
            Finding(rule_id="P003", severity=Severity.MEDIUM, description="缺少约束"),
        ]
        text = "短"
        fixed, results = self.fixer.fix(text, findings)
        assert len(results) >= 1

    def test_append_fixes_dont_overlap(self):
        findings = [
            Finding(rule_id="P010", severity=Severity.MEDIUM, description="缺少错误处理"),
            Finding(rule_id="P068", severity=Severity.HIGH, description="幻觉预防缺失"),
        ]
        text = "你需要回答关于事实数据的问题"
        fixed, results = self.fixer.fix(text, findings)
        assert "错误处理" in fixed
        assert "幻觉预防" in fixed
        assert fixed.count("# 错误处理") <= 1
        assert fixed.count("# 幻觉预防") <= 1

    def test_pangu_fixes_dont_duplicate(self):
        findings = [
            Finding(rule_id="P096", severity=Severity.HIGH, description="盘古格式兼容性"),
            Finding(rule_id="P100", severity=Severity.HIGH, description="安全护栏缺失"),
        ]
        text = "使用盘古大模型"
        fixed, results = self.fixer.fix(text, findings)
        assert "盘古对话格式" in fixed
        assert "盘古安全护栏" in fixed
