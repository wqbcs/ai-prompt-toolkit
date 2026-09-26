"""Token压缩分析模块测试"""
import pytest
from ai_prompt_toolkit.linter.token_analyzer import (
    estimate_tokens, detect_redundancy, analyze_prompt_tokens,
    _TOKEN_RATIOS,
)
from ai_prompt_toolkit.pricing import get_catalog


class TestEstimateTokens:
    def test_default_model(self):
        result = estimate_tokens("hello world")
        assert result.estimated_tokens > 0
        assert result.char_count == 11

    def test_gpt4_model(self):
        result = estimate_tokens("hello world", "gpt-4")
        assert result.model == "gpt-4"
        assert result.estimated_tokens > 0

    def test_chinese_text(self):
        result = estimate_tokens("你好世界，这是一个测试")
        assert result.estimated_tokens > 0
        assert result.ratio < 1.0

    def test_pricing(self):
        result = estimate_tokens("a" * 1000, "gpt-4o")
        assert result.estimated_input_cost_usd > 0
        assert result.estimated_output_cost_usd > 0

    def test_deepseek_pricing(self):
        result = estimate_tokens("a" * 1000, "deepseek")
        assert result.estimated_input_cost_usd > 0
        assert result.estimated_input_cost_usd < 0.01

    def test_to_dict(self):
        result = estimate_tokens("test", "gpt-4o")
        d = result.to_dict()
        assert "estimated_tokens" in d
        assert "model" in d


class TestDetectRedundancy:
    def test_duplicate_words(self):
        suggestions = detect_redundancy("the the quick brown fox")
        assert len(suggestions) > 0
        assert any("重复单词" in s.description for s in suggestions)

    def test_extra_spaces(self):
        suggestions = detect_redundancy("hello   world    test")
        assert any("多余空格" in s.description for s in suggestions)

    def test_extra_newlines(self):
        suggestions = detect_redundancy("hello\n\n\n\nworld")
        assert any("多余空行" in s.description for s in suggestions)

    def test_clean_text(self):
        suggestions = detect_redundancy("The quick brown fox jumps over the lazy dog.")
        redundant = [s for s in suggestions if s.category == "redundancy"]
        assert len(redundant) == 0


class TestAnalyzePromptTokens:
    def test_short_prompt(self):
        result = analyze_prompt_tokens("You are a helpful assistant.", "gpt-4o")
        assert result.original_tokens > 0
        assert result.estimate.char_count > 0

    def test_long_prompt_triggers_warning(self):
        text = "a" * 15000
        result = analyze_prompt_tokens(text, "gpt-4o")
        assert any(f.rule_id == "TOKEN-001" for f in result.findings)

    def test_medium_prompt_structure_suggestion(self):
        text = "a" * 8000
        result = analyze_prompt_tokens(text, "gpt-4o")
        assert any(s.suggestion_id == "COMP-STR-001" for s in result.suggestions)

    def test_savings_calculation(self):
        text = "hello   world    test"
        result = analyze_prompt_tokens(text, "gpt-4o")
        assert result.savings_percent >= 0

    def test_to_dict(self):
        result = analyze_prompt_tokens("test prompt", "gpt-4o")
        d = result.to_dict()
        assert "original_tokens" in d
        assert "optimized_tokens" in d
        assert "suggestions" in d

    def test_all_models(self):
        for model in ["gpt-4", "gpt-4o", "claude-3", "deepseek", "qwen"]:
            result = estimate_tokens("test", model)
            assert result.estimated_tokens > 0
