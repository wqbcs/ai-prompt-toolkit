# 词法分析器设计 (Lexer)

> 模块路径: `_compiler/lexer`
> 版本: v1.0
> 依赖: 无外部依赖

---

## 1. 概述

词法分析器(Lexer)负责将原始模板文本转换为 Token 流，是编译管线的第一阶段。识别条件编译语法标记（`{{#if}}`, `{{else}}`, `{{else if}}`, `{{/if}}`）并将其与普通文本分离。

### 数据流

```
原始文本 ──→ Lexer.tokenize() ──→ List[Token]
                                       │
                              ┌────────┴────────┐
                              │  Token.kind 分类  │
                              ├─────────────────┤
                              │ IF_OPEN          │
                              │ IF_CLOSE         │
                              │ ELSE             │
                              │ ELSE_IF          │
                              │ TEXT             │
                              └─────────────────┘
```

---

## 2. 类型定义

### 2.1 TokenKind 枚举

```python
from enum import Enum, auto

class TokenKind(Enum):
    TEXT = auto()        # 普通文本内容
    IF_OPEN = auto()    # {{#if condition}}
    IF_CLOSE = auto()   # {{/if}}
    ELSE = auto()       # {{else}}
    ELSE_IF = auto()    # {{else if condition}}
```

### 2.2 Token 数据类

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str           # 原始文本内容
    line: int            # 行号 (1-based)
    column: int          # 列号 (1-based)
    offset: int          # 字符偏移量 (0-based)
```

### 2.3 LexerError 异常

```python
class LexerError(Exception):
    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        context: str,
        source_id: str = ""
    ):
        self.message = message
        self.line = line
        self.column = column
        self.context = context
        self.source_id = source_id
        super().__init__(
            f"[LexerError] {source_id}:{line}:{column} — {message}\n"
            f"  上下文: {context}"
        )
```

---

## 3. Lexer 类设计

### 3.1 类签名

```python
class Lexer:
    # 正则模式定义
    _PATTERNS: ClassVar[dict[str, re.Pattern[str]]]

    def __init__(self, config: LexerConfig | None = None) -> None: ...
    def tokenize(self, source: str, source_id: str = "<input>") -> list[Token]: ...
    def _scan(self, source: str, source_id: str) -> list[Token]: ...
    def _match_tag(self, source: str, pos: int) -> tuple[TokenKind, str, int] | None: ...
    def _build_context(self, source: str, offset: int, window: int = 40) -> str: ...
    def _track_position(self, source: str, offset: int) -> tuple[int, int]: ...
```

### 3.2 配置

```python
@dataclass
class LexerConfig:
    open_delimiter: str = "{{"     # 开标记
    close_delimiter: str = "}}"    # 闭标记
    max_source_size: int = 1_000_000  # 最大源文本大小 (1MB)
    context_window: int = 40       # 错误上下文窗口字符数
```

### 3.3 正则模式

```python
_PATTERNS = {
    "if_open":   re.compile(r'\{\{#if\s+(.+?)\}\}'),
    "else_if":   re.compile(r'\{\{else\s+if\s+(.+?)\}\}'),
    "else":      re.compile(r'\{\{else\}\}'),
    "if_close":  re.compile(r'\{\{/if\}\}'),
}
```

> **匹配顺序关键**: `else_if` 必须在 `else` 之前匹配，避免 `{{else if ...}}` 被错误识别为 `{{else}}`。

---

## 4. 核心算法

### 4.1 tokenize 流程

```
输入: source (原始文本), source_id (模板标识)

1. 校验源文本长度 ≤ max_source_size
2. 初始化 pos=0, tokens=[]
3. 循环:
   a. 从 pos 起，尝试匹配标签模式 (按优先级: else_if > else > if_open > if_close)
   b. 若 pos < 标签起始位置 → 生成 TEXT Token (pos 到标签前的文本)
   c. 生成匹配到的标签 Token
   d. pos = 标签结束位置
   e. 若 pos ≥ len(source) 且无标签匹配 → 将剩余文本作为 TEXT Token
4. 返回 tokens
```

### 4.2 位置追踪

```python
def _track_position(self, source: str, offset: int) -> tuple[int, int]:
    """计算 offset 对应的行号和列号"""
    line = source[:offset].count('\n') + 1
    last_newline = source.rfind('\n', 0, offset)
    column = offset - last_newline  # last_newline==-1 时自然为 offset+1
    return line, column
```

### 4.3 错误上下文

```python
def _build_context(self, source: str, offset: int, window: int = 40) -> str:
    """截取错误位置前后 window 字符作为上下文"""
    start = max(0, offset - window)
    end = min(len(source), offset + window)
    return source[start:end]
```

---

## 5. 完整示例

### 5.1 基础条件

**输入:**
```
你是一个{{#if model=="gpt-4o"}}高级推理{{/if}}助手。
```

**输出:**
```python
[
    Token(kind=TokenKind.TEXT,    value="你是一个",   line=1, column=1,  offset=0),
    Token(kind=TokenKind.IF_OPEN, value='model=="gpt-4o"', line=1, column=4,  offset=3),
    Token(kind=TokenKind.TEXT,    value="高级推理",   line=1, column=23, offset=22),
    Token(kind=TokenKind.IF_CLOSE, value="",          line=1, column=27, offset=26),
    Token(kind=TokenKind.TEXT,    value="助手。",     line=1, column=33, offset=32),
]
```

### 5.2 多分支条件

**输入:**
```
{{#if model=="gpt-4o"}}推理模式{{else if model=="claude-3"}}分析模式{{else}}通用模式{{/if}}
```

**输出:**
```python
[
    Token(kind=TokenKind.IF_OPEN,  value='model=="gpt-4o"',   line=1, column=1,  offset=0),
    Token(kind=TokenKind.TEXT,     value="推理模式",          line=1, column=22, offset=21),
    Token(kind=TokenKind.ELSE_IF,  value='model=="claude-3"', line=1, column=26, offset=25),
    Token(kind=TokenKind.TEXT,     value="分析模式",          line=1, column=51, offset=50),
    Token(kind=TokenKind.ELSE,     value="",                  line=1, column=55, offset=54),
    Token(kind=TokenKind.TEXT,     value="通用模式",          line=1, column=62, offset=61),
    Token(kind=TokenKind.IF_CLOSE, value="",                  line=1, column=66, offset=65),
]
```

### 5.3 错误定位

**输入:**
```
第1行正常内容
{{#if model==}}有问题
```

**输出异常:**
```
LexerError: <input>:2:5 — 条件表达式为空
  上下文: ...正常内容\n{{#if model==}}有问题\n...
```

---

## 6. 边界情况

| 场景 | 输入 | 预期行为 |
|------|------|---------|
| 空输入 | `""` | 返回 `[]` |
| 纯文本 | `"Hello World"` | `[TEXT]` |
| 未闭合标签 | `"{{#if x}}text"` | 抛出 `LexerError` |
| 嵌套标签 | `"{{#if a}}x{{#if b}}y{{/if}}{{/if}}"` | 正常识别6个Token |
| 连续条件 | `"{{#if a}}{{#if b}}{{/if}}{{/if}}"` | 正确解析 |
| 特殊字符 | `"{{#if model==\"gpt-4o\"}}"` | 引号内支持转义 |

---

## 7. 性能目标

| 指标 | 目标值 |
|------|--------|
| 词法分析吞吐 | ≥ 10MB/s |
| 单模板延迟 (1KB) | < 0.5ms |
| 内存占用 | O(n)，n为源文本长度 |
| 错误定位精度 | 字符级 (行+列) |

---

## 8. 与下游模块接口

Lexer 输出 `List[Token]` 直接作为 Parser 的输入:

```
Lexer.tokenize(source) → List[Token] → Parser.parse(tokens)
```

Parser 仅消费 `Token.kind` 和 `Token.value`，不依赖位置信息做语法判断，位置信息仅用于错误报告。
