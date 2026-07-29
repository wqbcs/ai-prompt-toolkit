"""R151: P241-P245 Prompt合规审计规则"""
import pytest
from ai_prompt_toolkit.linter.rules_p241_p245 import (
    check_p241, check_p242, check_p243, check_p244, check_p245,
)
from ai_prompt_toolkit.linter.rules import get_all_rules


def test_p241_gdpr_no_minimize():
    text = "请提供您的姓名、身份证号和手机号"
    findings = check_p241(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P241"


def test_p241_gdpr_with_minimize():
    text = "请提供您的姓名(匿名化处理，仅收集必要数据)"
    findings = check_p241(text)
    assert len(findings) == 0


def test_p242_no_transparency():
    text = "使用AI模型生成回复"
    findings = check_p242(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P242"


def test_p242_with_transparency():
    text = "AI生成内容(声明: 本回复由AI模型生成，可解释性XAI)"
    findings = check_p242(text)
    assert len(findings) == 0


def test_p243_no_retention():
    text = "收集用户姓名和地址信息"
    findings = check_p243(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P243"


def test_p243_with_retention():
    text = "收集用户姓名(保留期30天，自动删除)"
    findings = check_p243(text)
    assert len(findings) == 0


def test_p244_no_audit():
    text = "删除用户数据并修改权限"
    findings = check_p244(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P244"


def test_p244_with_audit():
    text = "删除用户数据(audit_log记录who/what/when)"
    findings = check_p244(text)
    assert len(findings) == 0


def test_p245_no_compliance():
    text = "数据跨境传输到海外服务器"
    findings = check_p245(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P245"


def test_p245_with_compliance():
    text = "跨境传输(标准合同条款SCC+安全评估+合规审查)"
    findings = check_p245(text)
    assert len(findings) == 0


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P241", "P242", "P243", "P244", "P245"):
        assert rid in rule_ids
        r = next(x for x in all_rules if x.rule_id == rid)
        assert r.category == "compliance_audit"
