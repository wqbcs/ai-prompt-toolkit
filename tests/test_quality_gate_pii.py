"""测试 Quality Gate 和 PII Detector"""

from __future__ import annotations

from ai_prompt_toolkit.linter.quality_gate import QualityGate, Verdict
from ai_prompt_toolkit.types import Finding, Severity


class TestQualityGate:
    def test_pass_no_findings(self):
        gate = QualityGate()
        result = gate.evaluate([], score=100.0)
        assert result.verdict == Verdict.PASS

    def test_fail_on_critical(self):
        gate = QualityGate()
        findings = [Finding(rule_id="TEST", severity=Severity.CRITICAL, description="test")]
        result = gate.evaluate(findings)
        assert result.verdict == Verdict.FAIL

    def test_fail_on_high(self):
        gate = QualityGate()
        findings = [Finding(rule_id="TEST", severity=Severity.HIGH, description="test")]
        result = gate.evaluate(findings)
        assert result.verdict == Verdict.FAIL

    def test_warn_on_medium(self):
        gate = QualityGate({"fail_on_high": False})
        findings = [Finding(rule_id="TEST", severity=Severity.MEDIUM, description="test") for _ in range(5)]
        result = gate.evaluate(findings)
        assert result.verdict == Verdict.WARN

    def test_pass_with_low(self):
        gate = QualityGate({"fail_on_high": False, "warn_on_medium": False})
        findings = [Finding(rule_id="TEST", severity=Severity.LOW, description="test")]
        result = gate.evaluate(findings)
        assert result.verdict == Verdict.PASS

    def test_fail_on_specific_rule(self):
        gate = QualityGate({"fail_on_critical": False, "fail_on_high": False, "fail_rule_ids": ["P007"]})
        findings = [Finding(rule_id="P007", severity=Severity.MEDIUM, description="test")]
        result = gate.evaluate(findings)
        assert result.verdict == Verdict.FAIL

    def test_warn_on_low_score(self):
        gate = QualityGate({"fail_on_critical": False, "fail_on_high": False, "warn_on_medium": False})
        findings = []
        result = gate.evaluate(findings, score=50.0)
        assert result.verdict == Verdict.WARN

    def test_to_dict(self):
        gate = QualityGate()
        result = gate.evaluate([], score=100.0)
        d = result.to_dict()
        assert d["verdict"] == "pass"
        assert d["score"] == 100.0


class TestPIIDetector:
    def test_detect_email(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector()
        text = "请联系 test@example.com 获取更多信息。"
        finding = detector.check(text)
        assert finding is not None
        assert finding.rule_id == "PII001"

    def test_detect_mobile(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector()
        text = "手机号：13800138000"
        finding = detector.check(text)
        assert finding is not None

    def test_detect_id_card(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector()
        text = "身份证号：110101199001011234"
        finding = detector.check(text)
        assert finding is not None
        assert finding.severity == Severity.CRITICAL

    def test_no_pii(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector()
        text = "你是一个翻译助手，请将中文翻译为英文。"
        finding = detector.check(text)
        assert finding is None

    def test_redact_text(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector()
        text = "邮箱test@example.com和手机13800138000"
        redacted = detector.redact_text(text)
        assert "test@example.com" not in redacted
        assert "13800138000" not in redacted

    def test_custom_patterns(self):
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        detector = PIIDetector(
            custom_patterns=[
                ("employee_id", r"EMP\d{6}", 0.9),
            ]
        )
        text = "工号：EMP123456"
        finding = detector.check(text)
        assert finding is not None
