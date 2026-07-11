# O1-5：SDK扩展接口 - 自定义评估器与组合器

> **迭代编号**：O1-5 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## 自定义评估器接口 (Custom Evaluator)

```typescript
interface IEvaluator {
  id: string
  name: string
  description: string
  evaluate(output: any, expected?: any): IEvaluationResult
}

interface IEvaluationResult {
  score: number
  maxScore: number
  details: string
  suggestions?: string[]
}

abstract class BaseEvaluator implements IEvaluator {
  abstract evaluate(output: any, expected?: any): IEvaluationResult
  
  compare(actual: any, expected: any): number {
    // 默认相似度计算
  }
}
```

### 内置评估器：
| 评估器 | 用途 | 评分范围 |
|--------|------|---------|
| AccuracyEvaluator | 准确性评估 | 0-20 |
| CompletenessEvaluator | 完整性评估 | 0-20 |
| ConsistencyEvaluator | 一致性评估 | 0-20 |
| FormatEvaluator | 格式规范评估 | 0-20 |
| SafetyEvaluator | 安全性评估 | 0-20 |

## 自定义组合器接口 (Custom Composer)

```typescript
interface IComposer {
  id: string
  name: string
  compose(scenarios: IScenario[], config?: IComposeConfig): IComposedWorkflow
}

interface IComposeConfig {
  mode: 'sequential' | 'parallel' | 'conditional'
  errorHandling: 'stop' | 'continue' | 'retry'
  outputChaining: boolean
  maxConcurrency: number
}

interface IComposedWorkflow {
  id: string
  steps: IWorkflowStep[]
  validate(): boolean
  execute(inputs: Record<string, any>): Promise<IWorkflowResult>
}

abstract class BaseComposer implements IComposer {
  abstract compose(scenarios: IScenario[], config?: IComposeConfig): IComposedWorkflow
  
  protected mergeOutputs(outputs: any[]): any
  protected handleError(error: Error, step: IWorkflowStep): void
}
```

### 组合模式：
1. **顺序组合**：A → B → C，前一步输出作为后一步输入
2. **并行组合**：A | B | C，同时执行，结果合并
3. **条件组合**：if(A.score > threshold) → B else → C
4. **循环组合**：while(B.score < target) → B.improve()
