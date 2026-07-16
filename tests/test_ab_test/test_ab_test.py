"""A/B测试模块测试 — Provider/Engine/Statistics/Recommender覆盖。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
from ai_prompt_toolkit.ab_test import (
    AliyunProvider,
    AnthropicProvider,
    BaseProvider,
    CostTracker,
    DeepSeekProvider,
    HuaweiProvider,
    OpenAIProvider,
    ProviderError,
    create_provider,
    get_cost_tracker,
)


class TestProviderType:
    def test_all_provider_types(self):
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.ALIYUN.value == "aliyun"
        assert ProviderType.DEEPSEEK.value == "deepseek"
        assert ProviderType.HUAWEI.value == "huawei"
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.MISTRAL.value == "mistral"
        assert ProviderType.COHERE.value == "cohere"
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.TOGETHER.value == "together"
        assert ProviderType.FIREWORKS.value == "fireworks"
        assert ProviderType.PERPLEXITY.value == "perplexity"
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.LMSTUDIO.value == "lmstudio"
        assert ProviderType.ZHIPU.value == "zhipu"
        assert ProviderType.MOONSHOT.value == "moonshot"
        assert ProviderType.BAIDU.value == "baidu"
        assert ProviderType.MINIMAX.value == "minimax"

    def test_provider_type_count(self):
        assert len(ProviderType) == 18


class TestCostTracker:
    def test_initial_state(self):
        tracker = CostTracker(limit=10.0)
        assert tracker.spent == 0.0
        assert tracker.remaining == 10.0
        assert not tracker.limit_reached

    def test_record_cost(self):
        tracker = CostTracker(limit=10.0)
        tracker.record(3.5)
        assert tracker.spent == 3.5
        assert tracker.remaining == 6.5

    def test_limit_reached(self):
        tracker = CostTracker(limit=5.0)
        tracker.record(5.0)
        assert tracker.limit_reached
        assert tracker.remaining == 0.0

    def test_reset(self):
        tracker = CostTracker(limit=10.0)
        tracker.record(5.0)
        tracker.reset()
        assert tracker.spent == 0.0


class TestProviderRegistry:
    def test_create_openai_provider(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        provider = create_provider(config)
        assert isinstance(provider, OpenAIProvider)

    def test_create_anthropic_provider(self):
        config = ModelConfig(provider=ProviderType.ANTHROPIC, model_name="claude-3-sonnet")
        provider = create_provider(config)
        assert isinstance(provider, AnthropicProvider)

    def test_create_aliyun_provider(self):
        config = ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max")
        provider = create_provider(config)
        assert isinstance(provider, AliyunProvider)

    def test_create_deepseek_provider(self):
        config = ModelConfig(provider=ProviderType.DEEPSEEK, model_name="deepseek-chat")
        provider = create_provider(config)
        assert isinstance(provider, DeepSeekProvider)

    def test_create_huawei_provider(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large")
        provider = create_provider(config)
        assert isinstance(provider, HuaweiProvider)

    def test_create_unsupported_provider_raises(self):
        from ai_prompt_toolkit.ab_test.providers import _PROVIDER_REGISTRY
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="test")
        original = _PROVIDER_REGISTRY.pop(ProviderType.OPENAI)
        try:
            with pytest.raises(ProviderError):
                create_provider(config)
        finally:
            _PROVIDER_REGISTRY[ProviderType.OPENAI] = original


class TestOpenAIProvider:
    def test_validate_no_key(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        provider = OpenAIProvider(config)
        assert not provider.validate()

    def test_validate_valid_key(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o", api_key_env="TEST_OPENAI_KEY")
        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "sk-test12345678901234567890"}):
            provider = OpenAIProvider(config)
            assert provider.validate()

    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        provider = OpenAIProvider(config)
        result = await provider.invoke("test prompt")
        assert result.status == TestStatus.COMPLETED
        assert "simulated" in result.response.lower()

    def test_estimate_cost(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        provider = OpenAIProvider(config)
        cost = provider.estimate_cost(1000, 500)
        assert cost > 0
        expected = (1000 * 0.005 + 500 * 0.015) / 1000
        assert abs(cost - expected) < 0.0001


class TestHuaweiProvider:
    def test_validate_no_key(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large")
        provider = HuaweiProvider(config)
        assert not provider.validate()

    def test_validate_valid_key(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large", api_key_env="TEST_HUAWEI_KEY")
        with patch.dict("os.environ", {"TEST_HUAWEI_KEY": "hw-test-key-12345678"}):
            provider = HuaweiProvider(config)
            assert provider.validate()

    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large")
        provider = HuaweiProvider(config)
        result = await provider.invoke("test prompt")
        assert result.status == TestStatus.COMPLETED
        assert "simulated" in result.response.lower()

    def test_estimate_cost_pangu_large(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large")
        provider = HuaweiProvider(config)
        cost = provider.estimate_cost(1000, 500)
        expected = (1000 * 0.012 + 500 * 0.036) / 1000
        assert abs(cost - expected) < 0.0001

    def test_pricing_models(self):
        assert "pangu-nlp" in HuaweiProvider._PRICING
        assert "pangu-vision" in HuaweiProvider._PRICING


class TestAliyunProvider:
    def test_validate_no_key(self):
        config = ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max")
        provider = AliyunProvider(config)
        assert not provider.validate()

    def test_validate_valid_key(self):
        config = ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max", api_key_env="TEST_ALIYUN_KEY")
        with patch.dict("os.environ", {"TEST_ALIYUN_KEY": "sk-test12345678901234567890"}):
            provider = AliyunProvider(config)
            assert provider.validate()

    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max")
        provider = AliyunProvider(config)
        result = await provider.invoke("test prompt")
        assert result.status == TestStatus.COMPLETED
        assert "simulated" in result.response.lower()

    def test_estimate_cost(self):
        config = ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max")
        provider = AliyunProvider(config)
        cost = provider.estimate_cost(1000, 500)
        expected = (1000 * 0.004 + 500 * 0.012) / 1000
        assert abs(cost - expected) < 0.0001

    def test_pricing_models(self):
        assert "qwen-plus" in AliyunProvider._PRICING
        assert "qwen-turbo" in AliyunProvider._PRICING
        assert "qwen-long" in AliyunProvider._PRICING


class TestDeepSeekProvider:
    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(provider=ProviderType.DEEPSEEK, model_name="deepseek-chat")
        provider = DeepSeekProvider(config)
        result = await provider.invoke("test prompt")
        assert result.status == TestStatus.COMPLETED

    def test_estimate_cost(self):
        config = ModelConfig(provider=ProviderType.DEEPSEEK, model_name="deepseek-chat")
        provider = DeepSeekProvider(config)
        cost = provider.estimate_cost(1000, 500)
        expected = (1000 * 0.00014 + 500 * 0.00028) / 1000
        assert abs(cost - expected) < 0.0001


class TestAnthropicProvider:
    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(provider=ProviderType.ANTHROPIC, model_name="claude-3-sonnet")
        provider = AnthropicProvider(config)
        result = await provider.invoke("test prompt")
        assert result.status == TestStatus.COMPLETED

    def test_estimate_cost(self):
        config = ModelConfig(provider=ProviderType.ANTHROPIC, model_name="claude-3-sonnet")
        provider = AnthropicProvider(config)
        cost = provider.estimate_cost(1000, 500)
        expected = (1000 * 0.003 + 500 * 0.015) / 1000
        assert abs(cost - expected) < 0.0001


class TestModelResult:
    def test_to_dict(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        result = ModelResult(model_config=config, prompt_template="test", status=TestStatus.COMPLETED)
        d = result.to_dict()
        assert d["status"] == "completed"
        assert d["prompt_template"] == "test"

    def test_error_result(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        result = ModelResult(
            model_config=config, prompt_template="test",
            status=TestStatus.FAILED, error_message="timeout"
        )
        assert result.status == TestStatus.FAILED
        assert result.error_message == "timeout"


class TestModelConfig:
    def test_to_dict(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o", temperature=0.5)
        d = config.to_dict()
        assert d["provider"] == "openai"
        assert d["model_name"] == "gpt-4o"
        assert d["temperature"] == 0.5

    def test_default_values(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        assert config.temperature == 0.7
        assert config.max_tokens == 2048


class TestABTestConfig:
    def test_to_dict(self):
        config = ABTestConfig(test_id="test-001")
        d = config.to_dict()
        assert d["test_id"] == "test-001"
        assert d["significance_level"] == 0.05

    def test_with_models(self):
        models = [
            ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o"),
            ModelConfig(provider=ProviderType.ALIYUN, model_name="qwen-max"),
        ]
        config = ABTestConfig(test_id="test-002", models=models)
        assert len(config.models) == 2


class TestEvaluationDimension:
    def test_to_dict(self):
        dim = EvaluationDimension(dimension_id="D1", name="准确性", weight=2.0)
        d = dim.to_dict()
        assert d["dimension_id"] == "D1"
        assert d["weight"] == 2.0


class TestTestDataset:
    def test_to_dict(self):
        ds = TestDataset(dataset_id="ds-1", name="测试集", items=[{"input": "hi"}])
        d = ds.to_dict()
        assert d["dataset_id"] == "ds-1"
        assert len(d["items"]) == 1


class TestWinRateCell:
    def test_to_dict(self):
        cell = WinRateCell(model_a="gpt-4o", model_b="qwen-max", dimension_id="D1")
        d = cell.to_dict()
        assert d["model_a"] == "gpt-4o"


class TestStatisticalReport:
    def test_to_dict(self):
        report = StatisticalReport(test_id="r1")
        d = report.to_dict()
        assert d["test_id"] == "r1"


class TestOptimalMatch:
    def test_to_dict(self):
        config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o")
        match = OptimalMatch(model_config=config, prompt_template="test")
        d = match.to_dict()
        assert d["prompt_template"] == "test"


class TestProviderError:
    def test_error_message(self):
        err = ProviderError("openai", "timeout")
        assert "[openai]" in str(err)
        assert "timeout" in str(err)


class TestGlobalCostTracker:
    def test_get_cost_tracker(self):
        tracker = get_cost_tracker()
        assert isinstance(tracker, CostTracker)
