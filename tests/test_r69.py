"""R69测试: 多模态Token计数器, 华为云FunctionGraph Provider"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
from ai_prompt_toolkit.multimodal_token_counter import (
    MultimodalTokenCounter,
    TokenBudget,
    estimate_audio_tokens,
    estimate_image_tokens,
    estimate_text_tokens,
    estimate_video_tokens,
)


class TestTokenBudget:
    def test_default_values(self):
        b = TokenBudget()
        assert b.text_tokens == 0
        assert b.image_tokens == 0
        assert b.audio_tokens == 0
        assert b.video_tokens == 0
        assert b.max_total == 8192

    def test_total(self):
        b = TokenBudget(text_tokens=100, image_tokens=200, audio_tokens=50, video_tokens=30)
        assert b.total == 380

    def test_remaining(self):
        b = TokenBudget(text_tokens=100, max_total=8192)
        assert b.remaining == 8092

    def test_remaining_no_negative(self):
        b = TokenBudget(text_tokens=99999, max_total=100)
        assert b.remaining == 0

    def test_usage_ratio(self):
        b = TokenBudget(text_tokens=2048, max_total=8192)
        assert abs(b.usage_ratio - 0.25) < 0.001

    def test_usage_ratio_zero_max(self):
        b = TokenBudget(max_total=0)
        assert b.usage_ratio == 0.0

    def test_to_dict(self):
        b = TokenBudget(text_tokens=100, image_tokens=50, max_total=4096)
        d = b.to_dict()
        assert d["text_tokens"] == 100
        assert d["image_tokens"] == 50
        assert d["total_tokens"] == 150
        assert d["max_total"] == 4096
        assert d["remaining"] == 3946
        assert "usage_ratio" in d


class TestEstimateTextTokens:
    def test_short_text(self):
        tokens = estimate_text_tokens("Hello world")
        assert tokens >= 1

    def test_empty_text(self):
        tokens = estimate_text_tokens("")
        assert tokens >= 0

    def test_chinese_text_fallback(self):
        tokens = estimate_text_tokens("这是一个中文测试文本")
        assert tokens >= 1


class TestEstimateImageTokens:
    def test_low_detail(self):
        assert estimate_image_tokens(1024, 1024, "low") == 85

    def test_auto_detail(self):
        assert estimate_image_tokens(1024, 1024, "auto") == 85

    def test_high_detail_small_image(self):
        tokens = estimate_image_tokens(256, 256, "high")
        assert tokens >= 85

    def test_high_detail_large_image(self):
        tokens = estimate_image_tokens(2048, 2048, "high")
        assert tokens > 85


class TestEstimateAudioTokens:
    def test_one_second(self):
        assert estimate_audio_tokens(1.0) == 150

    def test_zero_duration(self):
        assert estimate_audio_tokens(0.0) == 0


class TestEstimateVideoTokens:
    def test_one_second_one_fps(self):
        assert estimate_video_tokens(1.0, fps=1) == 85

    def test_ten_seconds(self):
        assert estimate_video_tokens(10.0, fps=1) == 850

    def test_custom_fps(self):
        assert estimate_video_tokens(1.0, fps=2) == 170


class TestMultimodalTokenCounter:
    def test_count_text(self):
        c = MultimodalTokenCounter(max_total=8192)
        tokens = c.count_text("Hello world test")
        assert tokens >= 1
        assert c.budget.text_tokens == tokens

    def test_count_image(self):
        c = MultimodalTokenCounter()
        tokens = c.count_image(1024, 768, "low")
        assert tokens == 85
        assert c.budget.image_tokens == 85

    def test_count_audio(self):
        c = MultimodalTokenCounter()
        tokens = c.count_audio(2.0)
        assert tokens == 300
        assert c.budget.audio_tokens == 300

    def test_count_video(self):
        c = MultimodalTokenCounter()
        tokens = c.count_video(5.0, fps=2)
        assert tokens == 850
        assert c.budget.video_tokens == 850

    def test_mixed_modality_budget(self):
        c = MultimodalTokenCounter(max_total=1000)
        c.count_text("Hello world")
        c.count_image(512, 512, "low")
        c.count_audio(1.0)
        total = c.budget.total
        assert total > 0
        assert c.budget.total <= 1000 or not c.check_within_budget()

    def test_check_within_budget_pass(self):
        c = MultimodalTokenCounter(max_total=100000)
        c.count_text("Hello")
        assert c.check_within_budget() is True

    def test_check_within_budget_fail(self):
        c = MultimodalTokenCounter(max_total=10)
        c.count_image(2048, 2048, "high")
        assert c.check_within_budget() is False

    def test_reset(self):
        c = MultimodalTokenCounter(max_total=4096)
        c.count_text("test text content")
        c.count_audio(3.0)
        c.reset()
        assert c.budget.text_tokens == 0
        assert c.budget.audio_tokens == 0
        assert c.budget.max_total == 4096

    def test_get_budget(self):
        c = MultimodalTokenCounter(max_total=2048)
        b = c.get_budget()
        assert isinstance(b, TokenBudget)
        assert b.max_total == 2048


class TestFunctionGraphProvider:
    def test_provider_type_exists(self):
        assert ProviderType.FUNCTIONGRAPH.value == "functiongraph"

    def test_provider_in_registry(self):
        from ai_prompt_toolkit.ab_test.providers import get_registry
        registry = get_registry()
        assert ProviderType.FUNCTIONGRAPH in registry

    def test_provider_label(self):
        from ai_prompt_toolkit.ab_test.providers.functiongraph import FunctionGraphProvider
        provider = FunctionGraphProvider.__new__(FunctionGraphProvider)
        assert provider._PROVIDER_LABEL == "FunctionGraph"

    def test_provider_pricing(self):
        from ai_prompt_toolkit.ab_test.providers.functiongraph import FunctionGraphProvider
        assert "fg-pangu2-6b" in FunctionGraphProvider._PRICING
        assert "fg-pangu5-pro" in FunctionGraphProvider._PRICING
        assert "fg-pangu5-ultra" in FunctionGraphProvider._PRICING
        assert "fg-qwen2-7b" in FunctionGraphProvider._PRICING
        assert "fg-deepseek-v3" in FunctionGraphProvider._PRICING

    def test_provider_validate_no_env(self):
        from ai_prompt_toolkit.ab_test.providers.functiongraph import FunctionGraphProvider
        config = ModelConfig(provider=ProviderType.FUNCTIONGRAPH, model_name="fg-pangu5-pro", api_key_env="HUAWEI_CLOUD_AK")
        provider = FunctionGraphProvider(config)
        assert provider.validate() is False

    def test_provider_validate_with_env(self):
        from ai_prompt_toolkit.ab_test.providers.functiongraph import FunctionGraphProvider
        config = ModelConfig(provider=ProviderType.FUNCTIONGRAPH, model_name="fg-pangu5-pro", api_key_env="HUAWEI_CLOUD_AK")
        provider = FunctionGraphProvider(config)
        with patch.dict("os.environ", {"HUAWEI_CLOUD_AK": "ak-long-enough-key-1234567890"}):
            assert provider.validate() is True

    def test_provider_invoke_simulated(self):
        from ai_prompt_toolkit.ab_test.providers.functiongraph import FunctionGraphProvider
        config = ModelConfig(provider=ProviderType.FUNCTIONGRAPH, model_name="fg-pangu5-pro", api_key_env="HUAWEI_CLOUD_AK")
        provider = FunctionGraphProvider(config)
        result = asyncio.get_event_loop().run_until_complete(provider.invoke("test prompt"))
        assert result.status.value in ("completed", "failed")

    def test_provider_type_count_25(self):
        assert len(ProviderType) == 25

    def test_provider_endpoint_configured(self):
        from ai_prompt_toolkit.ab_test.provider import _PROVIDER_DEFAULT_ENDPOINTS
        assert ProviderType.FUNCTIONGRAPH in _PROVIDER_DEFAULT_ENDPOINTS
        assert "functiongraph" in _PROVIDER_DEFAULT_ENDPOINTS[ProviderType.FUNCTIONGRAPH]

    def test_provider_env_var_configured(self):
        from ai_prompt_toolkit.ab_test.provider import _PROVIDER_ENV_VARS
        assert ProviderType.FUNCTIONGRAPH in _PROVIDER_ENV_VARS

    def test_create_functiongraph_provider(self):
        from ai_prompt_toolkit.ab_test.provider import create_provider
        config = ModelConfig(provider=ProviderType.FUNCTIONGRAPH, model_name="fg-pangu5-pro")
        p = create_provider(config)
        assert p.provider_type == ProviderType.FUNCTIONGRAPH
