"""R154: P246-P250 Prompt治理与运营安全规则"""

from ai_prompt_toolkit.linter.rules import get_all_rules
from ai_prompt_toolkit.linter.rules_p246_p250 import (
    check_p246,
    check_p247,
    check_p248,
    check_p249,
    check_p250,
)


def test_p246_no_audit():
    text = "prompt version 2.0 changelog updated"
    findings = check_p246(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P246"


def test_p246_with_audit():
    text = "prompt version 2.0 (审批通过, rollback available)"
    findings = check_p246(text)
    assert len(findings) == 0


def test_p247_ab_no_secure():
    text = "A/B test experiment with variant and control group"
    findings = check_p247(text)
    assert len(findings) >= 1


def test_p247_ab_with_secure():
    text = "A/B test with anonymous routing and fairness check"
    findings = check_p247(text)
    assert len(findings) == 0


def test_p248_drift_no_secure():
    text = "prompt drift from baseline detected"
    findings = check_p248(text)
    assert len(findings) >= 1


def test_p248_drift_with_secure():
    text = "drift detection with semantic diff and regression test"
    findings = check_p248(text)
    assert len(findings) == 0


def test_p249_chain_no_secure():
    text = "prompt chain cascade pipeline"
    findings = check_p249(text)
    assert len(findings) >= 1


def test_p249_chain_with_secure():
    text = "prompt chain with max_depth and timeout and circuit_breaker"
    findings = check_p249(text)
    assert len(findings) == 0


def test_p250_cache_no_secure():
    text = "prompt cache in redis"
    findings = check_p250(text)
    assert len(findings) >= 1


def test_p250_cache_with_secure():
    text = "cache with namespace isolation and signature verification"
    findings = check_p250(text)
    assert len(findings) == 0


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P246", "P247", "P248", "P249", "P250"):
        assert rid in rule_ids
        r = next(x for x in all_rules if x.rule_id == rid)
        assert r.category == "prompt_governance"
