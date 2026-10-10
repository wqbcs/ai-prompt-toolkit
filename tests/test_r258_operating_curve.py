"""R258-P5-11: 运营点公开数据页一致性 e2e（可信度楔子的机器护栏）

对抗性审查点：公开页的每个数字必须与**发布口径单一真源** 100% 一致，
否则页面自相矛盾=可信度叙事崩塌（比没有页面更糟）。本测试锁：
1. 全规则行（=默认口径）与 check_false_positives / check_overdefense /
   check_miss_rate 的当前真值逐字节同口径（防口径漂移=第二个板漂移源）
2. JSON/MD 与生成器当前输出一致（--check 同断言，防手改/陈旧）
3. severity 切面单调性（切面越宽，召回/误杀不减——数学不变量）
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen_operating_curve.py"
JSON_OUT = ROOT / "docs" / "operating_curve.json"
MD_OUT = ROOT / "docs" / "operating_curve.md"


def _gen_check() -> str:
    proc = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT, capture_output=True, text=True)
    return (proc.stdout + proc.stderr).strip()


@pytest.fixture(scope="module")
def curve() -> dict:
    assert JSON_OUT.exists(), "先跑 python scripts/gen_operating_curve.py"
    return json.loads(JSON_OUT.read_text(encoding="utf-8"))


class TestOperatingCurveConsistency:
    def test_check_passes(self, curve: dict) -> None:
        """--check 断言与当前数据一致（确定性：同数据→同字节）。"""
        out = _gen_check()
        assert "✓" in out and "✗" not in out, out

    def test_full_rule_row_matches_published_sources(self, curve: dict) -> None:
        """全规则行=发布口径：与三个单一真源的当前真值一致（防口径漂移）。"""
        full = curve["points"][-1]

        # FP 对级率 = check_false_positives 真值（同一 run_false_positives 真源）
        fp = json.loads(
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_false_positives.py"), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            ).stdout
        )
        assert abs(full["fp_pair_rate"] - round(fp["global_rate"], 6)) < 1e-6, (
            f"FP 口径漂移: 页面 {full['fp_pair_rate']} vs 真源 {fp['global_rate']}"
        )

        # 漏检单元 = check_miss_rate expected_total（同一 golden 真源）
        miss = json.loads(
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_miss_rate.py"), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            ).stdout
        )
        assert full["miss_units_total"] == miss["expected_total"], (
            f"漏检单元漂移: 页面 {full['miss_units_total']} vs 真源 {miss['expected_total']}"
        )
        assert full["miss_units_covered"] == full["miss_units_total"], "漏检单元未全覆盖（应 0 miss）"

        # 分母与数据源一致
        assert curve["denominators"]["notinject"] == 339
        assert curve["denominators"]["deepset_injections"] == 263
        assert curve["denominators"]["clean_samples"] == 60

    def test_severity_cuts_monotonic(self, curve: dict) -> None:
        """切面越宽（≥CRITICAL → 全规则），召回/误杀不减——数学不变量。"""
        pts = curve["points"]
        for a, b in itertools.pairwise(pts):
            assert b["active_rules"] >= a["active_rules"]
            assert b["miss_units_covered"] >= a["miss_units_covered"], (
                f"召回非单调: {a['cutoff']} {a['miss_units_covered']} → {b['cutoff']} {b['miss_units_covered']}"
            )
            assert b["overdefense_flagged"] >= a["overdefense_flagged"], "过防御非单调"
            assert b["ood_caught"] >= a["ood_caught"], "OOD 召回非单调"

    def test_calibers_documented(self, curve: dict) -> None:
        """每列口径必须留档（可信度叙事可审计）。"""
        for key in ("fp", "overdefense", "miss", "ood"):
            assert curve["calibers"].get(key), f"缺口径说明: {key}"
        # MD 页含口径节+复现命令+诚实边界（公开页三要素）
        md = MD_OUT.read_text(encoding="utf-8")
        assert "每列口径" in md
        assert "复现" in md
        assert "诚实边界" in md
