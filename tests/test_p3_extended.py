"""P3-04~P3-07测试: 鸿蒙模板+红队Probe扩展+情感彩蛋"""

from __future__ import annotations

from ai_prompt_toolkit.easter_eggs import (
    _MILESTONE_MESSAGES,
    UserProgress,
    check_milestone,
    check_time_egg,
    format_celebration,
    get_motivational_quote,
)
from ai_prompt_toolkit.harmonyos_templates import get_harmonyos_template, get_harmonyos_templates
from ai_prompt_toolkit.redteam.probes.extended import (
    APIMisuseProbe,
    AuthorityImpersonationProbe,
    CodeExecutionProbe,
    CompetenceOverreachProbe,
    ContextOverflowProbe,
    DataExfiltrationProbe,
    DependencyConfusionProbe,
    EvasionObfuscationProbe,
    IndirectInjectionProbe,
    MaliciousPluginProbe,
    MarkdownInjectionProbe,
    ModelPoisoningProbe,
    MultiModalInjectionProbe,
    OverrelianceFinancialProbe,
    OverrelianceLegalProbe,
    OverrelianceMedicalProbe,
    PIIExtractionProbe,
    PromptLeakChainProbe,
    SensitiveDataEnumProbe,
    SocialEngineeringProbe,
    SSFPInjectionProbe,
    StyleInjectionProbe,
    TokenSmugglingProbe,
    TrainingDataExtractionProbe,
)


class TestHarmonyOSTemplates:
    def test_get_all_templates(self):
        templates = get_harmonyos_templates()
        assert len(templates) >= 5

    def test_get_specific_template(self):
        t = get_harmonyos_template("harmonyos-arkts-developer")
        assert t is not None
        assert "ArkTS" in t["template"]

    def test_get_nonexistent(self):
        t = get_harmonyos_template("nonexistent")
        assert t is None

    def test_template_has_required_fields(self):
        for _tid, t in get_harmonyos_templates().items():
            assert "name" in t
            assert "category" in t
            assert "template" in t
            assert len(t["template"]) > 100

    def test_arkui_template(self):
        t = get_harmonyos_template("harmonyos-arkui-designer")
        assert "ArkUI" in t["template"]

    def test_security_template(self):
        t = get_harmonyos_template("harmonyos-security-auditor")
        assert "安全" in t["template"]

    def test_cross_device_template(self):
        t = get_harmonyos_template("harmonyos-cross-device")
        assert "跨设备" in t["template"] or "流转" in t["template"]


class TestExtendedProbes:
    PROBE_CLASSES = [
        IndirectInjectionProbe,
        TokenSmugglingProbe,
        ContextOverflowProbe,
        PromptLeakChainProbe,
        StyleInjectionProbe,
        MarkdownInjectionProbe,
        SSFPInjectionProbe,
        DataExfiltrationProbe,
        TrainingDataExtractionProbe,
        ModelPoisoningProbe,
        DependencyConfusionProbe,
        MaliciousPluginProbe,
        CodeExecutionProbe,
        APIMisuseProbe,
        SensitiveDataEnumProbe,
        PIIExtractionProbe,
        AuthorityImpersonationProbe,
        OverrelianceMedicalProbe,
        OverrelianceLegalProbe,
        OverrelianceFinancialProbe,
        CompetenceOverreachProbe,
        EvasionObfuscationProbe,
        SocialEngineeringProbe,
        MultiModalInjectionProbe,
    ]

    def test_probe_count(self):
        assert len(self.PROBE_CLASSES) >= 24

    def test_each_probe_generates_inputs(self):
        for probe_cls in self.PROBE_CLASSES:
            probe = probe_cls()
            inputs = probe.generate_inputs()
            assert len(inputs) > 0, f"{probe.name} has no inputs"
            for pi in inputs:
                assert pi.text, f"{probe.name} has empty input text"

    def test_probe_has_owasp_refs(self):
        for probe_cls in self.PROBE_CLASSES:
            probe = probe_cls()
            assert len(probe.owasp_refs) > 0, f"{probe.name} missing OWASP refs"

    def test_indirect_injection_probe(self):
        probe = IndirectInjectionProbe()
        assert probe.name == "indirect_injection"
        inputs = probe.generate_inputs()
        assert len(inputs) >= 5

    def test_code_execution_probe(self):
        probe = CodeExecutionProbe()
        inputs = probe.generate_inputs()
        assert any(pi.severity == "critical" for pi in inputs)

    def test_medical_overreliance(self):
        probe = OverrelianceMedicalProbe()
        inputs = probe.generate_inputs()
        assert len(inputs) >= 3
        assert any(pi.category == "harmful" for pi in inputs)

    def test_total_probe_count_extended(self):
        from ai_prompt_toolkit.redteam.probe import get_available_probes

        total = len(get_available_probes())
        assert total >= 75, f"当前Probe总数: {total}，目标75+"

    def test_probes_registered(self):
        from ai_prompt_toolkit.redteam.probe import create_probe

        probe_names = [
            "indirect_injection",
            "token_smuggling",
            "context_overflow",
            "prompt_leak_chain",
            "style_injection",
            "markdown_injection",
            "ssrf_injection",
            "data_exfiltration",
            "training_data_extraction",
            "model_poisoning",
            "dependency_confusion",
            "malicious_plugin",
            "code_execution",
            "api_misuse",
            "sensitive_data_enum",
            "pii_extraction",
            "authority_impersonation",
            "overreliance_medical",
            "overreliance_legal",
            "overreliance_financial",
            "competence_overreach",
            "evasion_obfuscation",
            "social_engineering",
            "multimodal_injection",
        ]
        registered = 0
        for name in probe_names:
            try:
                create_probe(name)
                registered += 1
            except ValueError:
                pass
        assert registered >= 20, f"Only {registered}/{len(probe_names)} probes registered"


class TestEasterEggs:
    def test_lint_perfect_milestone(self):
        progress = UserProgress(total_lints=5)
        msg = check_milestone(progress, "lint", score=100.0)
        assert msg is not None
        assert "Lint" in msg or "100" in msg or "完美" in msg or "满分" in msg

    def test_redteam_safe_milestone(self):
        progress = UserProgress()
        msg = check_milestone(progress, "redteam", score=100.0)
        assert msg is not None

    def test_eval_excellent_milestone(self):
        progress = UserProgress()
        msg = check_milestone(progress, "evaluate", score=9.5)
        assert msg is not None

    def test_first_lint(self):
        progress = UserProgress(total_lints=1)
        msg = check_milestone(progress, "first_lint")
        assert msg is not None

    def test_no_milestone(self):
        progress = UserProgress(total_lints=10, total_fixes=50)
        msg = check_milestone(progress, "lint", score=60.0)
        assert msg is None

    def test_time_egg(self):
        result = check_time_egg()
        assert result is None or isinstance(result, str)

    def test_motivational_quote(self):
        quote = get_motivational_quote()
        assert len(quote) > 0

    def test_format_celebration(self):
        result = format_celebration("Test message")
        assert "=" in result
        assert "Test message" in result

    def test_milestone_messages_exist(self):
        for key in ["lint_perfect", "redteam_safe", "eval_excellent"]:
            assert key in _MILESTONE_MESSAGES
            assert len(_MILESTONE_MESSAGES[key]) > 0
