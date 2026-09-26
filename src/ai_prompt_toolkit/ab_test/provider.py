"""A/B测试模型提供者 — 基础设施层

参考: promptfoo Python SDK Provider模式 + garak generators目录结构
- BaseProvider抽象基类 + httpx异步调用
- CostTracker费用控制 + SIMULATED_MODE降级
- Provider子模块自动发现注册(providers/目录)
- 健康检查(prompt-cli doctor)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_prompt_toolkit.errors import AbTestError

import asyncio
import logging
import os
import socket
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ai_prompt_toolkit.ab_test.types import ModelConfig, ModelResult, ProviderType, TestStatus

logger = logging.getLogger(__name__)

SIMULATED_MODE = not bool(os.environ.get("PROMPT_CLI_REAL_API", ""))

_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 1.0
_COST_LIMIT_USD = float(os.environ.get("PROMPT_CLI_COST_LIMIT", "10.0"))
_HTTP_TIMEOUT = 30.0
_HTTP_MAX_CONNECTIONS = 100
_HTTP_MAX_KEEPALIVE = 20


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

_shared_http_client: Any = None
_client_lock = threading.Lock()


def _get_shared_http_client() -> Any:
    global _shared_http_client
    if _shared_http_client is None:
        with _client_lock:
            if _shared_http_client is None:
                try:
                    import httpx

                    _shared_http_client = httpx.AsyncClient(
                        timeout=_HTTP_TIMEOUT,
                        limits=httpx.Limits(
                            max_connections=_HTTP_MAX_CONNECTIONS, max_keepalive_connections=_HTTP_MAX_KEEPALIVE
                        ),
                    )
                except ImportError as e:
                    raise ProviderError("system", "httpx未安装，请运行: pip install httpx") from e
    return _shared_http_client


class ProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")

    def to_ab_test_error(self) -> AbTestError:
        from ai_prompt_toolkit.errors import AbTestError

        return AbTestError(self.args[0], provider=self.provider)


class BaseProvider(ABC):
    _PRICING: dict[str, tuple[float, float]] = {}
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.002)
    _PROVIDER_LABEL: str = "Base"

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

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = self._PRICING.get(self._config.model_name, self._DEFAULT_RATES)
        return (input_tokens * rates[0] + output_tokens * rates[1]) / 1000

    def _load_credential(self) -> str:
        if self._api_key is not None:
            return self._api_key
        env_var = self._config.api_key_env
        if not env_var:
            raise ProviderError(self._config.provider.value, "未配置环境变量名")
        key = os.environ.get(env_var, "")
        if not key:
            raise ProviderError(self._config.provider.value, f"环境变量 {env_var!r} 未设置")
        self._api_key = key
        return self._api_key

    def _make_error_result(self, prompt: str, error: str) -> ModelResult:
        return ModelResult(
            model_config=self._config,
            prompt_template=prompt,
            status=TestStatus.FAILED,
            error_message=error,
        )

    def _make_simulated_result(self, prompt: str, start: float, provider: str) -> ModelResult:
        latency = (time.perf_counter() - start) * 1000
        return ModelResult(
            model_config=self._config,
            prompt_template=prompt,
            response=f"[{provider} {self._config.model_name} simulated]",
            latency_ms=round(latency, 2),
            token_count=len(prompt.split()) + 50,
            cost=0.0,
            status=TestStatus.COMPLETED,
        )

    async def _http_post(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import httpx  # noqa: F401 — 可用性探测
        except ImportError as e:
            raise ProviderError(self._config.provider.value, "httpx未安装，请运行: pip install httpx") from e

        client = _get_shared_http_client()
        delay = _RETRY_BASE_DELAY
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", delay))
                    logger.warning("429 Rate Limit, 等待 %.1fs (attempt %d/%d)", retry_after, attempt + 1, _MAX_RETRIES)
                    await asyncio.sleep(retry_after)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    logger.warning("请求失败 (attempt %d/%d): %s, %.1fs后重试", attempt + 1, _MAX_RETRIES, e, delay)
                    await asyncio.sleep(delay)
                    delay *= 2
        raise ProviderError(self._config.provider.value, f"重试{_MAX_RETRIES}次后仍失败: {last_error}")

    async def _invoke_openai_compatible(
        self,
        prompt: str,
        api_base: str,
        extra_headers: dict[str, str] | None = None,
        max_tokens_default: int | None = None,
    ) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except ProviderError:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        if SIMULATED_MODE:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = api_base.rstrip("/") + "/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            if extra_headers:
                headers.update(extra_headers)
            payload: dict[str, Any] = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
            }
            mt = self._config.max_tokens or max_tokens_default
            if mt:
                payload["max_tokens"] = mt
            data = await self._http_post(url, headers, payload)
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self.estimate_cost(input_tokens, output_tokens)
            _global_cost_tracker.record(cost)
            latency = (time.perf_counter() - start) * 1000
            return ModelResult(
                model_config=self._config,
                prompt_template=prompt,
                response=content,
                latency_ms=round(latency, 2),
                token_count=input_tokens + output_tokens,
                cost=cost,
                status=TestStatus.COMPLETED,
            )
        except Exception as e:
            return self._make_error_result(prompt, str(e))


@dataclass
class HealthCheckResult:
    provider: ProviderType
    label: str
    status: str
    latency_ms: float = 0.0
    error: str = ""
    api_key_configured: bool = False
    endpoint: str = ""


_PROVIDER_DEFAULT_ENDPOINTS: dict[ProviderType, str] = {
    ProviderType.OPENAI: "https://api.openai.com/v1",
    ProviderType.ANTHROPIC: "https://api.anthropic.com/v1",
    ProviderType.ALIYUN: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ProviderType.DEEPSEEK: "https://api.deepseek.com/v1",
    ProviderType.HUAWEI: "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
    ProviderType.PANGU: "https://infer.cn-north-4.myhuaweicloud.com",
    ProviderType.GOOGLE: "https://generativelanguage.googleapis.com/v1beta/openai",
    ProviderType.MISTRAL: "https://api.mistral.ai/v1",
    ProviderType.COHERE: "https://api.cohere.com/v2",
    ProviderType.GROQ: "https://api.groq.com/openai/v1",
    ProviderType.TOGETHER: "https://api.together.xyz/v1",
    ProviderType.FIREWORKS: "https://api.fireworks.ai/inference/v1",
    ProviderType.PERPLEXITY: "https://api.perplexity.ai",
    ProviderType.OLLAMA: "http://localhost:11434/v1",
    ProviderType.LMSTUDIO: "http://localhost:1234/v1",
    ProviderType.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
    ProviderType.MOONSHOT: "https://api.moonshot.cn/v1",
    ProviderType.BAIDU: "https://qianfan.baidubce.com/v2",
    ProviderType.MINIMAX: "https://api.minimax.chat/v1",
    ProviderType.HUAWEI_MODELARTS: "https://infer.cn-north-4.myhuaweicloud.com",
    ProviderType.DOUBAO: "https://ark.cn-beijing.volces.com/api/v3",
    ProviderType.SPARK: "https://spark-api-open.xf-yun.com/v1",
    ProviderType.BAICHUAN: "https://api.baichuan-ai.com/v1",
    ProviderType.SENSENOVA: "https://api.sensenova.cn/v1",
    ProviderType.FUNCTIONGRAPH: "https://functiongraph.cn-north-4.myhuaweicloud.com",
}

_PROVIDER_ENV_VARS: dict[ProviderType, str] = {
    ProviderType.OPENAI: "OPENAI_API_KEY",
    ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
    ProviderType.ALIYUN: "ALIYUN_API_KEY",
    ProviderType.DEEPSEEK: "DEEPSEEK_API_KEY",
    ProviderType.HUAWEI: "HUAWEI_API_KEY",
    ProviderType.PANGU: "HUAWEI_CLOUD_AK",
    ProviderType.GOOGLE: "GOOGLE_API_KEY",
    ProviderType.MISTRAL: "MISTRAL_API_KEY",
    ProviderType.COHERE: "COHERE_API_KEY",
    ProviderType.GROQ: "GROQ_API_KEY",
    ProviderType.TOGETHER: "TOGETHER_API_KEY",
    ProviderType.FIREWORKS: "FIREWORKS_API_KEY",
    ProviderType.PERPLEXITY: "PERPLEXITY_API_KEY",
    ProviderType.OLLAMA: "",
    ProviderType.LMSTUDIO: "",
    ProviderType.ZHIPU: "ZHIPU_API_KEY",
    ProviderType.MOONSHOT: "MOONSHOT_API_KEY",
    ProviderType.BAIDU: "BAIDU_API_KEY",
    ProviderType.MINIMAX: "MINIMAX_API_KEY",
    ProviderType.HUAWEI_MODELARTS: "HUAWEI_CLOUD_AK",
    ProviderType.DOUBAO: "DOUBAO_API_KEY",
    ProviderType.SPARK: "SPARK_API_KEY",
    ProviderType.BAICHUAN: "BAICHUAN_API_KEY",
    ProviderType.SENSENOVA: "SENSENOVA_API_KEY",
    ProviderType.FUNCTIONGRAPH: "HUAWEI_CLOUD_AK",
}


def _check_tcp_reachable(host: str, port: int, timeout: float = 3.0) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, (time.perf_counter() - start) * 1000
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False, (time.perf_counter() - start) * 1000


def _check_https_reachable(url: str, timeout: float = 5.0) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        import httpx

        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            return resp.status_code < 500, (time.perf_counter() - start) * 1000
    except Exception:
        return False, (time.perf_counter() - start) * 1000


def run_health_check(providers: list[ProviderType] | None = None) -> list[HealthCheckResult]:
    from ai_prompt_toolkit.ab_test.providers import get_registry

    get_registry()
    results: list[HealthCheckResult] = []
    targets = providers or list(ProviderType)

    for pt in targets:
        label = pt.value
        endpoint = _PROVIDER_DEFAULT_ENDPOINTS.get(pt, "")
        env_var = _PROVIDER_ENV_VARS.get(pt, "")
        api_key_set = bool(env_var and os.environ.get(env_var, ""))

        if pt in (ProviderType.OLLAMA, ProviderType.LMSTUDIO):
            reachable, latency = _check_tcp_reachable("localhost", 11434 if pt == ProviderType.OLLAMA else 1234)
            results.append(
                HealthCheckResult(
                    provider=pt,
                    label=label,
                    status="healthy" if reachable else "unreachable",
                    latency_ms=round(latency, 1),
                    api_key_configured=True,
                    endpoint=endpoint,
                )
            )
            continue

        if not api_key_set:
            results.append(
                HealthCheckResult(
                    provider=pt,
                    label=label,
                    status="no_api_key",
                    api_key_configured=False,
                    endpoint=endpoint,
                )
            )
            continue

        if endpoint:
            reachable, latency = _check_https_reachable(endpoint)
            if reachable:
                results.append(
                    HealthCheckResult(
                        provider=pt,
                        label=label,
                        status="healthy",
                        latency_ms=round(latency, 1),
                        api_key_configured=True,
                        endpoint=endpoint,
                    )
                )
            else:
                results.append(
                    HealthCheckResult(
                        provider=pt,
                        label=label,
                        status="unreachable",
                        latency_ms=round(latency, 1),
                        api_key_configured=True,
                        endpoint=endpoint,
                        error="连接失败",
                    )
                )
        else:
            results.append(
                HealthCheckResult(
                    provider=pt,
                    label=label,
                    status="unknown",
                    api_key_configured=api_key_set,
                    endpoint=endpoint,
                )
            )

    return results


def create_provider(config: ModelConfig) -> BaseProvider:
    from ai_prompt_toolkit.ab_test.providers import get_registry

    registry = get_registry()
    cls = registry.get(config.provider)
    if cls is None:
        raise ProviderError(config.provider.value, f"不支持的提供者类型: {config.provider}")
    return cls(config)


def get_cost_tracker() -> CostTracker:
    return _global_cost_tracker
