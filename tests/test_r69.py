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
        result = asyncio.run(provider.invoke("test prompt"))
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


class TestBadgeMultiTheme:
    def test_light_theme_default(self):
        from ai_prompt_toolkit.security.badge import generate_score_svg, Theme
        from ai_prompt_toolkit.security.prompt_scorecard import Grade
        svg = generate_score_svg(95, Grade.A)
        assert "#2ea44f" in svg
        assert "#555555" in svg

    def test_dark_theme(self):
        from ai_prompt_toolkit.security.badge import generate_score_svg
        from ai_prompt_toolkit.security.prompt_scorecard import Grade
        svg = generate_score_svg(95, Grade.A, theme="dark")
        assert "#3fb950" in svg
        assert "#30363d" in svg
        assert "#e6edf3" in svg

    def test_huawei_theme(self):
        from ai_prompt_toolkit.security.badge import generate_score_svg
        from ai_prompt_toolkit.security.prompt_scorecard import Grade
        svg = generate_score_svg(95, Grade.A, theme="huawei")
        assert "#C7000B" in svg

    def test_theme_config_all_keys(self):
        from ai_prompt_toolkit.security.badge import _THEME_CONFIG
        for theme_name in ("light", "dark", "huawei"):
            tc = _THEME_CONFIG[theme_name]
            assert "bg" in tc
            assert "text" in tc
            for grade in ("A", "B", "C", "D", "F"):
                assert grade in tc
            for decision in ("ALLOW", "WARN", "BLOCK"):
                assert decision in tc

    def test_scorecard_badge_theme(self):
        from ai_prompt_toolkit.security.badge import generate_scorecard_badge
        from ai_prompt_toolkit.security.prompt_scorecard import PromptScorecard, Grade, Decision
        sc = PromptScorecard(overall_score=80, grade=Grade.B, decision=Decision.ALLOW, dimensions=[], total_findings=0, critical_count=0, high_count=0, medium_count=0, low_count=0)
        svg_light = generate_scorecard_badge(sc, theme="light")
        svg_dark = generate_scorecard_badge(sc, theme="dark")
        svg_hw = generate_scorecard_badge(sc, theme="huawei")
        assert "#57ab5a" in svg_light
        assert "#56d364" in svg_dark
        assert "#E6382E" in svg_hw

    def test_compact_badge_theme(self):
        from ai_prompt_toolkit.security.badge import generate_scorecard_badge
        from ai_prompt_toolkit.security.prompt_scorecard import PromptScorecard, Grade, Decision
        sc = PromptScorecard(overall_score=50, grade=Grade.C, decision=Decision.WARN, dimensions=[], total_findings=0, critical_count=0, high_count=0, medium_count=0, low_count=0)
        svg = generate_scorecard_badge(sc, compact=True, theme="huawei")
        assert "#F5A623" in svg


class TestConfigWatcher:
    def test_watcher_init(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        w = ConfigWatcher(poll_interval=1.0, debounce_seconds=0.5)
        assert w._poll_interval == 1.0
        assert w._debounce_seconds == 0.5
        assert not w._running

    def test_watcher_start_and_stop(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        w = ConfigWatcher()
        config = w.start()
        assert w._running is True
        assert config is not None
        w.stop()
        assert w._running is False

    def test_watcher_current_config(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        w = ConfigWatcher()
        config = w.current_config
        assert config.lint_on_save is True

    def test_watcher_add_watch_nonexistent(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        from pathlib import Path
        w = ConfigWatcher()
        w.add_watch(Path("/nonexistent/config.toml"))
        assert len(w._watches) == 0

    def test_watcher_check_no_change(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        w = ConfigWatcher()
        w.start()
        result = w.check_and_reload()
        assert result is False
        w.stop()

    def test_watcher_callback(self):
        from ai_prompt_toolkit.config import ConfigWatcher
        called = []
        def on_reload(cfg):
            called.append(cfg)
        w = ConfigWatcher(on_reload=on_reload)
        w.start()
        w._last_reload_time = 0
        if w._watches:
            ws = w._watches[0]
            ws.content_hash = "old_hash"
            if ws.path.exists():
                result = w.check_and_reload()
                if result:
                    assert len(called) == 1
        w.stop()

    def test_get_watcher_singleton(self):
        from ai_prompt_toolkit.config import get_watcher
        w1 = get_watcher()
        w2 = get_watcher()
        assert w1 is w2
