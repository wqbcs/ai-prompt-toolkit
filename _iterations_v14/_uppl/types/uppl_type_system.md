# UPPL类型系统

> 版本：v14.0.0 | 日期：2026-05-29

---

## 1. 基本类型

| 类型 | 说明 | 示例 |
|------|------|------|
| string | 字符串 | "hello" |
| number | 数值(int/float) | 42, 3.14 |
| bool | 布尔 | true, false |
| null | 空值 | null |

## 2. 提示词域类型(4大基本类型)

### 2.1 场景类型(Scene)
```uppl
type Scene = {
  role: string,
  task: string,
  context: dict<string, any>,
  metadata?: dict<string, any>
};
```

### 2.2 约束类型(Constraint)
```uppl
type Constraint = {
  must: list<Expr>,       // 必须满足
  must_not: list<Expr>,   // 必须不满足
  prefer: list<Expr>,     // 优选满足
  priority?: number       // 优先级(1-10)
};

// 约束求值结果
type ConstraintResult = {
  satisfied: bool,
  violations: list<Violation>,
  score: number  // [0, 20]
};
```

### 2.3 输出类型(Output)
```uppl
type Output = {
  format: Format,          // json|yaml|markdown|text|custom
  schema: TypeExpr,        // 输出Schema
  examples: list<Example>, // 输入→输出示例
  post_processors?: list<Processor>
};

type Example = {
  input: string,
  output: string,
  description?: string
};
```

### 2.4 检查项类型(Check)
```uppl
type Check = {
  assertions: list<Assert>,
  verifications: list<Verify>,
  measurements: dict<string, Expr>
};

type Assert = {
  condition: Expr,
  message: string,
  severity: "error" | "warning" | "info"
};

type Verify = {
  condition: Expr,
  method: "formal" | "statistical" | "empirical"
};
```

---

## 3. 组合类型

### 3.1 提示词模块类型
```uppl
type PromptModule = {
  name: string,
  version: SemVer,
  scene: Scene,
  constraints: list<Constraint>,
  output: Output,
  checks: list<Check>,
  steps?: list<Step>   // 命令式步骤(可选)
};
```

### 3.2 提示词链类型
```uppl
type PromptChain = {
  modules: list<PromptModule>,
  data_flow: "sequential" | "parallel" | "conditional",
  error_handling: "fail_fast" | "continue" | "retry"
};
```

### 3.3 提示词图类型
```uppl
type PromptGraph = {
  nodes: dict<string, PromptModule>,
  edges: list<Edge>,
  entry: string
};

type Edge = {
  from: string,
  to: string,
  condition?: Expr,
  transform?: Expr
};
```

---

## 4. 类型推导规则

### 4.1 推导规则
```
Γ ⊢ e₁ : τ₁   τ₁ <: τ₂
──────────────────────────  (Subsumption)
      Γ ⊢ e₁ : τ₂

Γ, x: τ₁ ⊢ e : τ₂
────────────────────  (Abstraction)
Γ ⊢ λx:τ₁.e : τ₁ → τ₂

Γ ⊢ e₁ : τ₁ → τ₂   Γ ⊢ e₂ : τ₁
──────────────────────────────────  (Application)
         Γ ⊢ e₁ e₂ : τ₂
```

### 4.2 类型安全
- **进展性(Progress)**：良类型表达式不会卡住
- **保持性(Preservation)**：求值保持类型

---

## 5. UPPL编译器目标

### 5.1 目标1：自然语言(NL)
```
UPPL源码 → 自然语言提示词
- scene.role → 系统指令角色段
- scene.task → 系统指令任务段
- constraints → 约束指令段
- output.format+schema → 输出格式指令段
- output.examples → 示例段
- checks → 验证指令段
```

### 5.2 目标2：JSON规范
```
UPPL源码 → JSON执行规范
- 结构化数据表示
- 可被运行时直接加载执行
- 含完整类型信息
```

### 5.3 目标3：Agent指令
```
UPPL源码 → Agent执行指令
- 步骤序列化
- 条件分支→Agent决策点
- 循环→Agent迭代指令
- 跨Agent调用→Agent委派指令
```

### 5.4 编译正确性
**语义保持定理**：对任意UPPL程序p，编译后程序c在24维度评估的偏差≤0.5：
```
∀p ∈ UPPL, ∀target ∈ {NL, JSON, Agent}:
  |evaluate(compile(p, target)) - evaluate(p)| ≤ 0.5
```
