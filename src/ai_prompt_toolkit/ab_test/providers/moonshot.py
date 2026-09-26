from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class MoonshotProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "moonshot-v1-8k": (0.001, 0.001),
        "moonshot-v1-32k": (0.001, 0.001),
        "moonshot-v1-128k": (0.001, 0.001),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.001)
    _PROVIDER_LABEL: str = "Moonshot"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-") and len(self._load_credential()) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.moonshot.cn/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
