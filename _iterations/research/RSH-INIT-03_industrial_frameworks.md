# RSH-INIT-03: 工业级Prompt框架与评估工具调研

> 调研日期: 2026-05-28
> 调研范围: DSPy, Promptfoo, LangSmith, Anthropic Prompt Caching, OpenAI Structured Outputs, Microsoft Guidance, PromptPerfect
> 调研重点: 版本管理、评估方法论、结构化输出、缓存优化、声明式vs命令式范式、组合编排

---

## 1. 框架概览与核心理念

### 1.1 框架矩阵总览

| 框架 | 核心定位 | 编程范式 | 星标数 | 核心能力 |
|------|---------|---------|--------|---------|
| **DSPy** (Stanford) | 编程而非提示LM | 声明式+自动优化 | 34.7k | Prompt自动编译、权重优化、管道组合 |
| **Promptfoo** (→OpenAI) | AI安全测试与评估 | 声明式YAML配置 | 20.6k | 红队测试、回归评估、CI/CD集成 |
| **LangSmith** (LangChain) | 可观测性+评估+部署 | 框架无关平台 | — | 追踪、Prompt版本管理、A/B测试、部署 |
| **Guidance** (Microsoft) | LM输出控制语言 | 命令式+约束生成 | 21.5k | CFG约束、JSON Schema、Token快进 |
| **Anthropic** | Prompt缓存 | API级优化 | — | 缓存前缀、成本降低90%、延迟降低 |
| **OpenAI** | 结构化输出 | API级约束 | — | JSON Schema严格模式、函数调用 |
| **PromptPerfect** (Jina) | Prompt自动优化 | 优化器即服务 | — | Prompt改写、A/B对比、多模型适配 |

### 1.2 核心理念分层

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (Application)                   │
│  LangSmith: 可观测性 → 评估 → 部署 (全生命周期)          │
├─────────────────────────────────────────────────────────┤
│                    编排层 (Orchestration)                 │
│  DSPy: 声明式管道 → 自动编译 → 自我改进                  │
├─────────────────────────────────────────────────────────┤
│                    约束层 (Constraint)                    │
│  Guidance: CFG/Regex/JSON约束 → Token快进 → 确定性输出   │
│  OpenAI: JSON Schema严格模式 → 结构化输出                 │
├─────────────────────────────────────────────────────────┤
│                    评估层 (Evaluation)                    │
│  Promptfoo: 红队测试 → 回归评估 → 安全扫描              │
│  LangSmith: LLM-as-Judge → 数据集评估 → 在线实验        │
├─────────────────────────────────────────────────────────┤
│                    优化层 (Optimization)                  │
│  DSPy: BootstrapFewShot/MIPRO/OBO → Prompt自动优化       │
│  PromptPerfect: Prompt改写优化 → 多模型适配              │
│  Anthropic: Prompt缓存 → 成本/延迟优化                   │
└─────────────────────────────────────────────────────────┘
```

### 1.3 关键设计理念对比

#### DSPy: "Programming — not prompting"
- **核心理念**: 将Prompt视为可编译的程序而非脆弱的字符串
- **关键创新**: 声明式自改进Python (Declarative Self-improving Python)
- **编译隐喻**: `Module → Teleprompter → Compiled Module`，类似编译器优化源码
- **论文支撑**: GEPA (Jul'25) 证明反射式Prompt进化可超越RL

#### Guidance: "Efficient programming paradigm for steering LMs"
- **核心理念**: 通过约束生成 (Constrained Generation) 精确控制LM输出
- **关键创新**: 上下文无关文法 (CFG) 约束 + Token快进 (Fast-forwarding)
- **效率优势**: 已知token可跳过前向传播，减少GPU计算
- **Pythonic接口**: `with system()/user()/assistant()` 上下文管理器

#### Promptfoo: "Ship agents, not vulnerabilities"
- **核心理念**: AI安全内建于开发流程，而非事后补救
- **关键创新**: 自动红队测试生成、50+漏洞类型覆盖、CI/CD原生集成
- **规模**: 156家Fortune 500企业使用，300k+开发者社区

#### LangSmith: "Framework-agnostic observability + evaluation + deployment"
- **核心理念**: 单一平台覆盖AI应用全生命周期
- **关键创新**: 追踪 → 评估 → 部署的工作流闭环
- **合规**: SOC 2 Type 2, HIPAA, GDPR

---

## 2. Prompt版本管理最佳实践

### 2.1 各框架版本管理机制

#### LangSmith: 企业级Prompt版本管理
- **Playground式迭代**: 内置Prompt编辑器 + 版本自动记录
- **自动版本化**: 每次修改自动创建新版本，保留完整历史
- **对比视图**: 并排对比不同版本的输出差异
- **A/B测试**: 自动流量分割 + 统计显著性检验
- **部署管理**: 从开发到生产的版本发布流程
- **协作**: 团队共享 + 评论 + 审批流程

#### DSPy: 编译驱动的版本管理
- **编译产物**: 优化后的Prompt作为编译产物自动保存
- **Teleprompter**: 优化器记录从源Module到优化Module的转换路径
- **配置快照**: `save/load` 方法保存完整优化状态
- **版本语义**: 类似编译器的 `-O1/-O2/-O3` 优化级别

```python
# DSPy版本管理示例
optimizer = dspy.MIPROv2(metric=my_metric, num_threads=4)
optimized_program = optimizer.compile(student_program, trainset=trainset)

# 保存优化后的版本
optimized_program.save("prompts/v2_optimized.json")

# 加载特定版本
loaded = dspy.load("prompts/v2_optimized.json")
```

#### Promptfoo: 配置即版本
- **YAML配置**: `promptfooconfig.yaml` 本身即为版本记录
- **Git集成**: 配置文件纳入Git版本控制
- **CI/CD**: 每次提交自动运行评估，阻止性能退化
- **基准对比**: 与baseline版本自动对比

```yaml
# Promptfoo配置示例 - 版本化Prompt评估
prompts:
  - file://prompts/v1_summary.txt
  - file://prompts/v2_summary.txt
providers:
  - openai:gpt-4
  - anthropic:claude-3-sonnet
tests:
  - vars:
      input: "测试输入"
    assert:
      - type: contains
        value: "期望输出"
```

### 2.2 版本管理最佳实践总结

| 实践 | 描述 | 适用场景 | 实现方式 |
|------|------|---------|---------|
| **语义化版本** | `major.minor.patch` 标记Prompt变更 | 生产环境 | Git tag + 元数据 |
| **不可变版本** | 每次修改创建新版本，永不覆盖 | 审计要求 | LangSmith自动版本 |
| **基准对比** | 新版本与基准版本自动对比 | 质量守卫 | Promptfoo CI/CD |
| **渐进发布** | 金丝雀发布 → 扩大流量 → 全量 | 风险控制 | LangSmith A/B测试 |
| **回滚机制** | 一键回滚到已知良好版本 | 线上故障 | LangSmith部署管理 |
| **变更日志** | 记录每次变更的意图和效果 | 团队协作 | Git commit + 评估报告 |

### 2.3 版本管理工作流

```
开发阶段                    评估阶段                   生产阶段
┌──────────┐            ┌──────────┐            ┌──────────┐
│ 编辑Prompt │──→ 提交 ──→│ 自动评估  │──→ 通过 ──→│ 金丝雀发布│
│ v_new     │            │ vs 基准   │            │ 5% 流量  │
└──────────┘            └──────────┘            └──────────┘
     │                       │ 退化?                    │
     │                       ↓                         ↓
     │                  ┌──────────┐            ┌──────────┐
     │                  │ 阻止合并  │            │ 扩大流量  │
     │                  │ 通知开发者│            │ 100%     │
     │                  └──────────┘            └──────────┘
     │                                               │ 退化?
     │                                               ↓
     │                                          ┌──────────┐
     │                                          │ 自动回滚  │
     │                                          │ → v_prev  │
     │                                          └──────────┘
```

---

## 3. Prompt评估方法论详解

### 3.1 评估方法论分层体系

```
┌──────────────────────────────────────────────────────────────┐
│ Level 4: 在线评估 (Online Evaluation)                        │
│   - A/B测试 (真实流量分割)                                    │
│   - 交错实验 (Interleaving)                                  │
│   - 用户反馈信号 (点赞/踩/修正)                               │
├──────────────────────────────────────────────────────────────┤
│ Level 3: 人类评估 (Human Evaluation)                         │
│   - 人类偏好排序                                              │
│   - 专家标注 (领域专家)                                       │
│   - 众包评估 (标注平台)                                       │
├──────────────────────────────────────────────────────────────┤
│ Level 2: LLM-as-Judge (模型辅助评估)                         │
│   - GPT-4/Claude作为评审                                     │
│   - 成对比较 (Pairwise Comparison)                           │
│   - 评分量表 (Rubric-based Scoring)                          │
├──────────────────────────────────────────────────────────────┤
│ Level 1: 自动化指标 (Automated Metrics)                      │
│   - 精确匹配 / 包含检查 / 正则匹配                            │
│   - BLEU / ROUGE / BERTScore                                │
│   - JSON Schema验证 / 类型检查                                │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Promptfoo评估体系

#### 核心评估模式
- **声明式评估配置**: YAML定义测试用例、断言、提供者
- **多模型对比**: 同时评估同一Prompt在不同模型上的表现
- **断言类型丰富**: `contains`, `regex`, `json`, `javascript`, `python`, `llm-rubric`, `similar`, `webhook`
- **红队测试**: 50+漏洞类型自动生成攻击用例

```yaml
# Promptfoo评估配置
prompts: [prompts/summary_v1.txt, prompts/summary_v2.txt]
providers: [openai:gpt-4, anthropic:claude-3-sonnet]
tests:
  - description: "摘要质量评估"
    vars: { article: "{{article}}" }
    assert:
      - type: llm-rubric
        value: "摘要应包含文章的关键信息，简洁准确"
        threshold: 0.8
      - type: latency
        threshold: 2000  # <2秒
      - type: cost
        threshold: 0.01  # <$0.01
```

#### 红队测试能力
- **直接/间接Prompt注入**: 测试系统提示的安全性
- **越狱攻击**: 生成针对特定防护的定制化攻击
- **数据/PII泄露**: 检测敏感信息泄露风险
- **不安全工具使用**: 验证Agent的工具调用安全性
- **商业规则违反**: 检查业务逻辑约束是否被绕过

### 3.3 LangSmith评估体系

#### 核心评估能力
- **离线评估**: 对数据集批量运行 + 多维度打分
- **在线评估**: A/B测试 + 统计显著性分析
- **LLM-as-Judge**: 可配置评审模型 + 评分标准
- **自定义评估器**: Python函数定义任意评估逻辑
- **追踪关联**: 评估结果与追踪数据关联，支持根因分析

#### 评估工作流
```
创建数据集 → 定义评估器 → 运行实验 → 分析结果 → 选择最优版本
     ↑                                              │
     └────────── 迭代优化 ←────────────────────────┘
```

### 3.4 DSPy评估体系

#### 优化驱动的评估
- **指标函数**: `metric(example, prediction) → float` 定义质量
- **自动优化**: Teleprompter根据指标自动调整Prompt
- **交叉验证**: 训练集/验证集分割，避免过拟合

```python
# DSPy评估示例
def metric(example, pred, trace=None):
    answer_match = example.answer.lower() == pred.answer.lower()
    reasoning_match = len(pred.reasoning) > 20
    return answer_match and reasoning_match

# 自动优化Prompt
optimizer = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=4)
optimized = optimizer.compile(RAG(), trainset=trainset)
```

### 3.5 LLM-as-Judge方法论

| 评估模式 | 描述 | 优势 | 劣势 | 适用场景 |
|---------|------|------|------|---------|
| **单点评分** | LLM对单个输出打分 (1-5) | 简单快速 | 绝对分数不稳定 | 快速筛选 |
| **成对比较** | LLM比较两个输出优劣 | 相对判断更可靠 | O(n²)复杂度 | 版本对比 |
| **参考对比** | 与参考答案对比 | 有基准 | 依赖参考质量 | 回归测试 |
| **多维度评分** | 按多个维度分别评分 | 细粒度反馈 | 成本高 | 质量审计 |
| **链式推理** | 先推理再评分 | 可解释性强 | 延迟高 | 关键决策 |

### 3.6 评估最佳实践

1. **金字塔评估**: 自动化指标(大量) → LLM-as-Judge(中量) → 人类评估(少量)
2. **回归守卫**: 每次变更自动运行基准对比，阻止性能退化
3. **多模型评估**: 不同模型作为评审，减少单一模型偏差
4. **标注一致性**: 多评审者 + Cohen's Kappa系数验证
5. **成本感知评估**: 在质量与成本/延迟间做权衡分析

---

## 4. 结构化输出技术对比

### 4.1 技术方案矩阵

| 技术 | 提供者 | 约束类型 | 保证级别 | 延迟影响 | 适用模型 |
|------|--------|---------|---------|---------|---------|
| **JSON Schema严格模式** | OpenAI | JSON Schema | 100%保证 | ~10ms | GPT-4o+ |
| **Guidance CFG约束** | Microsoft | CFG/Regex | 100%保证 | 减少(快进) | 本地模型 |
| **JSON Mode** | OpenAI/Anthropic | 有效JSON | JSON有效 | ~0ms | 所有 |
| **函数调用** | OpenAI/Anthropic | JSON Schema | 100%保证 | ~10ms | 所有 |
| **Constrained Decoding** | Guidance | 正则/CFG | 100%保证 | 减少(跳过) | 本地模型 |
| **Prompt Engineering** | 通用 | 自然语言 | 无保证 | 0ms | 所有 |

### 4.2 OpenAI Structured Outputs (深度解析)

- **严格模式**: `response_format = { type: "json_schema", json_schema: {...} }`
- **保证**: 输出100%匹配提供的JSON Schema (不额外支持draft 2020-12的所有特性)
- **限制**: 不支持 `$ref` 到外部schema、递归schema、`additionalProperties`
- **实现原理**: 在解码时约束token采样概率，只允许符合schema的token

```python
# OpenAI结构化输出示例
from openai import OpenAI
from pydantic import BaseModel

class Step(BaseModel):
    explanation: str
    output: str

class MathReasoning(BaseModel):
    steps: list[Step]
    final_answer: str

client = OpenAI()
response = client.responses.parse(
    model="gpt-4o-2024-08-06",
    input="What is 2+2?",
    text_format=MathReasoning,
)
math_reasoning = response.output_parsed  # 类型安全的Pydantic对象
```

### 4.3 Microsoft Guidance约束生成 (深度解析)

- **约束类型层次**: 正则表达式 → 上下文无关文法 (CFG) → JSON Schema
- **Token快进 (Fast-forwarding)**: 约束已确定token时跳过模型推理
- **select()函数**: 从预定义列表中选择，确保输出在枚举范围内
- **gen(regex=...)**: 正则约束生成
- **JSON Schema约束**: Pydantic模型直接转换为CFG

```python
# Guidance约束生成示例
from guidance import system, user, assistant, gen, select, json as gen_json
from pydantic import BaseModel, Field

class BloodPressure(BaseModel):
    systolic: int = Field(gt=300, le=400)
    diastolic: int = Field(gt=0, le=20)
    location: str = Field(max_length=50)
    model_config = dict(extra="forbid")

with assistant():
    lm += gen_json(name="bp", schema=BloodPressure)
    # 输出保证: 100%符合BloodPressure的JSON Schema
```

**Guidance独特优势**:
- **离线调试**: `Mock`模型验证语法约束，无需API调用
- **组合构建**: Guidance函数可嵌套组合，构建复杂文法
- **HTML生成示例**: 可约束生成符合HTML文法的完整网页

### 4.4 Anthropic JSON Mode
- **tool_use**: 通过工具调用强制JSON输出
- **cache_control**: 结合Prompt缓存减少结构化输出的重复前缀计算

### 4.5 技术选型决策树

```
需要结构化输出？
├── 是 → 使用本地模型？
│   ├── 是 → Guidance (CFG约束 + Token快进)
│   │        └── 需要JSON? → gen_json(schema=PydanticModel)
│   └── 否 → 使用OpenAI？
│        ├── 是 → GPT-4o+? → JSON Schema严格模式
│        │              └── 更早版本 → 函数调用
│        └── 否 → 使用Anthropic？
│                 └── tool_use + JSON Mode
└── 否 → 纯Prompt引导 + 输出验证 + 重试
```

---

## 5. Prompt组合编排范式

### 5.1 声明式 vs 命令式编程范式

#### 声明式 (Declarative) — DSPy代表

**核心思想**: 描述"做什么"而非"怎么做"，让框架自动优化

```python
# DSPy声明式示例
class RAG(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")
    
    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

# 编译器自动优化Prompt和few-shot示例
optimizer = dspy.MIPROv2(metric=accuracy)
optimized_rag = optimizer.compile(RAG(), trainset=data)
# 优化后的Prompt可能完全不同于手写的！
```

**优势**:
- Prompt自动优化，无需手动调参
- 模块可组合、可替换
- 编译器可以全局优化（跨模块联合优化）

**劣势**:
- 学习曲线陡峭
- 调试困难（优化后的Prompt可能难以理解）
- 依赖训练数据和指标定义的质量

#### 命令式 (Imperative) — Guidance代表

**核心思想**: 精确控制每一步生成， interleaving控制流和生成

```python
# Guidance命令式示例
@guidance
def multi_step_qa(lm, question):
    with user():
        lm += question
    
    with assistant():
        lm += "Let me think step by step.\n"
        lm += gen(name="reasoning", max_tokens=100)
        lm += "\nBased on this, the answer is: "
        lm += select(["Yes", "No"], name="answer")
    
    return lm
```

**优势**:
- 精确控制，可预测行为
- 约束生成保证输出格式
- Token快进减少延迟

**劣势**:
- 需要手动设计每个步骤
- 优化依赖人类经验
- 与特定模型/后端耦合

### 5.2 范式对比矩阵

| 维度 | 声明式 (DSPy) | 命令式 (Guidance) | 混合式 |
|------|-------------|----------------|--------|
| **Prompt质量** | 自动优化，可能超越人类 | 依赖人类经验 | 人机协同 |
| **开发效率** | 高（自动调优） | 中（手动调优） | 中高 |
| **可控性** | 低（编译器决策） | 高（完全控制） | 中 |
| **可调试性** | 低（黑盒优化） | 高（逐步可观察） | 中 |
| **输出保证** | 无（概率性） | 强（CFG约束） | 中 |
| **学习曲线** | 陡峭 | 中等 | 中 |
| **适用场景** | 探索性优化、RAG管道 | 精确格式、安全关键 | 通用 |

### 5.3 Prompt组合模式

#### 模式1: 管道组合 (Pipeline Composition)
```
Input → [Retriever] → [Reranker] → [Generator] → Output
```
DSPy `Module >> Module` 语法，Guidance函数嵌套调用

#### 模式2: 条件路由 (Conditional Routing)
```python
# DSPy条件路由
class Router(dspy.Module):
    def forward(self, query):
        if self.classifier(query).type == "factual":
            return self.rag(query)
        else:
            return self.direct(query)
```

#### 模式3: 迭代精炼 (Iterative Refinement)
```python
# DSPy Assertions — 计算约束 + 自精炼
dspy.Assert(
    len(prediction.answer) > 10,
    "Answer too short, please elaborate"
)
# 违反约束时自动重试
```

#### 模式4: 分支并行 (Branch & Merge)
- 多个Prompt变体并行执行 → 评审选择最优
- LangSmith支持这种实验模式

#### 模式5: 递归分解 (Recursive Decomposition)
- 复杂任务递归分解为子任务
- Agent模式: ReAct, Plan-and-Execute

### 5.4 工作流编排架构

```
┌─────────────────────────────────────────────────────────┐
│                   编排控制器 (Orchestrator)               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ 路由决策 │  │ 状态管理 │  │ 错误恢复 │                 │
│  └─────────┘  └─────────┘  └─────────┘                 │
├─────────────────────────────────────────────────────────┤
│                   Prompt层 (Prompts)                     │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │ P_v1 │  │ P_v2 │  │ P_v3 │  │ P_v4 │  (版本化)     │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
├─────────────────────────────────────────────────────────┤
│                   约束层 (Constraints)                   │
│  ┌──────┐  ┌──────┐  ┌──────┐                         │
│  │Schema│  │Regex │  │ CFG  │  (输出保证)              │
│  └──────┘  └──────┘  └──────┘                         │
├─────────────────────────────────────────────────────────┤
│                   模型层 (Models)                        │
│  ┌──────┐  ┌──────┐  ┌──────┐                         │
│  │ GPT  │  │Claude│  │本地  │  (多模型适配)            │
│  └──────┘  └──────┘  └──────┘                         │
├─────────────────────────────────────────────────────────┤
│                   缓存层 (Cache)                        │
│  ┌──────┐  ┌──────┐  ┌──────┐                         │
│  │Prefix│  │Result│  │Embed │  (成本/延迟优化)         │
│  └──────┘  └──────┘  └──────┘                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Prompt缓存与优化策略

### 6.1 Anthropic Prompt Caching

- **核心机制**: 标记Prompt前缀为可缓存，相同前缀复用KV计算
- **缓存标记**: 在消息中使用 `cache_control: {"type": "ephemeral"}`
- **成本节省**: 缓存命中时输入token费用降低90%
- **延迟降低**: 缓存命中时首token延迟降低
- **适用场景**: 
  - 大型系统提示 (工具定义、长上下文)
  - 多轮对话的共享前缀
  - RAG中的检索文档前缀
- **缓存生命周期**: 5分钟无访问后过期 (rolling)

```python
# Anthropic Prompt缓存示例
response = client.messages.create(
    model="claude-3-sonnet",
    messages=[
        {
            "role": "user", 
            "content": [
                {
                    "type": "text",
                    "text": large_system_prompt,  # 可缓存的大前缀
                    "cache_control": {"type": "ephemeral"}
                },
                {"type": "text", "text": user_query}
            ]
        }
    ]
)
```

### 6.2 缓存策略分类

| 缓存类型 | 层级 | TTL | 一致性 | 适用场景 |
|---------|------|-----|--------|---------|
| **Prompt前缀缓存** | API层 | 5min滚动 | 强一致 | 系统提示复用 |
| **结果缓存** | 应用层 | 可配置 | 最终一致 | 相同查询去重 |
| **嵌入缓存** | 向量层 | 长期 | 近似 | 语义相似复用 |
| **语义缓存** | 应用层 | 可配置 | 近似 | 语义等价查询 |

### 6.3 优化策略组合

1. **Prompt前缀缓存** (Anthropic/OpenAI): 大型系统提示 + 工具定义
2. **Token快进** (Guidance): 结构化输出中确定性token跳过推理
3. **自动Prompt优化** (DSPy): 编译器自动寻找最优Prompt
4. **Prompt蒸馏** (PromptPerfect): 将复杂Prompt简化为等价但更短的版本
5. **批量推理**: 多请求合并为单次推理 (vLLM连续批处理)

---

## 7. 对本体系的具体优化建议

### 7.1 版本管理优化

| 当前痛点 | 建议方案 | 优先级 | 参考来源 |
|---------|---------|--------|---------|
| Prompt变更无追踪 | 引入语义化版本 + 变更日志 | P0 | LangSmith |
| 无法对比版本效果 | 实现基准对比评估流程 | P0 | Promptfoo |
| 生产回滚困难 | 建立不可变版本 + 一键回滚 | P1 | LangSmith |
| 团队协作冲突 | Prompt注册中心 + 审批流程 | P2 | LangSmith |

**建议实现**:
```
prompts/
├── registry.json          # Prompt注册表
├── v1.0.0/               # 语义化版本目录
│   ├── system.md         # 系统提示
│   ├── few_shots.json    # Few-shot示例
│   ├── meta.json         # 元数据(指标、标签、作者)
│   └── eval_results.json # 评估结果
├── v1.1.0/
│   └── ...
└── current → v1.1.0/     # 当前版本软链接
```

### 7.2 评估体系优化

| 当前痛点 | 建议方案 | 优先级 | 参考来源 |
|---------|---------|--------|---------|
| 仅靠人工判断质量 | 引入LLM-as-Judge自动评估 | P0 | LangSmith + Promptfoo |
| 无回归守卫 | CI/CD中集成Promptfoo评估 | P0 | Promptfoo |
| 评估维度单一 | 多维度评分 (质量/延迟/成本/安全) | P1 | Promptfoo |
| 无法检测安全风险 | 集成红队测试 | P1 | Promptfoo |
| 无A/B测试能力 | 实现在线实验框架 | P2 | LangSmith |

**建议评估配置**:
```yaml
# 建议的评估金字塔
level_1_automated:    # 100% 运行
  - exact_match
  - json_schema_validation
  - regex_check
  - latency_threshold
  - cost_threshold

level_2_llm_judge:    # 50% 运行 (采样)
  - rubric_scoring (GPT-4 as judge)
  - pairwise_comparison
  - safety_check

level_3_human:        # 10% 运行 (关键场景)
  - expert_review
  - user_feedback
```

### 7.3 结构化输出优化

| 当前痛点 | 建议方案 | 优先级 | 参考来源 |
|---------|---------|--------|---------|
| JSON输出不稳定 | 使用OpenAI严格模式 / Guidance约束 | P0 | OpenAI + Guidance |
| 重试成本高 | 约束生成(一次成功) > 重试策略 | P0 | Guidance |
| 格式描述占Token | Schema约束替代自然语言描述 | P1 | OpenAI |

### 7.4 组合编排优化

| 当前痛点 | 建议方案 | 优先级 | 参考来源 |
|---------|---------|--------|---------|
| Prompt硬编码 | 模块化 + 声明式组合 | P0 | DSPy |
| 手动调优低效 | 引入自动优化器 (Bootstrap/MIPRO) | P1 | DSPy |
| 输出约束缺失 | Guidance式约束 + Assertions | P1 | DSPy + Guidance |
| 管道错误无恢复 | 计算约束 + 自精炼 | P2 | DSPy Assertions |

### 7.5 缓存优化

| 当前痛点 | 建议方案 | 优先级 | 参考来源 |
|---------|---------|--------|---------|
| 重复请求成本高 | Prompt前缀缓存 (cache_control) | P0 | Anthropic |
| 长系统提示重复计算 | 系统提示分离 + 前缀缓存 | P0 | Anthropic |
| 相似查询重复处理 | 语义缓存 (嵌入相似度阈值) | P1 | — |

### 7.6 推荐技术栈

```
┌─────────────────────────────────────────────────────┐
│                推荐的Prompt工程栈                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  编排:   DSPy (声明式管道 + 自动优化)                │
│  约束:   Guidance (CFG约束 + Token快进)              │
│  评估:   Promptfoo (YAML声明 + 红队 + CI/CD)        │
│  可观测: LangSmith (追踪 + 版本管理 + 部署)          │
│  缓存:   Anthropic Prompt Caching                   │
│  输出:   OpenAI Structured Outputs / Guidance JSON   │
│                                                     │
│  工作流:                                             │
│  开发 → Guidance约束生成                              │
│  优化 → DSPy自动编译                                 │
│  评估 → Promptfoo回归测试                             │
│  部署 → LangSmith金丝雀发布                          │
│  监控 → LangSmith追踪 + 缓存                         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 7.7 实施路线图

```
Phase 1 (2周): 基础建设
├── Prompt版本管理规范 + Git集成
├── 结构化输出约束 (JSON Schema严格模式)
└── 基础自动化评估 (精确匹配 + 包含检查)

Phase 2 (2周): 评估增强
├── LLM-as-Judge评估集成
├── Promptfoo CI/CD管道
└── 红队测试基础覆盖

Phase 3 (2周): 优化与缓存
├── Prompt前缀缓存启用
├── DSPy自动优化实验
└── 语义缓存原型

Phase 4 (2周): 生产化
├── A/B测试框架
├── 金丝雀发布流程
├── 完整可观测性
└── 自动回滚机制
```

---

## 附录A: 框架详细对比

| 维度 | DSPy | Promptfoo | LangSmith | Guidance |
|------|------|-----------|-----------|----------|
| **类型** | 框架 | 工具 | 平台 | 框架 |
| **语言** | Python | Node.js/Python | 多语言 | Python |
| **开源** | MIT | MIT | 部分 | MIT |
| **模型支持** | 多模型 | 多模型 | 多模型 | 本地+API |
| **Prompt优化** | ✅ 自动 | ❌ | ❌ | ❌ |
| **评估** | ✅ 基础 | ✅ 强 | ✅ 强 | ❌ |
| **版本管理** | 编译产物 | Git | ✅ 原生 | ❌ |
| **结构化输出** | ❌ | ❌ | ❌ | ✅ 强 |
| **安全测试** | ❌ | ✅ 强 | ❌ | ❌ |
| **可观测性** | ❌ | ❌ | ✅ 强 | ❌ |
| **部署** | ❌ | ❌ | ✅ | ❌ |
| **缓存** | ❌ | ❌ | ❌ | Token快进 |

## 附录B: 参考资源

1. DSPy: https://github.com/stanfordnlp/dspy | https://dspy.ai
2. Promptfoo: https://www.promptfoo.dev/ | https://github.com/promptfoo/promptfoo
3. LangSmith: https://docs.smith.langchain.com/
4. Anthropic Prompt Caching: https://docs.anthropic.com/claude/docs/prompt-caching
5. OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
6. Microsoft Guidance: https://github.com/guidance-ai/guidance
7. PromptPerfect: https://promptperfect.jina.ai/

## 附录C: 核心论文

- DSPy: Khattab et al., "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines", ICLR 2024
- GEPA: "Reflective Prompt Evolution Can Outperform Reinforcement Learning", arXiv 2025
- DSPy Assertions: "Computational Constraints for Self-Refining Language Model Pipelines", arXiv 2023
- Guidance: Microsoft Research, constrained generation for LLMs
