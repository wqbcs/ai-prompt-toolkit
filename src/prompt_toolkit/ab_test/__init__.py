"""A/B测试引擎。"""

from prompt_toolkit.ab_test.types import (
    ABTestConfig,
    EvaluationDimension,
    ModelConfig,
    ModelResult,
    OptimalMatch,
    ProviderType,
    StatisticalReport,
    TestDataset,
    TestResult,
    TestStatus,
    WinRateCell,
)
from prompt_toolkit.ab_test.provider import (
    AliyunProvider,
    AnthropicProvider,
    BaseProvider,
    HuaweiProvider,
    OpenAIProvider,
    ProviderError,
    create_provider,
)
from prompt_toolkit.ab_test.engine import ParallelEngine, TaskOutput, TaskProgress
from prompt_toolkit.ab_test.statistics import (
    auto_select_test,
    cohens_d,
    confidence_interval,
    mann_whitney_u_test,
    t_test,
)
from prompt_toolkit.ab_test.recommender import Recommender


async def run_ab_test(
    config: ABTestConfig,
    *,
    max_concurrency: int = 10,
    mode: str = "win_rate",
) -> StatisticalReport:
    """SDK 入口：运行完整的 A/B 测试流程。

    Args:
        config: A/B 测试配置。
        max_concurrency: 最大并发数。
        mode: 推荐模式（win_rate / composite）。

    Returns:
        StatisticalReport 统计报告。
    """
    engine = ParallelEngine(config)
    outputs = await engine.run(max_concurrency=max_concurrency)

    results_by_template: dict[str, list[TaskOutput]] = {}
    for output in outputs:
        results_by_template.setdefault(output.prompt, []).append(output)

    pairwise: list[tuple[ModelResult, ModelResult]] = []
    for prompt, group in results_by_template.items():
        while len(group) >= 2:
            a = group.pop(0)
            b = group.pop(0)
            pairwise.append((a.model_result, b.model_result))

    recommender = Recommender(config)
    report = recommender.build_report(pairwise, config.dimensions)

    recommendations = recommender.recommend(pairwise, config.dimensions, mode=mode)
    report.recommendations.extend(
        {"mode": mode, **r.to_dict()} for r in recommendations
    )

    return report


__all__ = [
    "ABTestConfig",
    "EvaluationDimension",
    "ModelConfig",
    "ModelResult",
    "OptimalMatch",
    "ProviderType",
    "StatisticalReport",
    "TestDataset",
    "TestResult",
    "TestStatus",
    "WinRateCell",
    "AliyunProvider",
    "AnthropicProvider",
    "BaseProvider",
    "HuaweiProvider",
    "OpenAIProvider",
    "ProviderError",
    "create_provider",
    "ParallelEngine",
    "TaskOutput",
    "TaskProgress",
    "auto_select_test",
    "cohens_d",
    "confidence_interval",
    "mann_whitney_u_test",
    "t_test",
    "Recommender",
    "run_ab_test",
]
