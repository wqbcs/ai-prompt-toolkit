"""R255-I-1: 过防御二阶信号机器化测试。

覆盖(R255 方案 §3.3, 红绿两态 ≥8 条):
1. 真仓首跑 rc=0(6 点单调收敛)
2. --json 结构断言
3. 红态: 注入升点 → ODT-1 rc=1 报版本对
4. 红态: 文件缺失 → 诚实失败
5. 红态: 非 backfill 仅 1 点 → ODT-2
6. backfill 排除: backfill=true 的升点不触发 ODT-1
7. ODT-3 触底提示: 连续 3 点同值 → 提示面 + rc=0(不阻断)
8. ODT-4 目标达成: 末条 ≤0.10 → 提示 + rc=0
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_overdefense_trend.py"
sys.path.insert(0, str(ROOT / "scripts"))

from check_overdefense_trend import TARGET_RATE, check, load_points, main  # noqa: E402


def _mk(tmp_path: Path, rates: list[tuple[str, float, bool]]) -> Path:
    """写临时 jsonl: [(version, rate, backfill)]"""
    p = tmp_path / "od.jsonl"
    lines = [
        {
            "ts": "2026-10-09T00:00:00",
            "version": v,
            "overdefense_rate": r,
            "backfill": b,
            "flagged_count": int(r * 339),
            "prompt_count": 339,
        }
        for v, r, b in rates
    ]
    p.write_text("\n".join(__import__("json").dumps(x) for x in lines) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------- 绿态(真仓)


class TestRealRepoGreen:
    def test_first_run_ok(self):
        """真仓 6 点单调(33.92%→20.94%→13.27%→11.50% 族), rc=0。"""
        rc = main()
        assert rc == 0

    def test_json_structure(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        data = __import__("json").loads(proc.stdout)
        assert data["ok"] is True
        assert data["issues"] == []
        assert len(data["real_points"]) >= 4
        assert data["status"] in ("converging", "plateau", "bottomed")  # R319: plateau=2 点同值(R315/R317 后真仓常态)

    def test_load_points_real(self):
        points = load_points(ROOT / "docs" / "overdefense_history.jsonl")
        assert len(points) >= 4
        assert all("overdefense_rate" in p for p in points)


# ---------------------------------------------------------------- 红态(注入)


class TestRed:
    def test_ratchet_regression_red(self, tmp_path: Path):
        """ODT-1: 末条回退(升点)→ 红, 报版本对。"""
        p = _mk(tmp_path, [("a", 0.20, False), ("b", 0.15, False), ("c", 0.18, False)])
        result = check(load_points(p))
        assert not result["ok"]
        # 回退=b(0.15)→c(0.18): 低于末点的历史点是 b, 早期点 a(0.20) 高于末点=收敛正常不判
        # (断言用精确版本 token——"a" 会子串误配 "rate" 的字母 a)
        assert any("ODT-1" in i and "高于 b rate=" in i and "最近 c rate=" in i for i in result["issues"])
        assert not any("高于 a rate=" in i for i in result["issues"])

    def test_missing_file_honest_fail(self, tmp_path: Path, capsys):
        """文件缺失 → 诚实失败 rc=1(不假绿)。"""
        import check_overdefense_trend as mod

        orig = mod.HISTORY
        mod.HISTORY = tmp_path / "nope.jsonl"
        try:
            rc = main()
        finally:
            mod.HISTORY = orig
        assert rc == 1
        assert "缺失" in capsys.readouterr().out

    def test_single_point_red(self, tmp_path: Path):
        """ODT-2: 非 backfill 仅 1 点 → 红(序列不足)。"""
        p = _mk(tmp_path, [("a", 0.20, False)])
        result = check(load_points(p))
        assert not result["ok"]
        assert any("ODT-2" in i for i in result["issues"])
        assert result["status"] == "insufficient"


# ---------------------------------------------------------------- backfill/提示面


class TestSemantics:
    def test_backfill_excluded_from_ratchet(self, tmp_path: Path):
        """backfill 条目不参与 ODT-1(回补不是真实轮次)。"""
        # backfill 升点 0.50 在序列前, 真实序列 0.20→0.15 单调
        p = _mk(tmp_path, [("bf", 0.50, True), ("a", 0.20, False), ("b", 0.15, False)])
        result = check(load_points(p))
        assert result["ok"], result["issues"]
        assert len(result["real_points"]) == 2

    def test_bottomed_hint_not_red(self, tmp_path: Path):
        """ODT-3: 连续 3 点同值=触底 → 提示面, 不阻断。"""
        p = _mk(
            tmp_path,
            [("a", 0.20, False), ("b", 0.15, False), ("c", 0.115, False), ("d", 0.115, False), ("e", 0.115, False)],
        )
        result = check(load_points(p))
        assert result["ok"]
        assert any("ODT-3" in h and "触底" in h for h in result["hints"])
        assert result["status"] == "bottomed"

    def test_plateau_two_points_hint(self, tmp_path: Path):
        """ODT-3: 仅连续 2 点同值=减速观察面(非触底)。"""
        p = _mk(tmp_path, [("a", 0.20, False), ("b", 0.15, False), ("c", 0.115, False), ("d", 0.115, False)])
        result = check(load_points(p))
        assert result["ok"]
        assert any("减速" in h for h in result["hints"])

    def test_target_reached_hint(self, tmp_path: Path):
        """ODT-4: 末条 ≤10% → 目标达成提示, 不阻断。"""
        assert TARGET_RATE == 0.10
        p = _mk(tmp_path, [("a", 0.20, False), ("b", 0.15, False), ("c", 0.099, False)])
        result = check(load_points(p))
        assert result["ok"]
        assert any("ODT-4" in h and "目标达成" in h for h in result["hints"])

    def test_convergence_acceleration_hint(self, tmp_path: Path):
        """ODT-3: 最近步长优于全序列均值 → 收敛加速提示。

        数据设计: 末步 0.115→0.02 = -0.095, 全序列均值 (0.02-0.3392)/4 = -0.0798,
        -0.095 < -0.0798 = 加速(负得更凶)。
        """
        p = _mk(
            tmp_path,
            [
                ("a", 0.3392, False),
                ("b", 0.2094, False),
                ("c", 0.1327, False),
                ("d", 0.1150, False),
                ("e", 0.02, False),
            ],
        )
        result = check(load_points(p))
        assert result["ok"]
        assert any("收敛加速" in h for h in result["hints"])

    def test_corrupt_file_honest_fail(self, tmp_path: Path, capsys):
        """坏行 JSON → 诚实失败 rc=1。"""
        import check_overdefense_trend as mod

        p = tmp_path / "bad.jsonl"
        p.write_text("not json\n", encoding="utf-8")
        orig = mod.HISTORY
        mod.HISTORY = p
        try:
            rc = main()
        finally:
            mod.HISTORY = orig
        assert rc == 1
        assert "损坏" in capsys.readouterr().out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
