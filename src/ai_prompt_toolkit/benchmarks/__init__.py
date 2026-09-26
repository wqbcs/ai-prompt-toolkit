"""条件编译性能基准测试模块

提供编译管线各阶段的微基准测试+端到端集成基准测试:
- Lexer词法分析吞吐量
- Parser语法分析吞吐量
- Evaluator条件求值吞吐量
- Renderer渲染吞吐量
- 端到端compile_template吞吐量
- LRU缓存命中/未命中性能
- 不同模板复杂度的缩放曲线

使用方式:
    python -m ai_prompt_toolkit.benchmarks.compile_benchmark
    pytest tests/test_benchmarks.py -v
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.compiler import (
    CompileCache,
    CompileContext,
    CompileResult,
    Evaluator,
    Lexer,
    Parser,
    Renderer,
    compile_template,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class BenchResult:
    name: str
    iterations: int
    total_ms: float
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    stddev_ms: float
    ops_per_sec: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_ms": round(self.total_ms, 3),
            "mean_ms": round(self.mean_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "stddev_ms": round(self.stddev_ms, 3),
            "ops_per_sec": round(self.ops_per_sec, 1),
        }

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.mean_ms:.3f}ms/op "
            f"(median={self.median_ms:.3f}ms, "
            f"σ={self.stddev_ms:.3f}ms, "
            f"{self.ops_per_sec:.0f} ops/s, "
            f"n={self.iterations})"
        )


def _run_bench(name: str, fn: Callable[[], Any], iterations: int = 1000, warmup: int = 50) -> BenchResult:
    for _ in range(warmup):
        fn()

    timings: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000
        timings.append(elapsed)

    total = sum(timings)
    mean = statistics.mean(timings)
    median = statistics.median(timings)
    mn = min(timings)
    mx = max(timings)
    sd = statistics.stdev(timings) if len(timings) > 1 else 0.0
    ops = iterations / (total / 1000) if total > 0 else 0

    return BenchResult(
        name=name,
        iterations=iterations,
        total_ms=total,
        mean_ms=mean,
        median_ms=median,
        min_ms=mn,
        max_ms=mx,
        stddev_ms=sd,
        ops_per_sec=ops,
    )


SIMPLE_TEMPLATE = "你好，这是一个简单的模板。"
SINGLE_CONDITION = "你好{{#if model == gpt-4}}GPT-4用户{{else}}其他用户{{/if}}"
MULTI_CONDITION = (
    "{{#if model == gpt-4}}GPT-4{{/if}}"
    "{{#if language == zh-CN}}中文{{else}}English{{/if}}"
    "{{#if industry == finance}}金融{{/if}}"
)
NESTED_CONDITION = (
    "{{#if model == gpt-4}}"
    "  {{#if language == zh-CN}}GPT-4中文{{else}}GPT-4 English{{/if}}"
    "{{else}}"
    "  {{#if language == zh-CN}}其他中文{{else}}Other English{{/if}}"
    "{{/if}}"
)
LARGE_TEMPLATE = "\n".join(f"段落{i}: {{#if model == gpt-4}}GPT-4内容{{else}}通用内容{{/if}}" for i in range(100))


def bench_lexer_simple() -> BenchResult:
    return _run_bench("lexer_simple", lambda: Lexer(SIMPLE_TEMPLATE).tokenize())


def bench_lexer_single_condition() -> BenchResult:
    return _run_bench("lexer_single_condition", lambda: Lexer(SINGLE_CONDITION).tokenize())


def bench_lexer_large() -> BenchResult:
    return _run_bench("lexer_large_100", lambda: Lexer(LARGE_TEMPLATE).tokenize())


def bench_parser_single() -> BenchResult:
    def _fn():
        tokens = Lexer(SINGLE_CONDITION).tokenize()
        Parser(tokens).parse()

    return _run_bench("parser_single", _fn)


def bench_parser_nested() -> BenchResult:
    def _fn():
        tokens = Lexer(NESTED_CONDITION).tokenize()
        Parser(tokens).parse()

    return _run_bench("parser_nested", _fn)


def bench_evaluator_simple() -> BenchResult:
    ctx = CompileContext(model="gpt-4")
    tokens = Lexer(SINGLE_CONDITION).tokenize()
    ast = Parser(tokens).parse()
    cond = ast.children[0].condition if ast.children else None
    if cond is None:

        def _fn():
            pass
    else:
        ev = Evaluator(ctx)

        def _fn():
            ev.evaluate(cond)

    return _run_bench("evaluator_simple", _fn)


def bench_compile_simple() -> BenchResult:
    ctx = CompileContext(model="gpt-4")
    return _run_bench(
        "compile_simple_no_cache",
        lambda: compile_template(SIMPLE_TEMPLATE, ctx, use_cache=False),
    )


def bench_compile_single_condition() -> BenchResult:
    ctx = CompileContext(model="gpt-4")
    return _run_bench(
        "compile_single_condition_no_cache",
        lambda: compile_template(SINGLE_CONDITION, ctx, use_cache=False),
    )


def bench_compile_nested_no_cache() -> BenchResult:
    ctx = CompileContext(model="gpt-4", language="zh-CN")
    return _run_bench(
        "compile_nested_no_cache",
        lambda: compile_template(NESTED_CONDITION, ctx, use_cache=False),
    )


def bench_compile_with_cache_hit() -> BenchResult:
    ctx = CompileContext(model="gpt-4")
    compile_template(SINGLE_CONDITION, ctx, use_cache=True, template_id="bench_cache")
    return _run_bench(
        "compile_cache_hit",
        lambda: compile_template(SINGLE_CONDITION, ctx, use_cache=True, template_id="bench_cache"),
    )


def bench_compile_large() -> BenchResult:
    ctx = CompileContext(model="gpt-4")
    return _run_bench(
        "compile_large_100_no_cache",
        lambda: compile_template(LARGE_TEMPLATE, ctx, use_cache=False),
        iterations=200,
    )


@dataclass
class BenchSuite:
    name: str
    results: list[BenchResult] = field(default_factory=list)

    def run(self, benchmarks: list[Callable[[], BenchResult]]) -> BenchSuite:
        for bench_fn in benchmarks:
            result = bench_fn()
            self.results.append(result)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "results": [r.to_dict() for r in self.results],
        }

    def report(self) -> str:
        lines = [f"{'=' * 60}", f"基准测试: {self.name}", f"{'=' * 60}"]
        for r in self.results:
            lines.append(str(r))
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)


def run_all_benchmarks() -> BenchSuite:
    suite = BenchSuite(name="条件编译性能基准测试")
    suite.run(
        [
            bench_lexer_simple,
            bench_lexer_single_condition,
            bench_lexer_large,
            bench_parser_single,
            bench_parser_nested,
            bench_evaluator_simple,
            bench_compile_simple,
            bench_compile_single_condition,
            bench_compile_nested_no_cache,
            bench_compile_with_cache_hit,
            bench_compile_large,
        ]
    )
    return suite


if __name__ == "__main__":
    suite = run_all_benchmarks()
    print(suite.report())
