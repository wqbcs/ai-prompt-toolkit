"""断言系统测试 — AssertType/AssertionConfig/AssertionResult/AssertionEngine/Levenshtein"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.assertion import (
    AssertionConfig,
    AssertionEngine,
    AssertionResult,
    AssertType,
)
from ai_prompt_toolkit.assertion.engine import _levenshtein_distance


class TestAssertType:
    def test_all_types(self):
        assert len(AssertType) == 8
        assert AssertType.CONTAINS.value == "contains"
        assert AssertType.NOT_CONTAINS.value == "not-contains"
        assert AssertType.REGEX.value == "regex"
        assert AssertType.JSON_SCHEMA.value == "json_schema"
        assert AssertType.SIMILARITY.value == "similarity"
        assert AssertType.LLM_RUBRIC.value == "llm-rubric"
        assert AssertType.LATENCY.value == "latency"
        assert AssertType.COST.value == "cost"

    def test_from_value(self):
        assert AssertType("contains") is AssertType.CONTAINS
        assert AssertType("similarity") is AssertType.SIMILARITY


class TestAssertionConfig:
    def test_defaults(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="hello")
        assert cfg.threshold == 0.8
        assert cfg.weight == 1.0
        assert cfg.provider == ""
        assert cfg.model == ""

    def test_custom_threshold(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="test", threshold=0.9)
        assert cfg.threshold == 0.9

    def test_list_value(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value=["a", "b", "c"])
        assert cfg.value == ["a", "b", "c"]

    def test_dict_value(self):
        cfg = AssertionConfig(
            assert_type=AssertType.JSON_SCHEMA,
            value={"required": ["name"], "type_checks": {"age": "int"}},
        )
        assert cfg.value["required"] == ["name"]

    def test_float_value(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value=3000.0)
        assert cfg.value == 3000.0

    def test_to_dict(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="test", threshold=0.7)
        d = cfg.to_dict()
        assert d["assert_type"] == "contains"
        assert d["value"] == "test"
        assert d["threshold"] == 0.7
        assert d["weight"] == 1.0


class TestAssertionResult:
    def test_basic(self):
        r = AssertionResult(assert_type=AssertType.CONTAINS, passed=True, score=1.0)
        assert r.passed
        assert r.score == 1.0
        assert r.reason == ""
        assert r.details == {}

    def test_with_details(self):
        r = AssertionResult(
            assert_type=AssertType.REGEX,
            passed=True,
            score=1.0,
            reason="正则匹配成功",
            details={"pattern": r"\d+", "matched_text": "123"},
        )
        assert r.details["pattern"] == r"\d+"

    def test_to_dict(self):
        r = AssertionResult(
            assert_type=AssertType.LATENCY,
            passed=True,
            score=0.95,
            reason="延迟 526ms",
            details={"max_latency": 5000},
        )
        d = r.to_dict()
        assert d["assert_type"] == "latency"
        assert d["passed"]
        assert d["score"] == 0.95
        assert d["reason"] == "延迟 526ms"


class TestContainsAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_single_keyword_match(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="华为云")
        result = self.engine.evaluate(cfg, response="欢迎使用华为云服务")
        assert result.passed
        assert result.score == 1.0

    def test_single_keyword_no_match(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="阿里云")
        result = self.engine.evaluate(cfg, response="欢迎使用华为云服务")
        assert not result.passed
        assert result.score == 0.0

    def test_multiple_keywords_partial(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value=["华为云", "安全", "高性能"])
        result = self.engine.evaluate(cfg, response="华为云提供安全的服务")
        assert result.score == pytest.approx(2 / 3)
        assert not result.passed

    def test_multiple_keywords_all_match(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value=["华为云", "安全"])
        result = self.engine.evaluate(cfg, response="华为云提供安全的服务")
        assert result.passed
        assert result.score == 1.0

    def test_empty_response(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="test")
        result = self.engine.evaluate(cfg, response="")
        assert not result.passed

    def test_threshold_05(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value=["a", "b", "c"], threshold=0.5)
        result = self.engine.evaluate(cfg, response="a and b are here")
        assert result.passed

    def test_details(self):
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value=["华为", "云"])
        result = self.engine.evaluate(cfg, response="华为云")
        assert result.details["matched"] == ["华为", "云"]
        assert result.details["total"] == 2


class TestNotContainsAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_no_forbidden_keywords(self):
        cfg = AssertionConfig(assert_type=AssertType.NOT_CONTAINS, value="密码")
        result = self.engine.evaluate(cfg, response="欢迎使用本系统")
        assert result.passed
        assert result.score == 1.0

    def test_found_forbidden_keyword(self):
        cfg = AssertionConfig(assert_type=AssertType.NOT_CONTAINS, value="密码")
        result = self.engine.evaluate(cfg, response="你的密码是123456")
        assert not result.passed
        assert result.score == 0.0

    def test_multiple_forbidden_partial(self):
        cfg = AssertionConfig(assert_type=AssertType.NOT_CONTAINS, value=["密码", "密钥", "token"])
        result = self.engine.evaluate(cfg, response="请勿泄露密码信息")
        assert not result.passed
        assert result.score == pytest.approx(2 / 3)

    def test_details_found(self):
        cfg = AssertionConfig(assert_type=AssertType.NOT_CONTAINS, value=["密码", "token"])
        result = self.engine.evaluate(cfg, response="你的密码是abc，token是xyz")
        assert result.details["found"] == ["密码", "token"]
        assert result.details["total"] == 2


class TestRegexAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_simple_match(self):
        cfg = AssertionConfig(assert_type=AssertType.REGEX, value=r"\d{4}-\d{2}-\d{2}")
        result = self.engine.evaluate(cfg, response="日期: 2024-01-15")
        assert result.passed
        assert result.score == 1.0
        assert "2024-01-15" in result.details["matched_text"]

    def test_no_match(self):
        cfg = AssertionConfig(assert_type=AssertType.REGEX, value=r"\d{4}-\d{2}-\d{2}")
        result = self.engine.evaluate(cfg, response="今天天气不错")
        assert not result.passed
        assert result.score == 0.0

    def test_invalid_regex(self):
        cfg = AssertionConfig(assert_type=AssertType.REGEX, value=r"[invalid")
        result = self.engine.evaluate(cfg, response="test")
        assert not result.passed
        assert "正则语法错误" in result.reason

    def test_case_insensitive(self):
        cfg = AssertionConfig(assert_type=AssertType.REGEX, value=r"hello")
        result = self.engine.evaluate(cfg, response="HELLO world")
        assert result.passed

    def test_email_pattern(self):
        cfg = AssertionConfig(assert_type=AssertType.REGEX, value=r"[\w.+-]+@[\w-]+\.[\w.]+")
        result = self.engine.evaluate(cfg, response="联系 admin@example.com 获取帮助")
        assert result.passed


class TestJsonSchemaAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_valid_json_no_schema(self):
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value={})
        result = self.engine.evaluate(cfg, response='{"name": "test"}')
        assert result.passed
        assert result.score == 1.0
        assert "无Schema验证" in result.reason

    def test_invalid_json(self):
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value={})
        result = self.engine.evaluate(cfg, response="not json at all")
        assert not result.passed
        assert "无效JSON" in result.reason

    def test_required_fields_present(self):
        schema = {"required": ["name", "age"]}
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value=schema)
        result = self.engine.evaluate(cfg, response='{"name": "Alice", "age": 30}')
        assert result.passed

    def test_required_fields_missing(self):
        schema = {"required": ["name", "age", "email"]}
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value=schema)
        result = self.engine.evaluate(cfg, response='{"name": "Alice"}')
        assert not result.passed
        assert "缺少必需字段" in result.reason
        assert "age" in result.details["missing"]
        assert "email" in result.details["missing"]

    def test_type_checks_pass(self):
        schema = {"required": ["name"], "type_checks": {"name": "str", "age": "int"}}
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value=schema)
        result = self.engine.evaluate(cfg, response='{"name": "Bob", "age": 25}')
        assert result.passed

    def test_type_checks_fail(self):
        schema = {"required": ["name"], "type_checks": {"name": "int"}}
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value=schema)
        result = self.engine.evaluate(cfg, response='{"name": "Bob"}')
        assert not result.passed
        assert "类型不匹配" in result.reason

    def test_non_dict_value_as_schema(self):
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value="not_a_dict")
        result = self.engine.evaluate(cfg, response='{"ok": true}')
        assert result.passed

    def test_nested_json(self):
        cfg = AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value={})
        result = self.engine.evaluate(cfg, response='{"user": {"name": "test", "tags": [1, 2]}}')
        assert result.passed


class TestSimilarityAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_exact_match(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="华为云服务", threshold=0.9)
        result = self.engine.evaluate(cfg, response="华为云服务")
        assert result.passed
        assert result.score == 1.0

    def test_similar_text(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="华为云提供安全服务", threshold=0.6)
        result = self.engine.evaluate(cfg, response="华为云提供安全的服务")
        assert result.passed
        assert result.score > 0.6

    def test_dissimilar_text(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="完全不同的文本内容", threshold=0.8)
        result = self.engine.evaluate(cfg, response="这是另一段毫不相关的文字")
        assert not result.passed

    def test_empty_expected(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="", threshold=0.8)
        result = self.engine.evaluate(cfg, response="任何文本")
        assert not result.passed
        assert "无期望文本" in result.reason

    def test_threshold_boundary(self):
        cfg = AssertionConfig(assert_type=AssertType.SIMILARITY, value="hello world", threshold=0.5)
        result = self.engine.evaluate(cfg, response="hello worl")
        assert result.score > 0.5
        assert result.passed


class TestLlmRubricAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_keyword_match(self):
        cfg = AssertionConfig(assert_type=AssertType.LLM_RUBRIC, value="准确,专业,详细", threshold=0.6)
        result = self.engine.evaluate(cfg, response="这个回答非常准确且专业")
        assert result.passed
        assert result.score == 0.7

    def test_no_keyword_match(self):
        cfg = AssertionConfig(assert_type=AssertType.LLM_RUBRIC, value="准确,专业,详细", threshold=0.6)
        result = self.engine.evaluate(cfg, response="这段文字毫无关联")
        assert not result.passed
        assert result.score == 0.3

    def test_empty_rubric(self):
        cfg = AssertionConfig(assert_type=AssertType.LLM_RUBRIC, value="", threshold=0.6)
        result = self.engine.evaluate(cfg, response="任何回答")
        assert result.passed
        assert result.score == 0.5
        assert "自动通过" in result.reason

    def test_single_keyword(self):
        cfg = AssertionConfig(assert_type=AssertType.LLM_RUBRIC, value="安全", threshold=0.6)
        result = self.engine.evaluate(cfg, response="请确保安全操作")
        assert result.passed


class TestLatencyAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_within_threshold(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value=5000.0)
        result = self.engine.evaluate(cfg, response="ok", latency_ms=300.0)
        assert result.passed
        assert result.score >= 0.0

    def test_exceeds_threshold(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value=1000.0)
        result = self.engine.evaluate(cfg, response="ok", latency_ms=5000.0)
        assert not result.passed

    def test_exact_threshold(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value=3000.0)
        result = self.engine.evaluate(cfg, response="ok", latency_ms=3000.0)
        assert result.passed

    def test_default_threshold(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value="")
        result = self.engine.evaluate(cfg, response="ok", latency_ms=4000.0)
        assert result.passed

    def test_zero_latency(self):
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value=1000.0)
        result = self.engine.evaluate(cfg, response="ok", latency_ms=0.0)
        assert result.passed
        assert result.score == 1.0


class TestCostAssertion:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_within_budget(self):
        cfg = AssertionConfig(assert_type=AssertType.COST, value=1.0)
        result = self.engine.evaluate(cfg, response="ok", cost=0.05)
        assert result.passed

    def test_exceeds_budget(self):
        cfg = AssertionConfig(assert_type=AssertType.COST, value=0.01)
        result = self.engine.evaluate(cfg, response="ok", cost=0.5)
        assert not result.passed

    def test_exact_budget(self):
        cfg = AssertionConfig(assert_type=AssertType.COST, value=0.1)
        result = self.engine.evaluate(cfg, response="ok", cost=0.1)
        assert result.passed

    def test_default_budget(self):
        cfg = AssertionConfig(assert_type=AssertType.COST, value="")
        result = self.engine.evaluate(cfg, response="ok", cost=0.5)
        assert result.passed

    def test_zero_cost(self):
        cfg = AssertionConfig(assert_type=AssertType.COST, value=1.0)
        result = self.engine.evaluate(cfg, response="ok", cost=0.0)
        assert result.passed


class TestEvaluateBatch:
    def setup_method(self):
        self.engine = AssertionEngine()

    def test_batch_mixed(self):
        configs = [
            AssertionConfig(assert_type=AssertType.CONTAINS, value="华为云"),
            AssertionConfig(assert_type=AssertType.LATENCY, value=5000.0),
        ]
        results = self.engine.evaluate_batch(configs, response="华为云服务", latency_ms=300.0)
        assert len(results) == 2
        assert results[0].passed
        assert results[1].passed

    def test_batch_empty(self):
        results = self.engine.evaluate_batch([], response="test")
        assert results == []

    def test_batch_all_types(self):
        configs = [
            AssertionConfig(assert_type=AssertType.CONTAINS, value="test"),
            AssertionConfig(assert_type=AssertType.NOT_CONTAINS, value="bad"),
            AssertionConfig(assert_type=AssertType.REGEX, value=r"\w+"),
            AssertionConfig(assert_type=AssertType.JSON_SCHEMA, value={}),
            AssertionConfig(assert_type=AssertType.SIMILARITY, value="test", threshold=0.5),
            AssertionConfig(assert_type=AssertType.LLM_RUBRIC, value="test", threshold=0.5),
            AssertionConfig(assert_type=AssertType.LATENCY, value=5000.0),
            AssertionConfig(assert_type=AssertType.COST, value=1.0),
        ]
        results = self.engine.evaluate_batch(
            configs,
            response="test response",
            latency_ms=100.0,
            cost=0.01,
        )
        assert len(results) == 8
        types = {r.assert_type for r in results}
        assert types == set(AssertType)


class TestUnknownAssertType:
    def test_unknown_type_returns_failure(self):
        engine = AssertionEngine()
        cfg = AssertionConfig(assert_type=AssertType.CONTAINS, value="test")
        cfg.assert_type = "invalid_type"  # type: ignore
        result = engine.evaluate(cfg, response="test")
        assert not result.passed
        assert "未知断言类型" in result.reason


class TestExceptionHandling:
    def test_engine_catches_exception(self):
        engine = AssertionEngine()
        cfg = AssertionConfig(assert_type=AssertType.LATENCY, value="not_a_number")
        result = engine.evaluate(cfg, response="ok", latency_ms=100.0)
        assert not result.passed
        assert "断言评估异常" in result.reason


class TestLevenshteinDistance:
    def test_identical_strings(self):
        assert _levenshtein_distance("hello", "hello") == 0

    def test_empty_strings(self):
        assert _levenshtein_distance("", "") == 0
        assert _levenshtein_distance("abc", "") == 3
        assert _levenshtein_distance("", "abc") == 3

    def test_single_char_diff(self):
        assert _levenshtein_distance("cat", "bat") == 1

    def test_insertion(self):
        assert _levenshtein_distance("abc", "abdc") == 1

    def test_deletion(self):
        assert _levenshtein_distance("abdc", "abc") == 1

    def test_chinese(self):
        assert _levenshtein_distance("华为云", "华为") == 1

    def test_completely_different(self):
        assert _levenshtein_distance("abc", "xyz") == 3

    def test_order_independence(self):
        assert _levenshtein_distance("abc", "b") == _levenshtein_distance("b", "abc")
