# P1-05 语义变更评分与影响评估

> **迭代**：v19-P1-05 | **日期**：2026-07-12

---

## 语义评分算法

### 评分模型

```typescript
interface SemanticScorer {
  score(change: SemanticChange): number
  aggregate(changes: SemanticChange[]): AggregateScore
  detectDrift(versions: PromptVersion[]): DriftReport
}

interface AggregateScore {
  totalScore: number
  categoryScores: Map<SemanticCategory, number>
  riskLevel: 'critical' | 'high' | 'medium' | 'low'
  summary: string
}

interface DriftReport {
  trend: 'improving' | 'stable' | 'degrading' | 'critical'
  driftScore: number
  milestones: DriftMilestone[]
  recommendation: string
}
```

### 评分维度

| 维度 | 权重 | 评分方法 |
|------|------|---------|
| 行为影响 | 0.30 | 输出差异度（BLEU/ROUGE） |
| 约束完整度 | 0.25 | 约束增删/修改比例 |
| 格式兼容性 | 0.20 | 输出格式变更检测 |
| 角色一致性 | 0.15 | 角色定义语义相似度 |
| 示例对齐度 | 0.10 | 示例风格相似度 |

### 评分流程

```
输入：两个版本的提示词
  │
  ├── 1. 文本差异提取
  │     └── diff算法（Myers/O(N)PD）
  │
  ├── 2. 语义分类
  │     └── NLP分类器（角色/约束/格式/示例/指令）
  │
  ├── 3. 影响量化
  │     └── 每类变更的权重×严重度
  │
  ├── 4. 场景关联
  │     └── 受影响场景匹配
  │
  └── 5. 综合评分
        └── 加权汇总 → 风险等级 → 建议
```

### 语义漂移检测

跨版本累积检测：
- v1→v2：0.05（低风险）
- v2→v3：0.08（低风险）
- v3→v4：0.32（高风险！语义漂移）
- 累积漂移：0.45（超过0.3阈值）

### 回归风险矩阵

| 变更类型 | 低频使用 | 中频使用 | 高频使用 |
|---------|---------|---------|---------|
| 角色变更 | 中 | 高 | 严重 |
| 约束删除 | 高 | 高 | 严重 |
| 格式变更 | 低 | 中 | 高 |
| 示例替换 | 低 | 低 | 中 |
| 变量调整 | 低 | 低 | 低 |
