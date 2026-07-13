"""A/B测试模型提供者 — httpx异步真实调用版

参考: promptfoo Python SDK Provider模式
- httpx.AsyncClient连接池+指数退避重试
- SIMULATED_MODE降级(无API Key时)
- CostTracker费用累计控制
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

from ai_prompt_toolkit.ab_test.types import ModelConfig, ModelResult, ProviderType, TestStatus

logger = logging.getLogger(__name__)

SIMULATED_MODE = not bool(os.environ.get("PROMPT_CLI_REAL_API", ""))

_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 1.0
_COST_LIMIT_USD = float(os.environ.get("PROMPT_CLI_COST_LIMIT", "10.0"))

_total_cost: float = 0.0


class CostTracker:
    def __init__(self, limit: float = _COST_LIMIT_USD) -> None:
        self._limit = limit
        self._spent: float = 0.0

    @property
    def spent(self) -> float:
        return self._spent

    @property
    def remaining(self) -> float:
        return max(self._limit - self._spent, 0.0)

    @property
    def limit_reached(self) -> bool:
        return self._spent >= self._limit

    def record(self, cost: float) -> None:
        self._spent += cost

    def reset(self) -> None:
        self._spent = 0.0


_global_cost_tracker = CostTracker()


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
    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult: ...

    @abstractmethod
    def validate(self) -> bool: ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...

    def _load_credential(self) -> str:
        if self._api_key is not None:
            return self._api_key
        env_var = self._config.api_key_env
        if not env_var:
            raise ProviderError(self._config.provider.value, f"未配置环境变量名")
        key = os.environ.get(env_var, "")
        if not key:
            raise ProviderError(self._config.provider.value, f"环境变量 {env_var!r} 未设置")
        self._api_key = key
        return self._api_key

    def _make_error_result(self, prompt: str, error: str) -> ModelResult:
        return ModelResult(
            model_config=self._config, prompt_template=prompt,
            status=TestStatus.FAILED, error_message=error,
        )

    async def _http_post(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import httpx
        except ImportError:
            raise ProviderError(self._config.provider.value, "httpx未安装，请运行: pip install httpx")

        delay = _RETRY_BASE_DELAY
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("retry-after", delay))
                        logger.warning("429 Rate Limit, 等待 %.1fs (attempt %d/%d)", retry_after, attempt + 1, _MAX_RETRIES)
                        import asyncio
                        await asyncio.sleep(retry_after)
                        delay *= 2
                        continue
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    import asyncio
                    logger.warning("请求失败 (attempt %d/%d): %s, %.1fs后重试", attempt + 1, _MAX_RETRIES, e, delay)
                    await asyncio.sleep(delay)
                    delay *= 2
        raise ProviderError(self._config.provider.value, f"重试{_MAX_RETRIES}次后仍失败: {last_error}")


class OpenAIProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "gpt-4o": (0.005, 0.015), "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03), "gpt-3.5-turbo": (0.0005, 0.0015),
    }

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-")
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return self._make_simulated_result(prompt, start, "OpenAI")

        if SIMULATED_MODE:
            return self._make_simulated_result(prompt, start, "OpenAI")

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = (self._config.api_base or "https://api.openai.com/v1") + "/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }
            data = await self._http_post(url, headers, payload)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config, prompt_template=prompt, response=content,
                latency_ms=round(latency, 2), token_count=input_tokens + output_tokens,
                cost=cost, status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def _make_simulated_result(self, prompt: str, start: float, provider: str) -> ModelResult:
        latency = (time.perf_counter() - start) * 1000
        return ModelResult(
            model_config=self._config, prompt_template=prompt,
            response=f"[{provider} {self._config.model_name} simulated]",
            latency_ms=round(latency, 2), token_count=len(prompt.split()) + 50,
            cost=0.0, status=TestStatus.COMPLETED,
        )

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.001, 0.002))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class AnthropicProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "claude-3-opus": (0.015, 0.075), "claude-3-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
    }

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-ant-")
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "Anthropic")

        if SIMULATED_MODE:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "Anthropic")

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = (self._config.api_base or "https://api.anthropic.com/v1") + "/messages"
            headers = {
                "x-api-key": key, "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self._config.max_tokens or 1024,
            }
            data = await self._http_post(url, headers, payload)
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config, prompt_template=prompt, response=content,
                latency_ms=round(latency, 2), token_count=input_tokens + output_tokens,
                cost=cost, status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.003, 0.015))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class DeepSeekProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "deepseek-chat": (0.00014, 0.00028),
        "deepseek-reasoner": (0.00055, 0.00219),
    }

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return key.startswith("sk-") and len(key) > 20
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "DeepSeek")

        if SIMULATED_MODE:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "DeepSeek")

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = (self._config.api_base or "https://api.deepseek.com/v1") + "/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }
            data = await self._http_post(url, headers, payload)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config, prompt_template=prompt, response=content,
                latency_ms=round(latency, 2), token_count=input_tokens + output_tokens,
                cost=cost, status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.00014, 0.00028))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class HuaweiProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "pangu-large": (0.012, 0.036), "pangu-medium": (0.004, 0.012),
        "pangu-nlp": (0.003, 0.009), "pangu-vision": (0.008, 0.024),
        "qwen-72b": (0.006, 0.018),
    }

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 16
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "HuaweiCloud")

        if SIMULATED_MODE:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "HuaweiCloud")

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            api_base = self._config.api_base or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
            if "modelarts" in api_base.lower() or "huawei" in api_base.lower():
                url = api_base.rstrip("/") + "/chat/completions"
                headers = {"X-Auth-Token": key, "Content-Type": "application/json"}
            else:
                url = api_base.rstrip("/") + "/chat/completions"
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }
            data = await self._http_post(url, headers, payload)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                content = data.get("result", data.get("output", {}).get("text", ""))
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config, prompt_template=prompt, response=content,
                latency_ms=round(latency, 2), token_count=input_tokens + output_tokens,
                cost=cost, status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.004, 0.012))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


class AliyunProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "qwen-max": (0.004, 0.012), "qwen-plus": (0.0008, 0.002),
        "qwen-turbo": (0.0003, 0.0006), "qwen-long": (0.0005, 0.002),
    }

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-") and len(self._load_credential()) > 20
        except ProviderError:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "Aliyun")

        if SIMULATED_MODE:
            return OpenAIProvider._make_simulated_result(self, prompt, start, "Aliyun")

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = (self._config.api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1") + "/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
            }
            data = await self._http_post(url, headers, payload)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config, prompt_template=prompt, response=content,
                latency_ms=round(latency, 2), token_count=input_tokens + output_tokens,
                cost=cost, status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, (0.004, 0.012))
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000


_PROVIDER_REGISTRY: dict[ProviderType, type[BaseProvider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.ALIYUN: AliyunProvider,
    ProviderType.DEEPSEEK: DeepSeekProvider,
    ProviderType.HUAWEI: HuaweiProvider,
}


def create_provider(config: ModelConfig) -> BaseProvider:
    cls = _PROVIDER_REGISTRY.get(config.provider)
    if cls is None:
        raise ProviderError(config.provider.value, f"不支持的提供者类型: {config.provider}")
    return cls(config)


def get_cost_tracker() -> CostTracker:
    return _global_cost_tracker
