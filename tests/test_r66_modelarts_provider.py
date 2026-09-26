"""R66测试: 华为云ModelArts Provider"""

import pytest

from ai_prompt_toolkit.ab_test.providers.huawei_modelarts import HuaweiModelArtsProvider
from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType


class TestHuaweiModelArtsProvider:
    def test_provider_type_exists(self):
        assert ProviderType.HUAWEI_MODELARTS.value == "huawei_modelarts"

    def test_provider_registered(self):
        from ai_prompt_toolkit.ab_test.providers import get_registry

        reg = get_registry()
        assert ProviderType.HUAWEI_MODELARTS in reg
        assert reg[ProviderType.HUAWEI_MODELARTS] is HuaweiModelArtsProvider

    def test_provider_instantiation(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
            api_key_env="HUAWEI_CLOUD_AK",
        )
        p = HuaweiModelArtsProvider(config)
        assert p.model_name == "pangu5-chat"
        assert p._PROVIDER_LABEL == "HuaweiModelArts"

    def test_pricing(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
        )
        p = HuaweiModelArtsProvider(config)
        cost = p.estimate_cost(1000, 500)
        assert cost > 0

    def test_pricing_unknown_model(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="unknown-model",
        )
        p = HuaweiModelArtsProvider(config)
        cost = p.estimate_cost(1000, 500)
        assert cost > 0

    def test_resolve_endpoint_default(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
        )
        p = HuaweiModelArtsProvider(config)
        endpoint = p._resolve_endpoint()
        assert "myhuaweicloud.com" in endpoint

    def test_resolve_endpoint_custom(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
            api_base="https://custom-endpoint.example.com",
        )
        p = HuaweiModelArtsProvider(config)
        endpoint = p._resolve_endpoint()
        assert "custom-endpoint" in endpoint

    def test_validate_without_credentials(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
            api_key_env="HUAWEI_CLOUD_AK",
        )
        p = HuaweiModelArtsProvider(config)
        assert p.validate() is False

    def test_sign_request(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
        )
        p = HuaweiModelArtsProvider(config)
        headers = p._sign_request(
            "HW_TEST_AK",
            "test_sk_value_1234567890",
            "POST",
            "https://infer.cn-north-4.myhuaweicloud.com/v1/chat/completions",
            '{"model":"pangu5-chat"}',
        )
        assert "Authorization" in headers
        assert "SDK-HMAC-SHA256" in headers["Authorization"]
        assert "X-Sdk-Date" in headers
        assert "Content-Type" in headers

    def test_endpoint_env_vars(self):
        from ai_prompt_toolkit.ab_test.provider import _PROVIDER_DEFAULT_ENDPOINTS, _PROVIDER_ENV_VARS

        assert ProviderType.HUAWEI_MODELARTS in _PROVIDER_DEFAULT_ENDPOINTS
        assert ProviderType.HUAWEI_MODELARTS in _PROVIDER_ENV_VARS
        assert _PROVIDER_ENV_VARS[ProviderType.HUAWEI_MODELARTS] == "HUAWEI_CLOUD_AK"

    @pytest.mark.asyncio
    async def test_invoke_simulated(self):
        config = ModelConfig(
            provider=ProviderType.HUAWEI_MODELARTS,
            model_name="pangu5-chat",
            api_key_env="HUAWEI_CLOUD_AK",
        )
        p = HuaweiModelArtsProvider(config)
        result = await p.invoke("你好")
        assert result.status.value == "completed"
        assert "HuaweiModelArts" in result.response or result.response == ""

    def test_total_provider_count(self):
        from ai_prompt_toolkit.ab_test.types import ProviderType

        providers = list(ProviderType)
        assert len(providers) == 25
