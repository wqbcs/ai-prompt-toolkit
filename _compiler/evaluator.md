# 条件求值器设计 (Evaluator)

> 模块路径: `_compiler/evaluator`
> 版本: v1.0
> 依赖: `ast.md` (AST 节点)

---

## 1. 概述

条件求值器接收 AST 和编译上下文，对每个条件分支进行布尔求值，确定哪些分支应该被激活。是编译管线的第三阶段。

### 数据流

```
ProgramNode + CompilationContext
         │
         ▼
  Evaluator.evaluate()
         │
    ┌────┴────┐
    │ 逐节点遍历 │
    ├─────────┤
    │ TextNode → 标记为 active
    │ ConditionalNode →
    │   if_branch → evaluate_conditions() → True/False
    │   else_if_branches → 逐个求值
    │   else_branch → 前面均 False 时激活
    └─────────┘
         │
         ▼
  EvaluatedAST (节点 + active/inactive 标记)
```

---

## 2. 类型定义

### 2.1 CompilationContext

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CompilationContext:
    model: str                          # 模型标识: "gpt-4o", "claude-3", "gemini-pro"
    language: str                       # 编程语言: "python", "go", "rust"
    industry: str                       # 行业领域: "finance", "healthcare", "education"
    extras: dict[str, str] = field(default_factory=dict)  # 扩展维度

    def get_dimension(self, name: str) -> str | None:
        """按名称获取维度值，支持 extras"""
        builtin = {"model": self.model, "language": self.language, "industry": self.industry}
        return builtin.get(name) or self.extras.get(name)
```

### 2.2 求值结果

```python
from enum import Enum, auto

class BranchStatus(Enum):
    ACTIVE = auto()     # 条件匹配，分支激活
    INACTIVE = auto()   # 条件不匹配，分支忽略

@dataclass
class EvaluatedBranch:
    branch: Branch
    status: BranchStatus
    evaluated_conditions: list[bool]    # 每个条件的求值结果

@dataclass
class EvaluatedConditional:
    node: ConditionalNode
    branches: list[EvaluatedBranch]     # 按顺序: if + else_ifs + else
    active_index: int                   # 激活分支的索引 (-1 表示无匹配)

EvaluatedNode = TextNode | EvaluatedConditional
```

### 2.3 求值报告

```python
@dataclass
class EvaluationReport:
    activated_branches: list[str]       # 激活分支的条件键
    ignored_branches: list[str]         # 忽略分支的条件键
    uncovered_conditions: list[str]     # 上下文未覆盖的条件维度
    warnings: list[str]                 # 警告信息
```

---

## 3. 核心函数

### 3.1 evaluateCondition

```python
def evaluate_condition(
    condition: Condition,
    context: CompilationContext,
) -> bool:
    """
    求值单个条件

    支持的4种操作符:
      ==      → 维度值 == 期望值
      !=      → 维度值 != 期望值
      in      → 维度值 in 期望值列表 (逗号分隔)
      not in  → 维度值 not in 期望值列表

    返回: True/False
    """
```

**操作符实现:**

```python
def _apply_operator(
    dimension_value: str | None,
    operator: Operator,
    expected_value: str,
) -> bool:
    if dimension_value is None:
        return False

    match operator:
        case Operator.EQ:
            return dimension_value == expected_value
        case Operator.NEQ:
            return dimension_value != expected_value
        case Operator.IN:
            values = [v.strip() for v in expected_value.split(",")]
            return dimension_value in values
        case Operator.NIN:
            values = [v.strip() for v in expected_value.split(",")]
            return dimension_value not in values
```

### 3.2 evaluateConditions (多条件求值)

```python
def evaluate_conditions(
    conditions: list[Condition],
    context: CompilationContext,
) -> bool:
    """
    求值条件列表，按 logical 连接符组合

    求值规则:
      单条件 → 直接求值
      A and B → 短路: A 为 False 则跳过 B
      A or B  → 短路: A 为 True 则跳过 B
      混合   → 从左到右顺序求值 (无优先级区分)

    返回: 组合布尔结果
    """
    if not conditions:
        return True  # else 分支无条件

    result = evaluate_condition(conditions[0], context)

    for i in range(1, len(conditions)):
        prev_logical = conditions[i - 1].logical
        current = evaluate_condition(conditions[i], context)

        match prev_logical:
            case LogicalOp.AND:
                result = result and current
            case LogicalOp.OR:
                result = result or current
            case LogicalOp.NONE:
                result = result and current  # 隐式 AND

    return result
```

### 3.3 自动选择规则

```python
def auto_select_dimension(
    context: CompilationContext,
    required_dimensions: set[str],
) -> dict[str, str]:
    """
    根据编译上下文自动选择条件维度值

    规则:
      1. context 中显式指定的维度优先
      2. 未指定的维度从 extras 中查找
      3. 都没有则加入 uncovered_conditions
    """
    selected = {}
    for dim in required_dimensions:
        value = context.get_dimension(dim)
        if value is not None:
            selected[dim] = value
    return selected
```

### 3.4 副作用检测

```python
def detect_side_effects(
    conditions: list[Condition],
    context: CompilationContext,
) -> list[str]:
    """
    检测条件求值可能产生的副作用

    检测项:
      1. 条件引用了上下文中不存在的维度
      2. in/not in 操作符的值列表包含空元素
      3. 同一维度出现矛盾条件 (A=="x" and A=="y")
      4. 维度值包含空白字符

    返回: 警告消息列表
    """
```

---

## 4. Evaluator 类设计

### 4.1 类签名

```python
class Evaluator:
    def __init__(self, config: EvaluatorConfig | None = None) -> None: ...
    def evaluate(
        self,
        ast: ProgramNode,
        context: CompilationContext,
    ) -> tuple[list[EvaluatedNode], EvaluationReport]: ...
    def _evaluate_conditional(
        self,
        node: ConditionalNode,
        context: CompilationContext,
        report: EvaluationReport,
    ) -> EvaluatedConditional: ...
    def _resolve_branch(
        self,
        branches: list[EvaluatedBranch],
    ) -> int: ...
```

### 4.2 配置

```python
@dataclass
class EvaluatorConfig:
    strict_mode: bool = False           # 严格模式: 未覆盖条件视为错误
    fallback_value: str = ""            # 缺失维度的回退值
    warn_uncovered: bool = True         # 是否警告未覆盖条件
```

### 4.3 evaluate 流程

```
输入: ProgramNode, CompilationContext

1. 初始化 evaluated_nodes=[], report=EvaluationReport()
2. 遍历 ast.children:
   a. TextNode → 直接加入 evaluated_nodes (始终 active)
   b. ConditionalNode → _evaluate_conditional()
3. 返回 (evaluated_nodes, report)
```

### 4.4 _evaluate_conditional 流程

```
输入: ConditionalNode, CompilationContext

1. 求值 if_branch → EvaluatedBranch
2. 逐个求值 else_if_branches → EvaluatedBranch 列表
3. 若有 else_branch:
   a. else 始终为 active=False (默认)
   b. 仅当前面所有分支都 INACTIVE 时，else 变为 ACTIVE
4. 计算 active_index:
   a. 找到第一个 ACTIVE 分支的索引
   b. 都不匹配 → active_index = -1
5. 更新 report (activated/ignored/uncovered)
6. 执行 detect_side_effects() → 合并到 report.warnings
7. 返回 EvaluatedConditional
```

---

## 5. 示例

### 5.1 基础求值

**上下文:**
```python
ctx = CompilationContext(model="gpt-4o", language="python", industry="tech")
```

**AST:**
```
ConditionalNode
├── if_branch: [Condition(model, EQ, "gpt-4o")] → children: [TextNode("推理模式")]
├── else_if: [Condition(model, EQ, "claude-3")] → children: [TextNode("分析模式")]
└── else_branch → children: [TextNode("通用模式")]
```

**求值结果:**
```
EvaluatedConditional
├── branches:
│   ├── EvaluatedBranch(if, ACTIVE, [True])
│   ├── EvaluatedBranch(else_if, INACTIVE, [False])
│   └── EvaluatedBranch(else, INACTIVE, [])
├── active_index: 0
```

### 5.2 复合条件求值

**条件:** `model=="gpt-4o" and language=="python"`

**上下文1:** `CompilationContext(model="gpt-4o", language="python", industry="tech")`
→ 结果: `True and True = True`

**上下文2:** `CompilationContext(model="gpt-4o", language="go", industry="tech")`
→ 结果: `True and False = False` (短路)

### 5.3 in 操作符

**条件:** `model in "gpt-4o,claude-3,gemini-pro"`

**上下文:** `CompilationContext(model="claude-3", ...)`
→ `claude-3 in ["gpt-4o", "claude-3", "gemini-pro"] = True`

### 5.4 副作用检测示例

**条件:** `model=="gpt-4o" and model=="claude-3"`

**警告:** `"同一维度 'model' 出现矛盾条件: 'gpt-4o' vs 'claude-3'"`

---

## 6. 性能目标

| 指标 | 目标值 |
|------|--------|
| 单条件求值延迟 | < 0.01ms |
| 100条件求值延迟 | < 0.1ms |
| 短路求值节省率 | ≥ 30% (平均) |
| 副作用检测开销 | < 求值总时间的 5% |

---

## 7. 与上下游模块接口

```
上游: Parser.parse() → ProgramNode + CompilationContext → Evaluator.evaluate()
下游: Evaluator.evaluate() → (List[EvaluatedNode], EvaluationReport) → Renderer.render()
```

EvaluationReport 的 activated_branches/ignored_branches/uncovered_conditions 直接映射到 compile_report.schema.json 的对应字段。
