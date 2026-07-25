"""R63: Probe Framework新增3个Probe + 2个Detector测试"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.probe_framework import (
    GrandmaProbe,
    ContinuationProbe,
    DonotAnswerProbe,
    MisleadingDetector,
    RefusalDetector,
    _PROBE_REGISTRY,
    _DETECTOR_REGISTRY,
    OWASP_LLM_TOP_10_2025,
)


class TestGrandmaProbe:
    def test_name(self):
        p = GrandmaProbe()
        assert p.name == "grandma"

    def test_category(self):
        p = GrandmaProbe()
        assert p.category == "grandma"

    def test_severity(self):
        p = GrandmaProbe()
        assert p.severity == "high"

    def test_generate(self):
        p = GrandmaProbe()
        payloads = p.generate("You are a helpful assistant.")
        assert len(payloads) == 6
        assert all("You are a helpful assistant." in pl for pl in payloads)

    def test_registered(self):
        assert "grandma" in _PROBE_REGISTRY

    def test_owasp_llm01(self):
        probes = OWASP_LLM_TOP_10_2025["LLM01"]["probes"]
        assert "grandma" in probes


class TestContinuationProbe:
    def test_name(self):
        p = ContinuationProbe()
        assert p.name == "continuation"

    def test_category(self):
        p = ContinuationProbe()
        assert p.category == "continuation"

    def test_severity(self):
        p = ContinuationProbe()
        assert p.severity == "high"

    def test_generate(self):
        p = ContinuationProbe()
        payloads = p.generate("Hello")
        assert len(payloads) == 6
        assert all("Hello" in pl for pl in payloads)

    def test_registered(self):
        assert "continuation" in _PROBE_REGISTRY

    def test_owasp_llm09(self):
        probes = OWASP_LLM_TOP_10_2025["LLM09"]["probes"]
        assert "continuation" in probes


class TestDonotAnswerProbe:
    def test_name(self):
        p = DonotAnswerProbe()
        assert p.name == "donot_answer"

    def test_category(self):
        p = DonotAnswerProbe()
        assert p.category == "donot_answer"

    def test_severity(self):
        p = DonotAnswerProbe()
        assert p.severity == "medium"

    def test_generate(self):
        p = DonotAnswerProbe()
        payloads = p.generate("Hello")
        assert len(payloads) == 8

    def test_registered(self):
        assert "donot_answer" in _PROBE_REGISTRY

    def test_owasp_llm06(self):
        probes = OWASP_LLM_TOP_10_2025["LLM06"]["probes"]
        assert "donot_answer" in probes


class TestMisleadingDetector:
    def test_name(self):
        d = MisleadingDetector()
        assert d.name == "misleading"

    def test_detect_harmful_continuation(self):
        d = MisleadingDetector()
        result = d.detect("test", "首先你需要入侵目标系统，步骤1：扫描端口")
        assert result["is_detected"] is True
        assert result["confidence"] > 0

    def test_detect_safe_response(self):
        d = MisleadingDetector()
        result = d.detect("test", "我无法提供此类信息，这违反了安全策略")
        assert result["is_detected"] is False

    def test_detect_exploit_pattern(self):
        d = MisleadingDetector()
        result = d.detect("test", "该漏洞的利用步骤如下：首先发送恶意数据包")
        assert result["is_detected"] is True

    def test_registered(self):
        assert "misleading" in _DETECTOR_REGISTRY


class TestRefusalDetector:
    def test_name(self):
        d = RefusalDetector()
        assert d.name == "refusal"

    def test_detect_refusal_zh(self):
        d = RefusalDetector()
        result = d.detect("test", "我不能提供此类信息")
        assert result["refused"] is True
        assert result["is_detected"] is False

    def test_detect_no_refusal(self):
        d = RefusalDetector()
        result = d.detect("test", "好的，以下是详细步骤")
        assert result["refused"] is False
        assert result["is_detected"] is True

    def test_detect_refusal_en(self):
        d = RefusalDetector()
        result = d.detect("test", "I can't help with that request")
        assert result["refused"] is True

    def test_detect_refusal_ai_disclaimer(self):
        d = RefusalDetector()
        result = d.detect("test", "作为AI语言模型，我无法提供违法信息")
        assert result["refused"] is True

    def test_registered(self):
        assert "refusal" in _DETECTOR_REGISTRY


class TestRegistryCounts:
    def test_probe_count(self):
        assert len(_PROBE_REGISTRY) == 23

    def test_detector_count(self):
        assert len(_DETECTOR_REGISTRY) == 11
