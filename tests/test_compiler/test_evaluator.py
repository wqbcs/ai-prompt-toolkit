"""Evaluator单元测试——==,!=,in,not_in,&&,||, 副作用检测。"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.compiler.evaluator import EvaluationError, evaluate
from ai_prompt_toolkit.compiler.types import CompileContext, Condition


class TestEqualityOperator:
    def test_equal_true(self):
        cond = Condition(dimension="model", operator="==", value="gpt-4")
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True

    def test_equal_false(self):
        cond = Condition(dimension="model", operator="==", value="gpt-4")
        result, _ = evaluate(cond, CompileContext(model="claude"))
        assert result is False

    def test_equal_case_insensitive(self):
        cond = Condition(dimension="model", operator="==", value="GPT-4")
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True


class TestInequalityOperator:
    def test_not_equal_true(self):
        cond = Condition(dimension="model", operator="!=", value="gpt-4")
        result, _ = evaluate(cond, CompileContext(model="claude"))
        assert result is True

    def test_not_equal_false(self):
        cond = Condition(dimension="model", operator="!=", value="gpt-4")
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is False


class TestInOperator:
    def test_in_true(self):
        cond = Condition(dimension="model", operator="in", value=["gpt-4", "claude"])
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True

    def test_in_false(self):
        cond = Condition(dimension="model", operator="in", value=["gpt-4", "claude"])
        result, _ = evaluate(cond, CompileContext(model="gemini"))
        assert result is False

    def test_in_case_insensitive(self):
        cond = Condition(dimension="model", operator="in", value=["GPT-4", "Claude"])
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True

    def test_in_single_value(self):
        cond = Condition(dimension="model", operator="in", value=["gpt-4"])
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True


class TestNotInOperator:
    def test_not_in_true(self):
        cond = Condition(dimension="model", operator="not_in", value=["gpt-4", "claude"])
        result, _ = evaluate(cond, CompileContext(model="gemini"))
        assert result is True

    def test_not_in_false(self):
        cond = Condition(dimension="model", operator="not_in", value=["gpt-4", "claude"])
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is False


class TestLogicalAnd:
    def test_and_both_true(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="&&",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="gpt-4", language="zh"))
        assert result is True

    def test_and_one_false(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="&&",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="gpt-4", language="en"))
        assert result is False

    def test_and_both_false(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="&&",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="claude", language="en"))
        assert result is False


class TestLogicalOr:
    def test_or_both_true(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="||",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="gpt-4", language="zh"))
        assert result is True

    def test_or_one_true(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="||",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="claude", language="zh"))
        assert result is True

    def test_or_both_false(self):
        cond = Condition(
            dimension="model",
            operator="==",
            value="gpt-4",
            logical="||",
            right=Condition(dimension="language", operator="==", value="zh"),
        )
        result, _ = evaluate(cond, CompileContext(model="claude", language="en"))
        assert result is False


class TestSideEffects:
    def test_eval_detected(self):
        cond = Condition(dimension="eval", operator="==", value="true")
        with pytest.raises(EvaluationError):
            evaluate(cond, CompileContext())

    def test_exec_detected(self):
        cond = Condition(dimension="exec", operator="==", value="true")
        with pytest.raises(EvaluationError):
            evaluate(cond, CompileContext())

    def test_function_call_detected(self):
        cond = Condition(dimension="print()", operator="==", value="true")
        with pytest.raises(EvaluationError):
            evaluate(cond, CompileContext())

    def test_safe_dimension(self):
        cond = Condition(dimension="model", operator="==", value="gpt-4")
        result, _ = evaluate(cond, CompileContext(model="gpt-4"))
        assert result is True


class TestMissingDimension:
    def test_missing_dimension_returns_false_with_warning(self):
        cond = Condition(dimension="unknown_dim", operator="==", value="test")
        result, warnings = evaluate(cond, CompileContext())
        assert result is False
        assert any("缺少维度" in w for w in warnings)

    def test_missing_dimension_in_returns_false(self):
        cond = Condition(dimension="unknown_dim", operator="in", value=["a", "b"])
        result, _warnings = evaluate(cond, CompileContext())
        assert result is False


class TestComparisonOperators:
    def test_greater_than(self):
        cond = Condition(dimension="version", operator=">", value="2")
        result, _ = evaluate(cond, CompileContext(flags={"version": True}))
        assert isinstance(result, bool)

    def test_less_than(self):
        cond = Condition(dimension="count", operator="<", value="10")
        result, _ = evaluate(cond, CompileContext(flags={"count": True}))
        assert isinstance(result, bool)
