"""R340-E1: 已知漏检台账（Known Misses Ledger）一致性测试（可信度楔子的机器护栏）

对抗性审查点：台账是"可机器验证的诚实边界"——每个数字必须与
measure_ood_recall 单一真源的当前实测一致（防口径漂移=板漂移同族静态面）。
本测试锁：
1. --check 与当前实测一致（确定性：同数据→同字节，gen_operating_curve --check 同形态）
2. 台账数字与单一真源一致（防手改/陈旧）
3. 数据面自洽（caught+misses==注入总数；索引唯一在域）
4. 红态：篡改/缺失必红（台账防漂移断言本身有效=护栏不空转）
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "scripts" / "gen_known_misses.py"
MEASURE = ROOT / "scripts" / "measure_ood_recall.py"
DOC = ROOT / "docs" / "known_misses.md"


def _gen_check() -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(GEN), "--check"], cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


@pytest.fixture(scope="module")
def ood() -> dict:
    proc = subprocess.run([sys.executable, str(MEASURE), "--json"], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


class TestKnownMissesLedger:
    def test_check_passes(self, ood: dict) -> None:
        """ "--check" 断言与当前实测一致（确定性：同数据→同字节）。"""
        rc, out = _gen_check()
        assert rc == 0 and "✓" in out and "✗" not in out, out

    def test_doc_numbers_match_source(self, ood: dict) -> None:
        """台账数字 = 单一真源当前值（防手改/陈旧）。"""
        doc = DOC.read_text(encoding="utf-8")
        n = ood["injection_count"]
        miss_n = n - ood["caught_count"]
        assert f"{ood['caught_count']}/{n}" in doc, "召回分式与真源不一致"
        assert f"{ood['ood_recall'] * 100:.2f}%" in doc, "召回百分比与真源不一致"
        assert f"| 漏检（已知抓不到） | {miss_n} 条 |" in doc, "漏检计数与真源不一致"
        assert f"| 安全族规则数 | {ood['security_rule_count']}" in doc, "安全族规则数与真源不一致"

    def test_source_numbers_consistent(self, ood: dict) -> None:
        """数据面自洽：caught + misses == 注入总数；召回=caught/总数（同口径）。"""
        n = ood["injection_count"]
        assert ood["caught_count"] + len(ood["misses"]) == n, "caught+misses ≠ 注入总数"
        assert 0.0 <= ood["ood_recall"] <= 1.0
        assert ood["ood_recall"] == round(ood["caught_count"] / n, 4), "召回口径漂移"
        assert n == 263, "deepset 注入面分母变更（数据集形态变化, 需重审口径）"

    def test_miss_indexes_valid_and_unique(self, ood: dict) -> None:
        """漏检索引：唯一、在域、摘录有界（渲染安全前提）。"""
        indexes = [m["index"] for m in ood["misses"]]
        assert len(indexes) == len(set(indexes)), "漏检索引重复"
        assert all(0 <= i < ood["injection_count"] for i in indexes), "漏检索引越界"
        assert all(len(m["excerpt"]) <= 80 for m in ood["misses"]), "摘录超界"

    def test_doc_lists_miss_samples(self, ood: dict) -> None:
        """台账样例清单覆盖前几条漏检（确定性文件行序）。"""
        doc = DOC.read_text(encoding="utf-8")
        for m in ood["misses"][:5]:
            assert f"`deepset_{m['index']}`" in doc, f"样例缺失: deepset_{m['index']}"

    def test_check_red_on_tamper(self) -> None:
        """红态：手改台账必红（防漂移断言本身有效, 护栏不空转）。"""
        original = DOC.read_text(encoding="utf-8")
        try:
            DOC.write_text(original + "\n<!-- tamper -->\n", encoding="utf-8")
            rc, out = _gen_check()
            assert rc == 1 and "✗" in out, f"篡改未红: rc={rc} out={out}"
        finally:
            DOC.write_text(original, encoding="utf-8")

    def test_check_red_on_missing(self) -> None:
        """红态：台账缺失必红（响亮失败, 非静默绿）。"""
        backup = DOC.with_suffix(".md.bak")
        try:
            DOC.rename(backup)
            rc, out = _gen_check()
            assert rc == 1 and "✗" in out, f"缺失未红: rc={rc} out={out}"
        finally:
            backup.rename(DOC)
