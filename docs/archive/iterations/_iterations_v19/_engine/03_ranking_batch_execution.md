# P2-04 推荐结果排序与解释 + P2-05/06/07 批量执行框架

> **迭代**：v19-P2-04~07 | **日期**：2026-07-12

---

## 推荐结果排序与解释

### 排序策略

```typescript
interface RankingStrategy {
  rank(recommendations: ScenarioRecommendation[]): ScenarioRecommendation[]
}

// 默认排序：综合评分降序
// 可选排序：按相关性/适用性/新鲜度单独排序
// 多样性排序：确保推荐结果覆盖不同类别
```

### 解释生成

```typescript
interface ExplanationGenerator {
  generate(recommendation: ScenarioRecommendation): string
}

// 解释模板：
// "推荐[场景名]因为：1) 技术栈匹配(Go+Gin)；2) 任务类型匹配(微服务开发)；3) 约束兼容(华为云部署)"
// "与你的项目相关度{relevance}%，适用度{applicability}%"
// "建议调整：[具体调整项]"
```

## 批量执行框架

### 核心接口

```typescript
interface BatchExecutor {
  submit(tasks: BatchTask[]): BatchJob
  getStatus(jobId: string): BatchJobStatus
  getResults(jobId: string): BatchResult
  cancel(jobId: string): void
}

interface BatchTask {
  scenarioId: string
  variables: Map<string, any>
  model: string
  priority: number
  retryPolicy: RetryPolicy
}

interface BatchJob {
  id: string
  tasks: BatchTask[]
  options: BatchOptions
  status: BatchJobStatus
  submittedAt: string
}

interface BatchOptions {
  parallelism: number
  timeout: number
  retryPolicy: RetryPolicy
  aggregationStrategy: 'concat' | 'merge' | 'compare' | 'vote'
  failStrategy: 'fail_fast' | 'continue' | 'retry'
}

interface RetryPolicy {
  maxRetries: number
  backoffMs: number
  backoffMultiplier: number
  retryableErrors: string[]
}
```

### 执行调度器

```
┌──────────────┐
│ 任务队列      │ ← 提交批量任务
└──────┬───────┘
       │
┌──────▼───────┐
│ 调度器        │ ← 控制并行度
└──────┬───────┘
       │
   ┌───┼───┐
   │   │   │
┌──▼┐┌▼──┐┌▼──┐
│W-1││W-2││W-3│  ← Worker池
└──┬┘└┬──┘└┬──┘
   │   │   │
┌──▼───▼───▼──┐
│ 结果聚合器    │ ← 合并/对比/投票
└──────┬───────┘
       │
┌──────▼───────┐
│ 报告生成器    │ ← 生成批量报告
└──────────────┘
```

### 结果聚合引擎

```typescript
interface ResultAggregator {
  aggregate(results: TaskResult[], strategy: AggregationStrategy): AggregatedResult
}

type AggregationStrategy = 
  | { type: 'concat' }
  | { type: 'merge'; conflictResolution: 'latest' | 'highest_score' | 'manual' }
  | { type: 'compare'; metrics: string[] }
  | { type: 'vote'; threshold: number; minAgreement: number }

interface AggregatedResult {
  summary: string
  results: TaskResult[]
  statistics: BatchStatistics
  anomalies: Anomaly[]
  comparisonTable?: ComparisonEntry[]
}

interface BatchStatistics {
  totalTasks: number
  completedTasks: number
  failedTasks: number
  avgLatency: number
  avgTokenCount: number
  consistencyScore: number
}

interface Anomaly {
  taskId: string
  type: 'timeout' | 'error' | 'output_mismatch' | 'constraint_violation'
  description: string
  severity: 'critical' | 'warning' | 'info'
}
```

### 批量执行报告

```markdown
# 批量执行报告

## 执行概要
- **任务总数**: 10
- **成功**: 9 | **失败**: 1 | **超时**: 0
- **平均延迟**: 2.3s | **平均Token**: 856
- **一致性评分**: 0.87

## 结果对比
| 场景 | 模型 | 状态 | 延迟 | Token | 评分 |
|------|------|------|------|-------|------|
| S-012 | gpt-4 | ✓ | 1.8s | 920 | 0.92 |
| S-012 | claude | ✓ | 2.1s | 780 | 0.89 |
| S-023 | gpt-4 | ✗ | 5.0s | - | 0.00 |

## 异常检测
- ⚠️ S-023在gpt-4上执行失败：约束检查未通过
- 建议检查S-023的输出格式约束

## CLI命令
```bash
# 提交批量执行
prompt-batch run --scenarios S-012,S-023 --models gpt-4,claude --parallel 3

# 查看执行状态
prompt-batch status <job-id>

# 获取结果
prompt-batch results <job-id> --format markdown
```
