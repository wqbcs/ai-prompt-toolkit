"""条件编译 LRU 缓存，基于 SHA-256 键和 cachetools.LRUCache。"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any

from cachetools import LRUCache

if TYPE_CHECKING:
    from ai_prompt_toolkit.compiler.types import CompileResult

_DEFAULT_MAXSIZE = 1000
_DEFAULT_TTL_SECONDS = 3600


class CompileCache:
    """条件编译结果 LRU 缓存。

    缓存键由模板源码 + 编译上下文 JSON 的 SHA-256 哈希生成。
    支持 TTL 过期和容量限制。

    Args:
        maxsize: 最大缓存条目数，默认 1000。
        ttl_seconds: 缓存条目生存时间（秒），默认 3600（1 小时）。
    """

    def __init__(
        self,
        maxsize: int = _DEFAULT_MAXSIZE,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._ttl = ttl_seconds
        self._store: LRUCache[str, tuple[float, CompileResult]] = LRUCache(maxsize=maxsize)

    @staticmethod
    def _make_key(source: str, context_dict: dict[str, Any]) -> str:
        """根据模板源码和上下文字典生成 SHA-256 缓存键。"""
        payload = json.dumps(
            {"source": source, "context": context_dict},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, source: str, context_dict: dict[str, Any]) -> CompileResult | None:
        """尝试获取缓存结果。

        Args:
            source: 模板源码。
            context_dict: CompileContext.to_dict() 的输出。

        Returns:
            缓存命中时返回 CompileResult（cache_hit 已置 True），否则返回 None。
        """
        key = self._make_key(source, context_dict)
        entry = self._store.get(key)
        if entry is None:
            return None

        stored_at, result = entry
        if time.monotonic() - stored_at > self._ttl:
            del self._store[key]
            return None

        result.cache_hit = True
        result.report.cache_hit = True
        return result

    def set(
        self,
        source: str,
        context_dict: dict[str, Any],
        result: CompileResult,
    ) -> None:
        """写入缓存。

        Args:
            source: 模板源码。
            context_dict: CompileContext.to_dict() 的输出。
            result: 编译结果。
        """
        key = self._make_key(source, context_dict)
        self._store[key] = (time.monotonic(), result)

    def clear(self) -> None:
        """清空缓存。"""
        self._store.clear()

    @property
    def size(self) -> int:
        """当前缓存条目数。"""
        return len(self._store)
