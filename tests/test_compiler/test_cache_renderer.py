"""编译缓存与渲染器单元测试"""

from __future__ import annotations

import time

from ai_prompt_toolkit.compiler import (
    CompileCache,
    CompileContext,
    CompileReport,
    CompileResult,
    Lexer,
    Parser,
    Renderer,
    compile_template,
)


def _make_result(text: str = "output", tid: str = "test") -> CompileResult:
    return CompileResult(
        compiled_text=text,
        report=CompileReport(template_id=tid),
    )


class TestCompileCache:
    def test_set_and_get(self):
        cache = CompileCache()
        result = _make_result()
        ctx = {"model": "gpt-4"}
        cache.set("template", ctx, result)
        got = cache.get("template", ctx)
        assert got is not None
        assert got.compiled_text == "output"
        assert got.cache_hit is True

    def test_miss(self):
        cache = CompileCache()
        assert cache.get("nonexistent", {}) is None

    def test_different_context_is_miss(self):
        cache = CompileCache()
        result = _make_result()
        cache.set("template", {"model": "gpt-4"}, result)
        assert cache.get("template", {"model": "claude-3"}) is None

    def test_clear(self):
        cache = CompileCache()
        cache.set("template", {}, _make_result())
        cache.clear()
        assert cache.size == 0

    def test_size(self):
        cache = CompileCache()
        assert cache.size == 0
        cache.set("t1", {}, _make_result())
        assert cache.size == 1
        cache.set("t2", {}, _make_result())
        assert cache.size == 2

    def test_ttl_expiry(self):
        cache = CompileCache(ttl_seconds=0)
        result = _make_result()
        cache.set("template", {}, result)
        time.sleep(0.05)
        assert cache.get("template", {}) is None

    def test_make_key_deterministic(self):
        key1 = CompileCache._make_key("src", {"model": "gpt-4"})
        key2 = CompileCache._make_key("src", {"model": "gpt-4"})
        assert key1 == key2

    def test_make_key_different_source(self):
        key1 = CompileCache._make_key("src1", {"model": "gpt-4"})
        key2 = CompileCache._make_key("src2", {"model": "gpt-4"})
        assert key1 != key2

    def test_lru_eviction(self):
        cache = CompileCache(maxsize=2)
        cache.set("t1", {}, _make_result("1"))
        cache.set("t2", {}, _make_result("2"))
        cache.set("t3", {}, _make_result("3"))
        assert cache.size == 2
        assert cache.get("t1", {}) is None


class TestRenderer:
    def test_render_plain_text(self):
        ctx = CompileContext()
        source = "Hello World"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx)
        result = renderer.render(ast)
        assert result.compiled_text == "Hello World"

    def test_render_condition_match(self):
        ctx = CompileContext(model="gpt-4")
        source = "{{#if model == gpt-4}}GPT-4内容{{else}}Other{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx)
        result = renderer.render(ast)
        assert "GPT-4内容" in result.compiled_text

    def test_render_condition_no_match(self):
        ctx = CompileContext(model="claude")
        source = "{{#if model == gpt-4}}GPT-4{{else}}Other{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx)
        result = renderer.render(ast)
        assert "Other" in result.compiled_text

    def test_render_fallback_warn(self):
        ctx = CompileContext(model="claude")
        source = "{{#if model == gpt-4}}GPT-4{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx, fallback="warn")
        result = renderer.render(ast)
        assert len(result.report.warnings) > 0

    def test_render_fallback_empty(self):
        ctx = CompileContext(model="claude")
        source = "{{#if model == gpt-4}}GPT-4{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx, fallback="empty")
        result = renderer.render(ast)
        assert "GPT-4" not in result.compiled_text

    def test_render_nested_conditions(self):
        ctx = CompileContext(model="gpt-4", language="zh-CN")
        source = "{{#if model == gpt-4}}{{#if language == zh-CN}}GPT4中文{{else}}GPT4EN{{/if}}{{else}}Other{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx)
        result = renderer.render(ast)
        assert "GPT4中文" in result.compiled_text

    def test_render_report_contains_branches(self):
        ctx = CompileContext(model="gpt-4")
        source = "{{#if model == gpt-4}}GPT-4{{else}}Other{{/if}}"
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse()
        renderer = Renderer(ctx)
        result = renderer.render(ast)
        assert len(result.report.activated_branches) > 0 or len(result.report.ignored_branches) > 0


class TestCompileTemplateCache:
    def test_cache_hit_flag(self):
        ctx = CompileContext(model="gpt-4")
        source = "Hello {{#if model == gpt-4}}World{{/if}}"
        result1 = compile_template(source, ctx, use_cache=True, template_id="cache_test")
        assert result1.cache_hit is False
        result2 = compile_template(source, ctx, use_cache=True, template_id="cache_test")
        assert result2.cache_hit is True

    def test_no_cache(self):
        ctx = CompileContext(model="gpt-4")
        source = "Hello {{#if model == gpt-4}}World{{/if}}"
        result1 = compile_template(source, ctx, use_cache=False)
        result2 = compile_template(source, ctx, use_cache=False)
        assert result2.cache_hit is False

    def test_cache_different_context(self):
        source = "Hello {{#if model == gpt-4}}World{{/if}}"
        ctx1 = CompileContext(model="gpt-4")
        ctx2 = CompileContext(model="claude")
        compile_template(source, ctx1, use_cache=True)
        result = compile_template(source, ctx2, use_cache=True)
        assert result.cache_hit is False
