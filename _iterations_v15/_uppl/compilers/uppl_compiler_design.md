# UPPL编译器设计：三个目标后端

> 版本：v1.0 | 日期：2026-05-29

---

## 1. 编译器架构

```
UPPL Source
    ↓
[Lexer] → Token Stream
    ↓
[Parser] → AST
    ↓
[Semantic Analyzer] → Typed AST + Symbol Table
    ↓
┌──────────────┬──────────────┬──────────────┐
│   NL Backend │  JSON Backend│ Agent Backend │
│ (自然语言)    │ (JSON Schema)│ (Agent指令)   │
└──────────────┴──────────────┴──────────────┘
```

## 2. UPPL→自然语言编译器

### 2.1 编译策略

| AST节点 | 自然语言输出 |
|---------|-------------|
| PromptDecl | `## {name}\n\n{body展开}` |
| GivenStmt | `前提条件：\n{语句列表}` |
| ThenStmt | `执行步骤：\n{表达式展开}` |
| EnsureStmt | `必须满足：{expression}` |
| ConstraintDecl | `约束：{message}({level}级别)` |
| ForEachStmt | `对每个{variable}执行：\n{body展开}` |
| WhenStmt | `当{condition}时：\n{body展开}` |
| TemplateExpr | 直接展开模板+变量替换 |
| PipeExpr | `{left}，然后{right}` |

### 2.2 模板展开规则

```
展开(PromptDecl):
  1. 输出标题：## {name}
  2. 输出描述：> {description}
  3. 展开约束块(如有)
  4. 展开given块(前提)
  5. 展开then块(执行)
  6. 展开output规范(如有)

展开(ConstraintBlock):
  "### 约束条件\n"
  for each ensure:
    "- [ERROR/WARN/INFO] {expression}"

展开(GivenStmt):
  "### 前提条件\n"
  for each statement:
    "- {statement展开}"

展开(ThenStmt):
  "### 执行步骤\n"
  管道表达式按步骤分解
```

### 2.3 示例

**UPPL输入**：
```uppl
prompt code_review(language: string, code: string)
  with {
    ensure language in ["Python", "TypeScript", "Java"] as "语言必须支持";
    ensure len(code) > 0 as "代码不能为空";
  }
  given {
    validate security_scan(code) == "pass";
  }
  then `请对以下{{language}}代码进行全面审查：\n{{code}}`
    |> add_checklist(language)
    |> format_markdown()
  output markdown :CodeReviewResult
```

**自然语言输出**：
```markdown
## 代码审查

### 约束条件
- [ERROR] language in ["Python", "TypeScript", "Java"] — 语言必须支持
- [ERROR] len(code) > 0 — 代码不能为空

### 前提条件
- 安全扫描必须通过

### 执行步骤
请对以下{language}代码进行全面审查：
{code}
然后添加检查清单
然后格式化为Markdown

### 输出规范
- 格式：Markdown
- 类型：CodeReviewResult
```

## 3. UPPL→JSON Schema编译器

### 3.1 类型映射

| UPPL类型 | JSON Schema |
|----------|-------------|
| string | `{"type": "string"}` |
| number | `{"type": "number"}` |
| boolean | `{"type": "boolean"}` |
| array<T> | `{"type": "array", "items": {T映射}}` |
| object | `{"type": "object", "properties": {...}}` |
| T1 \| T2 | `{"anyOf": [{T1映射}, {T2映射}]}` |
| enum | `{"enum": [values]}` |

### 3.2 编译规则

```
compile(PromptDecl) → {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": PromptDecl.id,
  "type": "object",
  "properties": {
    "inputs": compile(params),
    "constraints": compile(constraints),
    "output": compile(output_spec)
  },
  "required": [required params]
}

compile(ConstraintDecl) → {
  "type": "object",
  "properties": {
    "rule": {"const": expression},
    "level": {"enum": ["error", "warn", "info"]},
    "message": {"type": "string"}
  }
}

compile(OutputSpec) → {
  "format": output_format,
  "schema": compile(type_expr)
}
```

### 3.3 验证生成

编译器同时生成JSON Schema验证函数：

```python
def generate_validator(schema: dict) -> Callable:
    import jsonschema
    def validator(data: dict) -> tuple[bool, list]:
        try:
            jsonschema.validate(data, schema)
            return (True, [])
        except jsonschema.ValidationError as e:
            return (False, [str(e)])
    return validator
```

## 4. UPPL→Agent指令编译器

### 4.1 编译策略

将UPPL编译为Agent可执行指令序列，包含：
- 步骤分解(Step Decomposition)
- 工具调用映射(Tool Call Mapping)
- 条件路由(Conditional Routing)
- 输出聚合(Output Aggregation)

### 4.2 指令格式

```json
{
  "agent_instruction": {
    "id": "code_review",
    "type": "pipeline",
    "steps": [
      {
        "id": "step_1",
        "type": "validate",
        "tool": "constraint_checker",
        "input": {"constraints": [...]},
        "on_failure": "abort"
      },
      {
        "id": "step_2",
        "type": "llm_call",
        "tool": "llm_inference",
        "input": {"prompt": "...", "model": "auto"},
        "output_key": "review_result"
      },
      {
        "id": "step_3",
        "type": "tool_call",
        "tool": "add_checklist",
        "input": {"language": "{{language}}"},
        "depends_on": "step_2"
      },
      {
        "id": "step_4",
        "type": "tool_call",
        "tool": "format_markdown",
        "input": {},
        "depends_on": "step_3"
      }
    ],
    "output": {
      "format": "markdown",
      "schema": "CodeReviewResult"
    }
  }
}
```

### 4.3 管道表达式→步骤链

```
compile(PipeExpr):
  left_result = compile(left)
  right_result = compile(right)
  return StepChain([
    Step(type="tool_call", tool=left_result.tool, ...),
    Step(type="tool_call", tool=right_result.tool, depends_on=left_step.id, ...)
  ])
```

### 4.4 条件语句→路由

```
compile(WhenStmt):
  return {
    "type": "conditional",
    "condition": compile(expression),
    "if_true": [compile(stmt) for stmt in body],
    "if_false": []
  }
```

## 5. 语义保持性验证

编译器必须满足语义保持性：对任意UPPL程序P，三后端编译结果语义等价。

```
∀P ∈ UPPL:
  semantics(P) ≡ semantics(compile_NL(P))
  semantics(P) ≡ semantics(compile_JSON(P))
  semantics(P) ≡ semantics(compile_Agent(P))
```

验证方法：
1. 构造测试UPPL程序集合T
2. 对每个t∈T，分别编译为NL/JSON/Agent
3. 执行三者，比较输出语义等价性
4. 通过率≥95%视为语义保持
