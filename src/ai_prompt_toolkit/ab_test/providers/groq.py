from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class GroqProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "llama-3.3-70b-versatile": (0.00059, 0.00079),
        "mixtral-8x7b-32768": (0.00024, 0.00024),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.00024, 0.00024)
    _PROVIDER_LABEL: str = "Groq"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("gsk_")
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.groq.com/openai/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
