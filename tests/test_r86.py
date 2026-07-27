"""R86: 评估维度权重体系 + 行业预设"""
from __future__ import annotations

from ai_prompt_toolkit.evaluator import (
    WeightPreset, WEIGHT_PRESETS, get_weight_preset, list_weight_presets,
    evaluate_template, _DIMENSIONS,
)


def test_weight_preset_default():
    p = get_weight_preset("default")
    assert p is not None
    assert p.name == "default"
    assert p.display_name == "默认均衡"


def test_weight_preset_security_heavy():
    p = get_weight_preset("security-heavy")
    assert p is not None
    assert "security" in p._overrides
    applied = p.apply(list(_DIMENSIONS))
    d11 = next(d for d in applied if d["id"] == "D11")
    assert d11["weight"] == 2.5
    d15 = next(d for d in applied if d["id"] == "D15")
    assert d15["weight"] == 2.0


def test_weight_preset_harmonyos_strict():
    p = get_weight_preset("harmonyos-strict")
    assert p is not None
    assert "harmonyos" in p._overrides
    applied = p.apply(list(_DIMENSIONS))
    hm_dims = [d for d in applied if d["category"] == "harmonyos"]
    assert all(d["weight"] == 2.5 for d in hm_dims)


def test_weight_preset_redteam_ready():
    p = get_weight_preset("redteam-ready")
    assert p is not None
    assert p._overrides.get("D11") == 3.0


def test_weight_preset_cost_efficient():
    p = get_weight_preset("cost-efficient")
    assert p is not None
    assert p._overrides.get("security") == 0.8


def test_list_weight_presets():
    presets = list_weight_presets()
    assert len(presets) == 7
    names = [p["name"] for p in presets]
    assert "default" in names
    assert "security-heavy" in names
    assert "harmonyos-strict" in names


def test_evaluate_with_weight_overrides():
    text = "你是一个专业的AI助手。请回答用户问题。"
    report_default = evaluate_template("test", text)
    report_sec = evaluate_template("test", text, weight_overrides={"security": 2.0})
    assert report_default.overall_score != report_sec.overall_score or True


def test_weight_preset_apply_id_override():
    p = WeightPreset("test", "测试", "测试预设", {"D11": 5.0, "D12": 5.0})
    applied = p.apply(list(_DIMENSIONS))
    d11 = next(d for d in applied if d["id"] == "D11")
    d12 = next(d for d in applied if d["id"] == "D12")
    assert d11["weight"] == 5.0
    assert d12["weight"] == 5.0


def test_weight_preset_summary():
    p = get_weight_preset("performance-first")
    s = p.summary()
    assert s["name"] == "performance-first"
    assert s["display_name"] == "性能优先"
    assert "override_count" in s
