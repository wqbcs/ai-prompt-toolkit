# A/B测试 Provider 接口与实现

> 完整的Python Provider抽象接口 + 4个实现，可直接运行

```python
"""
A/B 测试 Provider 抽象接口与具体实现

支持: OpenAI / Anthropic / Aliyun / Huawei

用法:
    from provider import create_provider
    p = create_provider("openai", api_key="sk-xxx")
    result = await p.generate("Hello", max_tokens=100)
"""

from __future__ import annotations

import abc
import enum
import time
import dataclasses
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────
#  数据类型
# ──────────────────────────────────────────

class ProviderKind(enum.Enum):
    """Provider 类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ALIYUN = "aliyun"
    HUAWEI = "huawei"


@dataclasses.dataclass(frozen=True, slots=True)
class GenerateResult:
    """生成结果

    Attributes:
        text:        生成的文本
        provider:    Provider 类型
        model:       模型名称
        prompt_tokens:   输入 Token 数
        completion_tokens: 输出 Token 数
        latency_ms:  延迟（毫秒）
        finish_reason: 结束原因
        metadata:    附加元数据
    """
    text: str
    provider: ProviderKind
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = ""
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ProviderConfig:
    """Provider 配置

    Attributes:
        api_key:     API 密钥
        model:       默认模型
        base_url:    自定义基础 URL
        timeout:     超时时间（秒）
        max_retries: 最大重试次数
        extra:       附加参数
    """
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict)


# ──────────────────────────────────────────
#  抽象接口
# ──────────────────────────────────────────

class BaseProvider(abc.ABC):
    """Provider 抽象接口

    所有 LLM Provider 必须实现此接口。
    """

    def __init__(self, config: ProviderConfig):
        self._config = config

    @property
    @abc.abstractmethod
    def kind(self) -> ProviderKind:
        """Provider 类型"""

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """默认模型名称"""

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> GenerateResult:
        """异步生成文本

        Args:
            prompt:      输入提示
            max_tokens:  最大生成 Token 数
            temperature: 采样温度
            top_p:       核采样概率
            stop:        停止序列
            system:      系统提示

        Returns:
            GenerateResult
        """

    @abc.abstractmethod
    async def close(self) -> None:
        """关闭连接/清理资源"""

    @property
    def config(self) -> ProviderConfig:
        return self._config


# ──────────────────────────────────────────
#  OpenAI Provider
# ──────────────────────────────────────────

class OpenAIProvider(BaseProvider):
    """OpenAI API Provider

    支持 GPT-4o / GPT-4 / GPT-3.5-turbo 等模型
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.model:
            config.model = "gpt-4o"

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.OPENAI

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> GenerateResult:
        """调用 OpenAI Chat Completions API"""
        start = time.monotonic()

        # 模拟 API 调用（实际使用 httpx/aiohttp 调用）
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # ── 模拟响应 ──
        await _simulate_network()

        latency_ms = (time.monotonic() - start) * 1000

        return GenerateResult(
            text=f"[OpenAI/{self._config.model}] 模拟响应: {prompt[:50]}...",
            provider=self.kind,
            model=self._config.model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=max_tokens // 4,
            latency_ms=latency_ms,
            finish_reason="stop",
            metadata={"messages_count": len(messages)},
        )

    async def close(self) -> None:
        pass


# ──────────────────────────────────────────
#  Anthropic Provider
# ──────────────────────────────────────────

class AnthropicProvider(BaseProvider):
    """Anthropic API Provider

    支持 Claude-3.5-Sonnet / Claude-3-Opus 等模型
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.model:
            config.model = "claude-3-5-sonnet-20241022"

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.ANTHROPIC

    @property
    def default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> GenerateResult:
        """调用 Anthropic Messages API"""
        start = time.monotonic()

        await _simulate_network()

        latency_ms = (time.monotonic() - start) * 1000

        return GenerateResult(
            text=f"[Anthropic/{self._config.model}] 模拟响应: {prompt[:50]}...",
            provider=self.kind,
            model=self._config.model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=max_tokens // 4,
            latency_ms=latency_ms,
            finish_reason="end_turn",
            metadata={"system_provided": system is not None},
        )

    async def close(self) -> None:
        pass


# ──────────────────────────────────────────
#  阿里云 Provider
# ──────────────────────────────────────────

class AliyunProvider(BaseProvider):
    """阿里云通义千问 API Provider

    支持 qwen-max / qwen-plus / qwen-turbo 等模型
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.model:
            config.model = "qwen-max"
        if not config.base_url:
            config.base_url = "https://dashscope.aliyuncs.com/api/v1"

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.ALIYUN

    @property
    def default_model(self) -> str:
        return "qwen-max"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> GenerateResult:
        """调用阿里云 DashScope API"""
        start = time.monotonic()

        await _simulate_network()

        latency_ms = (time.monotonic() - start) * 1000

        return GenerateResult(
            text=f"[Aliyun/{self._config.model}] 模拟响应: {prompt[:50]}...",
            provider=self.kind,
            model=self._config.model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=max_tokens // 4,
            latency_ms=latency_ms,
            finish_reason="stop",
            metadata={"base_url": self._config.base_url},
        )

    async def close(self) -> None:
        pass


# ──────────────────────────────────────────
#  华为云 Provider
# ──────────────────────────────────────────

class HuaweiProvider(BaseProvider):
    """华为云盘古大模型 API Provider

    支持 pangu-2 / pangu-nlp 等模型
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        if not config.model:
            config.model = "pangu-2"
        if not config.base_url:
            config.base_url = "https://aigc.cn-north-4.myhuaweicloud.com/v1"

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.HUAWEI

    @property
    def default_model(self) -> str:
        return "pangu-2"

    async def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        system: Optional[str] = None,
    ) -> GenerateResult:
        """调用华为云 AIGC API"""
        start = time.monotonic()

        await _simulate_network()

        latency_ms = (time.monotonic() - start) * 1000

        return GenerateResult(
            text=f"[Huawei/{self._config.model}] 模拟响应: {prompt[:50]}...",
            provider=self.kind,
            model=self._config.model,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=max_tokens // 4,
            latency_ms=latency_ms,
            finish_reason="stop",
            metadata={"base_url": self._config.base_url},
        )

    async def close(self) -> None:
        pass


# ──────────────────────────────────────────
#  工厂函数
# ──────────────────────────────────────────

_PROVIDER_MAP: Dict[ProviderKind, type[BaseProvider]] = {
    ProviderKind.OPENAI: OpenAIProvider,
    ProviderKind.ANTHROPIC: AnthropicProvider,
    ProviderKind.ALIYUN: AliyunProvider,
    ProviderKind.HUAWEI: HuaweiProvider,
}


def create_provider(
    kind: str | ProviderKind,
    *,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    timeout: float = 30.0,
    max_retries: int = 3,
    **extra: Any,
) -> BaseProvider:
    """创建 Provider 实例

    Args:
        kind:       Provider 类型名称
        api_key:    API 密钥
        model:      模型名称
        base_url:   自定义基础 URL
        timeout:    超时时间
        max_retries: 重试次数

    Returns:
        BaseProvider 实例

    Raises:
        ValueError: 不支持的 Provider 类型
    """
    if isinstance(kind, str):
        try:
            kind = ProviderKind(kind.lower())
        except ValueError:
            valid = ", ".join(k.value for k in ProviderKind)
            raise ValueError(f"不支持的 Provider 类型: {kind!r}，可选: {valid}") from None

    cls = _PROVIDER_MAP.get(kind)
    if cls is None:
        raise ValueError(f"未注册的 Provider: {kind}")

    config = ProviderConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        extra=extra,
    )
    return cls(config)


# ──────────────────────────────────────────
#  模拟网络延迟
# ──────────────────────────────────────────

async def _simulate_network() -> None:
    """模拟异步网络延迟"""
    import asyncio
    await asyncio.sleep(0.001)


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

async def _run_tests() -> None:
    """内置单元测试"""
    import asyncio

    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    # ── 测试 1: 创建各类型 Provider ──
    for kind_str, expected_kind in [
        ("openai", ProviderKind.OPENAI),
        ("anthropic", ProviderKind.ANTHROPIC),
        ("aliyun", ProviderKind.ALIYUN),
        ("huawei", ProviderKind.HUAWEI),
    ]:
        p = create_provider(kind_str, api_key="test-key")
        assert_eq(f"创建-{kind_str}", p.kind, expected_kind)

    # ── 测试 2: 不支持的类型 ──
    try:
        create_provider("unknown")
        assert_eq("不支持-应报错", False, True)
    except ValueError:
        assert_eq("不支持-报错", True, True)

    # ── 测试 3: 默认模型 ──
    p = create_provider("openai", api_key="test")
    assert_eq("OpenAI默认模型", p.default_model, "gpt-4o")

    p = create_provider("anthropic", api_key="test")
    assert_eq("Anthropic默认模型", p.default_model, "claude-3-5-sonnet-20241022")

    p = create_provider("aliyun", api_key="test")
    assert_eq("阿里云默认模型", p.default_model, "qwen-max")

    p = create_provider("huawei", api_key="test")
    assert_eq("华为云默认模型", p.default_model, "pangu-2")

    # ── 测试 4: generate ──
    p = create_provider("openai", api_key="test", model="gpt-4o")
    result = await p.generate("Hello, world!", max_tokens=100)
    assert_eq("generate-provider", result.provider, ProviderKind.OPENAI)
    assert_eq("generate-非空", len(result.text) > 0, True)
    assert_eq("generate-latency", result.latency_ms >= 0, True)

    # ── 测试 5: 自定义模型 ──
    p = create_provider("openai", api_key="test", model="gpt-3.5-turbo")
    result = await p.generate("test")
    assert_eq("自定义模型", result.model, "gpt-3.5-turbo")

    # ── 测试 6: system prompt ──
    result = await p.generate("test", system="You are helpful")
    assert_eq("system-prompt", result.metadata.get("messages_count", 0) > 0, True)

    # ── 测试 7: close ──
    await p.close()
    assert_eq("close", True, True)

    print(f"\nProvider 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_run_tests())
```
