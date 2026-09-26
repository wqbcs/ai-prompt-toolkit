from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class AliyunProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "qwen-max": (0.004, 0.012),
        "qwen-plus": (0.0008, 0.002),
        "qwen-turbo": (0.0003, 0.0006),
        "qwen-long": (0.0005, 0.002),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.004, 0.012)
    _PROVIDER_LABEL: str = "Aliyun"

    def validate(self) -> bool:
        try:
            return self._load_credential().startswith("sk-") and len(self._load_credential()) > 20
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
