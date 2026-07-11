# R3-提示词调试与Diff工具开源项目调研

> **调研日期**：2026-07-12 | **调研来源**：github.com/topics/prompt-engineering

---

## 一、核心开源项目分析

### 1.1 promptfoo (23.2k stars)
- **定位**：提示词测试+红队评估+CI/CD集成
- **核心功能**：
  - 声明式配置（YAML格式测试用例）
  - 多模型对比（GPT/Claude/Gemini/DeepSeek）
  - 红队/渗透测试
  - CLI+CI/CD集成
  - 断言系统（contains/regex/json/llm-rubric）
- **可借鉴**：断言系统设计、CI/CD集成模式、多模型对比框架

### 1.2 langfuse (30.9k stars)
- **定位**：LLM可观测性+评估+提示词管理
- **核心功能**：
  - Trace追踪（输入/输出/延迟/Token）
  - 提示词版本管理
  - Playground在线调试
  - 评分系统（人工+LLM-as-Judge）
  - OpenTelemetry集成
- **可借鉴**：Trace设计、版本管理、评分体系

### 1.3 prompt-optimizer (32k stars)
- **定位**：AI提示词优化器
- **核心功能**：
  - 提示词自动优化
  - 多种优化策略
  - A/B测试
  - 效果对比
- **可借鉴**：优化策略分类、A/B测试框架

### 1.4 MLflow (27k stars)
- **定位**：AI工程平台
- **核心功能**：
  - 模型注册与管理
  - 实验追踪
  - 提示词工程支持
  - 评估与监控
  - 代理工作流
- **可借鉴**：实验追踪设计、评估框架

### 1.5 dair-ai/Prompt-Engineering-Guide (76.4k stars)
- **定位**：提示词工程指南
- **核心功能**：
  - 技术/论文/课程资源
  - RAG指南
  - Agent模式
  - Context Engineering
- **可借鉴**：知识体系结构、最佳实践分类

## 二、提示词调试器设计借鉴

### 2.1 逐步执行模式（参考langfuse Trace）
```typescript
interface PromptDebugger {
  stepThrough(prompt: string, context: Context): StepResult[]
  setBreakpoint(step: string): void
  inspectVariable(name: string): any
  evaluateExpression(expr: string): any
}

interface StepResult {
  stepIndex: number
  stepType: 'role' | 'instruction' | 'example' | 'constraint' | 'output_format'
  content: string
  intermediateOutput: string
  tokenCount: number
  latency: number
}
```

### 2.2 断点调试（参考promptfoo断言）
- 行级断点：在提示词特定行暂停
- 条件断点：满足条件时暂停（如输出包含特定文本）
- 变量检查：查看{{variable}}解析后的值
- 修改继续：运行时修改变量值继续执行

### 2.3 中间结果检查
- 每一步的Token消耗
- 每一步的延迟
- 部分输出预览
- 约束条件验证状态

## 三、提示词Diff工具设计借鉴

### 3.1 版本对比（参考langfuse版本管理）
```typescript
interface PromptDiff {
  compare(versionA: string, versionB: string): DiffResult
  detectSemanticChanges(): SemanticChange[]
  generateChangelog(): string
}

interface DiffResult {
  additions: Change[]
  deletions: Change[]
  modifications: Change[]
  semanticChanges: SemanticChange[]
  impactAssessment: ImpactReport
}
```

### 3.2 语义变更检测
- 角色定义变更检测
- 约束条件增删检测
- 输出格式变更检测
- 示例替换检测
- 语义漂移评分（0-1，越高影响越大）

### 3.3 影响评估
- 受影响场景列表
- 预期输出变化
- 兼容性检查
- 回归风险评分

## 四、智能推荐引擎设计借鉴

### 4.1 基于项目上下文推荐
```typescript
interface RecommendationEngine {
  analyzeContext(project: ProjectContext): ScenarioRecommendation[]
  rankByRelevance(recommendations: ScenarioRecommendation[]): ScenarioRecommendation[]
}

interface ProjectContext {
  language: string
  framework: string
  task: string
  constraints: string[]
  existingScenarios: string[]
}
```

### 4.2 3问题交互式向导
1. "你的项目使用什么技术栈？" → 缩小场景范围
2. "你要解决什么问题？" → 匹配场景类型
3. "有什么特殊约束？" → 精准推荐

## 五、批量执行框架设计借鉴

### 5.1 并行执行
```typescript
interface BatchExecutor {
  execute(scenarios: Scenario[], options: BatchOptions): BatchResult
}

interface BatchOptions {
  parallelism: number
  timeout: number
  retryPolicy: RetryPolicy
  aggregationStrategy: 'concat' | 'merge' | 'compare'
}
```

### 5.2 结果聚合
- 结果对比表
- 一致性评分
- 异常检测
- 统计摘要

## 六、调研结论
1. promptfoo的断言系统和CI/CD集成是提示词调试器的核心参考
2. langfuse的Trace和版本管理是Diff工具的最佳参考
3. 智能推荐引擎应结合项目上下文分析+3问题向导
4. 批量执行框架应支持并行+结果聚合+异常检测
5. 所有工具应提供CLI和API双模式访问
