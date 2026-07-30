"""R164: OSC2026参赛示例+华为云ModelArts评测基准"""
import pytest
from pathlib import Path


def test_osc2026_doc_exists():
    p = Path("docs/OSC2026-参赛示例.md")
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "255" in content
    assert "OWASP" in content
    assert "ModelArts" in content


def test_modelarts_provider_exists():
    from ai_prompt_toolkit.ab_test.providers import get_registry
    registry = get_registry()
    has_huawei = any("huawei" in str(k).lower() or "modelarts" in str(k).lower() or "pangu" in str(k).lower() for k in registry.keys())
    assert has_huawei


def test_arkts_rules_available():
    from ai_prompt_toolkit.linter.rules import get_all_rules
    all_rules = get_all_rules()
    arkts_rules = [r for r in all_rules if r.category == "arkts_security"]
    assert len(arkts_rules) >= 5


def test_harmonyos_rules_available():
    from ai_prompt_toolkit.linter.rules import get_all_rules
    all_rules = get_all_rules()
    harmony_rules = [r for r in all_rules if r.category in ("harmonyos", "harmonyos_v15", "harmonyos_v16")]
    assert len(harmony_rules) >= 10


def test_pipeline_template_exists():
    p = Path(".codearts/pipeline-lint.yml")
    assert p.exists()
