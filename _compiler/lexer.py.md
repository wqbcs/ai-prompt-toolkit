# 条件编译词法分析器 (Lexer)

> 完整的Python词法分析器实现，可直接运行

```python
"""
条件编译词法分析器 — 将原始文本拆分为 Token 流

支持指令:
    <<if condition>>  <<else>>  <<elseif condition>>  <<endif>>

用法:
    from lexer import Lexer
    tokens = Lexer.tokenize("Hello <<if lang=='zh'>>世界<<else>>World<<endif>>")
"""

from __future__ import annotations

import re
import enum
import dataclasses
from typing import List


# ──────────────────────────────────────────
#  Token 定义
# ──────────────────────────────────────────

class TokenKind(enum.Enum):
    """Token 类型枚举"""
    TEXT = "TEXT"           # 纯文本片段
    IF_OPEN = "IF_OPEN"    # <<if ...>>
    ELSE = "ELSE"          # <<else>>
    ELSE_IF = "ELSE_IF"    # <<elseif ...>>
    IF_CLOSE = "IF_CLOSE"  # <<endif>>


@dataclasses.dataclass(frozen=True, slots=True)
class Token:
    """词法单元

    Attributes:
        type:   Token 类型
        value:  原始文本 / 条件表达式
        line:   行号 (1-indexed)
        column: 列号 (1-indexed)
    """
    type: TokenKind
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.column})"


# ──────────────────────────────────────────
#  Lexer 异常
# ──────────────────────────────────────────

class LexerError(Exception):
    """词法分析错误，附带定位信息"""

    def __init__(self, message: str, line: int, column: int, source: str, window: int = 40):
        self.line = line
        self.column = column
        start = max(0, column - window)
        end = min(len(source), column + window)
        context = source[start:end]
        pointer = " " * (column - start) + "^"
        full = f"{message} (L{line}:{column})\n  {context}\n  {pointer}"
        super().__init__(full)


# ──────────────────────────────────────────
#  正则规则（按优先级排列）
# ──────────────────────────────────────────

_RULES: List[tuple[TokenKind, re.Pattern[str]]] = [
    (TokenKind.IF_OPEN,   re.compile(r"<<if\s+(.+?)>>")),
    (TokenKind.ELSE_IF,   re.compile(r"<<elseif\s+(.+?)>>")),
    (TokenKind.ELSE,      re.compile(r"<<else\s*>>")),
    (TokenKind.IF_CLOSE,  re.compile(r"<<endif\s*>>")),
]

# 合并所有指令模式，用于从文本中分割
_DIRECTIVE_RE = re.compile(
    r"(<<if\s+.+?>>|<<elseif\s+.+?>>|<<else\s*>>|<<endif\s*>>)"
)


# ──────────────────────────────────────────
#  Lexer
# ──────────────────────────────────────────

class Lexer:
    """条件编译词法分析器

    将包含条件编译指令的原始文本拆分为 Token 列表。
    """

    @staticmethod
    def tokenize(source: str) -> List[Token]:
        """对源文本进行词法分析，返回 Token 列表

        Args:
            source: 原始文本，可包含 <<if>> / <<else>> / <<elseif>> / <<endif>> 指令

        Returns:
            Token 列表，按出现顺序排列

        Raises:
            LexerError: 遇到无法识别的指令时抛出
        """
        tokens: List[Token] = []
        pos = 0
        line = 1
        line_start = 0

        while pos < len(source):
            # 尝试匹配指令
            best_match: re.Match[str] | None = None
            best_kind: TokenKind | None = None

            for kind, pattern in _RULES:
                m = pattern.match(source, pos)
                if m:
                    if best_match is None or m.start() < best_match.start():
                        best_match = m
                        best_kind = kind

            if best_match is not None and best_match.start() == pos:
                column = pos - line_start + 1

                # 提取条件表达式（IF_OPEN / ELSE_IF）
                if best_kind in (TokenKind.IF_OPEN, TokenKind.IF_CLOSE):
                    value = best_match.group(1) if best_kind == TokenKind.IF_OPEN else best_match.group(0)
                elif best_kind == TokenKind.ELSE_IF:
                    value = best_match.group(1)
                else:
                    value = best_match.group(0)

                tokens.append(Token(type=best_kind, value=value, line=line, column=column))

                # 更新行号
                matched_text = best_match.group(0)
                newlines = matched_text.count("\n")
                if newlines:
                    line += newlines
                    line_start = pos + matched_text.rfind("\n") + 1

                pos = best_match.end()
                continue

            # 检查是否是未识别的 << 指令开头
            if source[pos:pos + 2] == "<<":
                maybe_end = source.find(">>", pos)
                if maybe_end != -1:
                    column = pos - line_start + 1
                    directive = source[pos:maybe_end + 2]
                    raise LexerError(
                        f"未识别的条件编译指令: {directive}",
                        line=line,
                        column=column,
                        source=source,
                    )
                else:
                    column = pos - line_start + 1
                    raise LexerError(
                        "未闭合的指令标记 '<<'，缺少对应的 '>>'",
                        line=line,
                        column=column,
                        source=source,
                    )

            # 收集纯文本直到下一个指令或文本末尾
            next_directive = source.find("<<", pos)
            if next_directive == -1:
                text_chunk = source[pos:]
            else:
                text_chunk = source[pos:next_directive]

            if text_chunk:
                column = pos - line_start + 1
                tokens.append(Token(type=TokenKind.TEXT, value=text_chunk, line=line, column=column))

                newlines = text_chunk.count("\n")
                if newlines:
                    line += newlines
                    line_start = pos + text_chunk.rfind("\n") + 1

                pos += len(text_chunk)

        return tokens


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
    import traceback

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
    tokens = Lexer.tokenize("Hello World")
    assert_eq("纯文本-数量", len(tokens), 1)
    assert_eq("纯文本-类型", tokens[0].type, TokenKind.TEXT)
    assert_eq("纯文本-值", tokens[0].value, "Hello World")

    # ── 测试 2: 简单 if/else/endif ──
    src = "<<if x>>A<<else>>B<<endif>>"
    tokens = Lexer.tokenize(src)
    assert_eq("if-else-数量", len(tokens), 5)
    assert_eq("if-类型", tokens[0].type, TokenKind.IF_OPEN)
    assert_eq("if-值", tokens[0].value, "x")
    assert_eq("text-A", tokens[1].type, TokenKind.TEXT)
    assert_eq("else-类型", tokens[2].type, TokenKind.ELSE)
    assert_eq("text-B", tokens[3].type, TokenKind.TEXT)
    assert_eq("endif-类型", tokens[4].type, TokenKind.IF_CLOSE)

    # ── 测试 3: elseif ──
    src = "<<if a==1>>X<<elseif a==2>>Y<<endif>>"
    tokens = Lexer.tokenize(src)
    assert_eq("elseif-数量", len(tokens), 5)
    assert_eq("elseif-类型", tokens[2].type, TokenKind.ELSE_IF)
    assert_eq("elseif-值", tokens[2].value, "a==2")

    # ── 测试 4: 多行与行号 ──
    src = "Line1\n<<if cond>>\nLine3\n<<endif>>"
    tokens = Lexer.tokenize(src)
    assert_eq("多行-if行号", tokens[1].line, 2)
    assert_eq("多行-endif行号", tokens[3].line, 4)

    # ── 测试 5: 未识别指令 ──
    try:
        Lexer.tokenize("<<unknown x>>")
        assert_eq("未识别指令-应抛异常", False, True)
    except LexerError:
        assert_eq("未识别指令-抛异常", True, True)

    # ── 测试 6: 未闭合指令 ──
    try:
        Lexer.tokenize("<<if cond")
        assert_eq("未闭合指令-应抛异常", False, True)
    except LexerError:
        assert_eq("未闭合指令-抛异常", True, True)

    # ── 测试 7: 空输入 ──
    tokens = Lexer.tokenize("")
    assert_eq("空输入", len(tokens), 0)

    print(f"\nLexer 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
