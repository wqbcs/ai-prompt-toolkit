# SDK API文档与使用示例

> 版本：v1.0.0-beta | 日期：2026-05-29

---

## 1. 快速开始

### Python

```python
from prompt_engine import PromptEngine, PromptEngineBuilder

engine = (PromptEngineBuilder()
    .with_scenarios("./scenarios")
    .with_default_evaluators()
    .build())

result = engine.invoke("code_review", {"language": "Python", "code": "..."})
print(result.output)
print(result.evaluation_results)
```

### TypeScript

```typescript
import { PromptEngineBuilder } from './prompt-engine';

const engine = new PromptEngineBuilder()
  .withScenarios('./scenarios')
  .withDefaultEvaluators()
  .build();

const result = await engine.invoke('code_review', { language: 'TypeScript', code: '...' });
console.log(result.output);
console.log(result.evaluationResults);
```

## 2. 核心API

### 2.1 PromptEngine

| 方法 | Python | TypeScript | 描述 |
|------|--------|------------|------|
| invoke | `invoke(id, bindings, llm?)` | `invoke(id, bindings, llm?)` | 同步执行场景 |
| ainvoke | `ainvoke(id, bindings, llm?)` | - | 异步执行(Python) |
| batch | `batch(requests, llm?)` | `batch(requests, llm?)` | 批量执行 |
| abatch | `abatch(requests, llm?)` | - | 异步批量(Python) |
| add_evaluator | `add_evaluator(evaluator)` | `addEvaluator(evaluator)` | 添加评估器 |
| add_constraint | `add_constraint(constraint)` | `addConstraint(constraint)` | 添加约束 |
| set_adapter | `set_adapter(adapter)` | `setAdapter(adapter)` | 设置模型适配器 |
| add_pre_hook | `add_pre_hook(hook)` | `addPreHook(hook)` | 添加前置钩子 |
| add_post_hook | `add_post_hook(hook)` | `addPostHook(hook)` | 添加后置钩子 |

### 2.2 ScenarioLoader

| 方法 | 描述 |
|------|------|
| `load(id)` | 加载场景定义(带缓存) |
| `load_all()` | 加载所有场景 |
| `clear_cache()` | 清除缓存 |
| `resolve_template(scenario, bindings)` | 变量绑定+模板解析 |

### 2.3 Evaluator

| 评估器 | 描述 | 指标 |
|--------|------|------|
| StructureEvaluator | 结构完整性评估 | 非空/长度/格式/多行 |
| SafetyEvaluator | 安全性评估 | 危险模式检测 |

### 2.4 Combinator

| 方法 | 描述 |
|------|------|
| `generate_variants(template, variables)` | 变体生成(笛卡尔积) |
| `combine_prompts(prompts, strategy)` | 提示词组合 |
| `detect_conflicts(constraints_list)` | 约束冲突检测 |

## 3. PromptEngineBuilder(Builder模式)

```python
engine = (PromptEngineBuilder()
    .with_scenarios("./scenarios")
    .with_default_evaluators()
    .with_constraint(Constraint(
        rule="no_code_execution",
        level=ConstraintLevel.ERROR,
        message="禁止代码执行",
        checker=lambda x: "exec(" not in str(x)
    ))
    .with_adapter(lambda prompt, scenario: f"[{scenario.category}] {prompt}")
    .with_tracing(lambda result: print(f"Trace: {result.trace_id}"))
    .build())
```

## 4. 场景定义格式

```json
{
  "id": "code_review",
  "name": "代码审查",
  "version": "1.0.0",
  "description": "全维度代码审查提示词",
  "category": "quality",
  "template": "## 代码审查\n\n语言：{{language}}\n代码：{{code}}\n\n请执行以下检查...",
  "variables": [
    {
      "name": "language",
      "type": "string",
      "required": true,
      "description": "编程语言"
    },
    {
      "name": "code",
      "type": "string",
      "required": true,
      "description": "待审查代码"
    }
  ],
  "output_format": "markdown",
  "output_schema": null,
  "constraints": [],
  "examples": [],
  "metadata": {
    "author": "PEA",
    "tags": ["review", "quality"]
  }
}
```

## 5. 运行时集成

SDK与运行时引擎的集成模式：

```python
from prompt_engine import PromptEngineBuilder
from runtime import PromptRuntime, SandboxConfig

runtime = PromptRuntime(
    engine=engine,
    sandbox=SandboxConfig(
        timeout_ms=30000,
        max_memory_mb=512,
        network_whitelist=["api.openai.com"],
    )
)

result = runtime.execute("code_review", {"language": "Python", "code": "..."})
```
