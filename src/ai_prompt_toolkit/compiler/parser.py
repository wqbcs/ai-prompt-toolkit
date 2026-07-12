"""条件编译语法分析器，将 Token 流解析为 AST。"""
from __future__ import annotations

from ai_prompt_toolkit.compiler.types import (
    ASTNode,
    Condition,
    NodeType,
    Token,
    TokenKind,
)


class NestingError(Exception):
    """嵌套深度超出限制。"""

    def __init__(self, depth: int, line: int = 0) -> None:
        self.depth = depth
        self.line = line
        super().__init__(f"条件嵌套深度 {depth} 超出限制（最大 3），位于第 {line} 行")


class ParseError(Exception):
    """语法分析错误。"""

    def __init__(self, message: str, line: int = 0) -> None:
        self.line = line
        super().__init__(f"{message} (line {line})")


_MAX_DEPTH = 3


class Parser:
    """条件编译语法分析器。

    使用递归下降策略，将 Token 流解析为 AST。
    嵌套深度超过 ``_MAX_DEPTH`` 时抛出 ``NestingError``。
    未闭合的 ``{{#if}}`` 会抛出 ``ParseError``。
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token | None:
        """查看当前 Token 但不消费。"""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> Token:
        """消费并返回当前 Token。"""
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind: TokenKind) -> Token:
        """消费指定类型的 Token，类型不匹配则抛出异常。"""
        tok = self._peek()
        if tok is None:
            raise ParseError(f"期望 {kind.value!r}，但到达输入末尾")
        if tok.kind != kind:
            raise ParseError(
                f"期望 {kind.value!r}，实际为 {tok.kind.value!r}", tok.line
            )
        return self._advance()

    @staticmethod
    def _parse_condition_expr(expr: str) -> Condition:
        """解析条件表达式字符串为 Condition 对象。

        支持格式:
        - ``dimension op value``
        - ``dimension op value && dimension op value``
        - ``dimension op value || dimension op value``

        ``in`` / ``not_in`` 的 value 可为逗号分隔列表：``model in gpt-4,claude``
        """
        for logical_op in ("&&", "||"):
            if logical_op in expr:
                left_str, right_str = expr.split(logical_op, 1)
                left = Parser._parse_single_condition(left_str.strip())
                right = Parser._parse_single_condition(right_str.strip())
                left.logical = logical_op
                left.right = right
                return left
        return Parser._parse_single_condition(expr.strip())

    @staticmethod
    def _parse_single_condition(expr: str) -> Condition:
        """解析单个条件表达式。"""
        for op in ("not_in", "in", ">=", "<=", "!=", "==", ">", "<"):
            if op in expr:
                parts = expr.split(op, 1)
                dimension = parts[0].strip()
                raw_value = parts[1].strip()
                if op in ("in", "not_in"):
                    value: str | list[str] = [v.strip() for v in raw_value.split(",") if v.strip()]
                else:
                    value = raw_value
                return Condition(dimension=dimension, operator=op, value=value)
        return Condition(dimension=expr, operator="==", value="true")

    def parse(self) -> ASTNode:
        """执行语法分析，返回 AST 根节点。

        Returns:
            AST 根节点（NodeType.BLOCK）。

        Raises:
            NestingError: 嵌套深度超过 3。
            ParseError: 语法错误（未闭合等）。
        """
        root = ASTNode(type=NodeType.BLOCK, line_start=1, line_end=1)
        children, _ = self._parse_block(root, depth=0)
        root.children = children
        if children:
            root.line_end = children[-1].line_end
        return root

    def _parse_block(self, parent: ASTNode, depth: int) -> tuple[list[ASTNode], bool]:
        """解析一个块（可能包含文本和条件块）。

        Returns:
            (children, closed) — closed 为 True 表示遇到了 ``{{/if}}``。
        """
        nodes: list[ASTNode] = []

        while self._pos < len(self._tokens):
            tok = self._peek()
            if tok is None:
                break

            if tok.kind == TokenKind.TEXT:
                self._advance()
                nodes.append(
                    ASTNode(
                        type=NodeType.TEXT,
                        value=tok.value,
                        line_start=tok.line,
                        line_end=tok.line,
                    )
                )

            elif tok.kind == TokenKind.IF_OPEN:
                cond_node = self._parse_conditional(depth)
                nodes.append(cond_node)

            elif tok.kind in (TokenKind.IF_CLOSE, TokenKind.ELSE, TokenKind.ELSE_IF):
                break
            else:
                self._advance()

        return nodes, False

    def _parse_conditional(self, depth: int) -> ASTNode:
        """解析一个完整的条件块 ``{{#if}}...{{else}}...{{/if}}``。"""
        if_open = self._expect(TokenKind.IF_OPEN)
        new_depth = depth + 1

        if new_depth > _MAX_DEPTH:
            raise NestingError(new_depth, if_open.line)

        condition = self._parse_condition_expr(if_open.expr)
        node = ASTNode(
            type=NodeType.CONDITIONAL,
            condition=condition,
            line_start=if_open.line,
        )

        if_branch, _ = self._parse_block(node, new_depth)
        node.children = if_branch

        while True:
            tok = self._peek()
            if tok is None:
                raise ParseError(f"未闭合的 {{#if}}，开始于第 {if_open.line} 行")

            if tok.kind == TokenKind.ELSE_IF:
                self._advance()
                else_if_cond = self._parse_condition_expr(tok.expr)
                else_if_node = ASTNode(
                    type=NodeType.CONDITIONAL,
                    condition=else_if_cond,
                    line_start=tok.line,
                )
                else_children, _ = self._parse_block(else_if_node, new_depth)
                else_if_node.children = else_children
                node.children.append(else_if_node)
                continue

            if tok.kind == TokenKind.ELSE:
                self._advance()
                else_branch, _ = self._parse_block(node, new_depth)
                else_node = ASTNode(
                    type=NodeType.BLOCK,
                    line_start=tok.line,
                )
                else_node.children = else_branch
                node.children.append(else_node)
                continue

            if tok.kind == TokenKind.IF_CLOSE:
                self._advance()
                node.line_end = tok.line
                break

            break

        return node
