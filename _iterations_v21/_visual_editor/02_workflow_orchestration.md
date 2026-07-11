# R1-02 提示词可视化编辑器-可视化工作流编排

> **迭代**：v21-R1-02 | **日期**：2026-07-12

---

## 一、工作流编排引擎

### 工作流类型

```typescript
type WorkflowType = 
  | 'sequential'    // 顺序执行
  | 'parallel'      // 并行执行
  | 'conditional'   // 条件分支
  | 'loop'          // 循环迭代
  | 'fan_out_fan_in' // 扇出扇入
  | 'dag'           // 有向无环图

interface WorkflowDefinition {
  id: string
  name: string
  version: string
  type: WorkflowType
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  variables: WorkflowVariable[]
  errorHandling: ErrorHandlingStrategy
  timeout: number
  retryPolicy: RetryPolicy
}

interface WorkflowNode {
  id: string
  type: 'start' | 'end' | 'scenario' | 'transform' | 'validate' | 'condition' | 'loop' | 'delay' | 'notify'
  label: string
  config: Record<string, unknown>
  inputSchema?: JSONSchema
  outputSchema?: JSONSchema
  position: { x: number; y: number }
}

interface WorkflowEdge {
  id: string
  source: string
  target: string
  type: 'normal' | 'conditional_true' | 'conditional_false' | 'loop_back'
  condition?: string
  transform?: string
}

interface WorkflowVariable {
  name: string
  type: 'string' | 'number' | 'boolean' | 'object' | 'array'
  defaultValue?: unknown
  description: string
  scope: 'global' | 'node'
}
```

## 二、工作流编排可视化

### 画布交互

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 添加节点 | 双击画布 | 弹出节点选择器 |
| 连接节点 | 拖拽端口 | 创建连线 |
| 删除连线 | 点击+Delete | 删除边 |
| 条件分支 | 右键节点→添加分支 | 添加True/False路径 |
| 循环节点 | 右键节点→包裹循环 | 创建循环节点 |
| 分组 | 框选+Ctrl+G | 创建节点组 |
| 对齐 | 框选+对齐工具 | 左/右/上/下/居中 |
| 缩放 | Ctrl+滚轮 | 25%-400% |
| 小地图 | 右下角缩略图 | 快速导航 |

### 工作流模板（10种）

| # | 模板名 | 类型 | 适用场景 |
|---|--------|------|---------|
| 1 | 简单顺序 | sequential | 单场景执行 |
| 2 | 多场景并行 | parallel | 多语言/多框架对比 |
| 3 | 条件选择 | conditional | 根据项目类型选择场景 |
| 4 | 迭代优化 | loop | 提示词质量迭代 |
| 5 | 扇出扇入 | fan_out_fan_in | 多维度评估→汇总 |
| 6 | 代码审查 | dag | 语言检测→场景选择→审查→输出 |
| 7 | 安全审计 | sequential | SAST→DAST→依赖检查→报告 |
| 8 | 性能优化 | loop | 基准→优化→验证→迭代 |
| 9 | 迁移辅助 | conditional | 源技术→目标技术→迁移步骤 |
| 10 | 全流程 | dag | 需求→设计→开发→测试→部署 |

### 错误处理策略

```typescript
interface ErrorHandlingStrategy {
  type: 'retry' | 'fallback' | 'skip' | 'abort' | 'notify'
  maxRetries: number
  retryDelay: number
  fallbackNode?: string
  notifyTarget?: string
  errorMessage?: string
}

interface RetryPolicy {
  maxAttempts: number
  backoffStrategy: 'fixed' | 'linear' | 'exponential'
  initialDelay: number
  maxDelay: number
  retryableErrors: string[]
}
```

## 三、工作流执行引擎

### 执行模式

| 模式 | 说明 | 适用 |
|------|------|------|
| 同步 | 阻塞等待完成 | 调试/测试 |
| 异步 | 非阻塞+回调 | 生产执行 |
| 流式 | 逐步输出结果 | 大型工作流 |
| 暂停/恢复 | 人工审批节点 | Human-in-the-Loop |

### 执行状态

```
pending → running → completed
                 → failed → retrying → running
                 → cancelled
         → paused → running (人工审批后)
```

### 执行追踪

```typescript
interface WorkflowExecution {
  id: string
  workflowId: string
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  startedAt: string
  completedAt?: string
  nodeExecutions: NodeExecution[]
  variables: Record<string, unknown>
  totalTokens: number
  totalCost: number
}

interface NodeExecution {
  nodeId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  startedAt?: string
  completedAt?: string
  input?: unknown
  output?: unknown
  error?: string
  tokens: number
  latency: number
}
```

## 四、验收项

- [x] 工作流编排引擎定义（6种工作流类型）
- [x] 10种工作流模板设计
- [x] 画布交互8种操作+快捷键
- [x] 错误处理策略+重试策略
- [x] 执行引擎4种模式+状态机
- [x] 执行追踪数据结构
