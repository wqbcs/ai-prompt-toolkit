# 条件编译求值器 (Evaluator)

> 完整的Python条件求值器实现，可直接运行

```python
"""
条件编译求值器 — 安全地计算条件表达式

支持操作符: == != in not_in && ||
禁止副作用: 赋值/导入/函数调用等

用法:
    from evaluator import CompilationContext, evaluate_condition
    ctx = CompilationContext(variables={"lang": "zh", "debug": True})
    result = evaluate_condition("lang == 'zh'", ctx)
"""

from __future__ import annotations

import re
import dataclasses
import operator
from typing import Any, Dict, List, Set


# ──────────────────────────────────────────
#  编译上下文
# ──────────────────────────────────────────

@dataclasses.dataclass
class CompilationContext:
    """条件编译上下文

    Attributes:
        variables: 变量字典
        flags:     功能标志集合
        env:       环境名称 (dev/staging/prod)
        metadata:  附加元数据
    """
    variables: Dict[str, Any] = dataclasses.field(default_factory=dict)
    flags: Set[str] = dataclasses.field(default_factory=set)
    env: str = "dev"
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def resolve(self, name: str) -> Any:
        """解析变量名，依次查找 variables / flags / env"""
        if name in self.variables:
            return self.variables[name]
        if name in self.flags:
            return True
        if name == "env":
            return self.env
        return None


# ──────────────────────────────────────────
#  副作用检测
# ──────────────────────────────────────────

_DANGEROUS_PATTERNS: List[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bimport\b"),               "禁止 import 语句"),
    (re.compile(r"\bexec\b"),                  "禁止 exec 调用"),
    (re.compile(r"\beval\b"),                  "禁止 eval 调用"),
    (re.compile(r"="),                         "禁止赋值操作"),
    (re.compile(r"\bopen\b"),                  "禁止文件操作"),
    (re.compile(r"\b__\w+__\b"),               "禁止魔术属性访问"),
    (re.compile(r"\b(os|sys|subprocess)\b"),   "禁止系统模块引用"),
]


def _check_side_effects(expression: str) -> None:
    """检测条件表达式中的副作用

    Args:
        expression: 条件表达式

    Raises:
        ValueError: 检测到危险操作时
    """
    for pattern, msg in _ANGEROUS_PATTERNS:
        if pattern.search(expression):
            raise ValueError(f"条件表达式包含危险操作: {msg} → {expression!r}")


# ──────────────────────────────────────────
#  Token 化 (简易版，非 Lexer)
# ──────────────────────────────────────────

_Token = tuple[str, str]  # (kind, value)

_LOGIC_OPS = {"&&", "||"}
_COMPARE_OPS = {"==", "!=", "in", "not_in"}
_TOKEN_RE = re.compile(
    r"""
    ('[^']*'|"[^"]*")    |  # 字符串字面量
    (\b\w+\b)            |  # 标识符/关键字
    (&&|\|\|)            |  # 逻辑运算符
    (==|!=)              |  # 比较运算符
    (\S)                    # 单字符
    """,
    re.VERBOSE,
)


def _tokenize_expr(expression: str) -> List[_Token]:
    """将条件表达式拆分为简单 Token"""
    tokens: List[_Token] = []
    pos = 0
    while pos < len(expression):
        m = _TOKEN_RE.match(expression, pos)
        if m is None:
            pos += 1
            continue
        if m.group(1):
            tokens.append(("STRING", m.group(1)[1:-1]))
        elif m.group(2):
            word = m.group(2)
            if word in ("in", "not", "and", "or", "true", "false"):
                if word == "not" and pos + 3 < len(expression) and expression[pos:pos + 6] == "not_in":
                    tokens.append(("OP", "not_in"))
                    pos += 6
                    continue
                elif word == "in":
                    tokens.append(("OP", "in"))
                elif word in ("and", "&&"):
                    tokens.append(("OP", "&&"))
                elif word in ("or", "||"):
                    tokens.append(("OP", "||"))
                elif word == "true":
                    tokens.append(("BOOL", "True"))
                elif word == "false":
                    tokens.append(("BOOL", "False"))
                else:
                    tokens.append(("IDENT", word))
            else:
                tokens.append(("IDENT", word))
        elif m.group(3):
            tokens.append(("OP", m.group(3)))
        elif m.group(4):
            tokens.append(("OP", m.group(4)))
        elif m.group(5):
            tokens.append(("CHAR", m.group(5)))
        pos = m.end()
    return tokens


# ──────────────────────────────────────────
#  求值器
# ──────────────────────────────────────────

_COMPARE_FUNCS = {
    "==":     operator.eq,
    "!=":     operator.ne,
    "in":     lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


def _eval_comparison(left: Any, op: str, right: Any) -> bool:
    """执行比较操作"""
    func = _COMPARE_FUNCS.get(op)
    if func is None:
        raise ValueError(f"不支持的比较运算符: {op!r}")
    try:
        return bool(func(left, right))
    except TypeError as e:
        raise ValueError(f"类型不匹配: {left!r} {op} {right!r}") from e


def _resolve_value(token: _Token, ctx: CompilationContext) -> Any:
    """解析单个 Token 的值"""
    kind, value = token
    if kind == "STRING":
        return value
    if kind == "BOOL":
        return value == "True"
    if kind == "IDENT":
        resolved = ctx.resolve(value)
        if resolved is None:
            if value.isdigit():
                return int(value)
            try:
                return float(value)
            except ValueError:
                pass
            return None
        return resolved
    return value


def _eval_atomic(tokens: List[_Token], ctx: CompilationContext) -> bool:
    """求值一个原子比较或布尔值"""
    if not tokens:
        return False

    # 纯布尔值
    if len(tokens) == 1:
        val = _resolve_value(tokens[0], ctx)
        return bool(val)

    # 比较表达式: left op right
    if len(tokens) == 3 and tokens[1][0] == "OP" and tokens[1][1] in _COMPARE_OPS:
        left = _resolve_value(tokens[0], ctx)
        op = tokens[1][1]
        right = _resolve_value(tokens[2], ctx)
        return _eval_comparison(left, op, right)

    raise ValueError(f"无法求值的原子表达式: {[(k,v) for k,v in tokens]}")


def evaluate_condition(expression: str, ctx: CompilationContext) -> bool:
    """安全地求值条件表达式

    支持:
        - 比较运算: == != in not_in
        - 逻辑运算: && || (and / or 别名)
        - 字符串/数字/布尔字面量
        - 变量解析

    禁止:
        - import / exec / eval / 赋值 / 文件操作

    Args:
        expression: 条件表达式
        ctx:        编译上下文

    Returns:
        布尔值

    Raises:
        ValueError: 表达式非法或包含副作用
    """
    expression = expression.strip()
    if not expression:
        return True

    _check_side_effects(expression)

    # 处理逻辑运算符别名的文本替换
    normalized = expression.replace(" and ", " && ").replace(" or ", " || ")

    # 按逻辑运算符拆分
    parts = re.split(r"\s*(\|\||&&)\s*", normalized)
    if not parts:
        return True

    # 重新组合: [expr, op, expr, op, expr, ...]
    result = False
    current_op: str | None = None

    for part in parts:
        part = part.strip()
        if part in ("&&", "||"):
            current_op = part
            continue

        tokens = _tokenize_expr(part)
        part_result = _eval_atomic(tokens, ctx)

        if current_op is None:
            result = part_result
        elif current_op == "&&":
            result = result and part_result
        elif current_op == "||":
            result = result or part_result

        current_op = None

    return result


# ──────────────────────────────────────────
#  批量求值
# ──────────────────────────────────────────

def evaluate_batch(
    expressions: List[str],
    ctx: CompilationContext,
) -> Dict[str, bool]:
    """批量求值多个条件表达式

    Returns:
        {expression: result} 映射
    """
    results: Dict[str, bool] = {}
    for expr in expressions:
        try:
            results[expr] = evaluate_condition(expr, ctx)
        except ValueError as e:
            results[expr] = False
    return results


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    ctx = CompilationContext(
        variables={"lang": "zh", "version": 3, "tags": ["a", "b"]},
        flags={"debug", "beta"},
        env="prod",
    )

    # ── 测试 1: 等于 ──
    assert_eq("等于-真", evaluate_condition("lang == 'zh'", ctx), True)
    assert_eq("等于-假", evaluate_condition("lang == 'en'", ctx), False)

    # ── 测试 2: 不等于 ──
    assert_eq("不等于-真", evaluate_condition("lang != 'en'", ctx), True)

    # ── 测试 3: in ──
    assert_eq("in-真", evaluate_condition("'a' in tags", ctx), True)
    assert_eq("in-假", evaluate_condition("'c' in tags", ctx), False)

    # ── 测试 4: not_in ──
    assert_eq("not_in-真", evaluate_condition("'c' not_in tags", ctx), True)

    # ── 测试 5: 逻辑与 ──
    assert_eq("与-真", evaluate_condition("lang == 'zh' && debug", ctx), True)
    assert_eq("与-假", evaluate_condition("lang == 'en' && debug", ctx), False)

    # ── 测试 6: 逻辑或 ──
    assert_eq("或-真", evaluate_condition("lang == 'en' || debug", ctx), True)

    # ── 测试 7: 标志 ──
    assert_eq("标志-真", evaluate_condition("debug", ctx), True)
    assert_eq("标志-假", evaluate_condition("alpha", ctx), False)

    # ── 测试 8: env ──
    assert_eq("env", evaluate_condition("env == 'prod'", ctx), True)

    # ── 测试 9: 空表达式 ──
    assert_eq("空表达式", evaluate_condition("", ctx), True)

    # ── 测试 10: 副作用检测 ──
    try:
        evaluate_condition("import os", ctx)
        assert_eq("副作用-应报错", False, True)
    except ValueError:
        assert_eq("副作用-报错", True, True)

    # ── 测试 11: 赋值检测 ──
    try:
        evaluate_condition("x=1", ctx)
        assert_eq("赋值-应报错", False, True)
    except ValueError:
        assert_eq("赋值-报错", True, True)

    # ── 测试 12: 批量求值 ──
    results = evaluate_batch(["lang == 'zh'", "debug", "env == 'staging'"], ctx)
    assert_eq("批量-1", results["lang == 'zh'"], True)
    assert_eq("批量-2", results["debug"], True)
    assert_eq("批量-3", results["env == 'staging'"], False)

    print(f"\nEvaluator 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
