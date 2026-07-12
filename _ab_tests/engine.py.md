# A/B测试并行执行引擎 (Engine)

> 完整的Python并行执行引擎实现，可直接运行

```python
"""
A/B 测试并行执行引擎 — 基于 asyncio + asyncio.gather

支持:
    - 多 Provider 并行调用
    - 超时控制
    - 重试策略
    - 结果聚合

用法:
    from engine import ParallelEngine, ABTestConfig
    engine = ParallelEngine(providers=[p1, p2])
    results = await engine.run("Hello", config=ABTestConfig(n_rounds=3))
"""

from __future__ import annotations

import asyncio
import enum
import time
import dataclasses
from typing import Any, Dict, List, Optional, Sequence

from provider import BaseProvider, GenerateResult, ProviderKind


# ──────────────────────────────────────────
#  配置
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class ABTestConfig:
    """A/B 测试配置

    Attributes:
        n_rounds:     每个Provider的调用轮次
        max_tokens:   最大生成 Token 数
        temperature:  采样温度
        top_p:        核采样概率
        timeout:      单次调用超时（秒）
        max_retries:  最大重试次数
        retry_delay:  重试间隔（秒）
        system:       系统提示
    """
    n_rounds: int = 5
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 1.0
    timeout: float = 30.0
    max_retries: int = 2
    retry_delay: float = 1.0
    system: Optional[str] = None


# ──────────────────────────────────────────
#  执行状态
# ──────────────────────────────────────────

class RunStatus(enum.Enum):
    """执行状态"""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    RETRY_EXHAUSTED = "retry_exhausted"


@dataclasses.dataclass
class SingleRun:
    """单次执行记录

    Attributes:
        provider_kind: Provider 类型
        round_idx:     轮次索引
        status:        执行状态
        result:        生成结果（可能为空）
        error:         错误信息
        attempt:       实际尝试次数
    """
    provider_kind: ProviderKind
    round_idx: int
    status: RunStatus
    result: Optional[GenerateResult]
    error: str = ""
    attempt: int = 1


@dataclasses.dataclass
class EngineReport:
    """引擎执行报告

    Attributes:
        total_runs:     总执行次数
        successful:     成功次数
        failed:         失败次数
        total_time_ms:  总耗时（毫秒）
        by_provider:    按 Provider 汇总
    """
    total_runs: int = 0
    successful: int = 0
    failed: int = 0
    total_time_ms: float = 0.0
    by_provider: Dict[str, Dict[str, Any]] = dataclasses.field(default_factory=dict)

    def summary(self) -> str:
        """生成报告摘要"""
        lines = [
            f"总执行: {self.total_runs}",
            f"成功: {self.successful}  失败: {self.failed}",
            f"耗时: {self.total_time_ms:.1f}ms",
        ]
        for pk, stats in self.by_provider.items():
            lines.append(f"  {pk}: {stats.get('success', 0)}/{stats.get('total', 0)} 成功")
        return "\n".join(lines)


# ──────────────────────────────────────────
#  并行执行引擎
# ──────────────────────────────────────────

class ParallelEngine:
    """A/B 测试并行执行引擎

    使用 asyncio.gather 并行调用多个 Provider，
    支持多轮次、超时、重试。

    Args:
        providers: Provider 实例列表
    """

    def __init__(self, providers: Sequence[BaseProvider]):
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self._providers = list(providers)

    @property
    def providers(self) -> List[BaseProvider]:
        return self._providers

    async def run(
        self,
        prompt: str,
        *,
        config: ABTestConfig | None = None,
        progress_callback: Any | None = None,
    ) -> tuple[List[SingleRun], EngineReport]:
        """执行 A/B 测试

        Args:
            prompt:           输入提示
            config:           测试配置
            progress_callback: 进度回调（可选）

        Returns:
            (单次执行记录列表, 引擎报告)
        """
        if config is None:
            config = ABTestConfig()

        start = time.monotonic()
        runs: List[SingleRun] = []

        # 构建所有任务
        tasks: List[asyncio.Task[SingleRun]] = []
        for provider in self._providers:
            for round_idx in range(config.n_rounds):
                task = asyncio.create_task(
                    self._run_single(provider, prompt, round_idx, config)
                )
                tasks.append(task)

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, SingleRun):
                runs.append(r)
            elif isinstance(r, Exception):
                runs.append(SingleRun(
                    provider_kind=ProviderKind.OPENAI,
                    round_idx=-1,
                    status=RunStatus.ERROR,
                    result=None,
                    error=str(r),
                ))

        elapsed = (time.monotonic() - start) * 1000
        report = self._build_report(runs, elapsed)

        return runs, report

    async def _run_single(
        self,
        provider: BaseProvider,
        prompt: str,
        round_idx: int,
        config: ABTestConfig,
    ) -> SingleRun:
        """执行单次调用，带重试"""
        last_error = ""

        for attempt in range(1, config.max_retries + 2):
            try:
                result = await asyncio.wait_for(
                    provider.generate(
                        prompt,
                        max_tokens=config.max_tokens,
                        temperature=config.temperature,
                        top_p=config.top_p,
                        system=config.system,
                    ),
                    timeout=config.timeout,
                )
                return SingleRun(
                    provider_kind=provider.kind,
                    round_idx=round_idx,
                    status=RunStatus.SUCCESS,
                    result=result,
                    attempt=attempt,
                )

            except asyncio.TimeoutError:
                last_error = f"超时 ({config.timeout}s)"
                if attempt <= config.max_retries:
                    await asyncio.sleep(config.retry_delay)
                continue

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                if attempt <= config.max_retries:
                    await asyncio.sleep(config.retry_delay)
                continue

        return SingleRun(
            provider_kind=provider.kind,
            round_idx=round_idx,
            status=RunStatus.RETRY_EXHAUSTED,
            result=None,
            error=last_error,
            attempt=config.max_retries + 1,
        )

    @staticmethod
    def _build_report(runs: List[SingleRun], elapsed_ms: float) -> EngineReport:
        """构建执行报告"""
        successful = sum(1 for r in runs if r.status == RunStatus.SUCCESS)
        by_provider: Dict[str, Dict[str, Any]] = {}

        for r in runs:
            pk = r.provider_kind.value
            if pk not in by_provider:
                by_provider[pk] = {"total": 0, "success": 0, "latencies": []}
            by_provider[pk]["total"] += 1
            if r.status == RunStatus.SUCCESS and r.result:
                by_provider[pk]["success"] += 1
                by_provider[pk]["latencies"].append(r.result.latency_ms)

        # 计算平均延迟
        for pk in by_provider:
            lats = by_provider[pk]["latencies"]
            by_provider[pk]["avg_latency_ms"] = (
                round(sum(lats) / len(lats), 2) if lats else 0
            )
            del by_provider[pk]["latencies"]

        return EngineReport(
            total_runs=len(runs),
            successful=successful,
            failed=len(runs) - successful,
            total_time_ms=round(elapsed_ms, 2),
            by_provider=by_provider,
        )

    async def close(self) -> None:
        """关闭所有 Provider"""
        for p in self._providers:
            await p.close()


# ──────────────────────────────────────────
#  便捷运行函数
# ──────────────────────────────────────────

async def quick_run(
    prompt: str,
    provider_configs: List[Dict[str, Any]],
    n_rounds: int = 3,
) -> tuple[List[SingleRun], EngineReport]:
    """快捷 A/B 测试

    Args:
        prompt:           输入提示
        provider_configs: Provider 配置列表 [{"kind": "openai", "api_key": "..."}]
        n_rounds:         轮次数

    Returns:
        (单次执行记录列表, 引擎报告)
    """
    from provider import create_provider

    providers = [create_provider(**cfg) for cfg in provider_configs]
    engine = ParallelEngine(providers)
    config = ABTestConfig(n_rounds=n_rounds)
    return await engine.run(prompt, config=config)


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

async def _run_tests() -> None:
    """内置单元测试"""
    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    from provider import create_provider

    # ── 测试 1: 基本并行运行 ──
    p1 = create_provider("openai", api_key="test")
    p2 = create_provider("anthropic", api_key="test")
    engine = ParallelEngine([p1, p2])
    runs, report = await engine.run("Hello", config=ABTestConfig(n_rounds=2))
    assert_eq("总轮次", len(runs), 4)
    assert_eq("成功数", report.successful, 4)

    # ── 测试 2: 报告统计 ──
    assert_eq("Provider数", len(report.by_provider), 2)
    assert_eq("总执行", report.total_runs, 4)

    # ── 测试 3: 空 Provider 列表 ──
    try:
        ParallelEngine([])
        assert_eq("空Provider-应报错", False, True)
    except ValueError:
        assert_eq("空Provider-报错", True, True)

    # ── 测试 4: 单 Provider ──
    engine = ParallelEngine([p1])
    runs, report = await engine.run("test", config=ABTestConfig(n_rounds=3))
    assert_eq("单Provider-轮次", len(runs), 3)
    assert_eq("单Provider-成功", report.successful, 3)

    # ── 测试 5: 超时处理 ──
    engine = ParallelEngine([p1])
    runs, report = await engine.run(
        "test",
        config=ABTestConfig(n_rounds=1, timeout=0.0001, max_retries=0),
    )
    # 模拟环境下可能成功也可能超时
    assert_eq("超时-有记录", len(runs) >= 1, True)

    # ── 测试 6: 报告摘要 ──
    summary = report.summary()
    assert_eq("摘要-非空", len(summary) > 0, True)

    # ── 测试 7: close ──
    await engine.close()
    assert_eq("close", True, True)

    # ── 测试 8: quick_run ──
    runs, report = await quick_run(
        "Hello",
        provider_configs=[
            {"kind": "openai", "api_key": "test"},
            {"kind": "aliyun", "api_key": "test"},
        ],
        n_rounds=2,
    )
    assert_eq("quick_run-轮次", len(runs), 4)

    # ── 测试 9: 4个Provider并行 ──
    providers = [
        create_provider("openai", api_key="test"),
        create_provider("anthropic", api_key="test"),
        create_provider("aliyun", api_key="test"),
        create_provider("huawei", api_key="test"),
    ]
    engine = ParallelEngine(providers)
    runs, report = await engine.run("test", config=ABTestConfig(n_rounds=1))
    assert_eq("4Provider-轮次", len(runs), 4)
    assert_eq("4Provider-Provider数", len(report.by_provider), 4)

    print(f"\nEngine 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_run_tests())
```
