from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class SenseNovaProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "sensenova-5.0": (0.002, 0.006),
        "sensenova-4.0": (0.001, 0.003),
        "sensenova-3.5": (0.0005, 0.001),
        "nova-ptc-xl": (0.001, 0.002),
        "nova-ptc-large": (0.002, 0.004),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.002, 0.006)
    _PROVIDER_LABEL: str = "SenseNova"

    def validate(self) -> bool:
        try:
            cred = self._load_credential()
            return len(cred) > 10
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://api.sensenova.cn/v1"
        return await self._invoke_openai_compatible(prompt, api_base)
