"""R317 ODT-5 机器化测试: check_overdefense_trend floor_ratio 提示面（hermetic）

ODT-5 = R316 设计 §2.3: 地板 prompt 占比 ≥80% → T1 近地板提示（P2-26 终止
声明入口）; <80% → 可治理面余量提示。check() 纯函数 + composition 注入 =
hermetic（不触发 run_overdefense linting 面, 与 ODT-1~4 同测试纪律）。
importlib spec 加载脚本（R294 先例）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_overdefense_trend.py"

_spec = importlib.util.spec_from_file_location("check_overdefense_trend_r317", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check = _mod.check


def _points(rates: list[float]) -> list[dict]:
    return [{"version": f"v{i:03d}", "overdefense_rate": r, "backfill": False} for i, r in enumerate(rates)]


class TestODT5FloorSurface:
    def test_governable_surface_hint(self):
        # 23 flagged / 13 地板 = 56.5% < 80% → 可治理面提示（余 10 prompts）
        r = check(_points([0.115, 0.0767, 0.0678]), {"flagged": 23, "floor_prompts": 13})
        assert r["ok"]
        assert any("ODT-5 可治理面" in h and "余 10 prompts" in h for h in r["hints"])

    def test_floor_termination_hint(self):
        # 16 flagged / 13 地板 = 81.25% ≥ 80% → T1 近地板提示
        r = check(_points([0.115, 0.0767, 0.0472]), {"flagged": 16, "floor_prompts": 13})
        assert r["ok"]
        assert any("ODT-5 近地板(T1)" in h for h in r["hints"])

    def test_no_composition_no_hint(self):
        # composition=None → ODT-5 静默跳过（极简环境形态）
        r = check(_points([0.115, 0.0767]), None)
        assert r["ok"]
        assert not any(h.startswith("ODT-5") for h in r["hints"])

    def test_zero_flagged_guard(self):
        # flagged=0 → 除零守卫, 无 ODT-5 提示, 不崩
        r = check(_points([0.115, 0.0]), {"flagged": 0, "floor_prompts": 0})
        assert r["ok"]
        assert not any(h.startswith("ODT-5") for h in r["hints"])

    def test_hint_never_red(self):
        # 提示面纪律: ODT-5 永不阻断（ok 恒真, issues 恒空）
        r = check(_points([0.115, 0.0767]), {"flagged": 100, "floor_prompts": 100})
        assert r["ok"] and r["issues"] == []


class TestODT3Errata:
    def test_bottomed_text_p163_floor(self):
        # 连续 3 点同值 → 触底提示; 文本须为 R257 P163 口径（I/J 簇 36 条已勘误）
        r = check(_points([0.115, 0.0767, 0.0678, 0.0678, 0.0678]), {"flagged": 23, "floor_prompts": 13})
        bottomed = [h for h in r["hints"] if h.startswith("ODT-3 触底")]
        assert bottomed
        assert "P163 检测下限" in bottomed[0]
        assert not any("I/J 簇 36" in h for h in r["hints"])
