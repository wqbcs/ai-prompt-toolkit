from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class DeepSeekProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "deepseek-chat": (0.00014, 0.00028),
        "deepseek-reasoner": (0.00055, 0.00219),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.00014, 0.00028)
    _PROVIDER_LABEL: str = "DeepSeek"

    def validate(self) -> bool:
        try:
            key = self._load_credential()
            return key.startswith("sk-") and len(key) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.deepseek.com/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
