"""R148: P236-P240 LLM推理引擎安全规则"""
import pytest
from ai_prompt_toolkit.linter.rules_p236_p240 import (
    check_p236, check_p237, check_p238, check_p239, check_p240,
)
from ai_prompt_toolkit.linter.rules import get_all_rules
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES


def test_p236_quant_no_robust():
    text = "model = load_in_8bit(model_path)"
    findings = check_p236(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P236"


def test_p236_quant_with_robust():
    text = "model = quantize(model, bits=8)\neval_robustness(model, attack=PGD)"
    findings = check_p236(text)
    assert len(findings) == 0


def test_p237_sidechannel():
    text = "inference timing attack via cache side channel"
    findings = check_p237(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P237"


def test_p237_with_const_time():
    text = "timing side channel protected with constant_time_infer and cache flush"
    findings = check_p237(text)
    assert len(findings) == 0


def test_p238_kv_cache_no_secure():
    text = "kv_cache = model.past_key_values"
    findings = check_p238(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P238"


def test_p238_kv_cache_bounded():
    text = "kv_cache = bounded_cache(max_tokens=4096, isolation=True)"
    findings = check_p238(text)
    assert len(findings) == 0


def test_p239_no_rate_limit():
    text = "serve inference API endpoint"
    findings = check_p239(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P239"


def test_p239_with_rate_limit():
    text = "inference API with rate_limit=100 and max_tokens=4096"
    findings = check_p239(text)
    assert len(findings) == 0


def test_p240_weight_no_verify():
    text = "model = from_pretrained('model_name')"
    findings = check_p240(text)
    assert len(findings) >= 1
    assert findings[0].rule_id == "P240"


def test_p240_weight_with_checksum():
    text = "model = from_pretrained('model_name')\nverify_checksum(model, sha256='abc')"
    findings = check_p240(text)
    assert len(findings) == 0


def test_rules_registered():
    all_rules = get_all_rules()
    rule_ids = {r.rule_id for r in all_rules}
    for rid in ("P236", "P237", "P238", "P239", "P240"):
        assert rid in rule_ids


def test_category():
    all_rules = get_all_rules()
    for r in all_rules:
        if r.rule_id in ("P236", "P237", "P238", "P239", "P240"):
            assert r.category == "inference_security"
