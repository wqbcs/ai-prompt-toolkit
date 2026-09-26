"""性能基准+评估降频+模板推荐测试 — P2-04/P2-05/P2-06"""

from __future__ import annotations

from ai_prompt_toolkit.benchmark import (
    BenchmarkDB,
    BenchmarkResult,
    run_benchmark,
    run_full_benchmark,
)
from ai_prompt_toolkit.eval_frequency import (
    EvalFrequencyConfig,
    EvalFrequencyManager,
)
from ai_prompt_toolkit.template_recommender import (
    _BUILTIN_TEMPLATES,
    TemplateRecommendation,
    TemplateRecommender,
)


class TestBenchmarkResult:
    def test_to_dict(self):
        r = BenchmarkResult(case_id="test", name="Test", operation="lint", duration_ms=42.5)
        d = r.to_dict()
        assert d["case_id"] == "test"
        assert d["duration_ms"] == 42.5

    def test_auto_timestamp(self):
        r = BenchmarkResult(case_id="t", name="t", operation="lint", duration_ms=1.0)
        assert r.timestamp != ""


class TestBenchmarkDB:
    def test_save_and_get(self, tmp_path):
        db = BenchmarkDB(tmp_path / "bench.db")
        r = BenchmarkResult(case_id="lint_small", name="Lint", operation="lint", duration_ms=10.0)
        db.save(r)
        baseline = db.get_baseline("lint_small")
        assert baseline is not None
        assert baseline.duration_ms == 10.0

    def test_no_baseline(self, tmp_path):
        db = BenchmarkDB(tmp_path / "bench.db")
        assert db.get_baseline("nonexistent") is None

    def test_regression_detection(self, tmp_path):
        db = BenchmarkDB(tmp_path / "bench.db")
        db.save(BenchmarkResult(case_id="test", name="T", operation="lint", duration_ms=10.0))
        db.save(BenchmarkResult(case_id="test", name="T", operation="lint", duration_ms=25.0))
        alert = db.check_regression("test", threshold_pct=20.0)
        assert alert is not None
        assert alert.regression_pct > 100

    def test_no_regression(self, tmp_path):
        db = BenchmarkDB(tmp_path / "bench.db")
        db.save(BenchmarkResult(case_id="test", name="T", operation="lint", duration_ms=10.0))
        db.save(BenchmarkResult(case_id="test", name="T", operation="lint", duration_ms=11.0))
        alert = db.check_regression("test", threshold_pct=20.0)
        assert alert is None

    def test_get_history(self, tmp_path):
        db = BenchmarkDB(tmp_path / "bench.db")
        for i in range(5):
            db.save(BenchmarkResult(case_id="test", name="T", operation="lint", duration_ms=float(i)))
        history = db.get_history("test", limit=3)
        assert len(history) == 3


class TestRunBenchmark:
    def test_run_all(self):
        results = run_benchmark()
        assert len(results) > 0
        for r in results:
            assert r.duration_ms >= 0

    def test_run_specific_case(self):
        results = run_benchmark("lint_small")
        assert len(results) == 1
        assert results[0].case_id == "lint_small"

    def test_run_full_with_db(self, tmp_path):
        report = run_full_benchmark(db_path=tmp_path / "bench.db")
        assert "results" in report
        assert "regression_alerts" in report
        assert "summary" in report
        assert report["summary"]["total_cases"] > 0


class TestEvalFrequency:
    def test_should_eval_new_template(self, tmp_path):
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db")
        decision = mgr.should_evaluate("new_template", "hello world")
        assert decision.should_eval is True
        assert "需要评估" in decision.reason

    def test_should_eval_content_change(self, tmp_path):
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db")
        mgr.record_eval("t1", "old content", 9.0)
        decision = mgr.should_evaluate("t1", "new content")
        assert decision.should_eval is True
        assert "变更" in decision.reason

    def test_should_skip_stable(self, tmp_path):
        config = EvalFrequencyConfig(stable_threshold=8.0, stable_runs_required=3)
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db", config=config)
        content = "stable content"
        for _ in range(4):
            mgr.record_eval("t1", content, 9.0)
        decision = mgr.should_evaluate("t1", content)
        assert decision.should_eval is False
        assert "稳定" in decision.reason

    def test_budget_control(self, tmp_path):
        config = EvalFrequencyConfig(daily_budget=0.001)
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db", config=config)
        mgr.record_eval("t1", "content", 8.0, cost=0.01)
        decision = mgr.should_evaluate("t1", "new content", estimated_cost=0.01)
        assert decision.should_eval is False
        assert "预算" in decision.reason

    def test_budget_status(self, tmp_path):
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db")
        status = mgr.get_budget_status()
        assert "daily_budget" in status
        assert "daily_spent" in status

    def test_stable_templates(self, tmp_path):
        config = EvalFrequencyConfig(stable_threshold=8.0, stable_runs_required=3)
        mgr = EvalFrequencyManager(db_path=tmp_path / "freq.db", config=config)
        for _ in range(3):
            mgr.record_eval("stable_t", "content", 9.0)
        mgr.record_eval("unstable_t", "content", 5.0)
        stable = mgr.get_stable_templates()
        assert any(t["template_id"] == "stable_t" for t in stable)


class TestTemplateRecommender:
    def test_recommend_default(self):
        rec = TemplateRecommender()
        results = rec.recommend()
        assert len(results) == 5
        assert results[0].relevance_score > 0

    def test_recommend_by_category(self):
        rec = TemplateRecommender()
        results = rec.recommend(category="development")
        assert len(results) > 0
        dev_results = [r for r in results if "场景匹配" in r.reason]
        assert len(dev_results) > 0

    def test_recommend_by_industry(self):
        rec = TemplateRecommender()
        results = (
            rec.recommender.recommend(industry="华为云")
            if hasattr(rec, "recommender")
            else rec.recommend(industry="华为云")
        )
        assert len(results) > 0

    def test_recommend_by_model(self):
        rec = TemplateRecommender()
        results = rec.recommend(model="qwen")
        assert len(results) > 0
        qwen_results = [r for r in results if "模型适配" in r.reason]
        assert len(qwen_results) > 0

    def test_recommend_top_n(self):
        rec = TemplateRecommender()
        results = rec.recommend(top_n=3)
        assert len(results) == 3

    def test_get_categories(self):
        rec = TemplateRecommender()
        cats = rec.get_categories()
        assert len(cats) > 0
        assert "general" in cats

    def test_get_industries(self):
        rec = TemplateRecommender()
        ind = rec.get_industries()
        assert len(ind) > 0

    def test_get_template(self):
        rec = TemplateRecommender()
        t = rec.get_template("general-assistant")
        assert t is not None
        assert t.name == "通用助手"

    def test_get_nonexistent(self):
        rec = TemplateRecommender()
        t = rec.get_template("nonexistent")
        assert t is None

    def test_builtin_templates_count(self):
        assert len(_BUILTIN_TEMPLATES) >= 15

    def test_recommendation_to_dict(self):
        t = TemplateRecommendation("test", "Test", "cat", "ind", ["gpt-4"], 90.0, 4.5, 100, 85.0, "reason")
        d = t.to_dict()
        assert d["template_id"] == "test"
        assert d["relevance_score"] == 85.0
