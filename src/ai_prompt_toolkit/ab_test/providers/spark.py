from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class SparkProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "spark-v3.5": (0.003, 0.003),
        "spark-v3.0": (0.002, 0.002),
        "spark-v2.0": (0.001, 0.001),
        "spark-lite": (0.0005, 0.0005),
        "spark-pro": (0.003, 0.003),
        "spark-max": (0.004, 0.004),
        "spark-4.0-ultra": (0.005, 0.005),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.003, 0.003)
    _PROVIDER_LABEL: str = "Spark"

    def validate(self) -> bool:
        try:
            cred = self._load_credential()
            return ":" in cred and len(cred) > 10
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://spark-api-open.xf-yun.com/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
