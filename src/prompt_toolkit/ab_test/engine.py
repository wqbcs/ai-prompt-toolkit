"""A/B测试并行引擎——asyncio.gather并行调度、超时、重试、错误隔离、进度追踪。"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from prompt_toolkit.ab_test.types import (
    ABTestConfig,
    EvaluationDimension,
    ModelConfig,
    ModelResult,
    TestDataset,
    TestResult,
    TestStatus,
)
from prompt_toolkit.ab_test.provider import BaseProvider, create_provider


@dataclass
class TaskProgress:
    total: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.completed / self.total) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "in_progress": self.in_progress,
            "percentage": self.percentage,
        }


@dataclass
class TaskOutput:
    model_result: ModelResult
    prompt: str
    provider_name: str
    dataset_item: dict[str, str] = field(default_factory=dict)
    attempt: int = 1
    success: bool = True
    error: str = ""


class ParallelEngine:
    def __init__(self, config: ABTestConfig) -> None:
        self._config = config
        self._providers: dict[str, BaseProvider] = {}
        self._progress = TaskProgress()
        self._results: list[TaskOutput] = []
        self._lock = asyncio.Lock()
        self._cancelled = False
        self._init_providers()

    def _init_providers(self) -> None:
        for model in self._config.models:
            key = f"{model.provider.value}:{model.model_name}"
            self._providers[key] = create_provider(model)

    @property
    def progress(self) -> TaskProgress:
        return self._progress

    @property
    def results(self) -> list[TaskOutput]:
        return list(self._results)

    def cancel(self) -> None:
        self._cancelled = True

    def _get_provider(self, model: ModelConfig) -> BaseProvider:
        key = f"{model.provider.value}:{model.model_name}"
        return self._providers[key]

    async def _invoke_with_retry(
        self,
        provider: BaseProvider,
        prompt: str,
        dataset_item: dict[str, str],
        max_retries: int | None = None,
        timeout: float | None = None,
    ) -> TaskOutput:
        retries = max_retries if max_retries is not None else self._config.max_retries
        timeout_s = timeout if timeout is not None else self._config.timeout_seconds
        provider_name = f"{provider.provider_type.value}:{provider.model_name}"

        last_error = ""
        for attempt in range(1, retries + 1):
            if self._cancelled:
                return TaskOutput(
                    model_result=provider._make_error_result(prompt, "已取消"),
                    prompt=prompt,
                    provider_name=provider_name,
                    dataset_item=dataset_item,
                    attempt=attempt,
                    success=False,
                    error="cancelled",
                )

            try:
                result = await asyncio.wait_for(
                    provider.invoke(prompt, **dataset_item),
                    timeout=timeout_s,
                )
                return TaskOutput(
                    model_result=result,
                    prompt=prompt,
                    provider_name=provider_name,
                    dataset_item=dataset_item,
                    attempt=attempt,
                    success=result.status == TestStatus.COMPLETED,
                )
            except asyncio.TimeoutError:
                last_error = f"超时({timeout_s}s)于第{attempt}次尝试"
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"

            if attempt < retries:
                backoff = min(2 ** attempt, 10)
                await asyncio.sleep(backoff)

        return TaskOutput(
            model_result=provider._make_error_result(prompt, last_error),
            prompt=prompt,
            provider_name=provider_name,
            dataset_item=dataset_item,
            attempt=retries,
            success=False,
            error=last_error,
        )

    async def _run_task(
        self,
        provider: BaseProvider,
        prompt: str,
        dataset_item: dict[str, str],
        semaphore: asyncio.Semaphore,
    ) -> TaskOutput:
        async with semaphore:
            async with self._lock:
                self._progress.in_progress += 1

            output = await self._invoke_with_retry(provider, prompt, dataset_item)

            async with self._lock:
                self._progress.in_progress -= 1
                self._progress.completed += 1
                if not output.success:
                    self._progress.failed += 1
                self._results.append(output)

            return output

    async def run(
        self,
        models: list[ModelConfig] | None = None,
        datasets: list[TestDataset] | None = None,
        prompt_templates: list[str] | None = None,
        max_concurrency: int = 10,
        progress_callback: Any = None,
    ) -> list[TaskOutput]:
        models = models or self._config.models
        datasets = datasets or self._config.datasets
        templates = prompt_templates or self._config.prompt_templates

        if not templates:
            templates = ["请根据以下内容生成回复：{input}"]

        tasks: list[asyncio.Task[TaskOutput]] = []
        total = 0
        for model in models:
            for template in templates:
                for dataset in datasets:
                    total += len(dataset.items)

        self._progress = TaskProgress(total=total)
        self._results = []
        self._cancelled = False

        semaphore = asyncio.Semaphore(max_concurrency)

        for model in models:
            provider = self._get_provider(model)
            for template in templates:
                for dataset in datasets:
                    for item in dataset.items:
                        prompt = template.format(**{k: v for k, v in item.items() if v})
                        task = asyncio.create_task(
                            self._run_task(provider, prompt, item, semaphore)
                        )
                        tasks.append(task)

        async def _monitor() -> None:
            while not self._cancelled:
                await asyncio.sleep(0.5)
                if progress_callback:
                    progress_callback(self._progress)

        monitor_task = asyncio.create_task(_monitor())

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        if progress_callback:
            progress_callback(self._progress)

        return list(self._results)

    async def run_pairwise(
        self,
        model_a: ModelConfig,
        model_b: ModelConfig,
        dataset: TestDataset,
        prompt_template: str = "",
        max_concurrency: int = 5,
    ) -> list[tuple[TaskOutput, TaskOutput]]:
        template = prompt_template or "请根据以下内容生成回复：{input}"

        provider_a = self._get_provider(model_a)
        provider_b = self._get_provider(model_b)

        pairs: list[tuple[TaskOutput, TaskOutput]] = []
        self._progress = TaskProgress(total=len(dataset.items) * 2)
        self._results = []

        for item in dataset.items:
            prompt = template.format(**{k: v for k, v in item.items() if v})

            out_a, out_b = await asyncio.gather(
                self._invoke_with_retry(provider_a, prompt, item),
                self._invoke_with_retry(provider_b, prompt, item),
            )

            pairs.append((out_a, out_b))
            self._progress.completed += 2
            if not out_a.success:
                self._progress.failed += 1
            if not out_b.success:
                self._progress.failed += 1
            self._results.extend([out_a, out_b])

        return pairs

    def get_summary(self) -> dict[str, Any]:
        by_provider: dict[str, list[TaskOutput]] = {}
        for r in self._results:
            by_provider.setdefault(r.provider_name, []).append(r)

        summary: dict[str, Any] = {}
        for name, outputs in by_provider.items():
            successes = [o for o in outputs if o.success]
            summary[name] = {
                "total": len(outputs),
                "success": len(successes),
                "failed": len(outputs) - len(successes),
                "avg_latency_ms": (
                    sum(o.model_result.latency_ms for o in successes) / len(successes)
                    if successes
                    else 0.0
                ),
                "total_cost": sum(o.model_result.cost for o in successes),
                "avg_token_count": (
                    sum(o.model_result.token_count for o in successes) / len(successes)
                    if successes
                    else 0
                ),
            }

        return summary
