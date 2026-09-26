from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class DoubaoProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "doubao-pro-4k": (0.0008, 0.002),
        "doubao-pro-32k": (0.0005, 0.001),
        "doubao-pro-128k": (0.0005, 0.001),
        "doubao-lite-4k": (0.0003, 0.0006),
        "doubao-lite-32k": (0.0003, 0.0006),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0008, 0.002)
    _PROVIDER_LABEL: str = "Doubao"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("doubao-") or len(self._load_credential()) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://ark.cn-beijing.volces.com/api/v3"
        return await self._invoke_openai_compatible(prompt, api_base)
