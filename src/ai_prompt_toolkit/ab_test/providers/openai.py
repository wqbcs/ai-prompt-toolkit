from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class OpenAIProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.002)
    _PROVIDER_LABEL: str = "OpenAI"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-")
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.openai.com/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
