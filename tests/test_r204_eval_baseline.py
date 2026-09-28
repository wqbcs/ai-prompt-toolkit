"""R204: 评估基线 save/compare + 维度级drift检测 e2e"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.eval_baseline import (
    EvalBaselineSnapshot,
    compare_eval_baseline,
    load_eval_baseline,
    save_eval_baseline,
)
from ai_prompt_toolkit.evaluator import DimensionScore, EvaluationReport

_CLEAN = "version: 1.0.0\n# 角色\n你是测试工程师。\n# 任务\n编写用例。\n# 约束\n保持简洁。\n"


def _report(tid: str, dim_scores: dict[str, float], overall: float) -> EvaluationReport:
    scores = [
        DimensionScore(
            dimension_id=d,
            name=f"dim_{d}",
            category="structure",
            weight=1.0,
            score=s,
            max_score=10.0,
        )
        for d, s in dim_scores.items()
    ]
    return EvaluationReport(
        template_id=tid,
        scores=scores,
        overall_score=overall,
        max_possible_score=100.0,
        percentage=overall * 10,
        category_scores={"structure": overall},
        dimension_count=len(scores),
    )


def _run(*args):
    return CliRunner().invoke(main, list(args))


def _eval(*args):
    return _run("evaluate", *args)


class TestEvalBaselineModule:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        rep = _report("t1", {"D01": 8.0, "D02": 6.0}, 7.0)
        p = tmp_path / "b.json"
        snap = save_eval_baseline([rep], p, template_id="t1")
        assert p.exists()
        loaded = load_eval_baseline(p)
        assert loaded.overall_score == 7.0
        assert loaded.dimension_scores == {"D01": 8.0, "D02": 6.0}
        assert loaded.preset == "default"

    def test_compare_no_drift(self):
        base = EvalBaselineSnapshot(
            created_at="x",
            template_id="t1",
            overall_score=7.0,
            percentage=70.0,
            category_scores={"structure": 7.0},
            dimension_scores={"D01": 8.0, "D02": 6.0},
        )
        cur = _report("t1", {"D01": 8.1, "D02": 5.9}, 7.05)
        diff = compare_eval_baseline([cur], base, drift_threshold=1.5)
        assert not diff.drifted_dimensions
        assert diff.stable_dimensions == 2
        assert not diff.is_regression

    def test_compare_drift_down_and_up(self):
        base = EvalBaselineSnapshot(
            created_at="x",
            template_id="t1",
            overall_score=7.0,
            percentage=70.0,
            category_scores={"structure": 7.0},
            dimension_scores={"D01": 8.0, "D02": 6.0, "D03": 5.0},
        )
        # D01跌3分(drift), D02涨2.5分(drift), D03跌2.5分(drift)
        cur = _report("t1", {"D01": 5.0, "D02": 8.5, "D03": 2.5}, 5.33)
        diff = compare_eval_baseline([cur], base, drift_threshold=1.5)
        assert set(diff.drifted_dimensions) == {"D01", "D02", "D03"}
        assert diff.drifted_dimensions["D01"]["direction"] == "down"
        assert diff.drifted_dimensions["D02"]["direction"] == "up"
        assert diff.drifted_dimensions["D03"]["direction"] == "down"

    def test_compare_regression_exit_signal(self):
        base = EvalBaselineSnapshot(
            created_at="x",
            template_id="t1",
            overall_score=8.0,
            percentage=80.0,
            category_scores={"structure": 8.0},
            dimension_scores={"D01": 8.0},
        )
        cur = _report("t1", {"D01": 6.0}, 6.0)
        diff = compare_eval_baseline([cur], base, drift_threshold=1.5, overall_threshold=2.0)
        assert diff.is_regression
        assert diff.overall_delta == -2.0

    def test_multi_file_average(self, tmp_path: Path):
        r1 = _report("a", {"D01": 6.0}, 6.0)
        r2 = _report("b", {"D01": 8.0}, 8.0)
        p = tmp_path / "b.json"
        save_eval_baseline([r1, r2], p)
        loaded = load_eval_baseline(p)
        assert loaded.overall_score == 7.0
        assert loaded.dimension_scores["D01"] == 7.0


class TestEvalBaselineCLI:
    def test_baseline_save_cli(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "p.md").write_text(_CLEAN, encoding="utf-8")
        result = _eval("-t", "p.md", "--quick", "--baseline-save")
        assert result.exit_code in (0, 1), result.output[-300:]
        assert "评估基线已保存" in result.output
        snap = json.loads((tmp_path / ".eval-baseline.json").read_text(encoding="utf-8"))
        assert snap["preset"] == "default"
        assert len(snap["dimension_scores"]) >= 10  # quick模式D01-D10

    def test_baseline_compare_cli_same(self, tmp_path: Path, monkeypatch):
        """同prompt两次评估: 无drift(确定性评估器)"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "p.md").write_text(_CLEAN, encoding="utf-8")
        r1 = _eval("-t", "p.md", "--quick", "--baseline-save")
        assert r1.exit_code in (0, 1)
        r2 = _eval("-t", "p.md", "--quick", "--baseline", ".eval-baseline.json")
        assert r2.exit_code in (0, 1), r2.output[-300:]
        assert "评估基线对比" in r2.output
        assert "无drift维度" in r2.output
        assert "整体回归" not in r2.output

    def test_baseline_compare_cli_regression(self, tmp_path: Path, monkeypatch):
        """人为改高基线 → 当前评估相对基线触发回归"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "p.md").write_text(_CLEAN, encoding="utf-8")
        r1 = _eval("-t", "p.md", "--quick", "--baseline-save")
        assert r1.exit_code in (0, 1)
        # 把基线整体分抬高10分 → 当前评估相对回归
        bp = tmp_path / ".eval-baseline.json"
        snap = json.loads(bp.read_text(encoding="utf-8"))
        snap["overall_score"] = min(100.0, snap["overall_score"] + 10)
        for k in snap["dimension_scores"]:
            snap["dimension_scores"][k] = min(10.0, snap["dimension_scores"][k] + 3)
        bp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        r2 = _eval("-t", "p.md", "--quick", "--baseline", ".eval-baseline.json")
        assert r2.exit_code in (0, 1, 2, 3)
        assert "评估基线对比" in r2.output
        assert "整体回归" in r2.output
        assert "▼" in r2.output  # 有维度下跌drift

    def test_baseline_missing_file_exit3(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "p.md").write_text(_CLEAN, encoding="utf-8")
        result = _eval("-t", "p.md", "--quick", "--baseline", "nope.json")
        assert result.exit_code == 3
