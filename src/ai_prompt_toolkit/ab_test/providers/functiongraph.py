from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.ab_test.provider import BaseProvider

if TYPE_CHECKING:
    from ai_prompt_toolkit.ab_test.types import ModelResult


class FunctionGraphProvider(BaseProvider):
    _PRICING: dict[str, tuple[float, float]] = {
        "fg-pangu2-6b": (0.0006, 0.001),
        "fg-pangu5-pro": (0.003, 0.006),
        "fg-pangu5-ultra": (0.005, 0.01),
        "fg-qwen2-7b": (0.0005, 0.001),
        "fg-deepseek-v3": (0.001, 0.002),
    }
    _DEFAULT_RATES: tuple[float, float] = (0.003, 0.006)
    _PROVIDER_LABEL: str = "FunctionGraph"

    def validate(self) -> bool:
        try:
            cred = self._load_credential()
            return len(cred) > 10
        except Exception:
            return False

    async def invoke(self, prompt: str, **kwargs: Any) -> ModelResult:
        api_base = self._config.api_base or "https://functiongraph.cn-north-4.myhuaweicloud.com"
        return await self._invoke_openai_compatible(prompt, api_base)
