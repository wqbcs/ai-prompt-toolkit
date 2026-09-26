"""R102: 华为云ModelArts Provider增强 + 昇腾NPU验证"""

from __future__ import annotations

from ai_prompt_toolkit.ab_test.providers.ascend_npu import NPUProvider
from ai_prompt_toolkit.ab_test.providers.huawei_modelarts import HuaweiModelArtsProvider


class TestR102ModelArtsAndNPU:
    def test_modelarts_provider_exists(self):
        assert HuaweiModelArtsProvider is not None

    def test_modelarts_pricing_has_new_models(self):
        pricing = HuaweiModelArtsProvider._PRICING
        assert "qwen2.5-72b" in pricing
        assert "deepseek-v3" in pricing
        assert "llama3.1-70b" in pricing
        assert "chatglm4-9b" in pricing

    def test_modelarts_endpoints(self):
        endpoints = HuaweiModelArtsProvider._DEFAULT_ENDPOINTS
        assert "cn-north-4" in endpoints
        assert "cn-east-3" in endpoints

    def test_modelarts_label(self):
        assert HuaweiModelArtsProvider._PROVIDER_LABEL == "HuaweiModelArts"

    def test_npu_provider_exists(self):
        assert NPUProvider is not None

    def test_npu_label(self):
        assert NPUProvider._PROVIDER_LABEL == "AscendNPU"

    def test_npu_pricing(self):
        pricing = NPUProvider._PRICING
        assert "pangu-nlp-int8" in pricing
        assert "qwen-14b-fp16" in pricing
