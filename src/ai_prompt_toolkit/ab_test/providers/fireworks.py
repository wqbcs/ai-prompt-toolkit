from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class FireworksProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "accounts/fireworks/models/llama-v3p1-70b-instruct": (0.0009, 0.0009),
        "accounts/fireworks/models/mixtral-8x7b-instruct": (0.0005, 0.0005),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0005, 0.0005)
    _PROVIDER_LABEL: str = "Fireworks"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.fireworks.ai/inference/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
