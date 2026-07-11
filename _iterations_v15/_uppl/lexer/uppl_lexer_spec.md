# UPPL词法分析器设计

> 版本：v1.0 | 日期：2026-05-29

---

## 1. Token定义

### 1.1 Token类型

| 类型 | 值 | 示例 |
|------|-----|------|
| KEYWORD | prompt\|scenario\|constraint\|output\|when\|if\|for\|each\|import\|export\|use\|as\|from\|require\|ensure\|validate\|with\|given\|then\|return | `prompt` |
| IDENTIFIER | [a-zA-Z_][a-zA-Z0-9_]* | `code_review` |
| STRING_LITERAL | "..." | `"代码审查"` |
| NUMBER_LITERAL | [0-9]+(\.[0-9]+)? | `3.14` |
| BOOLEAN_LITERAL | true\|false | `true` |
| OPERATOR | +\|-\|*\|/\|==\|!=\|>=\|<=\|>\|<\|&&\|\|\|\|!\|=>\|-> | `==` |
| PUNCTUATION | (\|)\|{\|}\|[\|]\|:\|;\|,\|.\|@\|#\|\| | `{` |
| ARROW | =>\|-> | `=>` |
| PIPE | \|> | `\|>` |
| TYPE_ANNOTATION | :\|<\|> | `:string` |
| COMMENT | //...\|/*...*/ | `// 注释` |
| WHITESPACE | \s+ | ` ` |
| NEWLINE | \n | |
| EOF | - | - |

### 1.2 关键字保留表

```
prompt scenario constraint output
when if for each
import export use as from require
ensure validate with given then return
type enum interface extends implements
true false null
```

## 2. 词法分析状态机

### 2.1 状态定义

```
States = {START, IDENT, STRING, NUMBER, OPERATOR, COMMENT_LINE, COMMENT_BLOCK, WHITESPACE}
```

### 2.2 状态转移

```
START:
  [a-zA-Z_]      → IDENT
  "               → STRING
  [0-9]           → NUMBER
  [+\-*/=<>!&|]   → OPERATOR
  /               → look-ahead:
                     / → COMMENT_LINE
                     * → COMMENT_BLOCK
                     else → OPERATOR
  [|] + [>]       → PIPE
  [\s\t]          → WHITESPACE
  [\n]            → emit NEWLINE, → START
  [(){}\[\]:;,.@#] → emit PUNCTUATION, → START
  [EOF]           → emit EOF, → HALT

IDENT:
  [a-zA-Z0-9_]   → IDENT (accumulate)
  else            → check keyword → emit KEYWORD or IDENTIFIER, → START

STRING:
  "               → emit STRING_LITERAL, → START
  \\              → escape sequence
  else            → STRING (accumulate)

NUMBER:
  [0-9]           → NUMBER (accumulate)
  .               → NUMBER (decimal)
  else            → emit NUMBER_LITERAL, → START

OPERATOR:
  [=<>!&|]        → OPERATOR (check multi-char)
  else            → emit OPERATOR, → START

COMMENT_LINE:
  \n              → emit COMMENT, → START
  else            → COMMENT_LINE (accumulate)

COMMENT_BLOCK:
  */              → emit COMMENT, → START
  else            → COMMENT_BLOCK (accumulate)

WHITESPACE:
  [\s\t]          → WHITESPACE (accumulate)
  else            → emit WHITESPACE, → START
```

## 3. 词法分析器实现

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator

class TokenType(Enum):
    KEYWORD = auto()
    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    NUMBER_LITERAL = auto()
    BOOLEAN_LITERAL = auto()
    OPERATOR = auto()
    PUNCTUATION = auto()
    ARROW = auto()
    PIPE = auto()
    COMMENT = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

KEYWORDS = {
    'prompt', 'scenario', 'constraint', 'output',
    'when', 'if', 'for', 'each',
    'import', 'export', 'use', 'as', 'from', 'require',
    'ensure', 'validate', 'with', 'given', 'then', 'return',
    'type', 'enum', 'interface', 'extends', 'implements',
    'true', 'false', 'null',
}

class UPPLLexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens = []
        for token in self:
            if token.type not in (TokenType.WHITESPACE, TokenType.COMMENT):
                tokens.append(token)
        return tokens

    def __iter__(self) -> Iterator[Token]:
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '\n':
                yield self._emit(TokenType.NEWLINE, '\n')
                self.line += 1
                self.column = 1
            elif ch.isspace():
                yield self._read_whitespace()
            elif ch.isalpha() or ch == '_':
                yield self._read_identifier()
            elif ch == '"':
                yield self._read_string()
            elif ch.isdigit():
                yield self._read_number()
            elif ch == '/' and self._peek(1) == '/':
                yield self._read_line_comment()
            elif ch == '/' and self._peek(1) == '*':
                yield self._read_block_comment()
            elif ch == '|' and self._peek(1) == '>':
                yield self._emit(TokenType.PIPE, '|>')
            elif ch == '=' and self._peek(1) == '>':
                yield self._emit(TokenType.ARROW, '=>')
            elif ch == '-' and self._peek(1) == '>':
                yield self._emit(TokenType.ARROW, '->')
            elif ch in '+-*/=<>!&|':
                yield self._read_operator()
            elif ch in '(){}[]:;,.@#':
                yield self._emit(TokenType.PUNCTUATION, ch)
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at {self.line}:{self.column}")
        yield Token(TokenType.EOF, '', self.line, self.column)

    def _peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else ''

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        self.column += 1
        return ch

    def _emit(self, type: TokenType, value: str) -> Token:
        token = Token(type, value, self.line, self.column)
        for _ in value:
            pass
        self.pos += len(value)
        self.column += len(value) - 1
        return token

    def _read_identifier(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = ''
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
            value += self._advance()
        if value in KEYWORDS:
            return Token(TokenType.KEYWORD, value, start_line, start_col)
        if value in ('true', 'false'):
            return Token(TokenType.BOOLEAN_LITERAL, value, start_line, start_col)
        return Token(TokenType.IDENTIFIER, value, start_line, start_col)

    def _read_string(self) -> Token:
        start_col = self.column
        start_line = self.line
        self._advance()  # skip opening quote
        value = ''
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            if self.source[self.pos] == '\\':
                self._advance()
            value += self._advance()
        self._advance()  # skip closing quote
        return Token(TokenType.STRING_LITERAL, value, start_line, start_col)

    def _read_number(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = ''
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
            value += self._advance()
        return Token(TokenType.NUMBER_LITERAL, value, start_line, start_col)

    def _read_operator(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = self._advance()
        if self.pos < len(self.source) and self.source[self.pos] in '=<>&|':
            value += self._advance()
        return Token(TokenType.OPERATOR, value, start_line, start_col)

    def _read_whitespace(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = ''
        while self.pos < len(self.source) and self.source[self.pos] in ' \t\r':
            value += self._advance()
        return Token(TokenType.WHITESPACE, value, start_line, start_col)

    def _read_line_comment(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = ''
        while self.pos < len(self.source) and self.source[self.pos] != '\n':
            value += self._advance()
        return Token(TokenType.COMMENT, value, start_line, start_col)

    def _read_block_comment(self) -> Token:
        start_col = self.column
        start_line = self.line
        value = ''
        self._advance()  # /
        self._advance()  # *
        while self.pos < len(self.source) - 1:
            if self.source[self.pos] == '*' and self.source[self.pos + 1] == '/':
                self._advance()
                self._advance()
                break
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 0
            value += self._advance()
        return Token(TokenType.COMMENT, value, start_line, start_col)
```
