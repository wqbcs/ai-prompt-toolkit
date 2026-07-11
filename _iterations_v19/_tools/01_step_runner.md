# P1-01 提示词逐步执行引擎（StepRunner）

> **迭代**：v19-P1-01 | **日期**：2026-07-12

---

## StepRunner 架构设计

### 核心接口

```typescript
interface StepRunner {
  loadPrompt(prompt: string): PromptAST
  execute(context: ExecutionContext): StepResult[]
  stepForward(): StepResult
  stepBack(): void
  runTo(stepIndex: number): StepResult[]
  reset(): void
}

interface PromptAST {
  steps: PromptStep[]
  variables: Map<string, VariableDef>
  metadata: PromptMetadata
}

interface PromptStep {
  index: number
  type: 'role' | 'instruction' | 'example' | 'constraint' | 'output_format' | 'reference' | 'separator'
  content: string
  resolvedContent: string
  tokenEstimate: number
  dependencies: string[]
  children: PromptStep[]
}

interface ExecutionContext {
  variables: Map<string, any>
  model: string
  temperature: number
  maxTokens: number
  breakpoints: Set<number>
  watchExpressions: Map<string, string>
}

interface StepResult {
  stepIndex: number
  stepType: PromptStep['type']
  input: string
  output: string
  tokenCount: { prompt: number; completion: number; total: number }
  latency: number
  variables: Map<string, any>
  constraints: ConstraintCheck[]
  status: 'passed' | 'failed' | 'warning' | 'skipped'
}

interface ConstraintCheck {
  constraint: string
  expected: string
  actual: string
  passed: boolean
  message: string
}
```

### 执行流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 解析提示词   │────→│ 构建AST     │────→│ 逐步执行    │
│ (Parse)     │     │ (Build AST) │     │ (Execute)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────┐     ┌─────┴───────┐
                    │ 输出结果     │←────│ 检查约束    │
                    │ (Output)    │     │ (Verify)    │
                    └─────────────┘     └─────────────┘
```

### 步骤解析规则

| 提示词元素 | 步骤类型 | 解析规则 |
|-----------|---------|---------|
| `# Role: ...` | role | 角色定义行 |
| `## 指令/要求` | instruction | 以指令性动词开头 |
| `- 示例:` | example | 包含示例标记 |
| `- 约束/限制` | constraint | 包含约束关键词 |
| `## 输出格式` | output_format | 输出格式定义 |
| `> 参考` | reference | 引用块 |
| `---` | separator | 分隔线 |

### 变量解析

```
{{variable}} → 严格匹配，未定义则报错
{{variable|default}} → 未定义使用默认值
{{variable|default:"N/A"}} → 默认值含空格
{{#if condition}}...{{/if}} → 条件渲染
{{#each list}}...{{/each}} → 循环渲染
```

### 执行模式

1. **逐步模式**：每步暂停，可检查中间状态
2. **运行到断点**：连续执行直到遇到断点
3. **全量执行**：一次性执行所有步骤
4. **回放模式**：记录执行过程，可回放查看
