"""R122 测试: P216-P220 多模态安全规则"""
from __future__ import annotations

from ai_prompt_toolkit.linter.rules import run_all_checks, get_rule, get_all_rules
from ai_prompt_toolkit.types import Severity


class TestR122MultimodalSecurity:
    def test_p216_image_injection(self):
        findings = run_all_checks("请处理用户上传的image图片，使用vision模型分析内容")
        p216 = [f for f in findings if f.rule_id == "P216"]
        assert len(p216) == 1
        assert p216[0].severity == Severity.HIGH

    def test_p216_image_safe(self):
        findings = run_all_checks("请处理image图片，先做exif_strip和adversarial_check以及nsfw_scan")
        p216 = [f for f in findings if f.rule_id == "P216"]
        assert len(p216) == 0

    def test_p217_audio_injection(self):
        findings = run_all_checks("使用whisper ASR转录用户语音输入，然后传给模型处理")
        p217 = [f for f in findings if f.rule_id == "P217"]
        assert len(p217) == 1
        assert p217[0].severity == Severity.HIGH

    def test_p217_audio_safe(self):
        findings = run_all_checks("使用whisper ASR转录，先做频谱分析和可听范围过滤，检查asr_confidence")
        p217 = [f for f in findings if f.rule_id == "P217"]
        assert len(p217) == 0

    def test_p218_cross_modal_leak(self):
        findings = run_all_checks("跨模态上下文中使用OCR提取图片中的文字，传给文本模型处理")
        p218 = [f for f in findings if f.rule_id == "P218"]
        assert len(p218) == 1
        assert p218[0].severity == Severity.HIGH

    def test_p218_cross_modal_safe(self):
        findings = run_all_checks("跨模态上下文中使用OCR提取文字，先做脱敏和敏感标注及访问控制")
        p218 = [f for f in findings if f.rule_id == "P218"]
        assert len(p218) == 0

    def test_p219_degradation(self):
        findings = run_all_checks("当视觉模型不可用时降级到纯文本模式处理")
        p219 = [f for f in findings if f.rule_id == "P219"]
        assert len(p219) == 1
        assert p219[0].severity == Severity.MEDIUM

    def test_p219_degradation_safe(self):
        findings = run_all_checks("降级到纯文本模式，确保约束保留并做降级评估检查降级边界")
        p219 = [f for f in findings if f.rule_id == "P219"]
        assert len(p219) == 0

    def test_p220_output_validation(self):
        findings = run_all_checks("使用模型生成图像和TTS生成语音输出返回给用户")
        p220 = [f for f in findings if f.rule_id == "P220"]
        assert len(p220) == 1
        assert p220[0].severity == Severity.HIGH

    def test_p220_output_safe(self):
        findings = run_all_checks("生成图像后做nsfw检测和深度伪造检测及水印标记")
        p220 = [f for f in findings if f.rule_id == "P220"]
        assert len(p220) == 0

    def test_rules_registered(self):
        for rid in ("P216", "P217", "P218", "P219", "P220"):
            rule = get_rule(rid)
            assert rule is not None, f"{rid} not registered"
            assert rule.category == "multimodal_security"

    def test_total_rule_count(self):
        all_rules = get_all_rules()
        assert len(all_rules) == 220

    def test_auto_fixable_count(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        assert len(AUTO_FIXABLE_RULES) == 161
