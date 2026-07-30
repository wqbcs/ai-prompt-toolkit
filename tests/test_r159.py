"""R159: P251包幻觉+P252-P255 PII增强探测"""
import pytest
from ai_prompt_toolkit.linter.rules_p251_p255 import (
    check_p251, check_p252, check_p253, check_p254, check_p255,
)
from ai_prompt_toolkit.linter.rules import get_all_rules


def test_p251_hallucinated_package():
    text = "pip install langcahin\nimport langcahin"
    findings = check_p251(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P251"


def test_p251_npm_hallucinated():
    text = "npm install torchh"
    findings = check_p251(text)
    assert len(findings) >= 1


def test_p251_clean():
    text = "import json\nfrom pathlib import Path"
    findings = check_p251(text)
    assert len(findings) == 0


def test_p252_biometric():
    text = "用户面部识别指纹验证登录"
    findings = check_p252(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P252"


def test_p252_biometric_secure():
    text = "面部识别使用加密模板特征提取(本地化)"
    findings = check_p252(text)
    assert len(findings) == 0


def test_p253_financial():
    text = "银行卡号6225880123456789 信用卡CVV 123"
    findings = check_p253(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P253"


def test_p253_financial_secure():
    text = "银行卡Token化脱敏处理(PCI合规审计)"
    findings = check_p253(text)
    assert len(findings) == 0


def test_p254_medical():
    text = "患者诊断: 高血压 处方: 缬沙坦 医保卡号"
    findings = check_p254(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P254"


def test_p254_medical_secure():
    text = "诊断脱敏匿名化处理(k-anonymity+访问控制+审计)"
    findings = check_p254(text)
    assert len(findings) == 0


def test_p255_minor():
    text = "未成年人年龄<18 学籍信息 监护人"
    findings = check_p255(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P255"


def test_p255_minor_secure():
    text = "未成年人(年龄门控+监护人同意+快速删除+数据最小化)"
    findings = check_p255(text)
    assert len(findings) == 0


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P251", "P252", "P253", "P254", "P255"):
        assert rid in rule_ids


def test_severity_critical():
    all_rules = get_all_rules()
    for r in all_rules:
        if r.rule_id in ("P252", "P253", "P254", "P255"):
            assert r.severity.value == "critical"
