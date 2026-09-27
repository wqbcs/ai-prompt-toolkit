"""条件编译求值器，对 Condition AST 进行安全求值。"""

from __future__ import annotations

import operator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_prompt_toolkit.compiler.types import CompileContext, Condition

_DANGEROUS_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "__import__",
        "breakpoint",
        "memoryview",
    }
)

_COMPARISON_OPS: dict[str, Any] = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

_LOGICAL_OPS: dict[str, Any] = {
    "&&": lambda a, b: a and b,
    "||": lambda a, b: a or b,
}


class EvaluationError(Exception):
    """求值过程中检测到副作用或非法操作。"""

    def __init__(self, message: str, dimension: str = "") -> None:
        self.dimension = dimension
        super().__init__(message)


class Evaluator:
    """条件编译求值器。

    支持 ``==``, ``!=``, ``>``, ``<``, ``>=``, ``<=``, ``in``, ``not_in``
    比较运算以及 ``&&``, ``||`` 逻辑运算。
    内置副作用检测，禁止 eval/exec/函数调用等。
    """

    def __init__(self, context: CompileContext) -> None:
        self._ctx = context
        self._warnings: list[str] = []
        self._resolved: dict[str, str] = {
            "model": context.model,
            "language": context.language,
            "industry": context.industry,
        }
        self._resolved.update({k: str(v).lower() for k, v in context.flags.items()})

    @property
    def warnings(self) -> list[str]:
        """返回求值期间产生的警告。"""
        return list(self._warnings)

    def _check_side_effects(self, condition: Condition) -> None:
        """检测条件中是否包含副作用关键词。"""
        self._check_identifier(condition.dimension)
        if isinstance(condition.value, str):
            self._check_identifier(condition.value)
        if condition.right:
            self._check_side_effects(condition.right)

    @staticmethod
    def _check_identifier(name: str) -> None:
        """检查标识符是否为危险名称。"""
        stripped = name.strip().lower()
        if stripped in _DANGEROUS_NAMES:
            raise EvaluationError(f"检测到副作用关键词: {name!r}", dimension=name)
        if "(" in stripped or ")" in stripped:
            raise EvaluationError(f"检测到函数调用: {name!r}", dimension=name)

    def _resolve_dimension(self, dimension: str) -> str:
        """解析维度值，缺失则返回空字符串并记录警告。"""
        value = self._resolved.get(dimension, "")
        if not value and dimension not in self._resolved:
            self._warnings.append(f"上下文缺少维度 {dimension!r}，条件视为 false")
        return value

    def _evaluate_single(self, condition: Condition) -> bool:
        """求值单个条件。"""
        dim_value = self._resolve_dimension(condition.dimension)
        dim_lower = dim_value.lower()

        if condition.operator in ("in", "not_in"):
            if not isinstance(condition.value, list):
                values = [condition.value]
            else:
                values = condition.value
            values_lower = [v.lower() for v in values]

            if not dim_value:
                return False

            result = dim_lower in values_lower
            return result if condition.operator == "in" else not result

        op_func = _COMPARISON_OPS.get(condition.operator)
        if op_func is None:
            self._warnings.append(f"未知的比较运算符: {condition.operator!r}，条件视为 false")
            return False

        target = condition.value if isinstance(condition.value, str) else str(condition.value)
        try:
            result: bool = bool(op_func(dim_lower, target.lower()))
            return result
        except (TypeError, ValueError):
            self._warnings.append(f"比较失败: {dim_lower!r} {condition.operator} {target!r}")
            return False

    def evaluate(self, condition: Condition) -> bool:
        """对 Condition 进行求值。

        Args:
            condition: 条件表达式节点。

        Returns:
            条件是否成立。

        Raises:
            EvaluationError: 检测到副作用时抛出。
        """
        self._check_side_effects(condition)
        left = self._evaluate_single(condition)

        if condition.logical and condition.right:
            right_val = self.evaluate(condition.right)
            logical_func = _LOGICAL_OPS.get(condition.logical)
            if logical_func is None:
                self._warnings.append(f"未知的逻辑运算符: {condition.logical!r}")
                return False
            return bool(logical_func(left, right_val))

        return left


def evaluate(condition: Condition, context: CompileContext) -> tuple[bool, list[str]]:
    """便捷函数：对条件进行求值并返回 (结果, 警告列表)。

    Args:
        condition: 条件表达式节点。
        context: 编译上下文。

    Returns:
        (求值结果, 警告列表)
    """
    ev = Evaluator(context)
    result = ev.evaluate(condition)
    return result, ev.warnings
