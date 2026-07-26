"""Prompt语义缓存 — 基于SimHash的语义去重

避免对语义相同的Prompt重复执行lint/scan/evaluate。
使用SimHash(局部敏感哈希)检测高相似度文本，支持:
- 相似度阈值配置(默认0.85)
- 缓存TTL过期
- LRU淘汰策略

参考: gptcache(https://github.com/zilliztech/gptcache)语义缓存设计
"""
from __future__ import annotations

import hashlib
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

_SIMHASH_BITS = 64


@dataclass
class CacheEntry:
    text_hash: str
    simhash: int
    text_preview: str
    result_summary: dict[str, Any]
    timestamp: float
    hit_count: int = 0


class SimHash:
    """局部敏感哈希 — 相似文本产生相似哈希值"""

    def __init__(self, bits: int = _SIMHASH_BITS):
        self._bits = bits

    def compute(self, text: str) -> int:
        tokens = self._tokenize(text)
        if not tokens:
            return 0
        v = [0] * self._bits
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            for i in range(self._bits):
                bitmask = 1 << i
                if token_hash & bitmask:
                    v[i] += 1
                else:
                    v[i] -= 1
        fingerprint = 0
        for i in range(self._bits):
            if v[i] >= 0:
                fingerprint |= (1 << i)
        return fingerprint

    @staticmethod
    def similarity(hash1: int, hash2: int, bits: int = _SIMHASH_BITS) -> float:
        xor = hash1 ^ hash2
        diff_bits = bin(xor).count('1')
        return 1.0 - (diff_bits / bits)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = re.sub(r'\s+', ' ', text.lower().strip())
        tokens: list[str] = []
        words = text.split()
        for i in range(len(words)):
            tokens.append(words[i])
            if i < len(words) - 1:
                tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens


class SemanticCache:
    """语义缓存 — 基于SimHash相似度检测

    用法:
        cache = SemanticCache(threshold=0.85, max_size=1000)
        cached = cache.lookup(text)
        if cached:
            result = cached
        else:
            result = expensive_operation(text)
            cache.store(text, result)
    """

    def __init__(
        self,
        *,
        threshold: float = 0.85,
        max_size: int = 1000,
        ttl_seconds: float = 86400.0,
    ) -> None:
        self._threshold = threshold
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._simhash = SimHash()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def lookup(self, text: str) -> dict[str, Any] | None:
        query_hash = self._simhash.compute(text)
        query_md5 = hashlib.md5(text.encode('utf-8')).hexdigest()

        if query_md5 in self._entries:
            entry = self._entries[query_md5]
            if time.time() - entry.timestamp < self._ttl:
                entry.hit_count += 1
                self._entries.move_to_end(query_md5)
                self._hits += 1
                return entry.result_summary
            else:
                del self._entries[query_md5]

        for key, entry in self._entries.items():
            if time.time() - entry.timestamp >= self._ttl:
                continue
            sim = SimHash.similarity(query_hash, entry.simhash)
            if sim >= self._threshold:
                entry.hit_count += 1
                self._entries.move_to_end(key)
                self._hits += 1
                return entry.result_summary

        self._misses += 1
        return None

    def store(self, text: str, result_summary: dict[str, Any]) -> None:
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        simhash = self._simhash.compute(text)
        preview = text[:100] + "..." if len(text) > 100 else text

        self._entries[text_hash] = CacheEntry(
            text_hash=text_hash,
            simhash=simhash,
            text_preview=preview,
            result_summary=result_summary,
            timestamp=time.time(),
        )

        while len(self._entries) > self._max_size:
            self._entries.popitem(last=False)

    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._entries),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "threshold": self._threshold,
        }

    def clear(self) -> None:
        self._entries.clear()
        self._hits = 0
        self._misses = 0
