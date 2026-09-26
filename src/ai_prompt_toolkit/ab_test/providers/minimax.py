from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class MiniMaxProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "MiniMax-Text-01": (0.001, 0.001),
        "abab6.5s-chat": (0.001, 0.001),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.001)
    _PROVIDER_LABEL: str = "MiniMax"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.minimax.chat/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
