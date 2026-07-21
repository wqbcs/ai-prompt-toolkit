"""EvaluatorRegistry 模块测试——评估器注册表与管道评估"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.evaluator_registry import (
    AggregatedResult,
    AssertionEvaluator,
    BaseEvaluator,
    DimensionEvaluator,
    EvaluatorRegistry,
    EvaluatorResult,
    LintEvaluator,
    SecurityEvaluator,
    TokenEvaluator,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestEvaluatorResult:
    def test_normalized_score(self):
        r = EvaluatorResult(evaluator_name="test", evaluator_type="quality", score=7.5, max_score=10.0)
        assert r.normalized_score == 0.75

    def test_percentage(self):
        r = EvaluatorResult(evaluator_name="test", evaluator_type="quality", score=8.0, max_score=10.0)
        assert r.percentage == 80.0

    def test_to_dict(self):
        r = EvaluatorResult(evaluator_name="lint", evaluator_type="quality", score=95.0, max_score=100.0, passed=True)
        d = r.to_dict()
        assert d["evaluator_name"] == "lint"
        assert d["score"] == 95.0
        assert d["passed"] is True

    def test_zero_max_score(self):
        r = EvaluatorResult(evaluator_name="test", evaluator_type="quality", score=5.0, max_score=0.0)
        assert r.normalized_score == 0.0
        assert r.percentage == 0.0


class TestAggregatedResult:
    def test_to_dict(self):
        results = [EvaluatorResult(evaluator_name="lint", evaluator_type="quality", score=95.0, max_score=100.0)]
        ar = AggregatedResult(template_id="test", results=results, overall_score=9.5)
        d = ar.to_dict()
        assert d["template_id"] == "test"
        assert d["evaluator_count"] == 1
        assert len(d["results"]) == 1


class TestBaseEvaluator:
    def test_subclass_auto_name(self):
        class MyEval(BaseEvaluator):
            evaluator_type = "custom"
            def evaluate(self, template_id, text, **kwargs):
                return EvaluatorResult(evaluator_name=self.name, evaluator_type=self.evaluator_type, score=5.0)

        e = MyEval()
        assert e.name == "MyEval"

    def test_custom_name(self):
        class CustomEval(BaseEvaluator):
            name = "my_custom"
            evaluator_type = "custom"
            def evaluate(self, template_id, text, **kwargs):
                return EvaluatorResult(evaluator_name=self.name, evaluator_type=self.evaluator_type, score=5.0)

        e = CustomEval()
        assert e.name == "my_custom"

    def test_to_dict(self):
        class DictEval(BaseEvaluator):
            name = "dict_eval"
            evaluator_type = "test"
            description = "test evaluator"
            tags = ["test"]
            def evaluate(self, template_id, text, **kwargs):
                return EvaluatorResult(evaluator_name=self.name, evaluator_type=self.evaluator_type, score=5.0)

        e = DictEval()
        d = e.to_dict()
        assert d["name"] == "dict_eval"
        assert d["type"] == "test"
        assert "test" in d["tags"]


class TestLintEvaluator:
    def test_evaluate(self):
        ev = LintEvaluator()
        result = ev.evaluate("test", "# 角色\n你是专家助手, 必须回答用户问题. 禁止编造信息.", threshold=0.0)
        assert result.evaluator_name == "lint"
        assert result.evaluator_type == "quality"
        assert result.max_score == 100.0
        assert result.execution_time_ms >= 0


class TestSecurityEvaluator:
    def test_evaluate(self):
        ev = SecurityEvaluator()
        result = ev.evaluate("test", "正常的安全文本内容", threshold=0.0)
        assert result.evaluator_name == "security"
        assert result.evaluator_type == "security"


class TestDimensionEvaluator:
    def test_evaluate(self):
        ev = DimensionEvaluator()
        result = ev.evaluate("test", "# 角色\n你是专业助手, 必须精确回答.", threshold=0.0)
        assert result.evaluator_name == "dimension"
        assert result.details["dimension_count"] > 0

    def test_evaluate_with_dimensions(self):
        ev = DimensionEvaluator(dimensions=["D01", "D02", "D03"])
        result = ev.evaluate("test", "你是助手, 请回答问题, 输出JSON格式", threshold=0.0)
        assert result.details["dimension_count"] == 3

    def test_evaluate_with_categories(self):
        ev = DimensionEvaluator(categories=["structure"])
        result = ev.evaluate("test", "# 角色\n你是助手", threshold=0.0)
        assert result.details["dimension_count"] > 0


class TestTokenEvaluator:
    def test_evaluate(self):
        ev = TokenEvaluator()
        result = ev.evaluate("test", "简短文本", threshold=0.0)
        assert result.evaluator_name == "token"
        assert result.evaluator_type == "performance"
        assert result.score >= 0


class TestAssertionEvaluator:
    def test_evaluate_with_dicts(self):
        assertions = [
            {"name": "角色", "contains": ["你是"]},
            {"name": "约束", "contains_any": ["禁止", "不得", "约束"]},
        ]
        ev = AssertionEvaluator(assertions=assertions)
        result = ev.evaluate("test", "你是助手, 禁止编造信息.", threshold=0.0)
        assert result.evaluator_name == "assertion"
        assert result.score == 10.0
        assert result.passed is True

    def test_evaluate_failing(self):
        assertions = [
            {"name": "角色", "contains": ["你是"]},
            {"name": "格式", "contains": ["JSON"]},
        ]
        ev = AssertionEvaluator(assertions=assertions)
        result = ev.evaluate("test", "你是助手.", threshold=0.0)
        assert result.passed is False

    def test_evaluate_empty(self):
        ev = AssertionEvaluator(assertions=[])
        result = ev.evaluate("test", "任意文本", threshold=0.0)
        assert result.score == 10.0
        assert result.passed is True


class TestEvaluatorRegistry:
    def test_default_evaluators_registered(self):
        registry = EvaluatorRegistry()
        evaluators = registry.list_evaluators()
        names = [e["name"] for e in evaluators]
        assert "lint" in names
        assert "security" in names
        assert "dimension" in names
        assert "token" in names
        assert "redteam" in names

    def test_register_custom_evaluator(self):
        class MyEval(BaseEvaluator):
            name = "my_eval"
            evaluator_type = "custom"
            description = "自定义评估器"
            tags = ["custom"]
            def evaluate(self, template_id, text, **kwargs):
                return EvaluatorResult(evaluator_name=self.name, evaluator_type=self.evaluator_type, score=8.0)

        registry = EvaluatorRegistry()
        registry.register(MyEval())
        assert registry.get("my_eval") is not None

    def test_register_auto_named_evaluator(self):
        class AutoEval(BaseEvaluator):
            evaluator_type = "custom"
            def evaluate(self, template_id, text, **kwargs):
                return EvaluatorResult(evaluator_name=self.name, evaluator_type=self.evaluator_type, score=5.0)

        registry = EvaluatorRegistry()
        registry.register(AutoEval())
        assert registry.get("AutoEval") is not None

    def test_unregister(self):
        registry = EvaluatorRegistry()
        registry.unregister("lint")
        assert registry.get("lint") is None
        assert registry.get("security") is not None

    def test_list_by_type(self):
        registry = EvaluatorRegistry()
        quality_evals = registry.list_evaluators(evaluator_type="quality")
        for e in quality_evals:
            assert e["type"] == "quality"

    def test_list_by_tag(self):
        registry = EvaluatorRegistry()
        tagged = registry.list_evaluators(tag="security")
        for e in tagged:
            assert "security" in e["tags"]

    def test_evaluate_all(self):
        registry = EvaluatorRegistry()
        result = registry.evaluate("test", "# 角色\n你是专家, 必须精确回答.", thresholds={"lint": 0.0, "security": 0.0})
        assert result.template_id == "test"
        assert len(result.results) > 0

    def test_evaluate_by_names(self):
        registry = EvaluatorRegistry()
        result = registry.evaluate("test", "# 角色\n你是助手.", evaluator_names=["lint"], thresholds={"lint": 0.0})
        assert len(result.results) == 1
        assert result.results[0].evaluator_name == "lint"

    def test_evaluate_by_type(self):
        registry = EvaluatorRegistry()
        result = registry.evaluate("test", "文本内容", evaluator_type="quality")
        assert all(r.evaluator_type == "quality" for r in result.results)

    def test_evaluate_pipeline(self):
        registry = EvaluatorRegistry()
        pipeline = [
            {"name": "lint", "threshold": 0.0},
            {"name": "token", "threshold": 0.0},
        ]
        result = registry.evaluate_pipeline("test", "# 角色\n你是助手.", pipeline)
        assert len(result.results) == 2

    def test_evaluate_pipeline_with_unknown(self):
        registry = EvaluatorRegistry()
        pipeline = [
            {"name": "lint", "threshold": 0.0},
            {"name": "nonexistent", "threshold": 0.0},
        ]
        result = registry.evaluate_pipeline("test", "文本", pipeline)
        assert len(result.results) == 2
        assert result.results[1].passed is False

    def test_evaluate_pipeline_fail_fast(self):
        registry = EvaluatorRegistry()
        pipeline = [
            {"name": "lint", "threshold": 999.0},
            {"name": "token", "threshold": 0.0, "fail_fast": True},
        ]
        result = registry.evaluate_pipeline("test", "短", pipeline)
        assert result.overall_passed is False

    def test_get_nonexistent(self):
        registry = EvaluatorRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_nonexistent(self):
        registry = EvaluatorRegistry()
        registry.unregister("nonexistent")

    def test_evaluate_empty_names(self):
        registry = EvaluatorRegistry()
        result = registry.evaluate("test", "文本", evaluator_names=["nonexistent"])
        assert len(result.results) == 0
        assert result.overall_passed is True

    def test_overall_score_calculation(self):
        registry = EvaluatorRegistry()
        result = registry.evaluate("test", "你是助手, 禁止编造.", evaluator_names=["lint"], thresholds={"lint": 0.0})
        assert result.overall_score >= 0
