"""R73测试: 语义缓存(SimHash + SemanticCache)"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.semantic_cache import SimHash, SemanticCache


class TestSimHash:
    def test_same_text_same_hash(self):
        sh = SimHash()
        h1 = sh.compute("你是一个AI助手")
        h2 = sh.compute("你是一个AI助手")
        assert h1 == h2

    def test_similar_text_high_similarity(self):
        sh = SimHash()
        h1 = sh.compute("你是一个专业的AI助手，请回答问题")
        h2 = sh.compute("你是一个专业的AI助手，请回答用户问题")
        assert SimHash.similarity(h1, h2) >= 0.3

    def test_different_text_low_similarity(self):
        sh = SimHash()
        h1 = sh.compute("你是一个AI助手")
        h2 = sh.compute("鸿蒙Stage模型应用开发")
        assert SimHash.similarity(h1, h2) < 0.7

    def test_empty_text(self):
        sh = SimHash()
        assert sh.compute("") == 0

    def test_similarity_range(self):
        h1 = SimHash().compute("hello world")
        h2 = SimHash().compute("hello world")
        sim = SimHash.similarity(h1, h2)
        assert 0.0 <= sim <= 1.0


class TestSemanticCache:
    def test_store_and_lookup_exact(self):
        cache = SemanticCache(threshold=0.85)
        cache.store("你是一个AI助手", {"findings": 5})
        result = cache.lookup("你是一个AI助手")
        assert result is not None
        assert result["findings"] == 5

    def test_miss(self):
        cache = SemanticCache(threshold=0.95)
        cache.store("文本A", {"findings": 3})
        result = cache.lookup("完全不同的文本B")
        assert result is None

    def test_stats(self):
        cache = SemanticCache()
        cache.store("text", {"v": 1})
        cache.lookup("text")
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_clear(self):
        cache = SemanticCache()
        cache.store("text", {"v": 1})
        cache.clear()
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0

    def test_lru_eviction(self):
        cache = SemanticCache(max_size=2)
        cache.store("a", {"v": 1})
        cache.store("b", {"v": 2})
        cache.store("c", {"v": 3})
        assert cache.stats()["size"] == 2
