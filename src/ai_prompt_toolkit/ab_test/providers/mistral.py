from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class MistralProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "mistral-large-latest": (0.004, 0.012),
        "mistral-medium-latest": (0.0027, 0.0081),
        "mistral-small-latest": (0.0002, 0.0006),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0002, 0.0006)
    _PROVIDER_LABEL: str = "Mistral"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.mistral.ai/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
