from __future__ import annotations

import time
from typing import Any

from ai_prompt_toolkit.ab_test.provider import SIMULATED_MODE, BaseProvider, _global_cost_tracker
from ai_prompt_toolkit.ab_test.types import ModelResult, TestStatus


class AnthropicProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
        "claude-3-haiku": (0.00025, 0.00125),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.003, 0.015)
    _PROVIDER_LABEL: str = "Anthropic"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-ant-")
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
            url = (self._config.api_base or "https://api.anthropic.com/v1") + "/messages"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
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
