from __future__ import annotations

import time
from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider, SIMULATED_MODE, _global_cost_tracker
from ai_prompt_toolkit.ab_test.types import ModelResult, TestStatus


class HuaweiProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "pangu-large": (0.012, 0.036), "pangu-medium": (0.004, 0.012),
        "pangu-nlp": (0.003, 0.009), "pangu-vision": (0.008, 0.024),
        "qwen-72b": (0.006, 0.018),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.004, 0.012)
    _PROVIDER_LABEL: str = "HuaweiCloud"

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
            api_base = self._config.api_base or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
            url = api_base.rstrip("/") + "/chat/completions"
            if "modelarts" in api_base.lower() or "huawei" in api_base.lower():
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
