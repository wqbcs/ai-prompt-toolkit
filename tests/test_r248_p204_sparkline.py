"""R248-P2-04: 双基线 sparkline 生成器测试（确定性 SVG）

楔子延伸至资产面：同一 jsonl 输入 → 同一 SVG 逐字节（无时间戳/时钟/随机）。
n/a 态纪律（ci-streak 同族）：有效点 <2 → 灰化占位，不画假曲线。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gen_baseline_sparkline as gbs  # noqa: E402


@pytest.fixture
def real_history() -> str:
    return (ROOT / "docs" / "baseline_history.jsonl").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolate_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, real_history: str):
    """把 HISTORY/OUTPUT 指向 tmp（不碰真实 jsonl/README 资产）。"""
    hist = tmp_path / "baseline_history.jsonl"
    hist.write_text(real_history, encoding="utf-8")
    out = tmp_path / "baseline-trend.svg"
    monkeypatch.setattr(gbs, "HISTORY", hist)
    monkeypatch.setattr(gbs, "OUTPUT", out)
    yield


class TestDeterminism:
    def test_same_input_same_bytes(self):
        """核心楔子：同 jsonl → 同 SVG 逐字节（无时钟/随机）。"""
        a = gbs.generate()
        b = gbs.generate()
        assert a == b

    def test_svg_has_no_timestamp(self):
        """确定性护栏：SVG 内无时间戳形态字节（2026- 日期串/epoch）。"""
        svg = gbs.generate()
        assert "2026-" not in svg
        assert "generated" not in svg.lower()

    def test_idempotent_file_write(self, monkeypatch: pytest.MonkeyPatch):
        """幂等：生成两次文件内容不变。"""
        monkeypatch.setattr(sys, "argv", ["gen_baseline_sparkline.py"])
        assert gbs.main() == 0
        first = gbs.OUTPUT.read_text(encoding="utf-8")
        assert gbs.main() == 0
        assert gbs.OUTPUT.read_text(encoding="utf-8") == first


class TestStructure:
    def test_svg_structure(self):
        svg = gbs.generate()
        assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
        assert "<polyline" in svg
        # 头部注释含数据源路径与点数（可审计）
        assert "docs/baseline_history.jsonl" in svg
        assert "fp_points:" in svg

    def test_fp_series_skips_null(self):
        """fp_rate null 记录被跳过（数据面契约）。"""
        assert len(gbs.load_fp_series(gbs.HISTORY)) >= 2

    def test_miss_rate_line_present(self):
        """miss_rate 底线恒在（全 0 也画 0 线=不漏检史可见）。"""
        svg = gbs.generate()
        assert svg.count("<polyline") == 2  # fp 主折线 + miss 底线

    def test_fixed_scale_labels(self):
        """固定刻度 0/5/10%（防曲线"看起来平"视觉欺骗）。"""
        svg = gbs.generate()
        assert "10%" in svg and "5%" in svg and "0%" in svg


class TestNAState:
    def test_na_with_few_points(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """<2 点 → n/a 灰化占位，不画假曲线。"""
        hist = tmp_path / "one.jsonl"
        hist.write_text(json.dumps({"ts": None, "version": "1.0", "fp_rate": 0.05}) + "\n", encoding="utf-8")
        monkeypatch.setattr(gbs, "HISTORY", hist)
        svg = gbs.generate()
        assert "n/a" in svg
        assert "<polyline" not in svg

    def test_check_detects_stale(self, monkeypatch: pytest.MonkeyPatch):
        """--check：SVG 与数据不一致 → rc=1（门禁红态）；一致 → rc=0。"""
        monkeypatch.setattr(sys, "argv", ["gen_baseline_sparkline.py", "--check"])
        # 陈旧 SVG → 红
        gbs.OUTPUT.write_text("<svg stale></svg>", encoding="utf-8")
        assert gbs.main() == 1
        # 缺失 → 红
        gbs.OUTPUT.unlink()
        assert gbs.main() == 1
        # 重新生成 → check 转绿
        monkeypatch.setattr(sys, "argv", ["gen_baseline_sparkline.py"])
        assert gbs.main() == 0
        monkeypatch.setattr(sys, "argv", ["gen_baseline_sparkline.py", "--check"])
        assert gbs.main() == 0
