"""GEPA反射式Prompt进化引擎 + Feedback Metric体系 + Prompt版本管理 测试套件"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_prompt_toolkit.gepa import (
    FEEDBACK_METRICS,
    Candidate,
    FeedbackMetric,
    GEPAEvaluator,
    GEPAOptimizer,
    GEPAResult,
    MergeStrategy,
    ParetoFrontier,
    ReflectiveProposer,
    RoundRobinSelector,
    ScoreWithFeedback,
    Trace,
    gepa_optimize,
)
from ai_prompt_toolkit.prompt_version import (
    ABCompareResult,
    PromptVersionStore,
    VersionDiff,
)

# ═══════════════════════════════════════
# ScoreWithFeedback 测试
# ═══════════════════════════════════════


class TestScoreWithFeedback:
    def test_basic_creation(self):
        swf = ScoreWithFeedback(score=0.85, feedback="Good but incomplete")
        assert swf.score == 0.85
        assert swf.feedback == "Good but incomplete"

    def test_no_feedback(self):
        swf = ScoreWithFeedback(score=1.0)
        assert swf.score == 1.0
        assert swf.feedback is None

    def test_to_dict(self):
        swf = ScoreWithFeedback(score=0.5, feedback="test")
        d = swf.to_dict()
        assert d["score"] == 0.5
        assert d["feedback"] == "test"


# ═══════════════════════════════════════
# Trace 测试
# ═══════════════════════════════════════


class TestTrace:
    def test_basic_creation(self):
        t = Trace(
            predictor_name="main",
            instruction="Answer the question",
            inputs={"q": "test"},
            outputs={"a": "response"},
            score=0.8,
            feedback="Partially correct",
        )
        assert t.predictor_name == "main"
        assert t.score == 0.8
        assert t.feedback == "Partially correct"

    def test_to_dict_truncation(self):
        long_instruction = "x" * 300
        t = Trace(predictor_name="main", instruction=long_instruction, inputs={}, outputs={})
        d = t.to_dict()
        assert "..." in d["instruction"]
        assert len(d["instruction"]) < len(long_instruction)


# ═══════════════════════════════════════
# Candidate 测试
# ═══════════════════════════════════════


class TestCandidate:
    def test_basic_creation(self):
        c = Candidate(id=1, instructions={"main": "test prompt"})
        assert c.id == 1
        assert c.parent_id is None
        assert c.generation == 0
        assert c.aggregate_score == 0.0

    def test_to_dict(self):
        c = Candidate(
            id=2,
            instructions={"main": "test"},
            parent_id=1,
            per_example_scores={0: 0.8, 1: 0.9},
            aggregate_score=0.85,
            generation=2,
        )
        d = c.to_dict()
        assert d["id"] == 2
        assert d["parent_id"] == 1
        assert d["generation"] == 2
        assert d["aggregate_score"] == 0.85


# ═══════════════════════════════════════
# ReflectiveProposer 测试
# ═══════════════════════════════════════


class TestReflectiveProposer:
    def test_heuristic_propose_no_lm(self):
        proposer = ReflectiveProposer()
        traces = [
            Trace(
                predictor_name="main",
                instruction="test",
                inputs={"q": "hello"},
                outputs={"a": "hi"},
                score=0.3,
                feedback="Output quality is critically low",
            )
        ]
        result = proposer.propose("Answer the question", traces, "main")
        assert "Answer the question" in result
        assert len(result) > len("Answer the question")

    def test_heuristic_propose_with_missing_feedback(self):
        proposer = ReflectiveProposer()
        traces = [
            Trace(
                predictor_name="main",
                instruction="test",
                inputs={"q": "hello"},
                outputs={"a": "hi"},
                score=0.5,
                feedback="missing required content",
            )
        ]
        result = proposer.propose("Answer the question", traces, "main")
        assert len(result) > len("Answer the question")

    def test_reflection_lm_propose(self):
        mock_lm = MagicMock(return_value="Improved instruction: Be specific and concise.")
        proposer = ReflectiveProposer(reflection_lm=mock_lm)
        traces = [
            Trace(
                predictor_name="main",
                instruction="test",
                inputs={"q": "hello"},
                outputs={"a": "hi"},
                score=0.3,
                feedback="Too vague",
            )
        ]
        result = proposer.propose("Answer the question", traces, "main")
        assert "Improved" in result
        mock_lm.assert_called_once()

    def test_reflection_lm_fallback_on_error(self):
        mock_lm = MagicMock(side_effect=RuntimeError("LM unavailable"))
        proposer = ReflectiveProposer(reflection_lm=mock_lm)
        traces = [
            Trace(
                predictor_name="main",
                instruction="test",
                inputs={},
                outputs={},
                score=0.3,
                feedback="Low quality",
            )
        ]
        result = proposer.propose("Original", traces, "main")
        assert "Original" in result

    def test_reflection_lm_returns_empty(self):
        mock_lm = MagicMock(return_value="")
        proposer = ReflectiveProposer(reflection_lm=mock_lm)
        traces = [
            Trace(
                predictor_name="main",
                instruction="test",
                inputs={},
                outputs={},
                score=0.3,
                feedback="Low",
            )
        ]
        result = proposer.propose("Original", traces, "main")
        assert result == "Original"


# ═══════════════════════════════════════
# ParetoFrontier 测试
# ═══════════════════════════════════════


class TestParetoFrontier:
    def test_empty_frontier(self):
        frontier = ParetoFrontier()
        assert frontier.frontier_size == 0
        assert frontier.best_candidate() is None

    def test_single_candidate(self):
        frontier = ParetoFrontier()
        c = Candidate(id=0, instructions={"main": "test"}, per_example_scores={0: 0.8}, aggregate_score=0.8)
        frontier.update(c)
        assert frontier.frontier_size == 1
        assert frontier.best_candidate().aggregate_score == 0.8

    def test_pareto_update_replaces_lower_score(self):
        frontier = ParetoFrontier()
        c1 = Candidate(id=0, instructions={"main": "a"}, per_example_scores={0: 0.5}, aggregate_score=0.5)
        c2 = Candidate(id=1, instructions={"main": "b"}, per_example_scores={0: 0.9}, aggregate_score=0.9)
        frontier.update(c1)
        frontier.update(c2)
        assert frontier.best_candidate().aggregate_score == 0.9

    def test_pareto_keeps_both_on_different_examples(self):
        frontier = ParetoFrontier()
        c1 = Candidate(id=0, instructions={"main": "a"}, per_example_scores={0: 0.9, 1: 0.3}, aggregate_score=0.6)
        c2 = Candidate(id=1, instructions={"main": "b"}, per_example_scores={0: 0.3, 1: 0.9}, aggregate_score=0.6)
        frontier.update(c1)
        frontier.update(c2)
        assert frontier.frontier_size == 2

    def test_sample_parent(self):
        import random

        frontier = ParetoFrontier()
        c1 = Candidate(id=0, instructions={"main": "a"}, per_example_scores={0: 0.8}, aggregate_score=0.8)
        frontier.update(c1)
        rng = random.Random(42)
        parent = frontier.sample_parent(rng)
        assert parent is not None
        assert parent.id == 0


# ═══════════════════════════════════════
# MergeStrategy 测试
# ═══════════════════════════════════════


class TestMergeStrategy:
    def test_merge_prefers_higher_scoring(self):
        merger = MergeStrategy()
        a = Candidate(
            id=0,
            instructions={"main": "prompt A", "helper": "help A"},
            per_example_scores={0: 0.9, 1: 0.3},
            aggregate_score=0.6,
        )
        b = Candidate(
            id=1,
            instructions={"main": "prompt B", "helper": "help B"},
            per_example_scores={0: 0.3, 1: 0.9},
            aggregate_score=0.6,
        )
        merged = merger.merge(a, b, ["main", "helper"])
        assert "main" in merged
        assert "helper" in merged


# ═══════════════════════════════════════
# RoundRobinSelector 测试
# ═══════════════════════════════════════


class TestRoundRobinSelector:
    def test_round_robin(self):
        selector = RoundRobinSelector(["a", "b", "c"])
        assert selector.select() == "a"
        assert selector.select() == "b"
        assert selector.select() == "c"
        assert selector.select() == "a"

    def test_single_predictor(self):
        selector = RoundRobinSelector(["main"])
        assert selector.select() == "main"
        assert selector.select() == "main"


# ═══════════════════════════════════════
# GEPAOptimizer 测试
# ═══════════════════════════════════════


class TestGEPAOptimizer:
    @pytest.fixture
    def simple_metric(self):
        def metric(gold, pred, pred_name=None, pred_trace=None):
            answer = pred.get("answer", "")
            expected = gold.get("expected", "")
            if expected and expected in answer:
                return ScoreWithFeedback(score=1.0, feedback=None)
            if "professional" in answer.lower():
                return ScoreWithFeedback(score=0.7, feedback="Contains professional but not exact match")
            return ScoreWithFeedback(score=0.0, feedback=f"Expected '{expected}' not found in output")

        return metric

    @pytest.fixture
    def simple_execute(self):
        def execute(instructions, inputs):
            return {"answer": instructions.get("main", "")}

        return execute

    def _fast_optimizer(self, metric, execute_fn, **kwargs):
        optimizer = GEPAOptimizer(
            metric=metric,
            execute_fn=execute_fn,
            predictor_names=kwargs.pop("predictor_names", ["main"]),
            auto="light",
            seed=42,
            use_merge=False,
            **kwargs,
        )
        optimizer.num_candidates = 2
        return optimizer

    def test_basic_optimization(self, simple_metric, simple_execute):
        optimizer = self._fast_optimizer(simple_metric, simple_execute)
        trainset = [
            {"inputs": {"q": "test1"}, "expected": "professional"},
        ]
        result = optimizer.optimize(
            initial_instructions={"main": "bad prompt"},
            trainset=trainset,
        )
        assert isinstance(result, GEPAResult)
        assert result.candidates_explored > 0
        assert result.initial_score >= 0.0

    def test_optimization_with_reflection_lm(self, simple_metric, simple_execute):
        call_count = 0

        def mock_lm(prompt):
            nonlocal call_count
            call_count += 1
            return "professional and improved prompt"

        optimizer = self._fast_optimizer(simple_metric, simple_execute, reflection_lm=mock_lm)
        trainset = [{"inputs": {"q": "test"}, "expected": "professional"}]
        result = optimizer.optimize(
            initial_instructions={"main": "bad prompt"},
            trainset=trainset,
        )
        assert result.candidates_explored > 0
        assert call_count > 0

    def test_optimization_perfect_initial(self, simple_metric, simple_execute):
        optimizer = self._fast_optimizer(simple_metric, simple_execute)
        trainset = [{"inputs": {}, "expected": "perfect"}]
        result = optimizer.optimize(
            initial_instructions={"main": "perfect"},
            trainset=trainset,
        )
        assert result.initial_score == 1.0

    def test_optimization_with_valset(self, simple_metric, simple_execute):
        optimizer = self._fast_optimizer(simple_metric, simple_execute)
        trainset = [{"inputs": {"q": "train"}, "expected": "professional"}]
        valset = [{"inputs": {"q": "val"}, "expected": "professional"}]
        result = optimizer.optimize(
            initial_instructions={"main": "test prompt"},
            trainset=trainset,
            valset=valset,
        )
        assert isinstance(result, GEPAResult)

    def test_optimization_multiple_predictors(self, simple_metric):
        def multi_execute(instructions, inputs):
            return {"answer": instructions.get("generator", "") + " " + instructions.get("refiner", "")}

        optimizer = self._fast_optimizer(simple_metric, multi_execute, predictor_names=["generator", "refiner"])
        trainset = [{"inputs": {}, "expected": "professional"}]
        result = optimizer.optimize(
            initial_instructions={"generator": "generate", "refiner": "refine"},
            trainset=trainset,
        )
        assert "generator" in result.best_instructions
        assert "refiner" in result.best_instructions

    def test_optimization_merge_disabled(self, simple_metric, simple_execute):
        optimizer = self._fast_optimizer(simple_metric, simple_execute)
        trainset = [{"inputs": {}, "expected": "professional"}]
        result = optimizer.optimize(
            initial_instructions={"main": "test prompt"},
            trainset=trainset,
        )
        assert isinstance(result, GEPAResult)

    def test_optimization_history(self, simple_metric, simple_execute):
        optimizer = self._fast_optimizer(simple_metric, simple_execute)
        trainset = [{"inputs": {}, "expected": "professional"}]
        result = optimizer.optimize(
            initial_instructions={"main": "test"},
            trainset=trainset,
        )
        assert len(result.history) > 0
        assert result.history[0]["event"] == "seed"

    def test_optimization_with_exception_in_execute(self, simple_metric):
        def failing_execute(instructions, inputs):
            raise ValueError("Execute failed")

        optimizer = self._fast_optimizer(simple_metric, failing_execute)
        trainset = [{"inputs": {}, "expected": "test"}]
        result = optimizer.optimize(
            initial_instructions={"main": "test"},
            trainset=trainset,
        )
        assert result.initial_score == 0.0


# ═══════════════════════════════════════
# FeedbackMetric 测试
# ═══════════════════════════════════════


class TestFeedbackMetric:
    def test_exact_match_success(self):
        result = FeedbackMetric.exact_match(gold={"expected": "hello"}, pred={"answer": "hello"})
        assert result.score == 1.0
        assert result.feedback is None

    def test_exact_match_failure(self):
        result = FeedbackMetric.exact_match(gold={"expected": "hello"}, pred={"answer": "world"})
        assert result.score == 0.0
        assert result.feedback is not None

    def test_exact_match_case_insensitive(self):
        result = FeedbackMetric.exact_match(gold={"expected": "Hello"}, pred={"answer": "hello"})
        assert result.score == 1.0

    def test_contains_match_all_found(self):
        result = FeedbackMetric.contains_match(
            gold={"expected_parts": ["alpha", "beta"]},
            pred={"answer": "alpha and beta are here"},
        )
        assert result.score == 1.0
        assert result.feedback is None

    def test_contains_match_partial(self):
        result = FeedbackMetric.contains_match(
            gold={"expected_parts": ["alpha", "beta", "gamma"]},
            pred={"answer": "alpha and beta"},
        )
        assert 0 < result.score < 1.0
        assert result.feedback is not None

    def test_regex_match_success(self):
        result = FeedbackMetric.regex_match(
            gold={"regex_pattern": r"\d{4}-\d{2}-\d{2}"},
            pred={"answer": "2025-01-15"},
        )
        assert result.score == 1.0

    def test_regex_match_failure(self):
        result = FeedbackMetric.regex_match(
            gold={"regex_pattern": r"\d{4}-\d{2}-\d{2}"},
            pred={"answer": "not a date"},
        )
        assert result.score == 0.0

    def test_regex_match_no_pattern(self):
        result = FeedbackMetric.regex_match(gold={}, pred={"answer": "anything"})
        assert result.score == 1.0

    def test_lint_score_high(self):
        result = FeedbackMetric.lint_score(
            gold={},
            pred={
                "answer": "You are a professional AI assistant. Your task: analyze the input. Constraints: be concise."
            },
        )
        assert result.score > 0.0

    def test_llm_judge_no_judge_fallback(self):
        result = FeedbackMetric.llm_judge(gold={}, pred={"answer": "test output"})
        assert isinstance(result, ScoreWithFeedback)

    def test_llm_judge_with_mock(self):
        mock_judge = MagicMock(return_value="Score: 8\nFeedback: Good quality output")
        result = FeedbackMetric.llm_judge(
            gold={"criteria": "quality"},
            pred={"answer": "test output"},
            judge_lm=mock_judge,
        )
        assert result.score == 0.8
        assert "Good" in result.feedback

    def test_feedback_metrics_registry(self):
        assert "exact_match" in FEEDBACK_METRICS
        assert "contains_match" in FEEDBACK_METRICS
        assert "regex_match" in FEEDBACK_METRICS
        assert "lint_score" in FEEDBACK_METRICS
        assert "llm_judge" in FEEDBACK_METRICS
        assert "pangu_judge" in FEEDBACK_METRICS
        assert len(FEEDBACK_METRICS) == 6


# ═══════════════════════════════════════
# gepa_optimize 便捷函数测试
# ═══════════════════════════════════════


class TestGepaOptimizeFunction:
    def test_basic_usage(self):
        def fast_metric(gold, pred, **kwargs):
            return ScoreWithFeedback(score=0.8, feedback=None)

        result = gepa_optimize(
            "You are a helpful assistant.",
            custom_metric=fast_metric,
            auto="light",
        )
        assert isinstance(result, GEPAResult)
        assert result.initial_score >= 0.0

    def test_with_custom_metric(self):
        def my_metric(gold, pred, **kwargs):
            return ScoreWithFeedback(score=0.5, feedback="Always 0.5")

        result = gepa_optimize(
            "test prompt",
            custom_metric=my_metric,
            auto="light",
        )
        assert isinstance(result, GEPAResult)

    def test_with_custom_execute(self):
        def my_execute(instructions, inputs):
            return {"answer": "custom response"}

        def fast_metric(gold, pred, **kwargs):
            return ScoreWithFeedback(score=0.8, feedback=None)

        result = gepa_optimize(
            "test",
            custom_metric=fast_metric,
            execute_fn=my_execute,
            auto="light",
        )
        assert isinstance(result, GEPAResult)


# ═══════════════════════════════════════
# GEPAEvaluator 测试
# ═══════════════════════════════════════


class TestGEPAEvaluator:
    def test_evaluate(self):
        def fast_metric(gold, pred, **kwargs):
            return ScoreWithFeedback(score=0.8, feedback=None)

        evaluator = GEPAEvaluator()
        result = evaluator.evaluate("test", "You are a helpful assistant.", custom_metric=fast_metric, auto="light")
        assert isinstance(result, GEPAResult)
        assert result.candidates_explored > 0

    def test_evaluate_attributes(self):
        evaluator = GEPAEvaluator()
        assert evaluator.name == "gepa"
        assert evaluator.evaluator_type == "optimization"
        assert "gepa" in evaluator.tags


# ═══════════════════════════════════════
# PromptVersionStore 测试
# ═══════════════════════════════════════


class TestPromptVersionStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_versions.db"
            s = PromptVersionStore(db_path=db_path)
            yield s
            s.close()

    def test_save_and_load(self, store):
        v = store.save("my-prompt", "Hello world", score=85.0, source="manual")
        loaded = store.load(v.version_id)
        assert loaded is not None
        assert loaded.prompt_name == "my-prompt"
        assert loaded.content == "Hello world"
        assert loaded.score == 85.0

    def test_load_nonexistent(self, store):
        assert store.load("nonexistent") is None

    def test_list_versions(self, store):
        store.save("prompt-a", "version 1", score=80.0)
        store.save("prompt-a", "version 2", score=90.0)
        store.save("prompt-b", "other", score=70.0)
        versions_a = store.list_versions("prompt-a")
        versions_b = store.list_versions("prompt-b")
        assert len(versions_a) == 2
        assert len(versions_b) == 1

    def test_list_versions_with_filter(self, store):
        store.save("p", "v1", score=50.0, source="manual")
        store.save("p", "v2", score=90.0, source="gepa")
        high_score = store.list_versions("p", min_score=80.0)
        assert len(high_score) == 1
        gepa_source = store.list_versions("p", source="gepa")
        assert len(gepa_source) == 1

    def test_get_latest(self, store):
        v1 = store.save("p", "first", score=80.0)
        v2 = store.save("p", "second", score=90.0)
        latest = store.get_latest("p")
        assert latest is not None
        assert latest.version_id == v2.version_id

    def test_get_latest_nonexistent(self, store):
        assert store.get_latest("nonexistent") is None

    def test_rollback(self, store):
        v1 = store.save("p", "original", score=80.0)
        v2 = store.save("p", "modified", score=70.0)
        rolled = store.rollback(v1.version_id)
        assert rolled is not None
        assert rolled.content == "original"
        assert rolled.source == "rollback"
        assert "rollback_from" in rolled.metadata

    def test_rollback_nonexistent(self, store):
        assert store.rollback("nonexistent") is None

    def test_diff(self, store):
        v1 = store.save("p", "line1\nline2\nline3")
        v2 = store.save("p", "line1\nmodified\nline3")
        diff = store.diff(v1.version_id, v2.version_id)
        assert isinstance(diff, VersionDiff)
        assert diff.similarity > 0.0
        assert diff.similarity < 1.0
        assert diff.added_lines > 0 or diff.removed_lines > 0

    def test_diff_identical(self, store):
        v1 = store.save("p", "same content")
        v2 = store.save("p", "same content")
        diff = store.diff(v1.version_id, v2.version_id)
        assert diff.similarity == 1.0
        assert diff.added_lines == 0
        assert diff.removed_lines == 0

    def test_diff_nonexistent(self, store):
        diff = store.diff("a", "b")
        assert diff.diff_text == ""

    def test_ab_compare(self, store):
        v1 = store.save("p", "version A", score=80.0)
        v2 = store.save("p", "version B", score=90.0)
        result = store.ab_compare(v1.version_id, v2.version_id)
        assert isinstance(result, ABCompareResult)
        assert result.winner == "B"
        assert result.score_diff == 10.0

    def test_ab_compare_tie(self, store):
        v1 = store.save("p", "version A", score=80.0)
        v2 = store.save("p", "version B", score=80.0)
        result = store.ab_compare(v1.version_id, v2.version_id)
        assert result.winner == "tie"

    def test_ab_compare_nonexistent(self, store):
        result = store.ab_compare("a", "b")
        assert result.score_a == 0.0
        assert result.score_b == 0.0

    def test_delete_version(self, store):
        v = store.save("p", "to delete")
        assert store.delete_version(v.version_id) is True
        assert store.load(v.version_id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete_version("nonexistent") is False

    def test_save_with_tags_and_metadata(self, store):
        v = store.save("p", "content", tags=["v1", "prod"], metadata={"author": "test", "round": 27})
        loaded = store.load(v.version_id)
        assert loaded.tags == ["v1", "prod"]
        assert loaded.metadata["author"] == "test"

    def test_version_to_dict(self, store):
        v = store.save("p", "test content", score=85.5)
        d = v.to_dict()
        assert d["prompt_name"] == "p"
        assert d["score"] == 85.5
        assert d["content_length"] == 12

    def test_get_history(self, store):
        store.save("p", "v1")
        store.save("p", "v2")
        history = store.get_history("p")
        assert len(history) == 2
