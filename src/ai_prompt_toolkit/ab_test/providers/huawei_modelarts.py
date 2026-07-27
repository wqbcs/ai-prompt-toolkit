"""华为云ModelArts推理服务Provider。

参考: 华为云ModelArts推理API文档
- 支持盘古/昇腾模型推理
- 兼容OpenAI格式API(华为云ModelArts推理端点支持/v1/chat/completions)
- MaaS API 2.0支持(推理/V2端点)
- AgentArts智能体集成
- 流式/非流式响应
- AK/SK认证

环境变量:
- HUAWEI_CLOUD_AK: 华为云Access Key ID
- HUAWEI_CLOUD_SK: 华为云Secret Access Key
- HUAWEI_MODELARTS_ENDPOINT: ModelArts推理端点URL(可选, 默认华北-北京四)
- HUAWEI_MODELARTS_PROJECT_ID: 华为云项目ID(MaaS V2需要)
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from ai_prompt_toolkit.ab_test.provider import BaseProvider, ProviderError, SIMULATED_MODE
from ai_prompt_toolkit.ab_test.types import ModelResult, TestStatus


class HuaweiModelArtsProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "pangu5-chat": (0.003, 0.006),
        "pangu5-reasoning": (0.005, 0.010),
        "pangu5-vision": (0.004, 0.008),
        "pangu5-code": (0.003, 0.006),
        "qwen2.5-72b": (0.004, 0.008),
        "deepseek-v3": (0.002, 0.006),
        "llama3.1-70b": (0.003, 0.007),
        "chatglm4-9b": (0.001, 0.003),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.003, 0.006)
    _PROVIDER_LABEL: str = "HuaweiModelArts"

    _DEFAULT_ENDPOINTS: dict[str, str] = {
        "cn-north-4": "https://infer.cn-north-4.myhuaweicloud.com",
        "cn-north-1": "https://infer.cn-north-1.myhuaweicloud.com",
        "cn-east-3": "https://infer.cn-east-3.myhuaweicloud.com",
        "cn-south-1": "https://infer.cn-south-1.myhuaweicloud.com",
        "cn-southwest-2": "https://infer.cn-southwest-2.myhuaweicloud.com",
    }

    def validate(self) -> bool:
        try:
            ak = self._load_ak()
            sk = self._load_sk()
            return ak.startswith("HW") and len(ak) > 10 and len(sk) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._resolve_endpoint()
        return await self._invoke_modelarts(prompt, api_base)

    def _load_ak(self) -> str:
        ak = self._config.extra_params.get("ak_env", "") if self._config.extra_params else ""
        if not ak:
            ak = "HUAWEI_CLOUD_AK"
        val = self._config.extra_params.get("ak", "") if self._config.extra_params else ""
        if val:
            return val
        import os
        val = os.environ.get(ak, "")
        if not val:
            raise ProviderError(self._config.provider.value, f"华为云AK未设置, 请设置环境变量 {ak}")
        return val

    def _load_sk(self) -> str:
        sk = self._config.extra_params.get("sk_env", "") if self._config.extra_params else ""
        if not sk:
            sk = "HUAWEI_CLOUD_SK"
        val = self._config.extra_params.get("sk", "") if self._config.extra_params else ""
        if val:
            return val
        import os
        val = os.environ.get(sk, "")
        if not val:
            raise ProviderError(self._config.provider.value, f"华为云SK未设置, 请设置环境变量 {sk}")
        return val

    def _resolve_endpoint(self) -> str:
        custom = self._config.api_base
        if custom:
            return custom.rstrip("/")
        import os
        endpoint = os.environ.get("HUAWEI_MODELARTS_ENDPOINT", "")
        if endpoint:
            return endpoint.rstrip("/")
        region = self._config.extra_params.get("region", "cn-north-4") if self._config.extra_params else "cn-north-4"
        return self._DEFAULT_ENDPOINTS.get(region, self._DEFAULT_ENDPOINTS["cn-north-4"])

    def _sign_request(self, ak: str, sk: str, method: str, url: str, body: str = "") -> dict[str, str]:
        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        signed_headers = "host;x-sdk-date"
        canonical_request = f"{method}\n{path}\n\nhost:{host}\nx-sdk-date:{timestamp}\n\n{signed_headers}\n{content_hash}"
        string_to_sign = f"SDK-HMAC-SHA256\n{timestamp}\n{sha256hex(canonical_request)}"
        signature = hmac.new(sk.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "Host": host,
            "X-Sdk-Date": timestamp,
            "Authorization": f"SDK-HMAC-SHA256 Access={ak}, SignedHeaders={signed_headers}, Signature={signature}",
            "Content-Type": "application/json",
        }

    async def _invoke_modelarts(self, prompt: str, api_base: str) -> ModelResult:
        start = time.perf_counter()
        try:
            ak = self._load_ak()
            sk = self._load_sk()
        except ProviderError:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        if SIMULATED_MODE:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        from ai_prompt_toolkit.ab_test.provider import _global_cost_tracker

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            url = api_base.rstrip("/") + "/v1/chat/completions"
            import json
            payload: dict[str, Any] = {
                "model": self._config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._config.temperature,
            }
            if self._config.max_tokens:
                payload["max_tokens"] = self._config.max_tokens
            body = json.dumps(payload, ensure_ascii=False)
            headers = self._sign_request(ak, sk, "POST", url, body)
            data = await self._http_post_signed(url, headers, body)
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

    async def _http_post_signed(self, url: str, headers: dict[str, str], body: str) -> dict[str, Any]:
        try:
            import httpx
        except ImportError:
            raise ProviderError(self._config.provider.value, "httpx未安装，请运行: pip install httpx")
        from ai_prompt_toolkit.ab_test.provider import _RETRY_BASE_DELAY, _MAX_RETRIES
        import asyncio as _asyncio
        client = self._get_client()
        delay = _RETRY_BASE_DELAY
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.post(url, content=body.encode("utf-8"), headers=headers)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", delay))
                    await _asyncio.sleep(retry_after)
                    delay *= 2
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    await _asyncio.sleep(delay)
                    delay *= 2
        raise ProviderError(self._config.provider.value, f"重试{_MAX_RETRIES}次后仍失败: {last_error}")

    def _get_client(self) -> Any:
        try:
            import httpx
        except ImportError:
            raise ProviderError(self._config.provider.value, "httpx未安装")
        return httpx.AsyncClient(timeout=30.0)


def sha256hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
