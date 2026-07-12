# 条件编译AST解析器 (Parser)

> 完整的Python AST解析器实现，可直接运行

```python
"""
条件编译 AST 解析器 — 将 Token 流解析为条件编译抽象语法树

支持嵌套 (≤3 层)，检测未闭合指令等语法错误。

用法:
    from parser import Parser
    ast = Parser.parse(tokens)
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional, Union

from lexer import Token, TokenKind


# ──────────────────────────────────────────
#  AST 节点定义
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class Condition:
    """条件表达式

    Attributes:
        expression: 原始条件表达式字符串
        line:       行号
        column:     列号
    """
    expression: str
    line: int
    column: int


@dataclasses.dataclass
class ConditionalNode:
    """条件编译节点

    Attributes:
        condition:      IF 条件
        if_body:        条件为真时的内容
        elseif_clauses: elseif 列表 (condition, body)
        else_body:      else 内容 (可为空)
        endif_line:     endif 所在行号
    """
    condition: Condition
    if_body: List[Union["TextNode", "ConditionalNode"]]
    elseif_clauses: List[tuple[Condition, List[Union["TextNode", "ConditionalNode"]]]]
    else_body: List[Union["TextNode", "ConditionalNode"]]
    endif_line: int


@dataclasses.dataclass(frozen=True, slots=True)
class TextNode:
    """纯文本节点

    Attributes:
        value: 文本内容
        line:  行号
    """
    value: str
    line: int


AST = List[Union[TextNode, ConditionalNode]]


# ──────────────────────────────────────────
#  Parser 异常
# ──────────────────────────────────────────

class ParserError(Exception):
    """解析错误"""

    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        self.line = line
        self.column = column
        loc = f" (L{line}:{column})" if line and column else ""
        super().__init__(f"{message}{loc}")


# ──────────────────────────────────────────
#  Parser
# ──────────────────────────────────────────

class Parser:
    """条件编译 AST 解析器

    将 Lexer 产生的 Token 流解析为嵌套的 AST。
    最大嵌套深度为 3 层，超出则报错。
    """

    MAX_DEPTH = 3

    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._pos = 0

    @classmethod
    def parse(cls, tokens: List[Token]) -> AST:
        """解析 Token 流为 AST

        Args:
            tokens: Lexer 产生的 Token 列表

        Returns:
            AST 根节点列表

        Raises:
            ParserError: 语法错误
        """
        parser = cls(tokens)
        return parser._parse_block(depth=0)

    # ── 内部方法 ──

    def _peek(self) -> Token | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _parse_block(self, depth: int) -> AST:
        """解析一个块级内容，直到遇到 endif / else / elseif 或文本结束"""
        nodes: AST = []

        while True:
            tok = self._peek()
            if tok is None:
                break

            if tok.type == TokenKind.TEXT:
                self._advance()
                nodes.append(TextNode(value=tok.value, line=tok.line))

            elif tok.type == TokenKind.IF_OPEN:
                node = self._parse_conditional(depth)
                nodes.append(node)

            elif tok.type in (TokenKind.IF_CLOSE, TokenKind.ELSE, TokenKind.ELSE_IF):
                # 由上层 _parse_conditional 处理
                break

            else:
                self._advance()

        return nodes

    def _parse_conditional(self, depth: int) -> ConditionalNode:
        """解析一个完整的条件块 (if / elseif / else / endif)"""
        if depth >= self.MAX_DEPTH:
            tok = self._peek()
            raise ParserError(
                f"条件编译嵌套深度超过 {self.MAX_DEPTH} 层限制",
                line=tok.line if tok else None,
                column=tok.column if tok else None,
            )

        # ── IF_OPEN ──
        if_tok = self._advance()
        if if_tok.type != TokenKind.IF_OPEN:
            raise ParserError(
                f"期望 IF_OPEN，得到 {if_tok.type.name}",
                line=if_tok.line,
                column=if_tok.column,
            )

        condition = Condition(
            expression=if_tok.value,
            line=if_tok.line,
            column=if_tok.column,
        )

        # ── if_body ──
        if_body = self._parse_block(depth + 1)

        # ── elseif / else / endif ──
        elseif_clauses: List[tuple[Condition, AST]] = []
        else_body: AST = []
        endif_line: int = 0

        while True:
            tok = self._peek()
            if tok is None:
                raise ParserError(
                    f"未闭合的条件块: <<if {condition.expression}>> 缺少 <<endif>>",
                    line=condition.line,
                    column=condition.column,
                )

            if tok.type == TokenKind.ELSE_IF:
                self._advance()
                elseif_cond = Condition(
                    expression=tok.value,
                    line=tok.line,
                    column=tok.column,
                )
                elseif_body = self._parse_block(depth + 1)
                elseif_clauses.append((elseif_cond, elseif_body))

            elif tok.type == TokenKind.ELSE:
                self._advance()
                else_body = self._parse_block(depth + 1)

            elif tok.type == TokenKind.IF_CLOSE:
                self._advance()
                endif_line = tok.line
                break

            else:
                raise ParserError(
                    f"条件块内出现意外 Token: {tok.type.name}",
                    line=tok.line,
                    column=tok.column,
                )

        return ConditionalNode(
            condition=condition,
            if_body=if_body,
            elseif_clauses=elseif_clauses,
            else_body=else_body,
            endif_line=endif_line,
        )

    @staticmethod
    def validate(ast: AST) -> List[str]:
        """校验 AST 的完整性

        Returns:
            警告消息列表（空列表表示无问题）
        """
        warnings: List[str] = []

        def _walk(nodes: AST, depth: int):
            for node in nodes:
                if isinstance(node, ConditionalNode):
                    if depth > Parser.MAX_DEPTH:
                        warnings.append(
                            f"L{node.condition.line}: 嵌套深度 {depth} 超过限制 {Parser.MAX_DEPTH}"
                        )
                    _walk(node.if_body, depth + 1)
                    for cond, body in node.elseif_clauses:
                        _walk(body, depth + 1)
                    _walk(node.else_body, depth + 1)

        _walk(ast, 1)
        return warnings


# ──────────────────────────────────────────
#  AST 格式化输出
# ──────────────────────────────────────────

def format_ast(nodes: AST, indent: int = 0) -> str:
    """将 AST 格式化为可读字符串"""
    lines: List[str] = []
    prefix = "  " * indent

    for node in nodes:
        if isinstance(node, TextNode):
            text = node.value.replace("\n", "\\n")
            if len(text) > 40:
                text = text[:37] + "..."
            lines.append(f"{prefix}TEXT: {text!r}")
        elif isinstance(node, ConditionalNode):
            lines.append(f"{prefix}IF [{node.condition.expression}]:")
            lines.append(format_ast(node.if_body, indent + 1))
            for cond, body in node.elseif_clauses:
                lines.append(f"{prefix}ELSEIF [{cond.expression}]:")
                lines.append(format_ast(body, indent + 1))
            if node.else_body:
                lines.append(f"{prefix}ELSE:")
                lines.append(format_ast(node.else_body, indent + 1))
            lines.append(f"{prefix}ENDIF")

    return "\n".join(lines)


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

    # ── 测试 1: 纯文本 ──
    from lexer import Lexer as _Lexer
    tokens = _Lexer.tokenize("Hello")
    ast = Parser.parse(tokens)
    assert_eq("纯文本-数量", len(ast), 1)
    assert_eq("纯文本-类型", isinstance(ast[0], TextNode), True)

    # ── 测试 2: 简单条件 ──
    tokens = _Lexer.tokenize("<<if x>>A<<else>>B<<endif>>")
    ast = Parser.parse(tokens)
    assert_eq("简单条件-数量", len(ast), 1)
    assert_eq("简单条件-类型", isinstance(ast[0], ConditionalNode), True)
    cond_node = ast[0]
    assert_eq("if_body-长度", len(cond_node.if_body), 1)
    assert_eq("else_body-长度", len(cond_node.else_body), 1)

    # ── 测试 3: elseif ──
    tokens = _Lexer.tokenize("<<if a>>1<<elseif b>>2<<else>>3<<endif>>")
    ast = Parser.parse(tokens)
    cond_node = ast[0]
    assert_eq("elseif-数量", len(cond_node.elseif_clauses), 1)
    assert_eq("else-有", len(cond_node.else_body), 1)

    # ── 测试 4: 嵌套 ──
    tokens = _Lexer.tokenize("<<if a>>A<<if b>>B<<endif>>C<<endif>>")
    ast = Parser.parse(tokens)
    outer = ast[0]
    assert_eq("嵌套-if_body-长度", len(outer.if_body), 3)
    inner = outer.if_body[1]
    assert_eq("嵌套-内层类型", isinstance(inner, ConditionalNode), True)

    # ── 测试 5: 超深嵌套 ──
    src = "<<if a>>" * 4 + "X" + "<<endif>>" * 4
    tokens = _Lexer.tokenize(src)
    try:
        Parser.parse(tokens)
        assert_eq("超深嵌套-应报错", False, True)
    except ParserError:
        assert_eq("超深嵌套-报错", True, True)

    # ── 测试 6: 未闭合 ──
    tokens = _Lexer.tokenize("<<if x>>text")
    try:
        Parser.parse(tokens)
        assert_eq("未闭合-应报错", False, True)
    except ParserError as e:
        assert_eq("未闭合-报错", "未闭合" in str(e), True)

    # ── 测试 7: 校验 ──
    warnings = Parser.validate(ast)  # 用上面的合法 AST
    assert_eq("合法AST-无警告", len(warnings), 0)

    print(f"\nParser 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
