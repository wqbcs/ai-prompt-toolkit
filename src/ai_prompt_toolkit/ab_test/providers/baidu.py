from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class BaiduProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "ernie-4.0-8k": (0.012, 0.012),
        "ernie-3.5-8k": (0.0012, 0.0012),
        "ernie-speed-8k": (0.0, 0.0),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.0012, 0.0012)
    _PROVIDER_LABEL: str = "Baidu"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://qianfan.baidubce.com/v2"
        return await self._invoke_openai_compatible(prompt, api_base)
