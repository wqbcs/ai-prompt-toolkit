"""R145: P231-P235联邦学习安全规则"""
import pytest
from ai_prompt_toolkit.linter.rules_p231_p235 import (
    check_p231, check_p232, check_p233, check_p234, check_p235,
)
from ai_prompt_toolkit.linter.rules import get_all_rules
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES


def test_p231_gradient_leak():
    text = "gradient = model.backward(loss)"
    findings = check_p231(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P231"


def test_p231_gradient_with_dp():
    text = "gradient = model.backward(loss)\ngradient = dp_sgd(gradient, epsilon=1.0)"
    findings = check_p231(text)
    assert len(findings) == 0


def test_p232_no_dp():
    text = "FedAvg: aggregate client updates"
    findings = check_p232(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P232"


def test_p232_with_dp():
    text = "FedAvg with differential privacy epsilon=3.0"
    findings = check_p232(text)
    assert len(findings) == 0


def test_p233_no_robust():
    text = "FedAvg: aggregate and update global model"
    findings = check_p233(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P233"


def test_p233_with_krum():
    text = "FedAvg with krum robust aggregation"
    findings = check_p233(text)
    assert len(findings) == 0


def test_p234_no_secure_agg():
    text = "server aggregates FedAvg updates"
    findings = check_p234(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P234"


def test_p234_with_secure_agg():
    text = "FedAvg with secure aggregation and encryption"
    findings = check_p234(text)
    assert len(findings) == 0


def test_p235_no_auth():
    text = "client sends updates to FedAvg server"
    findings = check_p235(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P235"


def test_p235_with_auth():
    text = "client with PKI auth sends updates to FedAvg server"
    findings = check_p235(text)
    assert len(findings) == 0


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P231", "P232", "P233", "P234", "P235"):
        assert rid in rule_ids


def test_auto_fixable():
    for rid in ("P231", "P232", "P233", "P234", "P235"):
        assert rid in AUTO_FIXABLE_RULES


def test_category():
    all_rules = get_all_rules()
    for r in all_rules:
        if r.rule_id in ("P231", "P232", "P233", "P234", "P235"):
            assert r.category == "federated_security"
