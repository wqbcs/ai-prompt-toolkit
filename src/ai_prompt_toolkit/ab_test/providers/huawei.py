from __future__ import annotations

import time
from typing import Any

from ai_prompt_toolkit.ab_test.provider import SIMULATED_MODE, BaseProvider, _global_cost_tracker
from ai_prompt_toolkit.ab_test.types import ModelResult, TestStatus


class HuaweiProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "pangu-large": (0.012, 0.036), "pangu-medium": (0.004, 0.012),
        "pangu-nlp": (0.003, 0.009), "pangu-vision": (0.008, 0.024),
        "pangu-code": (0.006, 0.018), "pangu-search": (0.005, 0.015),
        "pangu-nlp-65b": (0.004, 0.012), "pangu-nlp-7b": (0.001, 0.003),
        "pangu-prediction": (0.005, 0.015), "pangu-multimodal": (0.008, 0.024),
        "pangu-scientific": (0.010, 0.030),
        "qwen-72b": (0.006, 0.018),
        "deepseek-v3": (0.0014, 0.0028),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.004, 0.012)
    _PROVIDER_LABEL: str = "HuaweiCloud"
    _HUAWEI_MODELARTS_BASE = "https://modelarts.cn-north-4.myhuaweicloud.com/v1"
    _HUAWEI_MAAS_BASE = "https://maas.cn-north-4.myhuaweicloud.com/v1"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 16
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        start = time.perf_counter()
        try:
            key = self._load_credential()
        except Exception:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        if SIMULATED_MODE:
            return self._make_simulated_result(prompt, start, self._PROVIDER_LABEL)

        if _global_cost_tracker.limit_reached:
            return self._make_error_result(prompt, f"费用超限(${_global_cost_tracker.limit:.2f})")

        try:
            api_base = self._config.api_base or self._HUAWEI_MODELARTS_BASE
            url = api_base.rstrip("/") + "/chat/completions"
            if "maas" in api_base.lower():
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            elif "modelarts" in api_base.lower() or "huawei" in api_base.lower():
                headers = {"X-Auth-Token": key, "Content-Type": "application/json"}
            else:
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
