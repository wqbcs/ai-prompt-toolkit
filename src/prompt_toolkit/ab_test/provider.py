"""A/B测试模型提供者——抽象基类与4个实现。"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from prompt_toolkit.ab_test.types import ModelConfig, ModelResult, ProviderType, TestStatus


class ProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class BaseProvider(ABC):
    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._api_key: str | None = None

    @property
    def provider_type(self) -> ProviderType:
        return self._config.provider

    @property
    def model_name(self) -> str:
        return self._config.model_name

    @abstractmethod
    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        ...

    @abstractmethod
    def validate(self) -> bool:
        ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        ...

    def _load_credential(self) -> str:
        if self._api_key is not None:
            return self._api_key
        env_var = self._config.api_key_env
        if not env_var:
            raise ProviderError(
                self._config.provider.value,
                f"未配置环境变量名: {self._config.provider.value}",
            )
        key = os.environ.get(env_var, "")
        if not key:
            raise ProviderError(
                self._config.provider.value,
                f"环境变量 {env_var!r} 未设置或为空",
            )
        self._api_key = key
        return self._api_key

    def _make_error_result(self, prompt: str, error: str) -> ModelResult:
        return ModelResult(
            model_config=self._config,
            prompt_template=prompt,
            status=TestStatus.FAILED,
            error_message=error,
        )


class OpenAIProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return key.startswith("sk-")
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        import asyncio
        import json
        import time

        start = time.perf_counter()
        try:
            self._load_credential()
            api_base = self._config.api_base or "https://api.openai.com/v1/chat/completions"

            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
                **self._config.extra_params,
                **kwargs,
            }

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    api_base.split("//")[1].split("/")[0].split(":")[0],
                    443,
                ),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()

            latency = (time.perf_counter() - start) * 1000

            return ModelResult(
                model_config=self._config,
                prompt_template=prompt,
                response=f"[OpenAI {self._config.model_name} simulated response]",
                latency_ms=round(latency, 2),
                token_count=len(prompt.split()) + 50,
                cost=self.estimate_cost(len(prompt.split()), 50),
                status=TestStatus.COMPLETED,
            )
        except ProviderError as e:
            return self._make_error_result(prompt, str(e))
        except asyncio.TimeoutError:
            return self._make_error_result(prompt, "请求超时")
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.001, 0.002))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class AnthropicProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
    }

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return key.startswith("sk-ant-")
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        import asyncio
        import time

        start = time.perf_counter()
        try:
            self._load_credential()
            latency = (time.perf_counter() - start) * 1000

            return ModelResult(
                model_config=self._config,
                prompt_template=prompt,
                response=f"[Anthropic {self._config.model_name} simulated response]",
                latency_ms=round(latency, 2),
                token_count=len(prompt.split()) + 50,
                cost=self.estimate_cost(len(prompt.split()), 50),
                status=TestStatus.COMPLETED,
            )
        except ProviderError as e:
            return self._make_error_result(prompt, str(e))
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.003, 0.015))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class AliyunProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "qwen-turbo": (0.002, 0.006),
        "qwen-plus": (0.004, 0.012),
        "qwen-max": (0.02, 0.06),
    }

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return key.startswith("sk-") and len(key) > 20
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        import asyncio
        import time

        start = time.perf_counter()
        try:
            self._load_credential()
            latency = (time.perf_counter() - start) * 1000

            return ModelResult(
                model_config=self._config,
                prompt_template=prompt,
                response=f"[Aliyun {self._config.model_name} simulated response]",
                latency_ms=round(latency, 2),
                token_count=len(prompt.split()) + 50,
                cost=self.estimate_cost(len(prompt.split()), 50),
                status=TestStatus.COMPLETED,
            )
        except ProviderError as e:
            return self._make_error_result(prompt, str(e))
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.002, 0.006))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class HuaweiProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "pangu-large": (0.012, 0.036),
        "pangu-medium": (0.004, 0.012),
        "盘古大模型": (0.012, 0.036),
    }

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return len(key) >= 16
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        import asyncio
        import time

        start = time.perf_counter()
        try:
            self._load_credential()
            latency = (time.perf_counter() - start) * 1000

            return ModelResult(
                model_config=self._config,
                prompt_template=prompt,
                response=f"[Huawei {self._config.model_name} simulated response]",
                latency_ms=round(latency, 2),
                token_count=len(prompt.split()) + 50,
                cost=self.estimate_cost(len(prompt.split()), 50),
                status=TestStatus.COMPLETED,
            )
        except ProviderError as e:
            return self._make_error_result(prompt, str(e))
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.004, 0.012))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


_PROVIDER_REGISTRY: dict[ProviderType, type[BaseProvider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.ALIYUN: AliyunProvider,
    ProviderType.HUAWEI: HuaweiProvider,
}


def create_provider(config: ModelConfig) -> BaseProvider:
    cls = _PROVIDER_REGISTRY.get(config.provider)
    if cls is None:
        raise ProviderError(config.provider.value, f"不支持的提供者类型: {config.provider}")
    return cls(config)
