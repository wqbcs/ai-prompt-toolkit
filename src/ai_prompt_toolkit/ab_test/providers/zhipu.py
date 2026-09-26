from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class ZhipuProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "glm-4": (0.001, 0.001),
        "glm-4-flash": (0.0001, 0.0001),
        "glm-4-plus": (0.005, 0.005),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.001, 0.001)
    _PROVIDER_LABEL: str = "Zhipu"

    def validate(self) -> bool:
        try:
            return len(self._load_credential()) >= 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://open.bigmodel.cn/api/paas/v4"
        return await self._invoke_openai_compatible(prompt, api_base)
