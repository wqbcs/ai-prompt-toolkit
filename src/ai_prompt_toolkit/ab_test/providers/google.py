from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class GoogleProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "gemini-1.5-pro": (0.0035, 0.0105), "gemini-1.5-flash": (0.000075, 0.0003),
        "gemini-pro": (0.0005, 0.0015),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0005, 0.0015)
    _PROVIDER_LABEL: str = "Google"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://generativelanguage.googleapis.com/v1beta/openai"
        return await self._invoke_openai_compatible(prompt, api_base)
