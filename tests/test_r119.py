"""R119 测试: eval --benchmark基准测试"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.evaluator import run_benchmark, BenchmarkResult


class TestR119Benchmark:
    def test_benchmark_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = str(Path(tmpdir) / "bench.json")
            results = run_benchmark(
                [("test.md", "你是一个专业的翻译助手")],
                history_path=history,
            )
            assert len(results) == 1
            assert results[0].template_name == "test.md"
            assert results[0].current_score >= 0
            assert results[0].grade in ("S", "A", "B", "C", "D", "F")
            assert results[0].decision in ("PASS", "FAIL")
            assert results[0].previous_score is None
            assert results[0].delta is None

    def test_benchmark_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history = str(Path(tmpdir) / "bench.json")
            run_benchmark(
                [("test.md", "你是一个专业的翻译助手")],
                history_path=history,
            )
            results2 = run_benchmark(
                [("test.md", "你是一个专业的翻译助手")],
                history_path=history,
            )
            assert results2[0].previous_score is not None
            assert results2[0].delta is not None

    def test_benchmark_result_fields(self):
        r = BenchmarkResult("a.md", 85.0, 80.0, 5.0, "A", "PASS", "2026-01-01")
        assert r.delta == 5.0
        assert r.grade == "A"
