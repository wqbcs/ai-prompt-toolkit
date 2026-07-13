"""条件编译性能基准测试 — 单元测试验证"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.benchmarks import (
    BenchResult,
    BenchSuite,
    _run_bench,
    run_all_benchmarks,
    bench_lexer_simple,
    bench_lexer_single_condition,
    bench_compile_simple,
    bench_compile_single_condition,
    bench_compile_with_cache_hit,
)


class TestBenchResult:
    def test_to_dict(self):
        r = BenchResult(
            name="test", iterations=10, total_ms=100, mean_ms=10,
            median_ms=10, min_ms=8, max_ms=12, stddev_ms=1.5, ops_per_sec=100,
        )
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["iterations"] == 10
        assert d["ops_per_sec"] == 100

    def test_str_format(self):
        r = BenchResult(
            name="mybench", iterations=100, total_ms=50, mean_ms=0.5,
            median_ms=0.5, min_ms=0.3, max_ms=0.8, stddev_ms=0.1, ops_per_sec=2000,
        )
        s = str(r)
        assert "mybench" in s
        assert "ops/s" in s


class TestRunBench:
    def test_basic_execution(self):
        counter = {"n": 0}
        def fn():
            counter["n"] += 1
        result = _run_bench("test_fn", fn, iterations=10, warmup=2)
        assert result.iterations == 10
        assert result.name == "test_fn"
        assert result.ops_per_sec > 0
        assert counter["n"] == 12

    def test_warmup_runs_first(self):
        calls = {"warmup": 0, "main": 0}
        def fn():
            calls["main"] += 1
        _run_bench("test", fn, iterations=5, warmup=3)
        assert calls["main"] == 8


class TestBenchSuite:
    def test_run_suite(self):
        suite = BenchSuite(name="test_suite")
        suite.run([bench_lexer_simple, bench_lexer_single_condition])
        assert len(suite.results) == 2
        assert suite.results[0].name == "lexer_simple"

    def test_suite_report(self):
        suite = BenchSuite(name="test_suite")
        suite.run([bench_lexer_simple])
        report = suite.report()
        assert "test_suite" in report
        assert "lexer_simple" in report

    def test_suite_to_dict(self):
        suite = BenchSuite(name="test_suite")
        suite.run([bench_lexer_simple])
        d = suite.to_dict()
        assert d["name"] == "test_suite"
        assert len(d["results"]) == 1


class TestCompileBenchmarks:
    def test_lexer_simple(self):
        r = bench_lexer_simple()
        assert r.mean_ms > 0
        assert r.ops_per_sec > 100

    def test_lexer_single_condition(self):
        r = bench_lexer_single_condition()
        assert r.mean_ms > 0

    def test_compile_simple(self):
        r = bench_compile_simple()
        assert r.mean_ms > 0

    def test_compile_single_condition(self):
        r = bench_compile_single_condition()
        assert r.mean_ms > 0

    def test_compile_cache_hit(self):
        r = bench_compile_with_cache_hit()
        assert r.mean_ms > 0

    def test_full_suite(self):
        suite = run_all_benchmarks()
        assert len(suite.results) == 11
        for r in suite.results:
            assert r.mean_ms > 0
            assert r.ops_per_sec > 0
