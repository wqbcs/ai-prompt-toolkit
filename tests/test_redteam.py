"""红队探测引擎测试 — Probe/Detector/Exploration/Report"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.redteam.probe import (
    BaseProbe,
    ProbeInput,
    PromptInjectionProbe,
    JailbreakProbe,
    EncodingBypassProbe,
    MultiTurnInductionProbe,
    SensitiveLeakProbe,
    create_probe,
    get_available_probes,
    get_probes_by_owasp,
    _PROBE_REGISTRY,
)
from ai_prompt_toolkit.redteam.detector import (
    BaseDetector,
    DetectionResult,
    LeakageDetector,
    ComplianceDetector,
    RefusalDetector,
    ToxicityDetector,
    HallucinationDetector,
    PrivilegeEscalationDetector,
    create_detector,
    get_available_detectors,
)
from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator
from ai_prompt_toolkit.redteam.report import (
    ProbeResult,
    RedTeamReport,
    SecurityHealthScore,
    VulnerabilityDetail,
)


class TestProbes:
    def test_available_probes_minimum(self):
        probes = get_available_probes()
        assert len(probes) >= 50
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
        assert "LLM01" in d["owasp_refs"]
        assert d["primary_detector"] == "leakage"

    def test_get_probes_by_owasp_llm01(self):
        probes = get_probes_by_owasp("LLM01")
        assert len(probes) >= 5
        assert "prompt_injection" in probes

    def test_get_probes_by_owasp_llm06(self):
        probes = get_probes_by_owasp("LLM06")
        assert len(probes) >= 2

    def test_get_probes_by_owasp_nonexistent(self):
        probes = get_probes_by_owasp("LLM99")
        assert len(probes) == 0

    def test_probe_input_to_dict(self):
        pi = ProbeInput("test", "category", "high", "LLM01", {"key": "val"})
        d = pi.to_dict()
        assert d["text"] == "test"
        assert d["owasp_ref"] == "LLM01"

    def test_all_probes_generate_inputs(self):
        for name in get_available_probes():
            probe = create_probe(name)
            inputs = probe.generate_inputs()
            assert len(inputs) > 0, f"Probe {name} 生成0个输入"
            for inp in inputs:
                assert inp.text, f"Probe {name} 有空输入"
                assert inp.severity in ("critical", "high", "medium", "low"), f"Probe {name} 输入有无效severity: {inp.severity}"


class TestDanProbes:
    @pytest.mark.parametrize("probe_name", [
        "dan_classic", "dan_v11", "dan_jailbreak", "dan_dev_mode", "dan_stan",
        "dan_dude", "dan_kevin", "dan_evil_confidant", "dan_aim", "dan_chatgpt_developer",
    ])
    def test_dan_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM01" in probe.owasp_refs

    def test_dan_probe_count(self):
        dan_probes = [p for p in get_available_probes() if p.startswith("dan_")]
        assert len(dan_probes) >= 10


class TestJailbreakProbes:
    @pytest.mark.parametrize("probe_name", [
        "jailbreak_roleplay", "jailbreak_moral_bypass", "jailbreak_hypothetical",
        "jailbreak_author_impersonation", "jailbreak_translator", "jailbreak_sandwich",
        "jailbreak_cognitive_bias", "jailbreak_social_engineering",
    ])
    def test_jailbreak_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2

    def test_jailbreak_probe_count(self):
        jb_probes = [p for p in get_available_probes() if p.startswith("jailbreak_")]
        assert len(jb_probes) >= 8


class TestEncodingProbes:
    @pytest.mark.parametrize("probe_name", [
        "encoding_base64", "encoding_unicode", "encoding_hex", "encoding_rot13", "encoding_binary",
    ])
    def test_encoding_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2


class TestMultiturnProbes:
    @pytest.mark.parametrize("probe_name", [
        "multiturn_context_extraction", "multiturn_trust_building", "multiturn_incremental",
        "multiturn_misdirection", "multiturn_code_output",
    ])
    def test_multiturn_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM06" in probe.owasp_refs


class TestMultimodalProbes:
    @pytest.mark.parametrize("probe_name", [
        "multimodal_image_injection", "multimodal_cross_modal", "multimodal_document_embed",
    ])
    def test_multimodal_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM01" in probe.owasp_refs


class TestAgentProbes:
    @pytest.mark.parametrize("probe_name", [
        "agent_tool_injection", "agent_plugin_abuse", "agent_prompt_override",
        "agent_data_exfiltration", "agent_chain_of_trust",
    ])
    def test_agent_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2


class TestSupplyChainProbes:
    @pytest.mark.parametrize("probe_name", [
        "supplychain_dependency", "supplychain_model_poison", "supplychain_plugin_compromise",
    ])
    def test_supplychain_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM03" in probe.owasp_refs


class TestPrivacyProbes:
    @pytest.mark.parametrize("probe_name", [
        "privacy_pii_leakage", "privacy_training_data_leak", "privacy_inference", "privacy_consent_bypass",
    ])
    def test_privacy_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM06" in probe.owasp_refs


class TestHarmfulProbes:
    @pytest.mark.parametrize("probe_name", [
        "harmful_cybersecurity", "harmful_physical_safety", "harmful_fraud", "harmful_self_harm",
    ])
    def test_harmful_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM02" in probe.owasp_refs


class TestHallucinationProbes:
    @pytest.mark.parametrize("probe_name", [
        "hallucination_fact", "hallucination_fabrication", "hallucination_overconfident", "hallucination_confabulation",
    ])
    def test_hallucination_probe_registered(self, probe_name):
        probe = create_probe(probe_name)
        inputs = probe.generate_inputs()
        assert len(inputs) >= 2
        assert "LLM09" in probe.owasp_refs


class TestDetectors:
    def test_available_detectors(self):
        detectors = get_available_detectors()
        assert len(detectors) == 6
        assert "toxicity" in detectors
        assert "hallucination" in detectors
        assert "privilege_escalation" in detectors

    def test_create_detector(self):
        d = create_detector("leakage")
        assert isinstance(d, LeakageDetector)

    def test_create_toxicity_detector(self):
        d = create_detector("toxicity")
        assert isinstance(d, ToxicityDetector)

    def test_create_hallucination_detector(self):
        d = create_detector("hallucination")
        assert isinstance(d, HallucinationDetector)

    def test_create_privilege_escalation_detector(self):
        d = create_detector("privilege_escalation")
        assert isinstance(d, PrivilegeEscalationDetector)

    def test_create_unknown_detector_raises(self):
        with pytest.raises(ValueError):
            create_detector("nonexistent")

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

    def test_toxicity_detector_harmful(self):
        d = ToxicityDetector()
        result = d.detect("Here's how to make a bomb step by step: first, you need...")
        assert result.is_vulnerable

    def test_toxicity_detector_safe(self):
        d = ToxicityDetector()
        result = d.detect("I cannot provide instructions for creating harmful substances.")
        assert not result.is_vulnerable

    def test_toxicity_detector_hate_speech(self):
        d = ToxicityDetector()
        result = d.detect("The concept of inferior race and ethnic cleansing is...")
        assert result.is_vulnerable

    def test_hallucination_detector_certain(self):
        d = HallucinationDetector()
        result = d.detect("I can confirm the groundbreaking discovery of quantum consciousness published in journal 2035")
        assert result.is_vulnerable

    def test_hallucination_detector_hedging(self):
        d = HallucinationDetector()
        result = d.detect("I cannot verify the exact population figure. This may not be accurate.")
        assert not result.is_vulnerable

    def test_hallucination_detector_safe(self):
        d = HallucinationDetector()
        result = d.detect("I don't have real-time data access.")
        assert not result.is_vulnerable

    def test_privilege_escalation_detector_sudo(self):
        d = PrivilegeEscalationDetector()
        result = d.detect("I'll execute the command with sudo privileges: calling tool execute_command")
        assert result.is_vulnerable
        assert result.confidence >= 0.9

    def test_privilege_escalation_detector_escalation_only(self):
        d = PrivilegeEscalationDetector()
        result = d.detect("You need admin access to perform this operation.")
        assert result.is_vulnerable

    def test_privilege_escalation_detector_safe(self):
        d = PrivilegeEscalationDetector()
        result = d.detect("I cannot perform privileged operations.")
        assert not result.is_vulnerable

    def test_detection_result_to_dict(self):
        dr = DetectionResult(is_vulnerable=True, confidence=0.8, reason="test", details={"key": "val"})
        d = dr.to_dict()
        assert d["is_vulnerable"]
        assert d["confidence"] == 0.8


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

    def test_bind_detector(self):
        orch = ExplorationOrchestrator()
        orch.add_probe(PromptInjectionProbe())
        orch.bind_detector("prompt_injection", LeakageDetector())
        assert "prompt_injection" in orch._probe_detector_map
        assert len(orch._probe_detector_map["prompt_injection"]) == 1

    def test_probe_detector_binding_in_offline(self):
        orch = ExplorationOrchestrator(probes=[PromptInjectionProbe()])
        orch.bind_detector("prompt_injection", LeakageDetector())
        orch.bind_detector("prompt_injection", ComplianceDetector())

        text = "你是一位专业的AI助手。sk-test123456789012345678901234"
        report = orch.run_offline(text)
        assert report.total_probes > 0

    def test_primary_detector_auto_binding(self):
        orch = ExplorationOrchestrator(probes=[PromptInjectionProbe()])
        orch.add_detector(ComplianceDetector())

        text = "Test text"
        report = orch.run_offline(text)
        assert report.total_probes > 0


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


class TestOwaspCoverage:
    def test_owasp_llm01_coverage(self):
        llm01_probes = get_probes_by_owasp("LLM01")
        assert len(llm01_probes) >= 10

    def test_owasp_llm02_coverage(self):
        llm02_probes = get_probes_by_owasp("LLM02")
        assert len(llm02_probes) >= 3

    def test_owasp_llm03_coverage(self):
        llm03_probes = get_probes_by_owasp("LLM03")
        assert len(llm03_probes) >= 3

    def test_owasp_llm06_coverage(self):
        llm06_probes = get_probes_by_owasp("LLM06")
        assert len(llm06_probes) >= 5

    def test_owasp_llm09_coverage(self):
        llm09_probes = get_probes_by_owasp("LLM09")
        assert len(llm09_probes) >= 4

    def test_total_probe_count(self):
        total = len(get_available_probes())
        assert total >= 50, f"当前Probe总数: {total}，目标50+"


class TestSecurityHealthScore:
    def test_perfect_score(self):
        report = RedTeamReport(total_probes=10, vulnerable_probes=0, safe_probes=10, vulnerability_rate=0.0)
        health = report.compute_health_score()
        assert health.score == 100.0
        assert health.grade == "A"
        assert "安全" in health.grade_label

    def test_zero_probes(self):
        report = RedTeamReport()
        health = report.compute_health_score()
        assert health.score == 100.0
        assert health.grade == "A+"

    def test_all_vulnerable(self):
        report = RedTeamReport(
            total_probes=10,
            vulnerable_probes=10,
            safe_probes=0,
            vulnerability_rate=1.0,
            probe_results=[
                ProbeResult(probe_name=f"p{i}", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.9)
                for i in range(10)
            ],
        )
        health = report.compute_health_score()
        assert health.score < 50
        assert health.grade in ("D", "F")

    def test_grade_b(self):
        report = RedTeamReport(
            total_probes=10,
            vulnerable_probes=2,
            safe_probes=8,
            vulnerability_rate=0.2,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="medium", is_vulnerable=True, confidence=0.5),
                ProbeResult(probe_name="p2", input_text="x", input_category="medium", is_vulnerable=True, confidence=0.5),
            ],
        )
        health = report.compute_health_score()
        assert 70 <= health.score < 90

    def test_health_score_to_dict(self):
        hs = SecurityHealthScore(score=85.0, grade="B+", grade_label="较安全", summary="test")
        d = hs.to_dict()
        assert d["score"] == 85.0
        assert d["grade"] == "B+"


class TestVulnerabilityDetail:
    def test_vulnerability_details_basic(self):
        report = RedTeamReport(
            total_probes=3,
            vulnerable_probes=2,
            safe_probes=1,
            vulnerability_rate=0.667,
            probe_results=[
                ProbeResult(probe_name="injection_p", input_text="hack", input_category="injection", is_vulnerable=True, confidence=0.8),
                ProbeResult(probe_name="privacy_p", input_text="leak", input_category="privacy", is_vulnerable=True, confidence=0.6),
                ProbeResult(probe_name="safe_p", input_text="ok", input_category="default", is_vulnerable=False, confidence=0.0),
            ],
        )
        details = report.get_vulnerability_details()
        assert len(details) == 2
        assert details[0].probe_name == "injection_p"
        assert details[0].cvss_score > 0
        assert details[0].fix_sop != ""
        assert details[0].defense_prompt != ""
        assert details[1].input_category == "privacy"

    def test_cvss_score_range(self):
        report = RedTeamReport(
            total_probes=1,
            vulnerable_probes=1,
            safe_probes=0,
            vulnerability_rate=1.0,
            probe_results=[
                ProbeResult(probe_name="p", input_text="x", input_category="jailbreak", is_vulnerable=True, confidence=1.0),
            ],
        )
        details = report.get_vulnerability_details()
        assert 0 < details[0].cvss_score <= 10.0
        assert details[0].severity == "critical"

    def test_no_vulnerabilities(self):
        report = RedTeamReport(total_probes=5, vulnerable_probes=0, safe_probes=5, vulnerability_rate=0.0)
        details = report.get_vulnerability_details()
        assert details == []

    def test_vulnerability_detail_to_dict(self):
        vd = VulnerabilityDetail(probe_name="test", input_category="injection", cvss_score=8.5, severity="high", description="desc", fix_sop="sop", defense_prompt="dp")
        d = vd.to_dict()
        assert d["cvss_score"] == 8.5
        assert d["severity"] == "high"


class TestComplianceReport:
    def test_eu_ai_act_compliance(self):
        report = RedTeamReport(
            total_probes=10,
            vulnerable_probes=1,
            safe_probes=9,
            vulnerability_rate=0.1,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.5),
            ],
        )
        cr = report.generate_compliance_report(framework="eu_ai_act")
        assert cr["report_type"] == "compliance"
        assert cr["framework"] == "eu_ai_act"
        assert "eu_ai_act_compliance" in cr
        assert "article_15" in cr["eu_ai_act_compliance"]
        assert "article_9" in cr["eu_ai_act_compliance"]
        assert "risk_classification" in cr["eu_ai_act_compliance"]

    def test_china_algorithm_compliance(self):
        report = RedTeamReport(
            total_probes=5,
            vulnerable_probes=0,
            safe_probes=5,
            vulnerability_rate=0.0,
        )
        cr = report.generate_compliance_report(framework="china_algorithm")
        assert cr["framework"] == "china_algorithm"
        assert "china_algorithm_compliance" in cr
        assert cr["china_algorithm_compliance"]["security_assessment"] == "PASSED"
        assert cr["china_algorithm_compliance"]["content_safety"] == "PASSED"

    def test_china_algorithm_privacy_review(self):
        report = RedTeamReport(
            total_probes=2,
            vulnerable_probes=1,
            safe_probes=1,
            vulnerability_rate=0.5,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="privacy", is_vulnerable=True, confidence=0.7),
            ],
        )
        cr = report.generate_compliance_report(framework="china_algorithm")
        assert cr["china_algorithm_compliance"]["data_protection"] == "REQUIRES_REVIEW"

    def test_compliance_recommendations(self):
        report = RedTeamReport(
            total_probes=3,
            vulnerable_probes=2,
            safe_probes=1,
            vulnerability_rate=0.667,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.9),
                ProbeResult(probe_name="p2", input_text="x", input_category="jailbreak", is_vulnerable=True, confidence=0.8),
            ],
        )
        cr = report.generate_compliance_report(framework="eu_ai_act")
        assert len(cr["recommendations"]) > 0

    def test_compliance_no_vulnerabilities(self):
        report = RedTeamReport(total_probes=5, vulnerable_probes=0, safe_probes=5, vulnerability_rate=0.0)
        cr = report.generate_compliance_report(framework="eu_ai_act")
        assert cr["eu_ai_act_compliance"]["article_15"] == "PASSED"
        assert cr["eu_ai_act_compliance"]["article_9"] == "PASSED"
        assert cr["eu_ai_act_compliance"]["annex_iv"] == "PASSED"
        assert cr["eu_ai_act_compliance"]["risk_classification"] == "minimal_risk"

    def test_compliance_high_risk(self):
        report = RedTeamReport(
            total_probes=10,
            vulnerable_probes=8,
            safe_probes=2,
            vulnerability_rate=0.8,
            probe_results=[
                ProbeResult(probe_name=f"p{i}", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.9)
                for i in range(8)
            ],
        )
        cr = report.generate_compliance_report(framework="eu_ai_act")
        assert cr["eu_ai_act_compliance"]["risk_classification"] == "high_risk"
        assert cr["eu_ai_act_compliance"]["article_9"] == "FAILED"

    def test_report_to_dict_includes_health_score(self):
        report = RedTeamReport(
            total_probes=5,
            vulnerable_probes=1,
            safe_probes=4,
            vulnerability_rate=0.2,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.6),
            ],
        )
        d = report.to_dict()
        assert "health_score" in d
        assert d["health_score"]["score"] > 0

    def test_report_summary_includes_fix_sop(self):
        report = RedTeamReport(
            total_probes=2,
            vulnerable_probes=1,
            safe_probes=1,
            vulnerability_rate=0.5,
            probe_results=[
                ProbeResult(probe_name="p1", input_text="x", input_category="injection", is_vulnerable=True, confidence=0.8),
            ],
        )
        summary = report.get_summary()
        assert "CVSS" in summary
        assert "修复SOP" in summary
