# O1-4：SDK扩展接口 - 自定义场景

> **迭代编号**：O1-4 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## SDK扩展接口规范

### 1. 自定义场景接口 (Custom Scenario)

```typescript
interface ICustomScenario {
  id: string
  name: string
  category: ScenarioCategory
  description: string
  template: string
  inputSchema: JSONSchema
  outputSchema: JSONSchema
  evaluators: IEvaluator[]
  metadata: IScenarioMetadata
}

abstract class BaseScenario implements ICustomScenario {
  abstract validate(inputs: Record<string, any>): ValidationResult
  abstract transform(inputs: Record<string, any>): string
  abstract parseOutput(raw: string): Record<string, any>
  
  register(): void
  unregister(): void
  update(template: string): void
}
```

### 2. 自定义场景生命周期

```
register() → validate() → transform() → [execute] → parseOutput() → [evaluate] → report()
```

### 3. 场景注册协议

```yaml
# custom_scenario.yaml
apiVersion: v1
kind: CustomScenario
metadata:
  name: my-custom-review
  version: 1.0.0
  author: developer
spec:
  category: coding
  inputSchema:
    type: object
    properties:
      code: { type: string }
      language: { type: string, enum: [dart, go, rust, arkts] }
    required: [code]
  outputSchema:
    type: object
    properties:
      issues: { type: array }
      score: { type: number }
  template: |
    你是一个{{language}}代码审查专家...
  evaluators:
    - accuracy
    - completeness
```

### 4. SDK使用示例

```typescript
import { PromptSDK, BaseScenario } from '@prompt-system/sdk'

class FlutterReviewScenario extends BaseScenario {
  id = 'flutter-review-custom'
  name = 'Flutter代码审查(自定义)'
  
  validate(inputs) {
    return inputs.code?.length > 0 
      ? { valid: true } 
      : { valid: false, errors: ['代码不能为空'] }
  }
  
  transform(inputs) {
    return this.template
      .replace('{{language}}', 'Dart/Flutter')
      .replace('{{code}}', inputs.code)
  }
  
  parseOutput(raw) {
    return JSON.parse(raw)
  }
}

const sdk = new PromptSDK({ baseUrl: 'http://localhost:3000' })
sdk.registerScenario(new FlutterReviewScenario())
```
