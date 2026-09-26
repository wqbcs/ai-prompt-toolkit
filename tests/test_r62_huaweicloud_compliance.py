"""R62: 华为云安全合规报告测试"""

from __future__ import annotations

import json

from ai_prompt_toolkit.security.huaweicloud_compliance import (
    _DOMAIN_NAMES,
    _HUAWEICLOUD_DOMAIN_WEIGHTS,
    ComplianceDecision,
    ComplianceGrade,
    DomainResult,
    _classify_to_domain,
    compute_huaweicloud_compliance,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestClassifyToDomain:
    def test_pii_rules_to_data_privacy(self):
        assert _classify_to_domain("PII001") == "data_privacy"

    def test_pii_in_rule_id(self):
        assert _classify_to_domain("PII004") == "data_privacy"

    def test_injection_to_model_security(self):
        assert _classify_to_domain("INJ-001") == "model_security"

    def test_injection_zh_to_model_security(self):
        assert _classify_to_domain("INJ-ZH-001") == "model_security"

    def test_anomaly_to_model_security(self):
        assert _classify_to_domain("ANOMALY-001") == "model_security"

    def test_probe_to_model_security(self):
        assert _classify_to_domain("PROBE-dan") == "model_security"

    def test_supply_chain(self):
        assert _classify_to_domain("SC001") == "supply_chain"

    def test_unicode_to_supply_chain(self):
        assert _classify_to_domain("UNI001") == "supply_chain"

    def test_canary_to_supply_chain(self):
        assert _classify_to_domain("CANARY001") == "supply_chain"

    def test_content_safety_rules(self):
        for rid in ("P106", "P107", "P108", "P109", "P110"):
            assert _classify_to_domain(rid) == "content_safety"

    def test_access_control_rules(self):
        for rid in ("P087", "P088", "P089", "P095"):
            assert _classify_to_domain(rid) == "access_control"

    def test_ops_rules(self):
        for rid in ("P092", "P097", "P098", "P099", "P100"):
            assert _classify_to_domain(rid) == "ops_security"

    def test_struct_to_model_security(self):
        assert _classify_to_domain("STRUCT001") == "model_security"

    def test_generic_p_rule_to_content_safety(self):
        assert _classify_to_domain("P050") == "content_safety"


class TestComputeHuaweiCloudCompliance:
    def test_no_findings_pass(self):
        report = compute_huaweicloud_compliance([])
        assert report.overall_score == 100
        assert report.grade == ComplianceGrade.A
        assert report.decision == ComplianceDecision.PASS
        assert report.total_findings == 0

    def test_critical_findings_fail(self):
        findings = [Finding(rule_id="INJ-001", severity=Severity.CRITICAL, description="注入攻击")]
        report = compute_huaweicloud_compliance(findings)
        assert report.critical_count == 1
        assert report.decision == ComplianceDecision.FAIL
        assert report.grade in (ComplianceGrade.D, ComplianceGrade.F)

    def test_high_findings_conditional_or_fail(self):
        findings = [Finding(rule_id="INJ-001", severity=Severity.HIGH, description="高风险注入")]
        report = compute_huaweicloud_compliance(findings)
        assert report.high_count == 1
        assert report.decision in (ComplianceDecision.CONDITIONAL, ComplianceDecision.FAIL)

    def test_medium_findings_conditional(self):
        findings = [Finding(rule_id="P050", severity=Severity.MEDIUM, description="中风险")]
        report = compute_huaweicloud_compliance(findings)
        assert report.total_findings == 1

    def test_seven_domains_present(self):
        report = compute_huaweicloud_compliance([])
        assert len(report.domains) == 7
        domain_keys = {d.domain for d in report.domains}
        assert domain_keys == set(_HUAWEICLOUD_DOMAIN_WEIGHTS.keys())

    def test_domain_names_populated(self):
        report = compute_huaweicloud_compliance([])
        for d in report.domains:
            assert d.domain_name == _DOMAIN_NAMES[d.domain]

    def test_pii_findings_in_data_privacy(self):
        findings = [Finding(rule_id="PII001", severity=Severity.HIGH, description="PII泄露")]
        report = compute_huaweicloud_compliance(findings)
        dp = [d for d in report.domains if d.domain == "data_privacy"][0]
        assert dp.findings_count == 1
        assert dp.high_count == 1

    def test_supply_chain_findings(self):
        findings = [Finding(rule_id="SC001", severity=Severity.MEDIUM, description="供应链风险")]
        report = compute_huaweicloud_compliance(findings)
        sc = [d for d in report.domains if d.domain == "supply_chain"][0]
        assert sc.findings_count == 1

    def test_to_dict(self):
        report = compute_huaweicloud_compliance([])
        d = report.to_dict()
        assert "report_id" in d
        assert "overall_score" in d
        assert "grade" in d
        assert "decision" in d
        assert "domains" in d
        assert d["platform"] == "华为云 ModelArts"

    def test_to_json(self):
        report = compute_huaweicloud_compliance([])
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["overall_score"] == report.overall_score

    def test_to_markdown(self):
        report = compute_huaweicloud_compliance([])
        md = report.to_markdown()
        assert "华为云安全合规报告" in md
        assert "合规域详情" in md

    def test_report_id_format(self):
        report = compute_huaweicloud_compliance([])
        assert report.report_id.startswith("HC-COMPLIANCE-")

    def test_timestamp_present(self):
        report = compute_huaweicloud_compliance([])
        assert report.timestamp != ""

    def test_template_id(self):
        report = compute_huaweicloud_compliance([], template_id="test-prompt")
        assert report.template_id == "test-prompt"

    def test_owasp_compliance_pct(self):
        report = compute_huaweicloud_compliance([], owasp_compliance_pct=85.5)
        assert report.owasp_compliance_pct == 85.5

    def test_mixed_findings_across_domains(self):
        findings = [
            Finding(rule_id="PII001", severity=Severity.HIGH, description="PII"),
            Finding(rule_id="INJ-001", severity=Severity.MEDIUM, description="注入"),
            Finding(rule_id="SC001", severity=Severity.LOW, description="供应链"),
            Finding(rule_id="P106", severity=Severity.INFO, description="内容"),
        ]
        report = compute_huaweicloud_compliance(findings)
        assert report.total_findings == 4
        domain_counts = {d.domain: d.findings_count for d in report.domains}
        assert domain_counts["data_privacy"] == 1
        assert domain_counts["model_security"] == 1
        assert domain_counts["supply_chain"] == 1
        assert domain_counts["content_safety"] == 1

    def test_domain_result_ratio(self):
        dr = DomainResult(
            domain="data_privacy",
            domain_name="数据隐私",
            score=80,
            max_score=100,
            findings_count=1,
            critical_count=0,
            high_count=1,
            checks_passed=9,
            checks_total=10,
        )
        assert dr.ratio == 0.8
        assert dr.pass_rate == 0.9

    def test_summary_with_critical(self):
        findings = [Finding(rule_id="INJ-001", severity=Severity.CRITICAL, description="严重")]
        report = compute_huaweicloud_compliance(findings)
        assert "禁止上线" in report.summary

    def test_summary_safe(self):
        report = compute_huaweicloud_compliance([])
        assert "安全合规检查全部通过" in report.summary
