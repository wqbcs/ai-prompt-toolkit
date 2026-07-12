# 条件编译LRU缓存 (Cache)

> 完整的Python LRU缓存实现，可直接运行

```python
"""
条件编译 LRU 缓存 — 基于内容哈希的编译结果缓存

特性:
    - SHA256 缓存键（源文本 + 变量 + 环境组合）
    - TTL 过期淘汰
    - LRU 淘汰策略
    - 线程安全（可选）

用法:
    from cache import LRUCache, CacheEntry
    cache = LRUCache(max_size=100, ttl_seconds=3600)
    key = LRUCache.make_key(source, variables, env)
    cache.put(key, "cached output")
    result = cache.get(key)
"""

from __future__ import annotations

import hashlib
import json
import time
import threading
import dataclasses
from typing import Any, Dict, Optional, OrderedDict


# ──────────────────────────────────────────
#  缓存条目
# ──────────────────────────────────────────

@dataclasses.dataclass
class CacheEntry:
    """缓存条目

    Attributes:
        key:       SHA256 缓存键
        value:     缓存值
        created_at: 创建时间戳
        accessed_at: 最后访问时间戳
        hit_count: 命中次数
        size_bytes: 估算占用字节
    """
    key: str
    value: Any
    created_at: float
    accessed_at: float
    hit_count: int = 0
    size_bytes: int = 0

    def touch(self) -> None:
        """更新访问时间和命中次数"""
        self.accessed_at = time.monotonic()
        self.hit_count += 1

    @property
    def age_seconds(self) -> float:
        """条目年龄（秒）"""
        return time.monotonic() - self.created_at


# ──────────────────────────────────────────
#  LRU 缓存
# ──────────────────────────────────────────

class LRUCache:
    """基于 SHA256 键的 LRU 缓存

    支持:
        - 最大容量限制 + LRU 淘汰
        - TTL 过期淘汰
        - 缓存统计
        - 线程安全（通过 lock 参数启用）

    Args:
        max_size:     最大条目数
        ttl_seconds:  生存时间（秒），0 表示永不过期
        thread_safe:  是否启用线程安全锁
    """

    def __init__(
        self,
        max_size: int = 128,
        ttl_seconds: float = 0,
        thread_safe: bool = False,
    ):
        if max_size <= 0:
            raise ValueError(f"max_size 必须为正数, 得到 {max_size}")

        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock() if thread_safe else None

        # 统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    # ── 公开接口 ──

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        Args:
            key: SHA256 缓存键

        Returns:
            缓存值，未命中或已过期返回 None
        """
        with self._lock_or_noop():
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None

            if self._is_expired(entry):
                del self._store[key]
                self._misses += 1
                self._evictions += 1
                return None

            # LRU: 移到末尾
            self._store.move_to_end(key)
            entry.touch()
            self._hits += 1
            return entry.value

    def put(self, key: str, value: Any, size_bytes: int = 0) -> None:
        """写入缓存

        Args:
            key:        SHA256 缓存键
            value:      缓存值
            size_bytes: 估算大小（字节）
        """
        with self._lock_or_noop():
            now = time.monotonic()

            if key in self._store:
                self._store.move_to_end(key)
                self._store[key].value = value
                self._store[key].accessed_at = now
                self._store[key].size_bytes = size_bytes
                return

            # 淘汰
            while len(self._store) >= self._max_size:
                self._evict_one()

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                size_bytes=size_bytes,
            )
            self._store[key] = entry

    def invalidate(self, key: str) -> bool:
        """使指定缓存键失效

        Returns:
            是否成功删除
        """
        with self._lock_or_noop():
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock_or_noop():
            self._store.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def purge_expired(self) -> int:
        """清理所有过期条目

        Returns:
            清理的条目数
        """
        if self._ttl <= 0:
            return 0

        with self._lock_or_noop():
            expired_keys = [
                k for k, v in self._store.items() if self._is_expired(v)
            ]
            for k in expired_keys:
                del self._store[k]
                self._evictions += 1
            return len(expired_keys)

    @property
    def size(self) -> int:
        """当前缓存条目数"""
        return len(self._store)

    @property
    def stats(self) -> Dict[str, Any]:
        """缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 4),
            "ttl_seconds": self._ttl,
        }

    # ── 静态工具 ──

    @staticmethod
    def make_key(source: str, variables: Dict[str, Any], env: str = "") -> str:
        """生成 SHA256 缓存键

        Args:
            source:    原始源文本
            variables: 变量字典
            env:       环境标识

        Returns:
            SHA256 十六进制摘要
        """
        payload = json.dumps(
            {"s": source, "v": variables, "e": env},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ── 内部方法 ──

    def _is_expired(self, entry: CacheEntry) -> bool:
        if self._ttl <= 0:
            return False
        return entry.age_seconds > self._ttl

    def _evict_one(self) -> None:
        """淘汰最老的条目"""
        if self._store:
            self._store.popitem(last=False)
            self._evictions += 1

    def _lock_or_noop(self):
        """返回上下文管理器"""
        if self._lock is not None:
            return self._lock
        return _NoopContext()


class _NoopContext:
    """空上下文管理器"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
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

    # ── 测试 1: 基本读写 ──
    cache = LRUCache(max_size=10)
    key = LRUCache.make_key("hello", {"lang": "zh"})
    cache.put(key, "output")
    assert_eq("基本读", cache.get(key), "output")

    # ── 测试 2: 未命中 ──
    assert_eq("未命中", cache.get("nonexistent"), None)

    # ── 测试 3: LRU 淘汰 ──
    cache = LRUCache(max_size=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.put("d", 4)  # 应淘汰 a
    assert_eq("LRU淘汰-a", cache.get("a"), None)
    assert_eq("LRU淘汰-b", cache.get("b"), 2)
    assert_eq("LRU淘汰-d", cache.get("d"), 4)

    # ── 测试 4: TTL 过期 ──
    cache = LRUCache(max_size=10, ttl_seconds=0.05)
    cache.put("ttl_key", "value")
    assert_eq("TTL-未过期", cache.get("ttl_key"), "value")
    time.sleep(0.1)
    assert_eq("TTL-已过期", cache.get("ttl_key"), None)

    # ── 测试 5: 淘汰计数 ──
    cache = LRUCache(max_size=2)
    cache.put("x", 1)
    cache.put("y", 2)
    cache.put("z", 3)
    assert_eq("淘汰次数", cache.stats["evictions"], 1)

    # ── 测试 6: 命中率 ──
    cache = LRUCache(max_size=10)
    cache.put("k", "v")
    cache.get("k")   # hit
    cache.get("k")   # hit
    cache.get("no")  # miss
    assert_eq("命中率", cache.stats["hit_rate"], 2 / 3)

    # ── 测试 7: 失效 ──
    cache = LRUCache(max_size=10)
    cache.put("rm", "val")
    assert_eq("失效-删除", cache.invalidate("rm"), True)
    assert_eq("失效-确认", cache.get("rm"), None)

    # ── 测试 8: 清空 ──
    cache = LRUCache(max_size=10)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.clear()
    assert_eq("清空", cache.size, 0)

    # ── 测试 9: make_key 确定性 ──
    k1 = LRUCache.make_key("text", {"a": 1})
    k2 = LRUCache.make_key("text", {"a": 1})
    assert_eq("key确定性", k1, k2)

    # ── 测试 10: purge_expired ──
    cache = LRUCache(max_size=10, ttl_seconds=0.05)
    cache.put("e1", 1)
    cache.put("e2", 2)
    time.sleep(0.1)
    count = cache.purge_expired()
    assert_eq("purge数量", count, 2)

    # ── 测试 11: 线程安全 ──
    cache = LRUCache(max_size=100, thread_safe=True)
    import concurrent.futures

    def writer(i):
        cache.put(f"key_{i}", i)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(writer, range(50)))
    assert_eq("线程安全-大小", cache.size <= 100, True)

    print(f"\nCache 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
