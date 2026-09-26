"""条件编译词法分析器，将模板源码拆分为 Token 流。"""

from __future__ import annotations

import re

from ai_prompt_toolkit.compiler.types import Token, TokenKind

_IF_OPEN_RE = re.compile(r"\{\{#if\s+(.+?)\s*\}\}")
_ELSE_IF_RE = re.compile(r"\{\{#else\s+if\s+(.+?)\s*\}\}")
_ELSE_RE = re.compile(r"\{\{else\}\}")
_IF_CLOSE_RE = re.compile(r"\{\{/if\}\}")

_DELIMITER_RE = re.compile(r"\{\{(?:#if\s+.+?|/if|#else\s+if\s+.+?|else)\s*\}\}")


class LexerError(Exception):
    """词法分析错误。"""

    def __init__(self, message: str, line: int = 0, col: int = 0) -> None:
        self.line = line
        self.col = col
        super().__init__(f"{message} (line {line}, col {col})")


class Lexer:
    """条件编译词法分析器。

    将模板文本按 ``{{#if}}``, ``{{else}}``, ``{{#else if}}``, ``{{/if}}``
    分隔为 Token 流，普通文本归为 ``TokenKind.TEXT``。
    """

    def __init__(self, source: str) -> None:
        self._source = source
        self._tokens: list[Token] = []
        self._line = 1
        self._col = 1

    def _advance(self, text: str) -> None:
        """推进行/列位置。"""
        for ch in text:
            if ch == "\n":
                self._line += 1
                self._col = 1
            else:
                self._col += 1

    def _make_text_token(self, text: str, line: int, col: int) -> Token:
        """创建 TEXT Token。"""
        return Token(kind=TokenKind.TEXT, value=text, line=line, col=col)

    def _classify_delimiter(self, text: str, line: int, col: int) -> Token:
        """判断分隔符类型并生成对应 Token。"""
        m = _IF_OPEN_RE.fullmatch(text)
        if m:
            return Token(kind=TokenKind.IF_OPEN, value=text, line=line, col=col, expr=m.group(1))

        m = _ELSE_IF_RE.fullmatch(text)
        if m:
            return Token(kind=TokenKind.ELSE_IF, value=text, line=line, col=col, expr=m.group(1))

        if _ELSE_RE.fullmatch(text):
            return Token(kind=TokenKind.ELSE, value=text, line=line, col=col)

        if _IF_CLOSE_RE.fullmatch(text):
            return Token(kind=TokenKind.IF_CLOSE, value=text, line=line, col=col)

        raise LexerError(f"无法识别的分隔符: {text!r}", line, col)

    def tokenize(self) -> list[Token]:
        """执行词法分析，返回 Token 列表。

        Returns:
            按 Token 出现顺序排列的列表。

        Raises:
            LexerError: 遇到无法识别的分隔符时抛出。
        """
        self._tokens = []
        pos = 0
        src = self._source

        while pos < len(src):
            match = _DELIMITER_RE.search(src, pos)
            if match is None:
                remaining = src[pos:]
                if remaining:
                    self._tokens.append(self._make_text_token(remaining, self._line, self._col))
                    self._advance(remaining)
                break

            start, end = match.span()

            if start > pos:
                text = src[pos:start]
                self._tokens.append(self._make_text_token(text, self._line, self._col))
                self._advance(text)

            line, col = self._line, self._col
            delimiter_text = match.group(0)
            self._tokens.append(self._classify_delimiter(delimiter_text, line, col))
            self._advance(delimiter_text)

            pos = end

        return self._tokens
