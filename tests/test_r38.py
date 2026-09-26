"""R38: Lint规则P081-P085 + PromptCache缓存层 测试套件"""

from __future__ import annotations

import time
from typing import Any


class TestLintP081:
    def test_variable_without_default(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        f = check_p081("Hello {{name}}, welcome!")
        assert f is not None
        assert f.rule_id == "P081"
        assert "name" in f.description

    def test_variable_with_default(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        f = check_p081("Hello {{name|default('World')}}!")
        assert f is None

    def test_mixed_variables(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        f = check_p081("{{a}} and {{b|default('x')}}")
        assert f is not None
        assert "a" in f.description

    def test_no_variables(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        f = check_p081("No variables here")
        assert f is None


class TestLintP082:
    def test_long_prompt_no_trace(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        text = "x" * 600
        f = check_p082(text)
        assert f is not None
        assert f.rule_id == "P082"

    def test_long_prompt_with_trace(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        text = "This has trace enabled. " + "x" * 500
        f = check_p082(text)
        assert f is None

    def test_short_prompt(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        f = check_p082("Short text")
        assert f is None


class TestLintP083:
    def test_prompt_without_doctor(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        text = "x" * 300
        f = check_p083(text)
        assert f is not None

    def test_prompt_with_doctor(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        text = "This has doctor check. " + "x" * 200
        f = check_p083(text)
        assert f is None

    def test_short_prompt(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        f = check_p083("Short")
        assert f is None


class TestLintP084:
    def test_json_without_schema(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        f = check_p084("请返回JSON格式的结果")
        assert f is not None
        assert f.rule_id == "P084"

    def test_json_with_schema(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        f = check_p084('请返回JSON格式，Schema: {"name": "string"}')
        assert f is None

    def test_no_format_mention(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        f = check_p084("请回答问题")
        assert f is None

    def test_markdown_without_example(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        f = check_p084("输出Markdown格式的内容")
        assert f is not None


class TestLintP085:
    def test_chatml_without_model(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        f = check_p085("<|im_start|>system\nYou are helpful.<|im_end|>")
        assert f is not None
        assert "ChatML" in f.description

    def test_chatml_with_model(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        f = check_p085("<|im_start|>system\n适用于GPT-4模型")
        assert f is None

    def test_llama_syntax_without_model(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        f = check_p085("[INST] Hello [/INST]")
        assert f is not None

    def test_no_special_syntax(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        f = check_p085("普通Prompt文本")
        assert f is None


class TestLintRulesRegistered:
    def test_p081_registered(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        assert "P081" in _RULE_MAP

    def test_p085_registered(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        assert "P085" in _RULE_MAP

    def test_rules_in_checkers_extended(self):
        from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED

        checker_ids = set()
        for checker in _CHECKERS_EXTENDED:
            checker_ids.add(checker.__name__)
        for name in ["check_p081", "check_p082", "check_p083", "check_p084", "check_p085"]:
            assert name in checker_ids, f"Missing checker: {name}"

    def test_run_all_checks_includes_p081(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks

        findings = run_all_checks("Hello {{name}}, welcome!")
        p081_found = any(f.rule_id == "P081" for f in findings)
        assert p081_found

    def test_linter_can_lint_p081(self):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        linter = PromptLinter()
        result = linter.lint("test", "Hello {{name}}, welcome!")
        p081_found = any(f.rule_id == "P081" for f in result.findings)
        assert p081_found


class TestPromptCache:
    def test_make_key(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        k1 = PromptCache.make_key("hello")
        k2 = PromptCache.make_key("hello")
        k3 = PromptCache.make_key("world")
        assert k1 == k2
        assert k1 != k3
        assert len(k1) == 24

    def test_put_and_get(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache(maxsize=100, ttl=300)
        cache.put("key1", {"score": 95})
        result = cache.get("key1")
        assert result == {"score": 95}

    def test_get_miss(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache(maxsize=100, ttl=1)
        cache.put("key1", "value1")
        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_maxsize_eviction(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache(maxsize=3, ttl=300)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")
        cache.put("k4", "v4")
        assert cache.size <= 3

    def test_invalidate(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        cache.put("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.invalidate("key1") is False

    def test_clear(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.clear()
        assert cache.size == 0

    def test_expire(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache(maxsize=100, ttl=1)
        cache.put("k1", "v1")
        time.sleep(1.5)
        expired = cache.expire()
        assert expired == 1
        assert cache.size == 0

    def test_hit_rate(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        cache.put("k1", "v1")
        cache.get("k1")
        cache.get("k2")
        assert cache.hit_rate == 0.5

    def test_stats(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache(maxsize=50, ttl=600)
        cache.put("k1", "v1")
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["maxsize"] == 50
        assert stats["ttl_seconds"] == 600

    def test_cached_decorator(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        call_count = 0

        @cache.cached
        def expensive_fn(text: str) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {"result": text.upper()}

        r1 = expensive_fn("hello")
        r2 = expensive_fn("hello")
        assert r1 == {"result": "HELLO"}
        assert r2 == {"result": "HELLO"}
        assert call_count == 1

        r3 = expensive_fn("world")
        assert call_count == 2

    def test_access_count(self):
        from ai_prompt_toolkit.prompt_cache import PromptCache

        cache = PromptCache()
        cache.put("k1", "v1")
        cache.get("k1")
        cache.get("k1")
        assert cache._cache["k1"].access_count == 2


class TestGlobalCache:
    def test_get_cache(self):
        from ai_prompt_toolkit.prompt_cache import get_cache

        cache = get_cache()
        assert cache is not None

    def test_cached_prompt(self):
        from ai_prompt_toolkit.prompt_cache import cached_prompt, get_cache

        get_cache().clear()
        call_count = 0

        @cached_prompt
        def my_fn(text: str) -> str:
            nonlocal call_count
            call_count += 1
            return text + "!"

        assert my_fn("hi") == "hi!"
        assert my_fn("hi") == "hi!"
        assert call_count == 1


class TestLTSLogger:
    def test_lts_log_disabled(self):
        from ai_prompt_toolkit.prompt_cache import LTSLogger

        lts = LTSLogger(enabled=False)
        lts.log("INFO", "test message")
        assert len(lts.get_buffered()) == 0

    def test_lts_log_enabled(self):
        from ai_prompt_toolkit.prompt_cache import LTSLogger

        lts = LTSLogger(group_id="g1", stream_id="s1", enabled=True)
        lts.log("INFO", "cache miss event")
        buffered = lts.get_buffered()
        assert len(buffered) == 1
        assert buffered[0]["level"] == "INFO"
        assert buffered[0]["group_id"] == "g1"

    def test_lts_log_entry_to_dict(self):
        from ai_prompt_toolkit.prompt_cache import LTSLogEntry

        entry = LTSLogEntry(level="WARN", group_id="g1", content="test")
        d = entry.to_dict()
        assert d["level"] == "WARN"
        assert "timestamp" in d

    def test_lts_flush_empty(self):
        from ai_prompt_toolkit.prompt_cache import LTSLogger

        lts = LTSLogger(enabled=True)
        assert lts.flush() == 0

    def test_lts_flush_with_entries(self):
        from ai_prompt_toolkit.prompt_cache import LTSLogger

        lts = LTSLogger(enabled=True)
        lts.log("INFO", "entry1")
        lts.log("INFO", "entry2")
        count = lts.flush()
        assert count == 2
        assert len(lts.get_buffered()) == 0

    def test_configure_lts(self):
        from ai_prompt_toolkit.prompt_cache import configure_lts, get_lts_logger

        lts = configure_lts("grp1", "str1", enabled=True)
        assert lts.enabled is True
        assert lts._group_id == "grp1"
        get_lts_logger().enabled = False


class TestMCPCacheTools:
    def test_cache_stats_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_stats

        result = _tool_cache_stats({})
        assert "size" in result
        assert "hit_rate" in result

    def test_cache_lookup_miss(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_lookup

        result = _tool_cache_lookup({"text": "nonexistent prompt text"})
        assert result["status"] == "miss"

    def test_cache_lookup_hit(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_lookup
        from ai_prompt_toolkit.prompt_cache import PromptCache, get_cache

        cache = get_cache()
        cache.clear()
        text = "unique test prompt for lookup"
        key = PromptCache.make_key(text)
        cache.put(key, {"score": 42})
        result = _tool_cache_lookup({"text": text})
        assert result["status"] == "hit"
        assert result["value"]["score"] == 42

    def test_cache_invalidate_all(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_invalidate
        from ai_prompt_toolkit.prompt_cache import get_cache

        cache = get_cache()
        cache.put("test_key", "test_val")
        result = _tool_cache_invalidate({"all": True})
        assert result["status"] == "cleared"

    def test_cache_invalidate_by_key(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_invalidate
        from ai_prompt_toolkit.prompt_cache import get_cache

        cache = get_cache()
        cache.clear()
        cache.put("k1", "v1")
        result = _tool_cache_invalidate({"key": "k1"})
        assert result["status"] == "invalidated"

    def test_cache_invalidate_not_found(self):
        from ai_prompt_toolkit.mcp_server import _tool_cache_invalidate

        result = _tool_cache_invalidate({"key": "nonexistent"})
        assert result["status"] == "not_found"


class TestFixerP081P085:
    def test_fix_p081_adds_defaults(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p081_template_var_defaults

        result = _fix_p081_template_var_defaults("Hello {{name}}, welcome {{place}}!")
        assert "|default('')" in result
        assert "{{name|default('')}}" in result

    def test_fix_p082_adds_trace(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p082_trace_observability

        result = _fix_p082_trace_observability("Some long prompt")
        assert "Trace: enabled" in result

    def test_fix_p083_adds_doctor_hint(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p083_doctor_hint

        result = _fix_p083_doctor_hint("Some prompt")
        assert "Doctor" in result

    def test_fix_p084_json_schema(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p084_output_schema

        result = _fix_p084_output_schema("请返回JSON格式的结果")
        assert "Schema" in result

    def test_fix_p084_markdown_example(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p084_output_schema

        result = _fix_p084_output_schema("输出Markdown格式的内容")
        assert "格式示例" in result

    def test_fix_p085_model_compat(self):
        from ai_prompt_toolkit.linter.fixer import _fix_p085_model_compat

        result = _fix_p085_model_compat("<|im_start|>system\nHello")
        assert "模型兼容性" in result
        assert "ChatML" in result
