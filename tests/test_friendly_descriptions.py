"""测试友好描述翻译"""

from __future__ import annotations

from ai_prompt_toolkit.linter.friendly_descriptions import translate_finding, translate_findings
from ai_prompt_toolkit.types import Finding, Severity


class TestFriendlyDescriptions:
    def test_translate_p001(self):
        finding = Finding(rule_id="P001", severity=Severity.HIGH, description="缺失角色定义", remediation="添加角色")
        result = translate_finding(finding)
        assert "身份介绍" in result
        assert "[重要]" in result

    def test_translate_p006(self):
        finding = Finding(rule_id="P006", severity=Severity.HIGH, description="敏感信息暴露", remediation="移除")
        result = translate_finding(finding)
        assert "密码" in result or "密钥" in result

    def test_translate_pii(self):
        finding = Finding(rule_id="PII001", severity=Severity.CRITICAL, description="PII泄露", remediation="脱敏")
        result = translate_finding(finding)
        assert "隐私" in result
        assert "[严重]" in result

    def test_translate_sc(self):
        finding = Finding(rule_id="SC001", severity=Severity.HIGH, description="供应链风险", remediation="验证")
        result = translate_finding(finding)
        assert "外部资源" in result

    def test_translate_unknown(self):
        finding = Finding(rule_id="CUSTOM-999", severity=Severity.LOW, description="自定义问题", remediation="修复")
        result = translate_finding(finding)
        assert "自定义问题" in result

    def test_translate_findings_batch(self):
        findings = [
            Finding(rule_id="P001", severity=Severity.HIGH, description="缺失角色", remediation="添加"),
            Finding(rule_id="P007", severity=Severity.HIGH, description="注入风险", remediation="转义"),
        ]
        results = translate_findings(findings)
        assert len(results) == 2
        assert all("friendly_description" in r for r in results)
