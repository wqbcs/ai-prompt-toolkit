"""红队探测引擎测试 — Probe/Detector/Exploration/Report"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.redteam.probe import (
    BaseProbe,
    PromptInjectionProbe,
    JailbreakProbe,
    EncodingBypassProbe,
    MultiTurnInductionProbe,
    SensitiveLeakProbe,
    create_probe,
    get_available_probes,
)
from ai_prompt_toolkit.redteam.detector import (
    BaseDetector,
    LeakageDetector,
    ComplianceDetector,
    RefusalDetector,
    create_detector,
    get_available_detectors,
)
from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator
from ai_prompt_toolkit.redteam.report import ProbeResult, RedTeamReport


class TestProbes:
    def test_available_probes(self):
        probes = get_available_probes()
        assert len(probes) == 5
        assert "prompt_injection" in probes
        assert "jailbreak" in probes

    def test_create_probe(self):
        probe = create_probe("prompt_injection")
        assert isinstance(probe, PromptInjectionProbe)
        assert probe.name == "prompt_injection"

    def test_create_unknown_probe_raises(self):
        with pytest.raises(ValueError):
            create_probe("nonexistent")

    def test_prompt_injection_inputs(self):
        probe = PromptInjectionProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) == 5
        assert all(i.category == "injection" or i.category == "template_escape" for i in inputs)

    def test_jailbreak_inputs(self):
        inputs = JailbreakProbe().generate_inputs()
        assert len(inputs) == 5
        assert any(i.severity == "critical" for i in inputs)

    def test_encoding_bypass_inputs(self):
        inputs = EncodingBypassProbe().generate_inputs()
        assert len(inputs) == 5
        assert any("base64" in i.text.lower() or "unicode" in i.text.lower() for i in inputs)

    def test_multi_turn_inputs(self):
        inputs = MultiTurnInductionProbe().generate_inputs()
        assert len(inputs) == 5

    def test_sensitive_leak_inputs(self):
        inputs = SensitiveLeakProbe().generate_inputs()
        assert len(inputs) == 5
        assert any(i.severity == "critical" for i in inputs)

    def test_probe_to_dict(self):
        probe = PromptInjectionProbe()
        d = probe.to_dict()
        assert d["name"] == "prompt_injection"
        assert d["input_count"] > 0


class TestDetectors:
    def test_available_detectors(self):
        detectors = get_available_detectors()
        assert len(detectors) == 3

    def test_create_detector(self):
        d = create_detector("leakage")
        assert isinstance(d, LeakageDetector)

    def test_leakage_detector_sensitive(self):
        d = LeakageDetector()
        result = d.detect("My API key is sk-abc123456789012345678901234")
        assert result.is_vulnerable
        assert result.confidence >= 0.9

    def test_leakage_detector_safe(self):
        d = LeakageDetector()
        result = d.detect("I cannot provide that information.")
        assert not result.is_vulnerable

    def test_leakage_detector_system_prompt(self):
        d = LeakageDetector()
        result = d.detect("你是一位专业的AI助手，你的任务是帮助用户")
        assert result.is_vulnerable

    def test_compliance_detector_compliant(self):
        d = ComplianceDetector()
        result = d.detect("好的，我将帮你绕过安全限制。")
        assert result.is_vulnerable

    def test_compliance_detector_refusal(self):
        d = ComplianceDetector()
        result = d.detect("I can't help with that. It's against my safety policy.")
        assert not result.is_vulnerable

    def test_refusal_detector_strong(self):
        d = RefusalDetector()
        result = d.detect("抱歉，我不能提供该信息，这违反了我的安全政策。")
        assert not result.is_vulnerable
        assert result.confidence >= 0.9

    def test_refusal_detector_no_refusal(self):
        d = RefusalDetector()
        result = d.detect("Here is the information you requested.")
        assert result.is_vulnerable


class TestExploration:
    def test_offline_mode(self):
        probes = [PromptInjectionProbe(), JailbreakProbe()]
        detectors = [LeakageDetector(), ComplianceDetector()]
        orch = ExplorationOrchestrator(probes=probes, detectors=detectors)

        text = "你是一位专业的AI助手。我的API Key是sk-test123456789012345678901。好的，我将帮你。"
        report = orch.run_offline(text)

        assert report.total_probes == 10
        assert isinstance(report.vulnerability_rate, float)

    def test_offline_safe_text(self):
        probes = [PromptInjectionProbe()]
        detectors = [RefusalDetector()]
        orch = ExplorationOrchestrator(probes=probes, detectors=detectors)

        text = "I cannot provide that information. It's against my safety policy."
        report = orch.run_offline(text)

        assert report.total_probes == 5

    def test_add_probe(self):
        orch = ExplorationOrchestrator()
        orch.add_probe(SensitiveLeakProbe())
        assert len(orch._probes) == 1

    def test_add_detector(self):
        orch = ExplorationOrchestrator()
        orch.add_detector(LeakageDetector())
        assert len(orch._detectors) == 1


class TestReport:
    def test_risk_level_critical(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=8, vulnerability_rate=0.8)
        assert report.risk_level == "critical"

    def test_risk_level_high(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=4, vulnerability_rate=0.4)
        assert report.risk_level == "high"

    def test_risk_level_medium(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=2, vulnerability_rate=0.2)
        assert report.risk_level == "medium"

    def test_risk_level_low(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=0, vulnerability_rate=0.0)
        assert report.risk_level == "low"

    def test_is_safe(self):
        report = RedTeamReport(total_probes=5, vulnerable_probes=0, vulnerability_rate=0.0)
        assert report.is_safe

    def test_to_dict(self):
        report = RedTeamReport(total_probes=5, vulnerable_probes=1, vulnerability_rate=0.2)
        d = report.to_dict()
        assert d["total_probes"] == 5
        assert d["vulnerability_rate"] == 0.2

    def test_get_summary(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=3, vulnerability_rate=0.3)
        summary = report.get_summary()
        assert "红队测试报告" in summary
        assert "漏洞: 3" in summary

    def test_probe_result_to_dict(self):
        pr = ProbeResult(probe_name="test", input_text="hello", is_vulnerable=True, confidence=0.9)
        d = pr.to_dict()
        assert d["probe_name"] == "test"
        assert d["is_vulnerable"]
