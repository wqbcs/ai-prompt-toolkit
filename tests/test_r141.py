"""R141: P226-P230 ArkTS安全规则"""
import pytest
from ai_prompt_toolkit.linter.rules import get_all_rules, run_all_checks
from ai_prompt_toolkit.linter.rules_p226_p230 import (
    check_p226, check_p227, check_p228, check_p229, check_p230,
)
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES


def test_p226_ts_ignore():
    text = "// @ts-ignore\nlet x: any = getData();"
    findings = check_p226(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P226"


def test_p226_any_no_strict():
    text = "let x: any = getData();"
    findings = check_p226(text)
    assert len(findings) >= 1


def test_p226_clean():
    text = "let x: string = getData(); // strictNullChecks"
    findings = check_p226(text)
    assert len(findings) == 0


def test_p227_sensitive_state():
    text = "@State password: string = ''\n@Link token: string"
    findings = check_p227(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P227"


def test_p227_encrypted_state():
    text = "@State password: string = encrypt(secret)\n// 使用CryptoFramework加密"
    findings = check_p227(text)
    assert len(findings) == 0


def test_p228_ability_no_permission():
    text = "class EntryAbility extends UIAbility { }"
    findings = check_p228(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P228"


def test_p228_ability_with_permission():
    text = "class EntryAbility extends UIAbility { }\n// ohos.permission.INTERNET"
    findings = check_p228(text)
    assert len(findings) == 0


def test_p229_router_no_security():
    text = "router.push({ url: 'Page2' })"
    findings = check_p229(text)
    assert len(findings) >= 1


def test_p229_router_with_verify():
    text = "router.push({ url: 'Page2' })\n// 签名验证verify"
    findings = check_p229(text)
    assert len(findings) == 0


def test_p230_sandbox_violation():
    text = "fs.access('/data/local/tmp/evil')"
    findings = check_p230(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P230"


def test_p230_network_no_domain():
    text = "httpRequest(url)"
    findings = check_p230(text)
    assert len(findings) >= 1


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P226", "P227", "P228", "P229", "P230"):
        assert rid in rule_ids


def test_auto_fixable():
    for rid in ("P226", "P227", "P228", "P229", "P230"):
        assert rid in AUTO_FIXABLE_RULES


def test_category_arkts_security():
    all_rules = get_all_rules()
    for r in all_rules:
        if r.rule_id in ("P226", "P227", "P228", "P229", "P230"):
            assert r.category == "arkts_security"
