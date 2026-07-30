"""R163: 成本追踪维度"""
import pytest
from ai_prompt_toolkit.linter.cost_tracker import CostTracker, CostRecord


def test_cost_record_gpt4o():
    tracker = CostTracker()
    rec = tracker.record("gpt-4o", input_tokens=1000, output_tokens=500, latency_ms=1500.0)
    assert rec.model == "gpt-4o"
    assert rec.input_tokens == 1000
    assert rec.cost_usd > 0


def test_cost_tracker_total():
    tracker = CostTracker()
    tracker.record("gpt-4o", 1000, 500, 1500.0)
    tracker.record("gpt-3.5-turbo", 2000, 1000, 800.0)
    assert tracker.total_input_tokens == 3000
    assert tracker.total_output_tokens == 1500
    assert tracker.total_tokens == 4500
    assert tracker.total_cost_usd > 0
    assert len(tracker.records) == 2


def test_cost_tracker_avg_latency():
    tracker = CostTracker()
    tracker.record("gpt-4o", 1000, 500, 1000.0)
    tracker.record("gpt-4o", 1000, 500, 2000.0)
    assert tracker.avg_latency_ms == 1500.0


def test_cost_tracker_by_model():
    tracker = CostTracker()
    tracker.record("gpt-4o", 1000, 500, 1500.0)
    tracker.record("gpt-3.5-turbo", 2000, 1000, 800.0)
    by_model = tracker.by_model
    assert "gpt-4o" in by_model
    assert "gpt-3.5-turbo" in by_model
    assert by_model["gpt-4o"]["count"] == 1


def test_cost_tracker_to_dict():
    tracker = CostTracker()
    tracker.record("gpt-4o", 1000, 500, 1500.0)
    d = tracker.to_dict()
    assert "total_cost_usd" in d
    assert "by_model" in d
    assert d["total_tokens"] == 1500


def test_cost_tracker_pangu():
    tracker = CostTracker()
    rec = tracker.record("pangu-large", 1000, 500, 2000.0)
    assert rec.cost_usd > 0
