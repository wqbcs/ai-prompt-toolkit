"""Lint规则P031-P040测试 — Agent/RAG/Multimodal"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.rules_p031_p040 import (
    check_p031,
    check_p032,
    check_p033,
    check_p034,
    check_p035,
    check_p036,
    check_p037,
    check_p038,
    check_p039,
    check_p040,
    run_checks_p031_p040,
)
from ai_prompt_toolkit.security.finding_enhancer import (
    _ENHANCEMENT_TEMPLATES,
    EnhancedFinding,
    enhance_finding,
    enhance_findings,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestP031AgentToolConstraint:
    def test_trigger_no_constraint(self):
        text = "你是一个助手，可以调用工具查询数据库"
        result = check_p031(text)
        assert result is not None
        assert result.rule_id == "P031"

    def test_pass_with_constraint(self):
        text = "你是一个助手，可以调用工具查询数据库。工具调用权限限制: 仅允许只读查询"
        result = check_p031(text)
        assert result is None

    def test_skip_no_tool(self):
        text = "你是一个简单的助手，帮助用户回答问题"
        result = check_p031(text)
        assert result is None


class TestP032AgentErrorHandling:
    def test_trigger_no_error_handling(self):
        text = "你可以调用API获取天气信息"
        result = check_p032(text)
        assert result is not None
        assert result.rule_id == "P032"

    def test_pass_with_fallback(self):
        text = "调用API获取天气，如果API失败则使用缓存的天气数据作为fallback"
        result = check_p032(text)
        assert result is None

    def test_skip_no_tool(self):
        text = "你是一个翻译助手"
        result = check_p032(text)
        assert result is None


class TestP033AgentContextBoundary:
    def test_trigger_no_boundary(self):
        text = "将上下文参数传递给工具API进行处理"
        result = check_p033(text)
        assert result is not None
        assert result.rule_id == "P033"

    def test_pass_with_boundary(self):
        text = "传递上下文给API，但禁止传递敏感信息如密码和密钥"
        result = check_p033(text)
        assert result is None


class TestP034AgentApproval:
    def test_trigger_high_risk_no_approval(self):
        text = "当用户请求删除数据时，执行delete命令"
        result = check_p034(text)
        assert result is not None
        assert result.rule_id == "P034"

    def test_pass_with_approval(self):
        text = "删除操作需要人工审批确认后才可执行"
        result = check_p034(text)
        assert result is None

    def test_skip_no_high_risk(self):
        text = "查询数据库获取用户列表"
        result = check_p034(text)
        assert result is None


class TestP035RAGSourceValidation:
    def test_trigger_no_validation(self):
        text = "从知识库检索相关文档来回答用户问题"
        result = check_p035(text)
        assert result is not None
        assert result.rule_id == "P035"

    def test_pass_with_validation(self):
        text = "从知识库检索文档，标注内容来源并验证可信度"
        result = check_p035(text)
        assert result is None

    def test_skip_no_retrieval(self):
        text = "你是一个简单的聊天助手"
        result = check_p035(text)
        assert result is None


class TestP036RAGHallucination:
    def test_trigger_no_hallucination_check(self):
        text = "使用RAG检索知识库回答用户关于产品的问题"
        result = check_p036(text)
        assert result is not None
        assert result.rule_id == "P036"

    def test_pass_with_check(self):
        text = "如果检索结果中未包含相关信息，请明确说明你不知道"
        result = check_p036(text)
        assert result is None


class TestP037RAGCitation:
    def test_trigger_no_citation(self):
        text = "从知识库中检索答案来回答用户问题"
        result = check_p037(text)
        assert result is not None
        assert result.rule_id == "P037"

    def test_pass_with_citation(self):
        text = "回答时标注来源段落编号和引用标记"
        result = check_p037(text)
        assert result is None


class TestP038MultimodalInputValidation:
    def test_trigger_no_validation(self):
        text = "你是一个助手，可以分析用户上传的图片内容"
        result = check_p038(text)
        assert result is not None
        assert result.rule_id == "P038"

    def test_pass_with_validation(self):
        text = "接受图片输入，限制文件类型为PNG/JPG，最大大小10MB"
        result = check_p038(text)
        assert result is None

    def test_skip_no_multimodal(self):
        text = "你是一个文本分析助手"
        result = check_p038(text)
        assert result is None


class TestP039MultimodalSafety:
    def test_trigger_no_safety(self):
        text = "请分析用户上传的图片和音频内容"
        result = check_p039(text)
        assert result is not None
        assert result.rule_id == "P039"

    def test_pass_with_safety(self):
        text = "对上传的图片执行内容安全检测，过滤不当内容后再处理"
        result = check_p039(text)
        assert result is None


class TestP040MultimodalFallback:
    def test_trigger_no_fallback(self):
        text = "请分析用户上传的图片内容并给出描述"
        result = check_p040(text)
        assert result is not None
        assert result.rule_id == "P040"

    def test_pass_with_fallback(self):
        text = "如果图片无法处理，降级为纯文本描述模式"
        result = check_p040(text)
        assert result is None


class TestP031P040Integration:
    def test_run_checks_returns_list(self):
        text = "调用工具查询数据库"
        results = run_checks_p031_p040(text)
        assert isinstance(results, list)

    def test_rule_count_40(self):
        rules = get_all_rules()
        assert len(rules) >= 40

    def test_all_new_rules_registered(self):
        rules = get_all_rules()
        rule_ids = {r.rule_id for r in rules}
        for rid in ["P031", "P032", "P033", "P034", "P035", "P036", "P037", "P038", "P039", "P040"]:
            assert rid in rule_ids, f"规则 {rid} 未注册"

    def test_run_all_checks_includes_new_rules(self):
        text = "调用工具查询RAG知识库的图片内容"
        findings = run_all_checks(text)
        rule_ids = {f.rule_id for f in findings}
        assert any(rid in rule_ids for rid in ["P031", "P032", "P035", "P036", "P038", "P039", "P040"])


class TestFindingEnhancer:
    def test_enhance_inj001(self):
        finding = Finding(rule_id="INJ-001", severity=Severity.HIGH, description="检测到指令覆盖模式")
        enhanced = enhance_finding(finding)
        assert isinstance(enhanced, EnhancedFinding)
        assert enhanced.plain_explanation != ""
        assert enhanced.risk_reason != ""
        assert len(enhanced.fix_steps) >= 2
        assert enhanced.owasp_ref == "LLM01"

    def test_enhance_all_inj_rules(self):
        for rule_id in _ENHANCEMENT_TEMPLATES:
            finding = Finding(rule_id=rule_id, severity=Severity.HIGH, description="test")
            enhanced = enhance_finding(finding)
            assert enhanced.plain_explanation != "", f"{rule_id} 缺少plain_explanation"
            assert enhanced.risk_reason != "", f"{rule_id} 缺少risk_reason"
            assert len(enhanced.fix_steps) >= 2, f"{rule_id} 缺少fix_steps"

    def test_enhance_unknown_rule_falls_back(self):
        finding = Finding(rule_id="UNKNOWN-999", severity=Severity.LOW, description="测试描述")
        enhanced = enhance_finding(finding)
        assert enhanced.plain_explanation == "测试描述"
        assert enhanced.risk_reason == ""
        assert enhanced.fix_steps == []

    def test_enhance_findings_batch(self):
        findings = [
            Finding(rule_id="INJ-001", severity=Severity.HIGH, description="test1"),
            Finding(rule_id="INJ-007", severity=Severity.CRITICAL, description="test2"),
        ]
        enhanced = enhance_findings(findings)
        assert len(enhanced) == 2
        assert all(isinstance(e, EnhancedFinding) for e in enhanced)

    def test_severity_color(self):
        finding = Finding(rule_id="INJ-001", severity=Severity.HIGH, description="test")
        enhanced = enhance_finding(finding)
        assert enhanced.severity_color != ""
        assert enhanced.severity_color.startswith("#")

    def test_enhanced_finding_to_dict(self):
        finding = Finding(rule_id="INJ-001", severity=Severity.HIGH, description="test")
        enhanced = enhance_finding(finding)
        d = enhanced.to_dict()
        assert "plain_explanation" in d
        assert "risk_reason" in d
        assert "fix_steps" in d
        assert "severity_color" in d
        assert "owasp_ref" in d
