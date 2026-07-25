"""R22 Provider拆分 + HealthCheck + doctor命令 测试"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
from ai_prompt_toolkit.ab_test.provider import (
    BaseProvider,
    HealthCheckResult,
    ProviderError,
    create_provider,
    run_health_check,
)
from ai_prompt_toolkit.ab_test.providers import get_registry


class TestProviderModuleSplit:
    def test_registry_has_all_24_providers(self):
        registry = get_registry()
        assert len(registry) == 25

    def test_create_all_openai_compatible_providers(self):
        openai_compatible = [
            (ProviderType.OPENAI, "openai"),
            (ProviderType.DEEPSEEK, "deepseek"),
            (ProviderType.ALIYUN, "aliyun"),
            (ProviderType.GOOGLE, "google"),
            (ProviderType.MISTRAL, "mistral"),
            (ProviderType.COHERE, "cohere"),
            (ProviderType.GROQ, "groq"),
            (ProviderType.TOGETHER, "together"),
            (ProviderType.FIREWORKS, "fireworks"),
            (ProviderType.PERPLEXITY, "perplexity"),
            (ProviderType.ZHIPU, "zhipu"),
            (ProviderType.MOONSHOT, "moonshot"),
            (ProviderType.BAIDU, "baidu"),
            (ProviderType.MINIMAX, "minimax"),
        ]
        for pt, _ in openai_compatible:
            config = ModelConfig(provider=pt, model_name="test")
            p = create_provider(config)
            assert isinstance(p, BaseProvider)

    def test_create_anthropic_provider(self):
        config = ModelConfig(provider=ProviderType.ANTHROPIC, model_name="claude-3-sonnet")
        p = create_provider(config)
        assert isinstance(p, BaseProvider)

    def test_create_huawei_provider(self):
        config = ModelConfig(provider=ProviderType.HUAWEI, model_name="pangu-large")
        p = create_provider(config)
        assert isinstance(p, BaseProvider)

    def test_create_ollama_provider(self):
        config = ModelConfig(provider=ProviderType.OLLAMA, model_name="llama3")
        p = create_provider(config)
        assert isinstance(p, BaseProvider)

    def test_create_lmstudio_provider(self):
        config = ModelConfig(provider=ProviderType.LMSTUDIO, model_name="test")
        p = create_provider(config)
        assert isinstance(p, BaseProvider)


class TestHealthCheck:
    def test_health_check_returns_all_providers(self):
        results = run_health_check()
        assert len(results) == 25

    def test_health_check_no_api_key_providers(self):
        results = run_health_check([ProviderType.OPENAI])
        assert len(results) == 1
        assert results[0].status == "no_api_key"
        assert not results[0].api_key_configured

    def test_health_check_local_unreachable(self):
        results = run_health_check([ProviderType.OLLAMA])
        assert len(results) == 1
        assert results[0].status in ("healthy", "unreachable")
        assert results[0].api_key_configured

    def test_health_check_with_api_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test12345678901234567890"}):
            results = run_health_check([ProviderType.OPENAI])
            assert len(results) == 1
            assert results[0].api_key_configured
            assert results[0].status in ("healthy", "unreachable")

    def test_health_check_result_dataclass(self):
        r = HealthCheckResult(
            provider=ProviderType.OPENAI, label="openai",
            status="healthy", latency_ms=42.5,
            api_key_configured=True, endpoint="https://api.openai.com/v1",
        )
        assert r.provider == ProviderType.OPENAI
        assert r.latency_ms == 42.5
        assert r.status == "healthy"

    def test_health_check_specific_provider(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test12345678901234567890"}):
            results = run_health_check([ProviderType.ANTHROPIC])
            assert len(results) == 1
            assert results[0].provider == ProviderType.ANTHROPIC
            assert results[0].api_key_configured


class TestDoctorCLI:
    def test_doctor_command_exists(self):
        from click.testing import CliRunner
        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "健康检查" in result.output

    def test_doctor_json_output(self):
        from click.testing import CliRunner
        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--json", "-p", "ollama"])
        assert result.exit_code in (0, 1)
        import json
        json_str = result.output.split("正在检查Provider健康状态...", 1)[-1].strip()
        if json_str:
            data = json.loads(json_str)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["provider"] == "ollama"
