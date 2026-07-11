# P1-03 断点调试系统

> **迭代**：v19-P1-03 | **日期**：2026-07-12

---

## 断点调试设计

### 断点类型

```typescript
interface Breakpoint {
  id: string
  type: 'line' | 'conditional' | 'variable' | 'error' | 'timeout'
  target: string
  condition?: string
  enabled: boolean
  hitCount: number
  actions: BreakpointAction[]
}

interface BreakpointAction {
  type: 'pause' | 'log' | 'modify_variable' | 'skip_step' | 'inject_output'
  params: Map<string, any>
}
```

### 四种断点模式

| 模式 | 触发条件 | 用途 |
|------|---------|------|
| 行级断点 | 执行到指定步骤 | 检查特定步骤中间状态 |
| 条件断点 | 满足表达式时触发 | 特定场景下调试 |
| 变量断点 | 变量值变更时触发 | 追踪变量流转 |
| 错误断点 | 约束检查失败时触发 | 快速定位问题 |

### 调试操作

```
continue    → 继续执行到下一个断点
step-over   → 执行当前步骤，停在下一条
step-into   → 进入子步骤（如示例展开）
step-out    → 执行完当前子步骤组
step-back   → 回退一步
restart     → 从头开始
```

### 变量检查

```typescript
interface VariableInspector {
  getAll(): Map<string, any>
  get(name: string): any
  set(name: string, value: any): void
  watch(expression: string): WatchResult
  evaluate(expression: string, context: ExecutionContext): any
}

interface WatchResult {
  expression: string
  value: any
  type: string
  changed: boolean
  previousValue?: any
}
```

### 调试会话

```typescript
interface DebugSession {
  id: string
  prompt: string
  context: ExecutionContext
  breakpoints: Breakpoint[]
  history: StepResult[]
  currentStep: number
  state: 'running' | 'paused' | 'completed' | 'error'
  
  start(): void
  pause(): void
  resume(): void
  stop(): void
  
  getCallStack(): CallFrame[]
  getVariables(): Map<string, any>
  getOutput(): string
}
```

### 运行时修改变量

```
> set {{temperature}} = 0.3
> set {{max_tokens}} = 1024
> set {{language}} = "Rust"
> continue
```

允许在暂停时修改变量值，然后继续执行观察效果变化。
