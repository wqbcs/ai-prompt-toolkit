"""Prompt缓存层 — 基于内容hash的LRU/TTL缓存

参考:
- cachetools TTLCache/LRUCache (带TTL的容量淘汰)
- functools.lru_cache (标准库LRU)
- Vercel AI SDK prompt caching (内容寻址缓存)
- 华为云LTS日志服务 (日志上报集成)

核心特性:
- PromptCache: 基于prompt_hash的TTL缓存(maxsize+ttl)
- @cached_lint/@cached_eval: 装饰器模式, 自动缓存lint/eval结果
- 华为云LTS日志上报: 缓存miss时自动上报trace
- 零依赖: 不引入cachetools, 纯Python标准库实现
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    size_bytes: int = 0

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


class PromptCache:
    def __init__(self, maxsize: int = 1024, ttl: int = 1800):
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(text: str, **kwargs: Any) -> str:
        payload = json.dumps({"t": text, "kw": kwargs}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()[:24]

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                self._log_lts("CACHE_MISS", key)
                return None
            if entry.age_seconds > self._ttl:
                del self._cache[key]
                self._misses += 1
                self._log_lts("CACHE_EXPIRED", key)
                return None
            entry.access_count += 1
            self._hits += 1
            self._log_lts("CACHE_HIT", key)
            return entry.value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._cache) >= self._maxsize:
                oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
            size = len(json.dumps(value, default=str).encode()) if isinstance(value, (dict, list)) else 0
            self._cache[key] = CacheEntry(key=key, value=value, size_bytes=size)

    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def put_batch(self, items: dict[str, Any]) -> int:
        count = 0
        for key, value in items.items():
            self.put(key, value)
            count += 1
        return count

    def get_batch(self, keys: list[str]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                results[key] = value
        return results

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def expire(self) -> int:
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items() if (now - v.created_at) > self._ttl]
            for k in expired:
                del self._cache[k]
            return len(expired)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "maxsize": self._maxsize,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
        }

    def _log_lts(self, event: str, key: str) -> None:
        try:
            lts = get_lts_logger()
            if lts.enabled:
                lts.log("INFO", f"{event} key={key} hits={self._hits} misses={self._misses}")
        except Exception:
            pass

    def cached(self, fn: Callable | None = None, *, key_fn: Callable | None = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if key_fn:
                    cache_key = key_fn(*args, **kwargs)
                elif args and isinstance(args[0], str):
                    cache_key = self.make_key(args[0], **kwargs)
                else:
                    cache_key = self.make_key(str(args), **kwargs)
                result = self.get(cache_key)
                if result is not None:
                    return result
                result = func(*args, **kwargs)
                self.put(cache_key, result)
                return result

            wrapper._cache = self  # type: ignore
            return wrapper

        if fn is not None:
            return decorator(fn)
        return decorator


_global_cache: PromptCache | None = None


def get_cache() -> PromptCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = PromptCache()
    return _global_cache


def cached_prompt(fn: Callable | None = None, **kwargs: Any) -> Callable:
    return get_cache().cached(fn, **kwargs)


@dataclass
class LTSLogEntry:
    timestamp: float = field(default_factory=time.time)
    level: str = "INFO"
    group_id: str = ""
    stream_id: str = ""
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": int(self.timestamp * 1000),
            "level": self.level,
            "group_id": self.group_id,
            "stream_id": self.stream_id,
            "content": self.content,
        }


class LTSLogger:
    def __init__(self, group_id: str = "", stream_id: str = "", endpoint: str = "", enabled: bool = False) -> None:
        self._group_id = group_id
        self._stream_id = stream_id
        self._endpoint = endpoint
        self._enabled = enabled
        self._buffer: list[LTSLogEntry] = []
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def log(self, level: str, content: str, **kwargs: Any) -> None:
        if not self._enabled:
            return
        entry = LTSLogEntry(
            level=level,
            group_id=kwargs.get("group_id", self._group_id),
            stream_id=kwargs.get("stream_id", self._stream_id),
            content=content,
        )
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= 100:
                self.flush()

    def flush(self) -> int:
        with self._lock:
            entries = self._buffer.copy()
            self._buffer.clear()
        if not entries:
            return 0
        if self._endpoint:
            try:
                import urllib.request

                payload = json.dumps(
                    {
                        "logs": [e.to_dict() for e in entries],
                    }
                ).encode()
                req = urllib.request.Request(
                    self._endpoint,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                logger.debug("LTS log flush failed (endpoint unreachable)")
        return len(entries)

    def get_buffered(self) -> list[dict[str, Any]]:
        with self._lock:
            return [e.to_dict() for e in self._buffer]


_lts_logger: LTSLogger | None = None


def get_lts_logger() -> LTSLogger:
    global _lts_logger
    if _lts_logger is None:
        _lts_logger = LTSLogger()
    return _lts_logger


def configure_lts(group_id: str, stream_id: str, endpoint: str = "", enabled: bool = True) -> LTSLogger:
    global _lts_logger
    _lts_logger = LTSLogger(group_id=group_id, stream_id=stream_id, endpoint=endpoint, enabled=enabled)
    return _lts_logger
