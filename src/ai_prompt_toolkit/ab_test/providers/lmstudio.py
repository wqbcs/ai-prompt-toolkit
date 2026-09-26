from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class LMStudioProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {}
    _DEFAULT_RATES: tuple[float, float] = (0.0, 0.0)
    _PROVIDER_LABEL: str = "LMStudio"

    def validate(self) -> bool:
        return True

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "http://localhost:1234/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
