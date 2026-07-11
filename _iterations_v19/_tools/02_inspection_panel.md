# P1-02 中间结果检查面板

> **迭代**：v19-P1-02 | **日期**：2026-07-12

---

## 检查面板设计

### 面板布局

```
┌────────────────────────────────────────────────────────┐
│ [步骤列表]  │  [当前步骤详情]  │  [变量监视]           │
│              │                  │                       │
│ ▶ 1 Role    │  类型: instruction│  {{task}}: "代码审查" │
│ ■ 2 指令 ← │  内容: ...        │  {{lang}}: "Go"      │
│ □ 3 示例    │  Token: 128/2048 │  {{model}}: "gpt-4"  │
│ □ 4 约束    │  延迟: 1.2s      │  {{temp}}: 0.7       │
│ □ 5 格式    │  状态: ✓ 通过     │                       │
│              │                  │  [Token分布图]        │
│              │  [约束检查结果]   │                       │
│              │  ✓ 必须包含代码   │                       │
│              │  ✓ 输出JSON格式   │                       │
│              │  ✗ 不超过500字    │                       │
├────────────────────────────────────────────────────────┤
│ [执行日志]                                              │
│ [09:01:23] Step 1 executed (role) - 45 tokens          │
│ [09:01:24] Step 2 executed (instruction) - 128 tokens  │
│ [09:01:24] Constraint check: 2/3 passed               │
└────────────────────────────────────────────────────────┘
```

### 检查指标

| 指标 | 类型 | 说明 |
|------|------|------|
| Token消耗 | 计数 | 每步prompt/completion/total |
| 延迟 | 时间 | 每步执行耗时(ms) |
| 变量状态 | 快照 | 当前变量解析结果 |
| 约束检查 | 通过率 | 已验证/总数 |
| 输出预览 | 文本 | 当前步骤部分输出 |
| 累计统计 | 汇总 | 总Token/总延迟/平均 |

### Token分析器

```typescript
interface TokenAnalyzer {
  countTokens(text: string, model: string): number
  analyzeDistribution(prompt: PromptAST): TokenDistribution
  estimateCost(tokens: number, model: string): CostEstimate
  optimizeSuggestions(distribution: TokenDistribution): OptimizationSuggestion[]
}

interface TokenDistribution {
  total: number
  byStep: Map<number, number>
  byType: Map<string, number>
  budget: number
  utilization: number
}

interface CostEstimate {
  inputCost: number
  outputCost: number
  totalCost: number
  currency: string
}

interface OptimizationSuggestion {
  step: number
  current: number
  suggested: number
  saving: number
  method: string
}
```

### 实时监视

- WebSocket推送步骤状态
- Token消耗实时更新
- 约束检查即时反馈
- 变量变更通知
