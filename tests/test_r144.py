"""R144: lint --suggest修复建议智能推荐"""

from ai_prompt_toolkit.linter.suggest import Suggestion, generate_suggestions
from ai_prompt_toolkit.types import Finding, Severity


def test_generate_suggestions_empty():
    suggestions = generate_suggestions([])
    assert suggestions == []


def test_generate_suggestions_basic():
    findings = [
        Finding("P001", "desc1", Severity.HIGH),
        Finding("P006", "desc2", Severity.HIGH),
        Finding("P002", "desc3", Severity.MEDIUM),
    ]
    suggestions = generate_suggestions(findings)
    assert len(suggestions) == 3
    assert suggestions[0].severity in ("high", "critical")


def test_generate_suggestions_priority_order():
    findings = [
        Finding("P005", "low", Severity.LOW),
        Finding("P001", "high", Severity.HIGH),
        Finding("P002", "medium", Severity.MEDIUM),
    ]
    suggestions = generate_suggestions(findings)
    sevs = [s.severity for s in suggestions]
    assert sevs.index("high") < sevs.index("medium")
    assert sevs.index("medium") < sevs.index("low")


def test_generate_suggestions_hit_count():
    findings = [
        Finding("P001", "d1", Severity.HIGH),
        Finding("P001", "d2", Severity.HIGH),
        Finding("P001", "d3", Severity.HIGH),
    ]
    suggestions = generate_suggestions(findings)
    assert len(suggestions) == 1
    assert suggestions[0].hit_count == 3
    assert "高" in suggestions[0].estimated_impact


def test_generate_suggestions_action_steps():
    findings = [Finding("P001", "desc", Severity.HIGH)]
    suggestions = generate_suggestions(findings)
    assert len(suggestions) == 1
    assert len(suggestions[0].action_steps) >= 1


def test_generate_suggestions_english():
    findings = [Finding("P001", "desc", Severity.HIGH)]
    suggestions = generate_suggestions(findings, lang="en")
    assert len(suggestions) == 1
    assert suggestions[0].rule_name != ""


def test_suggestion_to_dict():
    s = Suggestion(
        priority=1,
        rule_id="P001",
        rule_name="test",
        severity="high",
        category="structure",
        remediation="fix it",
        hit_count=1,
        estimated_impact="高",
        action_steps=["step1"],
    )
    d = s.to_dict()
    assert d["rule_id"] == "P001"
    assert d["action_steps"] == ["step1"]
