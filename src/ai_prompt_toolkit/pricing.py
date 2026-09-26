"""PricingCatalog — 模型定价单一加载入口（F3/D1: 数据外部化, 去硬编码）

定价数据采用 **LiteLLM schema**（行业事实标准, https://github.com/BerriAI/litellm）:
    input_cost_per_token / output_cost_per_token / max_tokens / litellm_provider / mode

加载链（后者覆盖前者, 均为可选）:
    1. 内置: src/ai_prompt_toolkit/data/model_pricing.json
    2. 环境变量 PROMPT_TOOLKIT_PRICING 指向的 JSON 文件
    3. 项目 .prompt-toolkit/pricing.json（CWD）
    4. 显式传入的 extra_paths

匹配语义: 精确匹配 → 最长前缀匹配 → "default" 条目。
（修复历史缺陷: token_analyzer 曾用 dict 首个前缀命中, "gpt-4o" 被 "gpt-4" 挡住误用其价格）
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BUILTIN_PRICING_PATH = Path(__file__).resolve().parent / "data" / "model_pricing.json"
ENV_PRICING_VAR = "PROMPT_TOOLKIT_PRICING"
USER_PRICING_RELPATH = Path(".prompt-toolkit") / "pricing.json"
DEFAULT_MODEL_KEY = "default"


@dataclass(frozen=True)
class ModelPricing:
    input_cost_per_token: float
    output_cost_per_token: float
    max_tokens: int | None = None
    litellm_provider: str = ""
    mode: str = "chat"


class PricingCatalog:
    def __init__(self, entries: dict[str, dict[str, Any]]):
        # 剔除元数据键(_开头), 保留 default
        self._entries: dict[str, dict[str, Any]] = {
            k: v for k, v in entries.items() if not k.startswith("_")
        }

    @classmethod
    def load(cls, extra_paths: list[Path | str] | None = None,
             include_user_override: bool = True) -> PricingCatalog:
        merged: dict[str, dict[str, Any]] = {}
        paths: list[Path] = [BUILTIN_PRICING_PATH]
        if include_user_override:
            env_path = os.environ.get(ENV_PRICING_VAR)
            if env_path:
                paths.append(Path(env_path))
            paths.append(Path.cwd() / USER_PRICING_RELPATH)
        for p in extra_paths or []:
            paths.append(Path(p))
        for path in paths:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(f"定价文件格式错误(需JSON对象): {path}")
                merged.update(data)
        return cls(merged)

    @property
    def model_keys(self) -> list[str]:
        return sorted(self._entries)

    def get(self, model: str) -> ModelPricing | None:
        """精确匹配 → 最长前缀匹配（长度相同的键按字母序保证确定性）"""
        if model in self._entries:
            return self._to_pricing(self._entries[model])
        lowered = model.lower()
        candidates = [k for k in self._entries if k != DEFAULT_MODEL_KEY and lowered.startswith(k.lower())]
        if candidates:
            best = max(candidates, key=lambda k: (len(k), k))
            return self._to_pricing(self._entries[best])
        return None

    def get_or_default(self, model: str) -> ModelPricing:
        pricing = self.get(model)
        if pricing is not None:
            return pricing
        default = self._entries.get(DEFAULT_MODEL_KEY)
        if default is not None:
            return self._to_pricing(default)
        return ModelPricing(input_cost_per_token=0.0, output_cost_per_token=0.0)

    def estimate_cost_usd(self, model: str, input_tokens: int, output_tokens: int) -> float:
        p = self.get_or_default(model)
        return input_tokens * p.input_cost_per_token + output_tokens * p.output_cost_per_token

    @staticmethod
    def _to_pricing(entry: dict[str, Any]) -> ModelPricing:
        return ModelPricing(
            input_cost_per_token=float(entry.get("input_cost_per_token", 0.0)),
            output_cost_per_token=float(entry.get("output_cost_per_token", 0.0)),
            max_tokens=entry.get("max_tokens"),
            litellm_provider=str(entry.get("litellm_provider", "")),
            mode=str(entry.get("mode", "chat")),
        )


_CATALOG: PricingCatalog | None = None


def get_catalog(refresh: bool = False) -> PricingCatalog:
    """进程级默认目录（懒加载; 测试可用 refresh=True 重建）"""
    global _CATALOG
    if _CATALOG is None or refresh:
        _CATALOG = PricingCatalog.load()
    return _CATALOG
