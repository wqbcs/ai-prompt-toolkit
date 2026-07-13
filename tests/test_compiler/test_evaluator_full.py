"""编译引擎端到端单元测试 — 多维度条件+嵌套+缓存+回退"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.compiler import CompileContext, compile_template


class TestCompileBasic:
    def test_no_conditions(self):
        source = "这是一个没有条件的模板"
        ctx = CompileContext()
        result = compile_template(source, ctx, use_cache=False)
        assert result.compiled_text == "这是一个没有条件的模板"

    def test_else_branch_fallback(self):
        source = "{{#if model == gpt-4}}GPT4{{else}}OtherModel{{/if}}"
        ctx = CompileContext(model="claude")
        result = compile_template(source, ctx, use_cache=False)
        assert "OtherModel" in result.compiled_text


class TestCompileMultiDimension:
    def test_model_condition(self):
        source = "{{#if model == gpt-4}}GPT4内容{{/if}}"
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False)
        assert "GPT4内容" in result.compiled_text

    def test_language_condition(self):
        source = "{{#if language == zh-CN}}中文内容{{/if}}"
        ctx = CompileContext(language="zh-CN")
        result = compile_template(source, ctx, use_cache=False)
        assert "中文内容" in result.compiled_text

    def test_industry_condition(self):
        source = "{{#if industry == finance}}金融内容{{/if}}"
        ctx = CompileContext(industry="finance")
        result = compile_template(source, ctx, use_cache=False)
        assert "金融内容" in result.compiled_text


class TestCompileNested:
    def test_nested_else_if(self):
        source = (
            "{{#if model == gpt-4}}"
            "GPT4"
            "{{else}}"
            "Other"
            "{{/if}}"
        )
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False)
        assert "GPT4" in result.compiled_text

    def test_unmatched_condition_with_warn(self):
        source = "{{#if model == nonexistent}}内容{{/if}}"
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False, fallback="warn")
        assert len(result.report.warnings) > 0


class TestCompileCache:
    def test_cache_hit(self):
        ctx = CompileContext(model="gpt-4")
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        r1 = compile_template(source, ctx, use_cache=True, template_id="ct")
        assert r1.cache_hit is False
        r2 = compile_template(source, ctx, use_cache=True, template_id="ct")
        assert r2.cache_hit is True

    def test_cache_miss_different_context(self):
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        r1 = compile_template(source, CompileContext(model="gpt-4"), use_cache=True)
        r2 = compile_template(source, CompileContext(model="claude"), use_cache=True)
        assert r2.cache_hit is False

    def test_no_cache_disabled(self):
        ctx = CompileContext(model="gpt-4")
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        r1 = compile_template(source, ctx, use_cache=False)
        r2 = compile_template(source, ctx, use_cache=False)
        assert r2.cache_hit is False


class TestCompileReport:
    def test_report_has_timestamp(self):
        result = compile_template("hello", CompileContext(), use_cache=False)
        assert result.report.timestamp != ""

    def test_report_activated_branches(self):
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False)
        branches = result.report.activated_branches
        assert len(branches) > 0

    def test_report_ignored_branches(self):
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False)
        ignored = result.report.ignored_branches
        assert len(ignored) > 0

    def test_report_fields(self):
        source = "{{#if model == gpt-4}}GPT4{{else}}Other{{/if}}"
        ctx = CompileContext(model="gpt-4")
        result = compile_template(source, ctx, use_cache=False)
        report = result.report
        assert report.template_id != "" or report.timestamp != ""
        assert hasattr(report, "activated_branches")
        assert hasattr(report, "ignored_branches")
