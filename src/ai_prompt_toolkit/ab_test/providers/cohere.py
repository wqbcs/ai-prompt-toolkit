from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class CohereProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "command-r-plus": (0.0025, 0.01), "command-r": (0.0005, 0.0015),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0005, 0.0015)
    _PROVIDER_LABEL: str = "Cohere"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.cohere.com/v2"
        return await self._invoke_openai_compatible(prompt, api_base)
