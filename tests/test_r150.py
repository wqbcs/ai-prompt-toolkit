"""R150: lint --explain交互式解释增强"""

from ai_prompt_toolkit.linter.explain import explain_finding, explain_results, format_explanation
from ai_prompt_toolkit.types import Finding, Severity


def test_explain_finding_basic():
    f = Finding("P001", "desc", Severity.HIGH)
    expl = explain_finding(f)
    assert expl["rule_id"] == "P001"
    assert expl["severity"] == "high"
    assert expl["category"] == "structure"
    assert "description" in expl
    assert "remediation" in expl


def test_explain_finding_owasp():
    f = Finding("P006", "desc", Severity.HIGH)
    expl = explain_finding(f)
    assert len(expl["owasp_refs"]) >= 1
    assert expl["owasp_refs"][0]["ref"].startswith("LLM")


def test_explain_finding_english():
    f = Finding("P001", "desc", Severity.HIGH)
    expl = explain_finding(f, lang="en")
    assert expl["description"] != ""
    assert expl["remediation"] != ""


def test_explain_finding_risk_level():
    f_high = Finding("P006", "desc", Severity.HIGH)
    expl_high = explain_finding(f_high)
    assert expl_high["risk_level"] == "高危"
    f_med = Finding("P002", "desc", Severity.MEDIUM)
    expl_med = explain_finding(f_med)
    assert expl_med["risk_level"] == "中等"


def test_explain_finding_unknown_rule():
    f = Finding("P999", "desc", Severity.HIGH)
    expl = explain_finding(f)
    assert expl.get("error") == "rule_not_found"


def test_explain_results():
    findings = [
        Finding("P001", "d1", Severity.HIGH),
        Finding("P006", "d2", Severity.HIGH),
    ]
    results = explain_results(findings)
    assert len(results) == 2


def test_format_explanation():
    f = Finding("P001", "desc", Severity.HIGH)
    expl = explain_finding(f)
    text = format_explanation(expl)
    assert "P001" in text
    assert "高危" in text or "high" in text
