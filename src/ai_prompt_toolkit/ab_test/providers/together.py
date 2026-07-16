from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class TogetherProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "meta-llama/Llama-3-70b-chat-hf": (0.0008, 0.0008),
        "mistralai/Mixtral-8x7B-Instruct-v0.1": (0.0006, 0.0006),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0006, 0.0006)
    _PROVIDER_LABEL: str = "Together"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.together.xyz/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
