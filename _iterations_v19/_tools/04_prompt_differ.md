# P1-04 提示词Diff工具-版本对比与语义变更检测

> **迭代**：v19-P1-04 | **日期**：2026-07-12

---

## Diff工具架构

### 核心接口

```typescript
interface PromptDiffer {
  compare(versionA: PromptVersion, versionB: PromptVersion): DiffResult
  detectSemanticChanges(diff: DiffResult): SemanticChange[]
  assessImpact(changes: SemanticChange[]): ImpactReport
  generateChangelog(diff: DiffResult): string
}

interface PromptVersion {
  id: string
  content: string
  metadata: PromptMetadata
  timestamp: string
  author: string
  tags: string[]
}

interface DiffResult {
  additions: TextChange[]
  deletions: TextChange[]
  modifications: TextChange[]
  moves: TextMove[]
  unchanged: number
  similarity: number
}

interface TextChange {
  lineA?: number
  lineB?: number
  content: string
  section: string
  type: 'role' | 'instruction' | 'example' | 'constraint' | 'output_format'
  severity: 'critical' | 'major' | 'minor' | 'cosmetic'
}
```

### 语义变更检测

```typescript
interface SemanticChange {
  id: string
  category: SemanticCategory
  description: string
  beforeValue: string
  afterValue: string
  impactScore: number
  affectedScenarios: string[]
  riskLevel: 'high' | 'medium' | 'low'
  recommendation: string
}

type SemanticCategory = 
  | 'role_change'
  | 'constraint_added'
  | 'constraint_removed'
  | 'constraint_modified'
  | 'output_format_change'
  | 'example_replacement'
  | 'instruction_shift'
  | 'variable_change'
  | 'tone_change'
  | 'scope_change'
```

### 语义变更评分

| 变更类别 | 评分范围 | 说明 |
|---------|---------|------|
| 角色变更 | 0.8-1.0 | 影响全局行为 |
| 约束删除 | 0.7-1.0 | 可能导致输出失控 |
| 输出格式变更 | 0.5-0.9 | 影响下游解析 |
| 约束修改 | 0.4-0.8 | 视修改幅度 |
| 示例替换 | 0.3-0.7 | 影响风格对齐 |
| 指令微调 | 0.2-0.5 | 影响可控 |
| 变量变更 | 0.1-0.4 | 参数化调整 |
| 格式修饰 | 0.0-0.2 | 纯样式变更 |

### 影响评估报告

```typescript
interface ImpactReport {
  overallRisk: 'critical' | 'high' | 'medium' | 'low'
  semanticChanges: SemanticChange[]
  affectedScenarios: AffectedScenario[]
  compatibilityMatrix: CompatibilityEntry[]
  regressionRisk: number
  recommendedActions: string[]
  testSuggestions: string[]
}

interface AffectedScenario {
  scenarioId: string
  scenarioName: string
  impactLevel: 'breaking' | 'significant' | 'minor' | 'none'
  description: string
  testRequired: boolean
}

interface CompatibilityEntry {
  scenarioId: string
  versionA: 'compatible' | 'partial' | 'incompatible'
  versionB: 'compatible' | 'partial' | 'incompatible'
  migrationNeeded: boolean
}
```

### Diff可视化模式

1. **Side-by-Side**：左右并排对照
2. **Inline**：行内差异标注（+/-高亮）
3. **Unified**：统一视图（类git diff）
4. **Semantic**：语义视图（只显示语义变更）
5. **Impact**：影响视图（按风险等级着色）
