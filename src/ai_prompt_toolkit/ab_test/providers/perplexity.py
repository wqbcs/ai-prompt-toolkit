from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class PerplexityProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "llama-3.1-sonar-large-128k-online": (0.001, 0.001),
        "llama-3.1-sonar-small-128k-online": (0.0002, 0.0002),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0002, 0.0002)
    _PROVIDER_LABEL: str = "Perplexity"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("pplx-")
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.perplexity.ai"
        return await self._invoke_openai_compatible(prompt, api_base)
