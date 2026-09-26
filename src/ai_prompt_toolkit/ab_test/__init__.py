"""A/B测试引擎。"""

from ai_prompt_toolkit.ab_test.engine import ParallelEngine, TaskOutput, TaskProgress
from ai_prompt_toolkit.ab_test.provider import (
    BaseProvider,
    CostTracker,
    HealthCheckResult,
    ProviderError,
    create_provider,
    get_cost_tracker,
    run_health_check,
)
from ai_prompt_toolkit.ab_test.providers.aliyun import AliyunProvider
from ai_prompt_toolkit.ab_test.providers.anthropic import AnthropicProvider
from ai_prompt_toolkit.ab_test.providers.baidu import BaiduProvider
from ai_prompt_toolkit.ab_test.providers.cohere import CohereProvider
from ai_prompt_toolkit.ab_test.providers.deepseek import DeepSeekProvider
from ai_prompt_toolkit.ab_test.providers.fireworks import FireworksProvider
from ai_prompt_toolkit.ab_test.providers.google import GoogleProvider
from ai_prompt_toolkit.ab_test.providers.groq import GroqProvider
from ai_prompt_toolkit.ab_test.providers.huawei import HuaweiProvider
from ai_prompt_toolkit.ab_test.providers.lmstudio import LMStudioProvider
from ai_prompt_toolkit.ab_test.providers.minimax import MiniMaxProvider
from ai_prompt_toolkit.ab_test.providers.mistral import MistralProvider
from ai_prompt_toolkit.ab_test.providers.moonshot import MoonshotProvider
from ai_prompt_toolkit.ab_test.providers.ollama import OllamaProvider
from ai_prompt_toolkit.ab_test.providers.openai import OpenAIProvider
from ai_prompt_toolkit.ab_test.providers.perplexity import PerplexityProvider
from ai_prompt_toolkit.ab_test.providers.together import TogetherProvider
from ai_prompt_toolkit.ab_test.providers.zhipu import ZhipuProvider
from ai_prompt_toolkit.ab_test.recommender import Recommender
from ai_prompt_toolkit.ab_test.statistics import (
    auto_select_test,
    bayesian_ab_test,
    cohens_d,
    confidence_interval,
    mann_whitney_u_test,
    recommend_statistical_method,
    sequential_analysis,
    t_test,
    thompson_sampling,
)
from ai_prompt_toolkit.ab_test.types import (
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


async def run_ab_test(
    config: ABTestConfig,
    *,
    max_concurrency: int = 10,
    mode: str = "win_rate",
) -> StatisticalReport:
    engine = ParallelEngine(config)
    outputs = await engine.run(max_concurrency=max_concurrency)

    results_by_template: dict[str, list[TaskOutput]] = {}
    for output in outputs:
        results_by_template.setdefault(output.prompt, []).append(output)

    pairwise: list[tuple[ModelResult, ModelResult]] = []
    for _prompt, group in results_by_template.items():
        while len(group) >= 2:
            a = group.pop(0)
            b = group.pop(0)
            pairwise.append((a.model_result, b.model_result))

    recommender = Recommender(config)
    report = recommender.build_report(pairwise, config.dimensions)

    recommendations = recommender.recommend(pairwise, config.dimensions, mode=mode)
    report.recommendations.extend({"mode": mode, **r.to_dict()} for r in recommendations)

    return report


__all__ = [
    "ABTestConfig",
    "AliyunProvider",
    "AnthropicProvider",
    "BaiduProvider",
    "BaseProvider",
    "CohereProvider",
    "CostTracker",
    "DeepSeekProvider",
    "EvaluationDimension",
    "FireworksProvider",
    "GoogleProvider",
    "GroqProvider",
    "HealthCheckResult",
    "HuaweiProvider",
    "LMStudioProvider",
    "MiniMaxProvider",
    "MistralProvider",
    "ModelConfig",
    "ModelResult",
    "MoonshotProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "OptimalMatch",
    "ParallelEngine",
    "PerplexityProvider",
    "ProviderError",
    "ProviderType",
    "Recommender",
    "StatisticalReport",
    "TaskOutput",
    "TaskProgress",
    "TestDataset",
    "TestResult",
    "TestStatus",
    "TogetherProvider",
    "WinRateCell",
    "ZhipuProvider",
    "auto_select_test",
    "bayesian_ab_test",
    "cohens_d",
    "confidence_interval",
    "create_provider",
    "get_cost_tracker",
    "mann_whitney_u_test",
    "recommend_statistical_method",
    "run_ab_test",
    "run_health_check",
    "sequential_analysis",
    "t_test",
    "thompson_sampling",
]
