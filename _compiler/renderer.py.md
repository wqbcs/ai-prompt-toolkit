# 条件编译渲染器 (Renderer)

> 完整的Python渲染器实现，可直接运行

```python
"""
条件编译渲染器 — 深度优先遍历 AST 生成最终文本

支持 3 种回退策略: empty / skip / warn
生成 CompileReport 编译报告

用法:
    from renderer import render, FallbackStrategy
    text, report = render(ast, ctx, FallbackStrategy.WARN)
"""

from __future__ import annotations

import enum
import dataclasses
from typing import List, Optional, Dict, Any

from parser import AST, ConditionalNode, TextNode
from evaluator import CompilationContext, evaluate_condition


# ──────────────────────────────────────────
#  回退策略
# ──────────────────────────────────────────

class FallbackStrategy(enum.Enum):
    """条件不匹配时的回退策略

    Attributes:
        EMPTY: 返回空字符串
        SKIP:  跳过该块（同 EMPTY，语义不同）
        WARN:  返回空字符串并记录警告
    """
    EMPTY = "empty"
    SKIP = "skip"
    WARN = "warn"


# ──────────────────────────────────────────
#  编译报告
# ──────────────────────────────────────────

@dataclasses.dataclass
class CompileReport:
    """编译报告

    Attributes:
        output_length:     输出文本长度
        conditions_evaluated: 求值过的条件数
        conditions_matched:   匹配成功的条件数
        warnings:          警告列表
        branches_taken:    实际选中的分支描述
        metadata:          附加元数据
    """
    output_length: int = 0
    conditions_evaluated: int = 0
    conditions_matched: int = 0
    warnings: List[str] = dataclasses.field(default_factory=list)
    branches_taken: List[str] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def summary(self) -> str:
        """生成报告摘要"""
        lines = [
            f"输出长度: {self.output_length}",
            f"条件求值: {self.conditions_evaluated}",
            f"条件匹配: {self.conditions_matched}",
        ]
        if self.warnings:
            lines.append(f"警告: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.branches_taken:
            lines.append("选中分支:")
            for b in self.branches_taken:
                lines.append(f"  - {b}")
        return "\n".join(lines)


# ──────────────────────────────────────────
#  渲染器
# ──────────────────────────────────────────

def render(
    ast: AST,
    ctx: CompilationContext,
    fallback: FallbackStrategy = FallbackStrategy.WARN,
) -> tuple[str, CompileReport]:
    """深度优先遍历 AST，生成最终文本

    Args:
        ast:     解析器生成的 AST
        ctx:     编译上下文
        fallback: 回退策略

    Returns:
        (输出文本, 编译报告)
    """
    report = CompileReport()
    output = _render_nodes(ast, ctx, fallback, report)
    report.output_length = len(output)
    return output, report


def _render_nodes(
    nodes: AST,
    ctx: CompilationContext,
    fallback: FallbackStrategy,
    report: CompileReport,
    path: str = "",
) -> str:
    """递归渲染节点列表"""
    parts: List[str] = []

    for i, node in enumerate(nodes):
        if isinstance(node, TextNode):
            parts.append(node.value)

        elif isinstance(node, ConditionalNode):
            result = _render_conditional(node, ctx, fallback, report, f"{path}[{i}]")
            parts.append(result)

    return "".join(parts)


def _render_conditional(
    node: ConditionalNode,
    ctx: CompilationContext,
    fallback: FallbackStrategy,
    report: CompileReport,
    path: str,
) -> str:
    """渲染单个条件节点"""
    report.conditions_evaluated += 1
    cond_expr = node.condition.expression

    # ── 求值 IF 条件 ──
    if_result = _safe_evaluate(cond_expr, ctx, fallback, report, node.condition.line)

    if if_result:
        report.conditions_matched += 1
        report.branches_taken.append(f"L{node.condition.line}: IF [{cond_expr}] → TRUE")
        return _render_nodes(node.if_body, ctx, fallback, report, f"{path}/if")

    # ── 求值 ELSEIF 条件 ──
    for elseif_cond, elseif_body in node.elseif_clauses:
        report.conditions_evaluated += 1
        elseif_result = _safe_evaluate(
            elseif_cond.expression, ctx, fallback, report, elseif_cond.line
        )
        if elseif_result:
            report.conditions_matched += 1
            report.branches_taken.append(
                f"L{elseif_cond.line}: ELSEIF [{elseif_cond.expression}] → TRUE"
            )
            return _render_nodes(elseif_body, ctx, fallback, report, f"{path}/elseif")

    # ── ELSE 分支 ──
    if node.else_body:
        report.branches_taken.append(
            f"L{node.condition.line}: ELSE (no condition matched)"
        )
        return _render_nodes(node.else_body, ctx, fallback, report, f"{path}/else")

    # ── 无匹配，回退 ──
    if fallback == FallbackStrategy.WARN:
        report.warnings.append(
            f"L{node.condition.line}: 条件 [{cond_expr}] 无匹配分支，输出为空"
        )
    return ""


def _safe_evaluate(
    expression: str,
    ctx: CompilationContext,
    fallback: FallbackStrategy,
    report: CompileReport,
    line: int,
) -> bool:
    """安全求值，捕获异常"""
    try:
        return evaluate_condition(expression, ctx)
    except ValueError as e:
        msg = f"L{line}: 条件求值失败 [{expression}]: {e}"
        if fallback == FallbackStrategy.WARN:
            report.warnings.append(msg)
        return False
    except Exception as e:
        msg = f"L{line}: 条件求值异常 [{expression}]: {type(e).__name__}: {e}"
        report.warnings.append(msg)
        return False


# ──────────────────────────────────────────
#  便捷函数
# ──────────────────────────────────────────

def render_string(
    source: str,
    variables: Optional[Dict[str, Any]] = None,
    flags: Optional[set] = None,
    env: str = "dev",
    fallback: FallbackStrategy = FallbackStrategy.WARN,
) -> tuple[str, CompileReport]:
    """从原始字符串直接渲染

    整合 Lexer → Parser → Renderer 的完整管线

    Args:
        source:    原始文本
        variables: 变量字典
        flags:     功能标志
        env:       环境名称
        fallback:  回退策略

    Returns:
        (输出文本, 编译报告)
    """
    from lexer import Lexer
    from parser import Parser

    tokens = Lexer.tokenize(source)
    ast = Parser.parse(tokens)
    ctx = CompilationContext(
        variables=variables or {},
        flags=flags or set(),
        env=env,
    )
    return render(ast, ctx, fallback)


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
        variables={"lang": "zh", "level": 2},
        flags={"debug"},
        env="prod",
    )

    # ── 测试 1: 纯文本 ──
    from lexer import Lexer as _Lexer
    from parser import Parser as _Parser

    tokens = _Lexer.tokenize("Hello")
    ast = _Parser.parse(tokens)
    output, report = render(ast, ctx)
    assert_eq("纯文本", output, "Hello")

    # ── 测试 2: if-else ──
    tokens = _Lexer.tokenize("<<if lang=='zh'>>你好<<else>>Hello<<endif>>")
    ast = _Parser.parse(tokens)
    output, report = render(ast, ctx)
    assert_eq("if-else-匹配", output, "你好")

    # ── 测试 3: 条件不匹配 ──
    ctx2 = CompilationContext(variables={"lang": "en"})
    tokens = _Lexer.tokenize("<<if lang=='zh'>>你好<<else>>Hello<<endif>>")
    ast = _Parser.parse(tokens)
    output, report = render(ast, ctx2)
    assert_eq("if-else-不匹配", output, "Hello")

    # ── 测试 4: 无else且不匹配 ──
    tokens = _Lexer.tokenize("<<if debug>>[DEBUG]<<endif>>end")
    ast = _Parser.parse(tokens)
    ctx_no_debug = CompilationContext(variables={}, flags=set())
    output, report = render(ast, ctx_no_debug, FallbackStrategy.WARN)
    assert_eq("无else-回退", output, "end")
    assert_eq("无else-警告", len(report.warnings), 1)

    # ── 测试 5: 回退策略 EMPTY ──
    output, report = render(ast, ctx_no_debug, FallbackStrategy.EMPTY)
    assert_eq("EMPTY策略-无警告", len(report.warnings), 0)

    # ── 测试 6: 嵌套条件 ──
    src = "<<if lang=='zh'>><<if debug>>调试中文<<else>>中文<<endif>><<else>>English<<endif>>"
    tokens = _Lexer.tokenize(src)
    ast = _Parser.parse(tokens)
    output, report = render(ast, ctx)
    assert_eq("嵌套-匹配", output, "调试中文")

    # ── 测试 7: 报告统计 ──
    tokens = _Lexer.tokenize("<<if a>>A<<elseif b>>B<<else>>C<<endif>>")
    ast = _Parser.parse(tokens)
    ctx3 = CompilationContext(variables={"a": False, "b": True})
    output, report = render(ast, ctx3)
    assert_eq("报告-求值数", report.conditions_evaluated, 2)
    assert_eq("报告-匹配数", report.conditions_matched, 1)
    assert_eq("报告-输出", output, "B")

    # ── 测试 8: render_string 便捷函数 ──
    output, report = render_string(
        "<<if lang=='zh'>>你好<<else>>Hello<<endif>>",
        variables={"lang": "zh"},
    )
    assert_eq("便捷函数", output, "你好")

    # ── 测试 9: 报告摘要 ──
    summary = report.summary()
    assert_eq("摘要-非空", len(summary) > 0, True)

    print(f"\nRenderer 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
