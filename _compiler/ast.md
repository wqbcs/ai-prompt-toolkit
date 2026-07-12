# AST 语法树设计 (Abstract Syntax Tree)

> 模块路径: `_compiler/ast`
> 版本: v1.0
> 依赖: `lexer.md` (Token 流)

---

## 1. 概述

定义条件编译模板的抽象语法树(AST)结构，以及将 Token 流转换为 AST 的 Parser。AST 是编译管线的核心数据结构，连接词法分析与条件求值/渲染。

### 数据流

```
List[Token] ──→ Parser.parse() ──→ AST (ProgramNode)
                                      │
                        ┌─────────────┼─────────────┐
                        │             │             │
                   TextNode    ConditionalNode  ProgramNode
                        │             │
                        │      ┌──────┼──────┐
                        │      │      │      │
                        │  IfBranch  ElseIfBranch  ElseBranch
                        │      │
                        │  Condition
                        │      │
                        │  ┌───┼───┐
                        │  │   │   │
                        │ dim op val logical
                        └──┘
```

---

## 2. 类型定义

### 2.1 节点类型枚举

```python
from enum import Enum, auto
from dataclasses import dataclass, field

class NodeType(Enum):
    PROGRAM = auto()       # 根节点
    TEXT = auto()          # 文本节点
    CONDITIONAL = auto()   # 条件分支节点
```

### 2.2 操作符与逻辑符

```python
class Operator(Enum):
    EQ = "=="      # 等于
    NEQ = "!="     # 不等于
    IN = "in"      # 包含于
    NIN = "not in" # 不包含于

class LogicalOp(Enum):
    AND = "and"    # 逻辑与
    OR = "or"      # 逻辑或
    NONE = ""      # 单条件 (无逻辑连接)
```

### 2.3 Condition 结构

```python
@dataclass(frozen=True)
class Condition:
    dimension: str          # 条件维度: model / language / industry
    operator: Operator      # 比较操作符
    value: str              # 比较值
    logical: LogicalOp = LogicalOp.NONE  # 与下一条件的逻辑关系

    def to_key(self) -> str:
        return f"{self.dimension}{self.operator.value}{self.value}"
```

### 2.4 分支结构

```python
@dataclass
class Branch:
    conditions: list[Condition]    # 条件列表 (多个条件用 AND/OR 连接)
    children: list["ASTNode"]      # 子节点
    depth: int                     # 嵌套深度
```

### 2.5 AST 节点

```python
@dataclass
class TextNode:
    kind: NodeType = field(default=NodeType.TEXT, init=False)
    value: str
    line: int
    column: int

@dataclass
class ConditionalNode:
    kind: NodeType = field(default=NodeType.CONDITIONAL, init=False)
    if_branch: Branch
    else_if_branches: list[Branch]
    else_branch: Branch | None
    line: int
    column: int

@dataclass
class ProgramNode:
    kind: NodeType = field(default=NodeType.PROGRAM, init=False)
    children: list[ASTNode]
    source_id: str

ASTNode = TextNode | ConditionalNode | ProgramNode
```

---

## 3. 条件表达式解析

### 3.1 语法格式

```
condition_expr := condition (logical condition)*
condition      := dimension operator value
dimension      := identifier
operator       := "==" | "!=" | "in" | "not in"
value          := quoted_string | identifier
logical        := "and" | "or"
```

### 3.2 解析规则

```python
def parse_condition_expr(expr: str) -> list[Condition]:
    """
    输入: 'model=="gpt-4o" and language=="python"'
    输出: [
        Condition(dimension="model", operator=EQ, value="gpt-4o", logical=AND),
        Condition(dimension="language", operator=EQ, value="python", logical=NONE),
    ]
    """
```

**解析步骤:**

1. 按 `and`/`or` 分割表达式 (保留逻辑操作符)
2. 对每个子条件按 `operator` 解析 dimension + value
3. 构造 Condition 列表，设置 `logical` 字段连接相邻条件

### 3.3 操作符优先级

```
"not in" > "in" > "!=" > "=="
```

> 所有操作符同级，使用贪心最长匹配。`not in` 优先于 `in` 匹配。

---

## 4. Parser 类设计

### 4.1 类签名

```python
class Parser:
    def __init__(self, config: ParserConfig | None = None) -> None: ...
    def parse(self, tokens: list[Token], source_id: str = "<input>") -> ProgramNode: ...
    def _parse_program(self) -> ProgramNode: ...
    def _parse_conditional(self, depth: int) -> ConditionalNode: ...
    def _parse_branch_body(self, depth: int) -> list[ASTNode]: ...
    def _expect(self, kind: TokenKind) -> Token: ...
    def _peek(self) -> Token | None: ...
    def _advance(self) -> Token: ...
```

### 4.2 配置

```python
@dataclass
class ParserConfig:
    max_nesting_depth: int = 3    # 最大嵌套深度 (与 config.yaml 一致)
```

### 4.3 解析状态

```python
@dataclass
class _ParserState:
    tokens: list[Token]
    pos: int = 0
    source_id: str = "<input>"
    errors: list[ParseError] = field(default_factory=list)
```

### 4.4 ParserError

```python
class ParserError(Exception):
    def __init__(self, message: str, token: Token, source_id: str = ""):
        self.message = message
        self.token = token
        self.source_id = source_id
        super().__init__(
            f"[ParserError] {source_id}:{token.line}:{token.column} — {message}"
        )
```

---

## 5. 核心算法

### 5.1 parse 流程

```
输入: tokens (Token流)

1. 初始化 _state, pos=0
2. 调用 _parse_program()
3. 若 _state.errors 非空 → 抛出 ParserError
4. 返回 ProgramNode
```

### 5.2 _parse_program

```
1. children = []
2. while pos < len(tokens):
   a. 若当前 Token 为 TEXT → 创建 TextNode, 加入 children
   b. 若当前 Token 为 IF_OPEN → 调用 _parse_conditional(depth=0), 加入 children
   c. 其他 → 错误 (IF_CLOSE/ELSE/ELSE_IF 出现在非预期位置)
3. 返回 ProgramNode(children=children, source_id=source_id)
```

### 5.3 _parse_conditional

```
输入: depth (当前嵌套深度)

1. 校验 depth ≤ max_nesting_depth, 否则抛出深度超限错误
2. 消费 IF_OPEN → 解析条件表达式 → 构造 if_branch
3. if_branch.children = _parse_branch_body(depth+1)
4. while 当前 Token 为 ELSE_IF:
   a. 消费 ELSE_IF → 解析条件 → 构造 else_if_branch
   b. branch.children = _parse_branch_body(depth+1)
   c. 加入 else_if_branches
5. 若当前 Token 为 ELSE:
   a. 消费 ELSE → 构造 else_branch
   b. else_branch.children = _parse_branch_body(depth+1)
6. 消费 IF_CLOSE
7. 返回 ConditionalNode
```

### 5.4 _parse_branch_body

```
输入: depth (当前深度)

1. children = []
2. while 当前 Token 不是 IF_CLOSE / ELSE / ELSE_IF:
   a. TEXT → TextNode
   b. IF_OPEN → 递归 _parse_conditional(depth)
3. 返回 children
```

---

## 6. 示例

### 6.1 简单条件

**Token 流:**
```python
[IF_OPEN("model==\"gpt-4o\""), TEXT("高级推理"), IF_CLOSE("")]
```

**AST:**
```
ProgramNode
└── ConditionalNode (line=1, col=1)
    ├── if_branch: conditions=[Condition(model, EQ, "gpt-4o")]
    │   └── children: [TextNode("高级推理")]
    ├── else_if_branches: []
    └── else_branch: None
```

### 6.2 多分支条件

**Token 流:**
```python
[
    IF_OPEN('model=="gpt-4o"'),
    TEXT("推理模式"),
    ELSE_IF('model=="claude-3"'),
    TEXT("分析模式"),
    ELSE(""),
    TEXT("通用模式"),
    IF_CLOSE(""),
]
```

**AST:**
```
ProgramNode
└── ConditionalNode (line=1, col=1)
    ├── if_branch: conditions=[Condition(model, EQ, "gpt-4o")]
    │   └── children: [TextNode("推理模式")]
    ├── else_if_branches:
    │   └── [Branch: conditions=[Condition(model, EQ, "claude-3")]
    │           children: [TextNode("分析模式")]]
    └── else_branch: Branch: conditions=[]
            children: [TextNode("通用模式")]
```

### 6.3 嵌套条件 (2层)

**模板:**
```
{{#if model=="gpt-4o"}}GPT-4o专属{{#if language=="python"}}Python模式{{/if}}{{/if}}
```

**AST:**
```
ProgramNode
└── ConditionalNode (depth=0)
    ├── if_branch: conditions=[Condition(model, EQ, "gpt-4o")]
    │   └── children:
    │       ├── TextNode("GPT-4o专属")
    │       └── ConditionalNode (depth=1)
    │           ├── if_branch: conditions=[Condition(language, EQ, "python")]
    │           │   └── children: [TextNode("Python模式")]
    │           ├── else_if_branches: []
    │           └── else_branch: None
    ├── else_if_branches: []
    └── else_branch: None
```

### 6.4 复合条件

**条件表达式:** `model=="gpt-4o" and language=="python"`

**解析结果:**
```python
[
    Condition(dimension="model", operator=Operator.EQ, value="gpt-4o", logical=LogicalOp.AND),
    Condition(dimension="language", operator=Operator.EQ, value="python", logical=LogicalOp.NONE),
]
```

---

## 7. 嵌套处理规则

| 嵌套层级 | 深度 | 行为 |
|----------|------|------|
| 0层 (顶层) | 0 | 正常解析 |
| 1层 | 1 | 正常解析 |
| 2层 | 2 | 正常解析 |
| 3层 | 3 | 达到 max_nesting_depth 上限，允许但警告 |
| >3层 | 4+ | 抛出 ParserError，执行 truncation 回退 |

### 嵌套深度与 config.yaml 的映射

```yaml
# config.yaml
max_nesting_depth: 3    # ParserConfig.max_nesting_depth 直接读取此值
```

---

## 8. 性能目标

| 指标 | 目标值 |
|------|--------|
| 解析吞吐 | ≥ 5MB/s (Token 流) |
| 单模板延迟 (100 条件, 1KB) | < 1ms |
| AST 内存 | O(n)，n 为节点数 |
| 嵌套深度检测 | O(1) 额外开销 |

---

## 9. 与上下游模块接口

```
上游: Lexer.tokenize() → List[Token] → Parser.parse()
下游: Parser.parse() → ProgramNode → Evaluator.evaluate() → Renderer.render()
```

AST 节点均为不可变数据类 (frozen=True)，确保在缓存和并行求值场景下的线程安全。
