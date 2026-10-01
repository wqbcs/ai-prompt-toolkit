# 提示词引擎SDK设计规范

> 版本：v14.0.0 | 日期：2026-05-29 | 语言：Python + TypeScript

---

## 1. SDK架构

### 1.1 分层架构
```
┌─────────────────────────────────────┐
│        Application Layer            │  用户代码
├─────────────────────────────────────┤
│        SDK API Layer                │  公开API
├──────────┬──────────┬──────────────┤
│  Execute  │  Evaluate│  Optimize    │  三大引擎
├──────────┴──────────┴──────────────┤
│        Runtime Layer                │  运行时
├──────────┬──────────┬──────────────┤
│  Parser  │  Validator│  Monitor    │  基硎设施
├──────────┴──────────┴──────────────┤
│        Adapter Layer                │  模型适配
├─────────────────────────────────────┤
│        Transport Layer              │  API调用
└─────────────────────────────────────┘
```

### 1.2 包结构
```
prompt-engine-sdk/
├── core/           # 核心引擎(执行/评估/优化/组合)
├── runtime/        # 运行时(加载/解析/验证/执行/监控)
├── uppl/           # UPPL编译器
├── adapters/       # 模型适配器(OpenAI/Anthropic/Gemini/...)
├── security/       # 安全模块(注入防御/数据保护/审计)
├── evaluate/       # 24维度评估引擎
├── cli/            # 命令行工具
└── types/          # 类型定义
```

---

## 2. Python SDK API

### 2.1 核心API
```python
from prompt_engine import PromptEngine, Prompt, EvaluationResult

# 初始化引擎
engine = PromptEngine(config={
    "model": "gpt-4",
    "security": {"sandbox": True, "injection_defense": True},
    "runtime": {"max_tokens": 4096, "timeout": 30}
})

# 执行提示词
result: ExecutionResult = engine.execute(
    prompt="prompt://code-review/v2",
    context={"code": "...", "language": "python"},
    options={"temperature": 0.1}
)

# 24维度评估
evaluation: EvaluationResult = engine.evaluate(
    prompt="prompt://code-review/v2",
    dimensions="all"  # 或 ["D1", "D5", "D14"]
)

# 优化提示词
optimized: Prompt = engine.optimize(
    prompt="prompt://code-review/v2",
    target_dimensions=["D1", "D3"],
    strategy="gradient_free"
)

# 组合提示词
composed: Prompt = engine.compose(
    prompts=["prompt://analyze", "prompt://review"],
    strategy="sequential"  # 或 "parallel", "conditional"
)
```

### 2.2 安全API
```python
from prompt_engine.security import SecurityScanner, InjectionDefense

# 安全扫描
scanner = SecurityScanner()
scan_result = scanner.scan(prompt_text, rules=["owasp-top-10", "custom-rules"])

# 注入防御
defense = InjectionDefense(layers=["input_validation", "instruction_isolation", 
                                    "output_filtering", "behavior_monitoring"])
safe_prompt = defense.protect(prompt_text)
```

### 2.3 UPPL API
```python
from prompt_engine.uppl import UPPLCompiler

# UPPL编译
compiler = UPPLCompiler()
natural_language = compiler.compile(uppl_source, target="natural_language")
json_spec = compiler.compile(uppl_source, target="json")
agent_instruction = compiler.compile(uppl_source, target="agent")
```

---

## 3. TypeScript SDK API

### 3.1 核心API
```typescript
import { PromptEngine, Prompt, EvaluationResult } from '@prompt-engine/sdk';

const engine = new PromptEngine({
    model: 'gpt-4',
    security: { sandbox: true, injectionDefense: true },
    runtime: { maxTokens: 4096, timeout: 30000 }
});

// 执行
const result = await engine.execute('prompt://code-review/v2', {
    context: { code: '...', language: 'typescript' }
});

// 评估
const evaluation = await engine.evaluate('prompt://code-review/v2', {
    dimensions: 'all'
});

// 优化
const optimized = await engine.optimize('prompt://code-review/v2', {
    targetDimensions: ['D1', 'D3']
});

// 组合
const composed = await engine.compose(
    ['prompt://analyze', 'prompt://review'],
    { strategy: 'sequential' }
);
```

---

## 4. 类型系统

### 4.1 核心类型
```typescript
interface Prompt {
    id: URN;                    // 唯一标识
    version: SemVer;            // 语义版本
    role: string;               // 角色
    task: string;               // 任务
    constraints: Constraint[];  // 约束
    output: OutputFormat;       // 输出格式
    examples: Example[];        // 示例
    securityLevel: L1|L2|L3|L4; // 安全等级
    metadata: PromptMetadata;   // 元数据
}

interface EvaluationResult {
    promptId: URN;
    timestamp: ISO8601;
    dimensions: Map<DimensionId, DimensionScore>;
    totalScore: number;         // 加权均分
    standardDeviation: number;  // 标准差
    passed: boolean;            // 是否通过门禁
    recommendations: string[];  // 改进建议
}

interface ExecutionResult {
    promptId: URN;
    output: any;
    metrics: ExecutionMetrics;
    audit: AuditLog;
    security: SecurityReport;
}
```

---

## 5. 配置与扩展

### 5.1 配置文件(prompt-engine.config.yaml)
```yaml
engine:
  default_model: gpt-4
  timeout: 30
  max_retries: 3

security:
  sandbox: true
  injection_defense:
    layers: [input_validation, instruction_isolation, output_filtering, behavior_monitoring]
  data_classification: auto
  audit: full

evaluation:
  dimensions: all
  threshold: 18.0
  sub_dimension_threshold: 4.0

runtime:
  max_tokens: 4096
  max_memory: 512MB
  max_cpu: 50%
```

### 5.2 插件机制
```python
from prompt_engine import PluginBase

class CustomEvaluator(PluginBase):
    name = "custom-dimension-evaluator"
    
    def evaluate(self, prompt, context):
        # 自定义评估逻辑
        return DimensionScore(value=19.5, details={...})

engine.register_plugin(CustomEvaluator())
```

---

## 6. 发布规范

### 6.1 Python包
- 包名：`prompt-engine-sdk`
- Python版本：≥3.10
- 发布：PyPI + GitHub Releases
- 文档：ReadTheDocs

### 6.2 TypeScript包
- 包名：`@prompt-engine/sdk`
- Node版本：≥18
- 发布：npm + GitHub Releases
- 文档：TypeDoc + Docusaurus
