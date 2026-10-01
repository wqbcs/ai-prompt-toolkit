# P2-01 智能推荐引擎-项目上下文分析器

> **迭代**：v19-P2-01 | **日期**：2026-07-12

---

## 项目上下文分析器

### 核心接口

```typescript
interface ContextAnalyzer {
  analyze(input: ProjectInput): ProjectContext
  extractKeywords(input: ProjectInput): string[]
  detectStack(input: ProjectInput): TechStack
  inferTask(input: ProjectInput): TaskType
}

interface ProjectInput {
  description: string
  files?: FileInfo[]
  dependencies?: string[]
  existingPrompts?: string[]
}

interface ProjectContext {
  id: string
  languages: string[]
  frameworks: string[]
  taskType: TaskType
  constraints: string[]
  domain: string
  existingScenarios: string[]
  keywords: string[]
  confidence: number
}

interface TechStack {
  primary: string
  secondary: string[]
  databases: string[]
  infrastructure: string[]
  tools: string[]
}

type TaskType = 
  | 'code_review' | 'bug_fix' | 'feature_dev' | 'refactoring'
  | 'testing' | 'deployment' | 'monitoring' | 'documentation'
  | 'architecture' | 'performance' | 'security' | 'migration'
```

### 上下文提取规则

| 输入信号 | 提取规则 | 示例 |
|---------|---------|------|
| 语言关键词 | 匹配语言名 | "Go后端"→Go |
| 框架关键词 | 匹配框架名 | "Gin框架"→Gin |
| 任务动词 | 匹配任务类型 | "审查代码"→code_review |
| 约束描述 | 提取约束 | "不超过100行"→length_constraint |
| 领域术语 | 匹配领域 | "微服务"→backend/distributed |

### 推荐匹配算法

```typescript
interface RecommendationEngine {
  recommend(context: ProjectContext): ScenarioRecommendation[]
  rank(recommendations: ScenarioRecommendation[]): ScenarioRecommendation[]
  explain(recommendation: ScenarioRecommendation): Explanation
}

interface ScenarioRecommendation {
  scenarioId: string
  scenarioName: string
  relevance: number
  applicability: number
  freshness: number
  score: number
  reason: string
  adjustments: string[]
}

// 评分公式
// score = 0.4 * relevance + 0.35 * applicability + 0.25 * freshness
```
