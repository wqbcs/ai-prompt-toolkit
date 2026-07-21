"""测试评估指标标准化模块"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.eval_metrics import (
    MetricCategory, MetricUnit, MetricDefinition, MetricResult,
    STANDARD_METRICS, get_metric, list_metrics,
    compute_metric_result, compute_weighted_score,
)


class TestMetricDefinitions:
    def test_standard_metrics_count(self):
        assert len(STANDARD_METRICS) == 12

    def test_all_have_required_fields(self):
        for m in STANDARD_METRICS:
            assert m.metric_id
            assert m.name
            assert m.name_zh
            assert m.category in MetricCategory
            assert m.unit in MetricUnit
            assert m.threshold_pass > 0

    def test_get_metric(self):
        m = get_metric("EVAL-001")
        assert m is not None
        assert m.name == "Answer Relevance"

    def test_get_metric_not_found(self):
        assert get_metric("EVAL-999") is None

    def test_list_metrics_by_category(self):
        safety = list_metrics(MetricCategory.SAFETY)
        assert len(safety) >= 2
        assert all(m.category == MetricCategory.SAFETY for m in safety)

    def test_list_metrics_all(self):
        all_metrics = list_metrics()
        assert len(all_metrics) == 12


class TestComputeMetricResult:
    def test_pass_quality_metric(self):
        result = compute_metric_result("EVAL-001", 0.85)
        assert result.passed is True
        assert result.warning is False

    def test_warn_quality_metric(self):
        result = compute_metric_result("EVAL-001", 0.55)
        assert result.passed is False
        assert result.warning is True

    def test_fail_quality_metric(self):
        result = compute_metric_result("EVAL-001", 0.3)
        assert result.passed is False
        assert result.warning is False

    def test_safety_bias_pass(self):
        result = compute_metric_result("EVAL-005", 0.1)
        assert result.passed is True

    def test_safety_bias_fail(self):
        result = compute_metric_result("EVAL-005", 0.7)
        assert result.passed is False

    def test_security_score_pass(self):
        result = compute_metric_result("EVAL-010", 85.0)
        assert result.passed is True

    def test_latency_pass(self):
        result = compute_metric_result("EVAL-011", 1000)
        assert result.passed is True

    def test_latency_fail(self):
        result = compute_metric_result("EVAL-011", 8000)
        assert result.passed is False

    def test_unknown_metric(self):
        result = compute_metric_result("EVAL-999", 0.5)
        assert result.passed is False
        assert result.warning is True


class TestComputeWeightedScore:
    def test_empty_results(self):
        result = compute_weighted_score([])
        assert result["overall"] == 0.0
        assert result["total"] == 0

    def test_all_pass(self):
        results = [
            compute_metric_result("EVAL-001", 0.9),
            compute_metric_result("EVAL-002", 0.85),
            compute_metric_result("EVAL-007", 0.8),
        ]
        result = compute_weighted_score(results)
        assert result["overall"] > 70
        assert result["passed"] == 3
        assert result["failed"] == 0

    def test_mixed_results(self):
        results = [
            compute_metric_result("EVAL-001", 0.8),
            compute_metric_result("EVAL-005", 0.6),
            compute_metric_result("EVAL-009", 0.4),
        ]
        result = compute_weighted_score(results)
        assert result["total"] == 3
        assert result["failed"] >= 1
