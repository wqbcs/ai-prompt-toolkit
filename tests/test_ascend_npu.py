"""ascend_npu Provider测试 — 昇腾NPU推理适配"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType


def _make_config(model_name: str = "pangu-nlp-fp16") -> ModelConfig:
    return ModelConfig(
        provider=ProviderType.HUAWEI,
        model_name=model_name,
        api_key_env="HW_CLOUD_API_KEY",
    )


class TestNPUProviderInit:
    def test_provider_is_base_provider(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        assert isinstance(provider, BaseProvider)

    def test_provider_label(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        assert provider._PROVIDER_LABEL == "AscendNPU"

    def test_npu_info_dict(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        info = provider.npu_info
        assert isinstance(info, dict)
        assert "available" in info

    def test_validate_without_npu(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        result = provider.validate()
        assert isinstance(result, bool)


class TestNPUProviderInvoke:
    @pytest.mark.asyncio
    async def test_invoke_without_npu_returns_error(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        if not provider.is_available:
            result = await provider.invoke("test prompt")
            assert result.status.value == "failed"

    @pytest.mark.asyncio
    async def test_invoke_simulated_mode(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        from ai_prompt_toolkit.ab_test import provider as prov_module
        original = prov_module.SIMULATED_MODE
        try:
            prov_module.SIMULATED_MODE = True
            config = _make_config()
            provider = NPUProvider(config)
            if provider.is_available:
                import os
                os.environ["PROMPT_CLI_USE_NPU"] = "1"
                result = await provider.invoke("test prompt")
                assert result.status.value == "completed"
        finally:
            prov_module.SIMULATED_MODE = original


class TestNPUPricing:
    def test_int8_pricing_lower_than_fp16(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config_int8 = _make_config("pangu-nlp-int8")
        config_fp16 = _make_config("pangu-nlp-fp16")
        provider_int8 = NPUProvider(config_int8)
        provider_fp16 = NPUProvider(config_fp16)

        cost_int8 = provider_int8.estimate_cost(1000, 1000)
        cost_fp16 = provider_fp16.estimate_cost(1000, 1000)
        assert cost_int8 < cost_fp16

    def test_default_pricing(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config("unknown-model")
        provider = NPUProvider(config)
        cost = provider.estimate_cost(1000, 1000)
        assert cost > 0


class TestNPUDeploymentConfig:
    def test_get_deployment_config(self):
        from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
        config = _make_config()
        provider = NPUProvider(config)
        dep_config = provider.get_deployment_config()
        assert dep_config["provider"] == "ascend-npu"
        assert "quantization" in dep_config
        assert "batch_size" in dep_config
        assert "cann_version" in dep_config
