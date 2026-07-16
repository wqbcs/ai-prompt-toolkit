from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ModelResult


class OllamaProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {}
    _DEFAULT_RATES: tuple[float, float] = (0.0, 0.0)
    _PROVIDER_LABEL: str = "Ollama"

    def validate(self) -> bool:
        return True

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "http://localhost:11434/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
