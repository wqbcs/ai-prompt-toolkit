"""result_cache模块测试 — CLI结果缓存"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from ai_prompt_toolkit.result_cache import CacheEntry, ResultCache, _content_hash


class TestContentHash:
    def test_deterministic(self):
        assert _content_hash("hello") == _content_hash("hello")

    def test_different_content(self):
        assert _content_hash("hello") != _content_hash("world")


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(
            key="test",
            category="lint",
            file_path="a.md",
            content_hash="abc",
            timestamp=time.time(),
            ttl=3600,
            data={"score": 90},
        )
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(
            key="test",
            category="lint",
            file_path="a.md",
            content_hash="abc",
            timestamp=time.time() - 7200,
            ttl=3600,
            data={"score": 90},
        )
        assert entry.is_expired() is True

    def test_to_dict(self):
        entry = CacheEntry(
            key="test",
            category="lint",
            file_path="a.md",
            content_hash="abc",
            timestamp=1000.0,
            ttl=3600,
            data={"score": 90},
        )
        d = entry.to_dict()
        assert d["key"] == "test"
        assert d["data"]["score"] == 90


class TestResultCache:
    def test_put_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "hello world", {"score": 95, "findings": 2})
            result = cache.get("lint", "test.md", "hello world")
            assert result is not None
            assert result["score"] == 95

    def test_get_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            result = cache.get("lint", "test.md", "hello world")
            assert result is None

    def test_content_change_invalidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "version1", {"score": 80})
            result = cache.get("lint", "test.md", "version2")
            assert result is None

    def test_different_category(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "content", {"score": 90})
            cache.put("eval", "test.md", "content", {"avg": 7.5})
            assert cache.get("lint", "test.md", "content")["score"] == 90
            assert cache.get("eval", "test.md", "content")["avg"] == 7.5

    def test_invalidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "content", {"score": 90})
            count = cache.invalidate("lint", "test.md")
            assert count >= 1
            assert cache.get("lint", "test.md", "content") is None

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "a.md", "content", {"score": 90})
            cache.put("eval", "b.md", "content", {"avg": 7.5})
            count = cache.clear()
            assert count >= 2
            assert cache.get("lint", "a.md", "content") is None

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "content", {"score": 90})
            stats = cache.stats()
            assert stats["memory_entries"] == 1
            assert stats["disk_entries"] >= 1

    def test_ttl_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir, ttl=0.01)
            cache.put("lint", "test.md", "content", {"score": 90})
            time.sleep(0.02)
            result = cache.get("lint", "test.md", "content")
            assert result is None

    def test_persistence_across_instances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = ResultCache(cache_dir=tmpdir)
            cache1.put("lint", "test.md", "content", {"score": 88})

            cache2 = ResultCache(cache_dir=tmpdir)
            result = cache2.get("lint", "test.md", "content")
            assert result is not None
            assert result["score"] == 88

    def test_gitignore_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResultCache(cache_dir=tmpdir)
            cache.put("lint", "test.md", "content", {"score": 90})
            gitignore = Path(tmpdir) / ".gitignore"
            assert gitignore.exists()
            assert gitignore.read_text() == "*\n"
