"""R22 评估结果持久化测试 — EvalStore + 回归检测 + 趋势 + A/B对比"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_prompt_toolkit.evaluator import evaluate_template, DimensionScore, EvaluationReport
from ai_prompt_toolkit.eval_store import EvalStore, EvalSnapshot, RegressionAlert, TrendPoint


@pytest.fixture
def store(tmp_path):
    s = EvalStore(db_path=tmp_path / "test_eval.db")
    yield s
    s.close()


def _make_report(template_id: str = "test", overall: float = 7.5, **kwargs) -> EvaluationReport:
    scores = [
        DimensionScore(dimension_id="D01", name="角色清晰度", category="structure", weight=1.0, score=8.0),
        DimensionScore(dimension_id="D02", name="目标明确性", category="structure", weight=1.0, score=7.0),
        DimensionScore(dimension_id="D11", name="注入防御", category="security", weight=1.0, score=9.0),
    ]
    return EvaluationReport(
        template_id=template_id,
        scores=scores,
        overall_score=overall,
        max_possible_score=30.0,
        percentage=overall / 30.0 * 100,
        category_scores={"structure": 7.5, "security": 9.0},
        evaluation_time_ms=42.0,
        dimension_count=3,
    )


class TestEvalStoreSave:
    def test_save_creates_snapshot(self, store):
        report = _make_report()
        snapshot = store.save(report)
        assert snapshot.snapshot_id > 0
        assert snapshot.template_id == "test"
        assert snapshot.overall_score == 7.5
        assert snapshot.dimension_count == 3

    def test_save_multiple_snapshots(self, store):
        for i in range(5):
            store.save(_make_report(overall=5.0 + i))
        snapshots = store.get_snapshots("test", limit=10)
        assert len(snapshots) == 5

    def test_dimension_scores_stored(self, store):
        report = _make_report()
        snapshot = store.save(report)
        assert "D01" in snapshot.dimension_scores
        assert snapshot.dimension_scores["D01"] == 8.0


class TestEvalStoreTrend:
    def test_trend_returns_points(self, store):
        for i in range(3):
            store.save(_make_report(overall=5.0 + i * 0.5))
        trend = store.get_trend("test")
        assert len(trend) == 3
        assert trend[0].overall_score < trend[-1].overall_score

    def test_trend_respects_limit(self, store):
        for i in range(20):
            store.save(_make_report(overall=5.0 + i * 0.1))
        trend = store.get_trend("test", limit=5)
        assert len(trend) == 5


class TestEvalStoreRegression:
    def test_regression_detected(self, store):
        report_good = _make_report(overall=9.0)
        for s in report_good.scores:
            s.score = 9.0
        store.save(report_good)

        report_bad = _make_report(overall=4.0)
        for s in report_bad.scores:
            s.score = 4.0
        store.save(report_bad)

        alerts = store.get_alerts(template_id="test")
        assert len(alerts) > 0
        assert all(a.change_percent < 0 for a in alerts)

    def test_no_regression_when_improved(self, store):
        report1 = _make_report(overall=5.0)
        for s in report1.scores:
            s.score = 5.0
        store.save(report1)

        report2 = _make_report(overall=9.0)
        for s in report2.scores:
            s.score = 9.0
        store.save(report2)

        alerts = store.get_alerts(template_id="test")
        assert len(alerts) == 0


class TestEvalStoreCompare:
    def test_compare_two_snapshots(self, store):
        report1 = _make_report(overall=6.0)
        for s in report1.scores:
            s.score = 6.0
        snap1 = store.save(report1)

        report2 = _make_report(overall=8.0)
        for s in report2.scores:
            s.score = 8.0
        snap2 = store.save(report2)

        result = store.compare(snap1.snapshot_id, snap2.snapshot_id)
        assert "dimension_diffs" in result
        assert result["overall_diff"] > 0

    def test_compare_nonexistent_snapshot(self, store):
        result = store.compare(999, 1000)
        assert "error" in result


class TestEvalStoreCLI:
    def test_eval_history_command(self):
        from click.testing import CliRunner
        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["eval-history", "--help"])
        assert result.exit_code == 0
        assert "评估历史" in result.output

    def test_eval_compare_command(self):
        from click.testing import CliRunner
        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["eval-compare", "--help"])
        assert result.exit_code == 0
        assert "评估对比" in result.output

    def test_evaluate_save_flag(self):
        from click.testing import CliRunner
        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write("---\ntemplate_type: prompt\n---\n你是一个AI助手，请帮我完成任务。")
            f.flush()
            result = runner.invoke(main, ["evaluate", "-t", f.name, "--save", "--quick"])
            assert result.exit_code == 0
