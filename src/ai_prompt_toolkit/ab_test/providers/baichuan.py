from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class BaichuanProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "baichuan2-turbo": (0.001, 0.001),
        "baichuan2-53b": (0.002, 0.002),
        "baichuan2-7b": (0.0005, 0.0005),
        "baichuan-4": (0.001, 0.001),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.001)
    _PROVIDER_LABEL: str = "Baichuan"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-") and len(self._load_credential()) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.baichuan-ai.com/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
