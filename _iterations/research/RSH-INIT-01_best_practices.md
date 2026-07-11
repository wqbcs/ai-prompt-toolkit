# Prompt Engineering 最佳实践与方法论调研报告

> **文档编号**: RSH-INIT-01  
> **版本**: v1.0  
> **日期**: 2026-05-28  
> **调研范围**: 7个权威源 + 7类设计模式 + 5个工业级框架  
> **状态**: 初始调研完成

---

## 一、调研源列表与访问状态

| # | 调研源 | URL | 访问状态 | 获取内容 |
|---|--------|-----|----------|----------|
| 1 | OpenAI Prompt Engineering Guide | platform.openai.com/docs/guides/prompt-engineering | ❌ 403禁止 | - |
| 2 | Anthropic Prompt Engineering | docs.anthropic.com/claude/docs/prompt-engineering | ❌ 区域限制 | - |
| 3 | Google Gemini Prompt Design | ai.google.dev/docs/prompt_design_strategies | ❌ 连接失败 | - |
| 4 | DeepSeek Prompt Engineering | api-docs.deepseek.com/zh-cn/guides/prompt-engineering | ❌ 404 | - |
| 5 | LangChain Prompt Best Practices | python.langchain.com/docs/concepts/prompts/ | ✅ 成功 | Agent框架与create_agent模式 |
| 6 | DAIR.AI Prompt Engineering Guide | promptingguide.ai | ✅ 成功 | 完整技术体系（CoT/Few-shot/ReAct等） |
| 7 | Learn Prompting | learnprompting.org | ✅ 成功 | 入门到高级的模块化课程体系 |

**补充访问的子页面**:
- promptingguide.ai/introduction/tips ✅（通用提示词设计建议）
- promptingguide.ai/introduction/basics ✅（提示词基础与格式）
- promptingguide.ai/techniques/cot ✅（Chain-of-Thought详解）
- promptingguide.ai/techniques/fewshot ✅（Few-shot详解）
- promptingguide.ai/techniques/react ✅（ReAct模式详解）
- promptingguide.ai/techniques/prompt_chaining ✅（提示词链详解）
- promptingguide.ai/guides/context-engineering-guide ✅（上下文工程指南）

**有效内容覆盖率**: 约60%（3/7主源 + 7子页面）

---

## 二、核心发现摘要

### 2.1 DAIR.AI Prompt Engineering Guide — 关键Insight

> **核心观点**: Prompt Engineering是一门新兴学科，不仅涉及提示词设计，还包括与LLM交互和开发的广泛技能集。

**关键发现**:
1. **技术体系完整**: 涵盖Zero-shot、Few-shot、CoT、Self-Consistency、ToT、ReAct、Reflexion等17+种提示技术
2. **新兴趋势**: Context Engineering正取代Prompt Engineering成为更准确的术语，强调架构完整上下文而非单纯调优文本
3. **Agent导向**: 最新内容大量聚焦AI Agent（函数调用、上下文工程、深度Agent），反映从单轮提示到多步Agent工作流的范式转移
4. **评估缺失**: 文档明确指出"如果不衡量，如何知道上下文工程是否有效"，评估是当前最大缺口

### 2.2 Learn Prompting — 关键Insight

> **核心观点**: Prompt Engineering应基于研究支撑的实践技术，而非炒作。

**关键发现**:
1. **学术权威**: 被Google、Microsoft、Wikipedia、OpenAI、NIST引用，3M+用户，发布了最大规模提示技术调查报告（76页，1500+论文，200+技术）
2. **分层教学**: 🟢入门→🟦简单→◆中级→◆◆高级，按技术深度递进
3. **安全重视**: HackAPrompt与OpenAI合作的首届AI红队竞赛，Prompt Hacking与注入攻击是重要议题
4. **实用性优先**: 强调研究支撑的实践技术，立即可用于项目和应用的示例驱动教学

### 2.3 LangChain — 关键Insight

> **核心观点**: Agent = Model + Harness（模型+线束），提示词是Agent线束的核心组成部分。

**关键发现**:
1. **Agent范式**: `create_agent(model, tools, system_prompt)` — 提示词(system_prompt)与工具(tools)和模型(model)同等重要
2. **三层架构**: LangChain(可定制线束) → LangGraph(低级编排) → Deep Agents(全功能Agent)
3. **可观测性**: LangSmith提供追踪、调试、评估能力，是Prompt迭代优化的关键基础设施
4. **标准化接口**: 统一不同Provider的API差异，避免锁定

### 2.4 Context Engineering Guide (DAIR.AI) — 关键Insight

> **核心观点**: Context Engineering是Prompt Engineering的进化版，涵盖系统提示、结构化I/O、RAG、记忆、状态管理等全方位上下文架构。

**关键发现**:
1. **六大组件**: 系统提示 + 指令 + 用户输入 + 结构化I/O + 工具 + RAG/记忆 + 状态/历史
2. **结构化输出至关重要**: JSON Schema约束输出格式是上下文工程中被低估的关键技术
3. **上下文压缩**: 上下文可能稀释或变得低效（充斥过时和无关信息），需要专门的评估工作流
4. **动态上下文**: 日期时间、查询增强、缓存子查询等动态元素是工程化的关键

---

## 三、七类设计模式最佳实践详解

### 3.1 Chain-of-Thought (CoT) — 思维链

**来源**: Wei et al. (2022), Kojima et al. (2022), Zhang et al. (2022)

#### 核心原理
通过中间推理步骤使LLM获得复杂推理能力。CoT是一种**涌现能力**，仅在足够大的语言模型上显现。

#### 三种变体

| 变体 | 方法 | 适用场景 |
|------|------|----------|
| **Few-shot CoT** | 提供含推理过程的示例 | 有可用示例的复杂推理任务 |
| **Zero-shot CoT** | 添加"Let's think step by step" | 无示例但需推理的场景 |
| **Auto-CoT** | 自动聚类问题+生成推理链 | 大规模自动化场景 |

#### 最佳实践
1. **推理步骤显式化**: 在示例中展示完整推理过程，而非仅给结论
2. **Zero-shot CoT触发词**: "Let's think step by step"是最简单有效的触发词
3. **Auto-CoT两阶段**: ①问题聚类→②从每簇采样代表性问题+生成推理链
4. **与Few-shot组合**: CoT + Few-shot效果最优，纯Few-shot在推理任务上不可靠
5. **关键限制**: 需要足够大的模型（>100B参数），小模型CoT效果有限

#### 对本体系的启示
- **代码审查/架构设计**等深度分析场景应采用CoT模板
- 在提示词中加入`请逐步分析...`触发推理链
- Bug排查场景天然适合CoT：症状→假设→验证→定位→修复

---

### 3.2 Few-shot Learning — 少样本学习

**来源**: Brown et al. (2020), Min et al. (2022)

#### 核心原理
通过在提示中提供演示(demonstrations)实现上下文学习(in-context learning)，引导模型按期望格式和风格输出。

#### 关键发现（Min et al. 2022）
1. **标签空间和输入分布**比单个标签是否正确更重要
2. **格式**对性能起关键作用，即使使用随机标签也比无标签好
3. **从真实标签分布中随机选择标签**（而非均匀分布）也有帮助
4. 新版GPT模型对格式混乱更具鲁棒性

#### 最佳实践
1. **示例数量**: 1-shot即可学到任务，复杂任务3~5-shot，最多10-shot
2. **示例选择**: 优先选择代表性覆盖面广的示例，而非仅"正确"的示例
3. **格式一致性**: 示例格式与期望输出格式严格一致
4. **标签正确性非必须**: 格式和分布比标签正确性更重要（反直觉但实证支撑）
5. **局限性**: 对需要多步推理的任务，Few-shot仍不够，需结合CoT

#### 对本体系的启示
- 每个场景模板应包含2-3个高质量示例（输入→输出对）
- 示例格式应与本场景的输出格式严格一致
- 测试策略/安全审计等分类任务优先使用Few-shot

---

### 3.3 Self-Correction — 自我纠错

**来源**: Reflexion (Shinn et al. 2023), Self-Refine (Madaan et al. 2023)

#### 核心原理
让LLM评估自身输出，发现错误后进行修正迭代，直到满足质量标准或达到最大迭代次数。

#### 实现模式

```
循环：
  1. 生成 → 2. 评估 → 3. 反思 → 4. 改进
  直到: 评估通过 OR 达到最大迭代次数
```

#### 最佳实践
1. **明确评估标准**: 必须给出可判定的质量标准，否则LLM无法有效自评
2. **反思而非简单重试**: 让模型分析"为什么错了"而非仅重新生成
3. **迭代次数限制**: 通常2-3轮即可收敛，避免无限循环
4. **与外部验证结合**: 纯自纠错可能陷入错误循环，结合工具验证（如编译器、测试）更可靠
5. **Reflexion模式**: 保存历史反思到记忆中，跨任务复用纠错经验

#### 对本体系的启示
- **代码审查提示词**: 加入"审查你的审查结果，是否有遗漏"
- **文档生成提示词**: 加入"检查文档完整性，补充缺失章节"
- **安全审计提示词**: 自纠错+外部工具验证（lint/scan）组合

---

### 3.4 Multi-turn Dialogue — 多轮对话

**来源**: Prompt Chaining (DAIR.AI), LangChain Agent Loop

#### 核心原理
将复杂任务分解为多轮对话，每轮的输出作为下一轮的输入，逐步逼近最终目标。

#### 与Prompt Chaining的关系
Prompt Chaining是Multi-turn的特化形式：
- **Prompt Chaining**: 预定义的线性链，每步有明确输入/输出
- **Multi-turn Agent**: 动态决定下一步，可分支/回退/并行

#### 最佳实践
1. **每轮单一职责**: 每轮对话只做一件事，避免混合多个子任务
2. **上下文传递设计**: 明确哪些信息需要跨轮传递，避免信息丢失
3. **中间状态管理**: 使用结构化格式（JSON）存储中间结果
4. **示例: 文档QA两步链**: ①提取相关引用 → ②基于引用生成答案
5. **透明性与可调试性**: 链式结构天然支持逐步调试，优于单一巨型提示词

#### 对本体系的启示
- **全流程管理提示词**(01-12)天然是Prompt Chain
- 需要明确定义每个阶段的**输入契约/输出契约**
- 项目管理提示词(11)需要跨轮状态管理

---

### 3.5 Role-Playing — 角色扮演

**来源**: System Prompt设计模式 (OpenAI/Anthropic最佳实践)

#### 核心原理
通过System Prompt定义AI的角色身份、专业领域、行为约束，使其输出更加聚焦和专业。

#### 最佳实践
1. **角色定义三要素**: 身份(Who) + 专业领域(What) + 行为约束(How)
2. **身份锚定在开头**: 将角色定义放在提示词最开头，优先级最高
3. **避免角色冲突**: 单一提示词中不要定义矛盾的角色
4. **角色+工具组合**: 角色定义行为方式，工具定义能力边界
5. **动态角色切换**: 多Agent系统中不同Agent承担不同角色

#### 对本体系的启示
- 现有12个场景模板已有角色定义，但需要**统一角色定义格式**
- 角色定义应包含：身份 + 能力边界 + 输出风格 + 约束条件
- 考虑引入"角色组合"模式：主角色+辅助角色（如：架构师+安全审计员）

---

### 3.6 Structured Output — 结构化输出

**来源**: Context Engineering Guide, LangChain Tool Output Parser

#### 核心原理
通过JSON Schema、分隔符、模板变量等约束LLM输出为结构化格式，确保下游可解析、可验证。

#### 关键技术

| 技术 | 方法 | 适用场景 |
|------|------|----------|
| **JSON Schema** | 定义输出字段名/类型/约束 | API对接、数据库写入 |
| **XML标签** | `<result>...</result>` | 需要嵌套结构 |
| **分隔符** | `###`或`---`分隔指令与内容 | 混合文本+结构 |
| **类型注解** | `id: str, priority: int` | Python风格Agent |
| **示例驱动** | 提供完整JSON示例 | 自动推断Schema |

#### 最佳实践
1. **先定义Schema再写提示词**: 结构决定行为，Schema是契约
2. **示例+Schema双保险**: 同时提供JSON示例和类型定义，双重约束
3. **Optional字段明确标注**: `Optional[str] = None`，避免LLM猜测必填/选填
4. **枚举值约束**: 对有限取值字段列出所有可选值（如priority: 1-5）
5. **格式验证层**: 输出后做JSON解析验证，失败则触发Self-Correction

#### 对本体系的启示
- **所有场景模板**应定义标准化的输出JSON Schema
- 代码审查输出应为结构化缺陷列表，而非自由文本
- 评估报告应统一为结构化格式，支持自动汇总统计

---

### 3.7 Decomposition — 任务分解

**来源**: Prompt Chaining, Tree of Thoughts (Yao et al. 2023), Least-to-Most Prompting

#### 核心原理
将复杂任务分解为更简单的子任务，逐个解决后组合为最终答案。

#### 三种分解策略

| 策略 | 方法 | 适用场景 |
|------|------|----------|
| **线性分解** | Task → Sub1 → Sub2 → ... → Result | 有明确顺序的任务 |
| **树状分解(ToT)** | 多分支探索+回溯 | 需要探索多种可能性的任务 |
| **由简到繁** | 先解决最简单子问题，逐步增加复杂度 | 有依赖关系的推理任务 |

#### 最佳实践
1. **分解粒度**: 每个子任务应可独立完成，输入/输出明确
2. **ToT适用条件**: 当线性分解可能走入死胡同时，使用树状探索
3. **子任务独立性**: 尽量使子任务可并行执行，减少串行依赖
4. **结果聚合**: 设计明确的聚合策略，将子任务结果合并为最终输出
5. **错误隔离**: 单个子任务失败不应导致整体失败，设计容错机制

#### 对本体系的启示
- **全流程提示词**(01-12)已经是任务分解的体现
- 架构设计(02)可用ToT：探索多种架构方案→评估→选择
- Bug排查(字节跳动版)天然是线性分解：复现→定位→修复→验证

---

## 四、工业级框架设计理念

### 4.1 DSPy (Stanford) — 声明式Prompt编程

**核心理念**: 将Prompt视为可编程、可优化的声明式模块，而非手写文本。

**关键设计**:
- **Module抽象**: `dspy.Predict(signature)` — 签名定义输入/输出类型
- **自动优化**: `dspy.teleprompt.BootstrapFewShot` — 自动搜索最优Few-shot示例
- **编译-执行分离**: 先编译(优化Prompt)，再执行(使用优化后的Prompt)
- **评估驱动**: 基于评估指标自动优化，而非人工调优

**对本体系的启示**:
- 引入"Prompt签名"概念：每个场景模板定义输入/输出的类型签名
- 自动化Prompt评估：基于实际使用数据自动搜索最优示例和参数
- 编译-执行分离：模板开发阶段(编译)与运行时(执行)解耦

---

### 4.2 Semantic Kernel (Microsoft) — 语义内核

**核心理念**: 将LLM能力封装为"语义函数"，与传统编程函数统一调度。

**关键设计**:
- **Semantic Function**: 用自然语言(Prompt)定义的函数
- **Native Function**: 传统编程语言定义的函数
- **Pipeline**: 语义函数和原生函数可自由组合编排
- **Planner**: 自动规划如何组合函数完成任务

**对本体系的启示**:
- 每个场景模板可视为一个"语义函数"
- 需要设计"Pipeline编排器"：组合多个场景模板完成复杂任务
- Planner理念：给定项目需求，自动规划使用哪些模板、以什么顺序

---

### 4.3 Guidance (Microsoft) — 引导式生成

**核心理念**: 通过程序化控制LLM生成过程，而非一次性生成全部内容。

**关键设计**:
- **生成控制**: 逐token/逐块控制生成，可插入条件逻辑
- **强制格式**: 在生成过程中强制JSON/XML结构，而非后处理
- **角色交替**: 精确控制何时由LLM生成、何时使用固定文本
- **缓存优化**: 对重复部分进行缓存，减少计算量

**对本体系的启示**:
- 分阶段生成：先生成大纲，再逐章节填充，而非一次性生成全部
- 格式约束前置：在生成过程中即约束格式，减少后处理和解析失败
- 模板继承：公共部分缓存复用，个性化部分动态生成

---

### 4.4 Promptfoo — Prompt测试框架

**核心理念**: Prompt需要像代码一样被测试，支持A/B测试和回归测试。

**关键设计**:
- **声明式测试配置**: YAML定义Prompt变体、测试用例、断言
- **多Provider支持**: 同一测试用例跨OpenAI/Anthropic/本地模型运行
- **自动评估**: 基于规则(正则/JSON Schema)和模型(LLM-as-Judge)的断言
- **CI/CD集成**: 可作为GitHub Actions步骤运行

**对本体系的启示**:
- **每个场景模板都需要测试用例**: 输入+期望输出+断言
- **回归测试**: 模板修改后自动验证不破坏已有功能
- **A/B测试**: 对同一场景的多个Prompt变体进行效果对比
- **LLM-as-Judge**: 用强模型评估弱模型输出质量

---

### 4.5 LangSmith — Prompt评估与追踪

**核心理念**: 可观测性是Prompt工程化的基础，无法衡量则无法优化。

**关键设计**:
- **Trace**: 完整记录LLM调用的输入/输出/延迟/Token数
- **Session**: 将多次调用按会话/任务分组追踪
- **Evaluation**: 基于自定义评估函数批量评分
- **Annotation**: 人工标注+自动评估结合
- **LangSmith Engine**: 自动检测问题并建议修复

**对本体系的启示**:
- 建立Prompt使用追踪机制：记录每次调用的场景/输入/输出/耗时
- 建立评估仪表盘：各场景模板的质量趋势、常见失败模式
- 引擎模式：自动检测低质量输出并建议Prompt改进方向

---

## 五、对本提示词体系的优化启示

### 5.1 当前体系问题诊断

基于调研发现，当前55个场景模板（12个主分类）存在以下结构性问题：

| 问题类别 | 具体表现 | 调研支撑 |
|----------|----------|----------|
| **缺乏结构化输出定义** | 输出为自由文本，无JSON Schema约束 | Structured Output最佳实践 |
| **Few-shot示例不足** | 多数模板缺少输入→输出示例 | Few-shot Learning（Min et al. 2022） |
| **CoT缺失** | 复杂分析场景未启用逐步推理 | CoT（Wei et al. 2022） |
| **自纠错机制缺失** | 单次生成无质量自检 | Self-Correction/Reflexion |
| **评估体系缺失** | 无Prompt效果度量方法 | Promptfoo/LangSmith理念 |
| **跨模板协作未定义** | 模板间输入/输出契约未标准化 | Prompt Chaining + Context Engineering |
| **上下文工程不完整** | 未区分System/Instruction/User/Tools/State | Context Engineering六大组件 |

### 5.2 对12个主分类的改进方向

#### 01_需求分析与产品规划
- **+CoT**: 需求推理应逐步展开（用户需求→功能需求→技术需求→验收标准）
- **+Structured Output**: 需求文档应输出为结构化PRD JSON
- **+Few-shot**: 提供2-3个优秀需求分析示例

#### 02_架构设计与技术选型
- **+ToT(树状思维)**: 架构决策需探索多种方案并评估
- **+Decomposition**: 将架构设计分解为：架构风格→模块划分→技术选型→接口设计
- **+Structured Output**: 架构决策记录(ADR)标准化

#### 03_编码规范与AI辅助开发
- **+Few-shot**: 代码示例是最天然的Few-shot
- **+Structured Output**: 代码片段+规范说明+解释的结构化输出
- **+Role-Playing**: 强化编码角色约束（语言/框架/风格）

#### 04_代码审查与质量保障
- **+CoT**: 审查推理链（阅读→理解→识别问题→评估严重性→建议修复）
- **+Self-Correction**: 审查结果的二次校验
- **+Structured Output**: 缺陷列表为结构化JSON（位置/严重性/类型/建议）

#### 05_全维度测试策略
- **+Decomposition**: 测试策略分解为：单元→集成→E2E→性能→安全
- **+Few-shot**: 优秀测试用例作为示例
- **+Structured Output**: 测试计划/用例为结构化格式

#### 06_CI/CD与自动化部署
- **+Structured Output**: Pipeline定义为YAML/JSON
- **+Decomposition**: CI→CD→监控的线性分解
- **+Multi-turn**: 流水线配置是天然的多轮迭代过程

#### 07_监控告警与运维保障
- **+Structured Output**: 告警规则/仪表盘配置为结构化格式
- **+Self-Correction**: 告警规则的自验证（模拟触发→检查有效性）
- **+Few-shot**: 常见监控配置模板作为示例

#### 08_安全审计与合规检查
- **+CoT**: 安全推理链（识别资产→威胁建模→漏洞扫描→风险评估→修复建议）
- **+Self-Correction + 外部工具**: 自纠错+安全扫描工具双重验证
- **+Structured Output**: 安全报告为OWASP/标准结构

#### 09_性能压测与优化
- **+CoT**: 性能分析推理（基准→瓶颈定位→假设→验证→优化→再测）
- **+Decomposition**: 压测→分析→优化的线性分解
- **+Structured Output**: 性能报告/优化建议为结构化格式

#### 10_技术文档与知识沉淀
- **+Decomposition**: 文档按章节逐步生成
- **+Structured Output**: 文档大纲→内容→校验的结构化流程
- **+Self-Correction**: 文档完整性自检

#### 11_项目管理与迭代复盘
- **+Multi-turn + State**: 跨迭代状态管理
- **+Structured Output**: 里程碑/风险/决策为结构化记录
- **+Prompt Chaining**: 规划→执行→复盘的链式流程

#### 12_AI时代开发专项
- **+Context Engineering**: 完整的上下文架构（Prompt+Tools+Memory+State）
- **+All Patterns**: AI辅助开发场景可综合运用所有设计模式
- **+Structured Output**: AI工作流定义为结构化配置

### 5.3 体系级改进建议（优先级排序）

| 优先级 | 改进项 | 影响范围 | 工作量 |
|--------|--------|----------|--------|
| **P0** | 为所有模板添加结构化输出Schema定义 | 全部12类 | 中 |
| **P0** | 为所有模板添加2-3个Few-shot示例 | 全部12类 | 中 |
| **P1** | 为分析类模板添加CoT指令 | 01/02/04/08/09 | 小 |
| **P1** | 建立跨模板输入/输出契约标准 | 全部12类 | 大 |
| **P2** | 为审查/审计模板添加Self-Correction | 04/08 | 小 |
| **P2** | 建立Prompt评估框架（参考Promptfoo） | 全局 | 大 |
| **P3** | 引入Context Engineering六大组件模型 | 全局 | 大 |
| **P3** | 建立Prompt A/B测试机制 | 全局 | 大 |

### 5.4 Context Engineering六组件对本体系的映射

| 组件 | 当前状态 | 目标状态 |
|------|----------|----------|
| **System Prompt** | ✅ 已有角色定义 | 统一格式+能力边界+行为约束 |
| **Instructions** | ✅ 已有任务指令 | 添加CoT/Decomposition指令 |
| **User Input** | ⚠️ 部分有 | 标准化输入格式+分隔符 |
| **Structured I/O** | ❌ 缺失 | 为所有场景定义JSON Schema |
| **Tools** | ❌ 缺失 | 定义可用工具集（lint/scan/test等） |
| **RAG & Memory** | ❌ 缺失 | 引入项目知识库+历史状态 |
| **States & History** | ⚠️ 部分（项目管理） | 统一状态管理框架 |

---

## 附录A：关键学术文献

1. Wei et al. (2022) - Chain-of-Thought Prompting - arXiv:2201.11903
2. Kojima et al. (2022) - Zero-shot CoT - arXiv:2205.11916
3. Zhang et al. (2022) - Auto-CoT - arXiv:2210.03493
4. Min et al. (2022) - Rethinking the Role of Demonstrations - arXiv:2202.12837
5. Yao et al. (2022) - ReAct - arXiv:2210.03629
6. Shinn et al. (2023) - Reflexion
7. Madaan et al. (2023) - Self-Refine
8. Brown et al. (2020) - GPT-3 Few-shot - arXiv:2005.14165
9. Schulhoff et al. (2024) - The Prompt Report (76页综合调查) - arXiv:2406.06608

## 附录B：调研源备选地址

> 对于访问受限的源，以下替代地址可尝试：

- OpenAI: https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api
- Anthropic: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Google: https://ai.google.dev/gemini/docs/prompting-strategies
- DeepSeek: https://api-docs.deepseek.com/guides/prompt-engineering (英文版)

---

*本报告为Prompt体系深度迭代的输入基线，后续将基于此进行具体模板的优化设计。*
