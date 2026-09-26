"""CLI结果缓存模块

参考promptfoo的cache机制, 基于文件内容hash缓存lint/eval结果,
避免对未变更文件重复执行耗时操作。

缓存策略:
- 以文件内容的SHA256 hash为key
- 缓存结果存储在 .prompt-cli-cache/ 目录下
- 默认TTL 24小时, 可通过配置调整
- 支持 lint/eval/security 三类缓存
- --no-cache 参数可强制跳过缓存
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CACHE_DIR_NAME = ".prompt-cli-cache"
_DEFAULT_TTL_SECONDS = 86400  # 24 hours


@dataclass
class CacheEntry:
    key: str
    category: str
    file_path: str
    content_hash: str
    timestamp: float
    ttl: float
    data: dict[str, Any]

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "data": self.data,
        }


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _cache_key(category: str, file_path: str, content_hash: str) -> str:
    return f"{category}:{file_path}:{content_hash}"


class ResultCache:
    def __init__(self, cache_dir: str | Path | None = None, ttl: float = _DEFAULT_TTL_SECONDS):
        self.ttl = ttl
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            self._cache_dir = Path.cwd() / _CACHE_DIR_NAME
        self._memory_cache: dict[str, CacheEntry] = {}

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _ensure_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        gitignore = self._cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n", encoding="utf-8")

    def _entry_path(self, key: str) -> Path:
        safe_key = key.replace(":", "_").replace("/", "_").replace("\\", "_")
        return self._cache_dir / f"{safe_key}.json"

    def get(self, category: str, file_path: str, content: str) -> dict[str, Any] | None:
        chash = _content_hash(content)
        key = _cache_key(category, file_path, chash)

        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                return entry.data
            del self._memory_cache[key]

        entry_file = self._entry_path(key)
        if entry_file.exists():
            try:
                raw = json.loads(entry_file.read_text(encoding="utf-8"))
                entry = CacheEntry(**raw)
                if not entry.is_expired():
                    self._memory_cache[key] = entry
                    return entry.data
                entry_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, TypeError, KeyError):
                entry_file.unlink(missing_ok=True)

        return None

    def put(self, category: str, file_path: str, content: str, data: dict[str, Any]) -> None:
        self._ensure_dir()
        chash = _content_hash(content)
        key = _cache_key(category, file_path, chash)
        entry = CacheEntry(
            key=key,
            category=category,
            file_path=file_path,
            content_hash=chash,
            timestamp=time.time(),
            ttl=self.ttl,
            data=data,
        )
        self._memory_cache[key] = entry

        entry_file = self._entry_path(key)
        entry_file.write_text(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def invalidate(self, category: str, file_path: str) -> int:
        count = 0
        prefix = f"{category}:{file_path}:"
        keys_to_remove = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._memory_cache[k]
            count += 1

        for f in self._cache_dir.glob("*.json"):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                if raw.get("key", "").startswith(prefix):
                    f.unlink(missing_ok=True)
                    count += 1
            except (json.JSONDecodeError, TypeError):
                pass
        return count

    def clear(self) -> int:
        count = len(self._memory_cache)
        self._memory_cache.clear()
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
                count += 1
        return count

    def stats(self) -> dict[str, Any]:
        disk_count = 0
        total_size = 0
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                disk_count += 1
                total_size += f.stat().st_size
        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": disk_count,
            "total_size_bytes": total_size,
            "cache_dir": str(self._cache_dir),
            "ttl_seconds": self.ttl,
        }
