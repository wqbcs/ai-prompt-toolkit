"""Provider子模块自动注册机制。

参考: garak generators自动发现模式 + promptfoo provider目录结构
- importlib扫描子模块，自动发现BaseProvider子类
- _PROVIDER_REGISTRY动态构建，新增Provider仅需创建1个文件
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from ai_prompt_toolkit.ab_test.provider import BaseProvider
from ai_prompt_toolkit.ab_test.types import ProviderType

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: dict[ProviderType, type[BaseProvider]] = {}


_PROVIDER_TYPE_MAP: dict[str, ProviderType] = {
    "OpenAIProvider": ProviderType.OPENAI,
    "AnthropicProvider": ProviderType.ANTHROPIC,
    "AliyunProvider": ProviderType.ALIYUN,
    "DeepSeekProvider": ProviderType.DEEPSEEK,
    "HuaweiProvider": ProviderType.HUAWEI,
    "PanguProvider": ProviderType.PANGU,
    "GoogleProvider": ProviderType.GOOGLE,
    "MistralProvider": ProviderType.MISTRAL,
    "CohereProvider": ProviderType.COHERE,
    "GroqProvider": ProviderType.GROQ,
    "TogetherProvider": ProviderType.TOGETHER,
    "FireworksProvider": ProviderType.FIREWORKS,
    "PerplexityProvider": ProviderType.PERPLEXITY,
    "OllamaProvider": ProviderType.OLLAMA,
    "LMStudioProvider": ProviderType.LMSTUDIO,
    "ZhipuProvider": ProviderType.ZHIPU,
    "MoonshotProvider": ProviderType.MOONSHOT,
    "BaiduProvider": ProviderType.BAIDU,
    "MiniMaxProvider": ProviderType.MINIMAX,
    "HuaweiModelArtsProvider": ProviderType.HUAWEI_MODELARTS,
    "DoubaoProvider": ProviderType.DOUBAO,
    "SparkProvider": ProviderType.SPARK,
    "BaichuanProvider": ProviderType.BAICHUAN,
    "SenseNovaProvider": ProviderType.SENSENOVA,
    "FunctionGraphProvider": ProviderType.FUNCTIONGRAPH,
}


def _discover_providers() -> None:
    providers_dir = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(providers_dir)]):
        if module_info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"ai_prompt_toolkit.ab_test.providers.{module_info.name}")
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if (isinstance(obj, type)
                        and issubclass(obj, BaseProvider)
                        and obj is not BaseProvider
                        and attr_name in _PROVIDER_TYPE_MAP):
                    pt = _PROVIDER_TYPE_MAP[attr_name]
                    _PROVIDER_REGISTRY[pt] = obj
        except Exception:
            logger.warning("Failed to load provider module: %s", module_info.name, exc_info=True)


_discover_providers()


def get_registry() -> dict[ProviderType, type[BaseProvider]]:
    return dict(_PROVIDER_REGISTRY)
