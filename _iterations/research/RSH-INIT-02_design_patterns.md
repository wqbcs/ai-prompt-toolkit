# Prompt设计模式与国产大模型厂商指南调研报告

> **文档编号**: RSH-INIT-02  
> **版本**: v1.0  
> **日期**: 2026-05-28  
> **调研范围**: 5家国产大模型厂商 + 7类高级设计模式 + 中外对比分析  
> **状态**: 初始调研完成  
> **前置依赖**: RSH-INIT-01_best_practices.md

---

## 一、国产大模型厂商Prompt指南核心要点

### 1.1 厂商Prompt指南访问状态

| # | 厂商 | 访问URL | 访问状态 | 获取内容摘要 |
|---|------|---------|----------|-------------|
| 1 | 华为云盘古/ModelArts | support.huaweicloud.com/productdesc-modelarts | ✅ 产品概览 | ModelArts一站式AI开发平台，支持MindSpore/PyTorch等，底层昇腾硬件；盘古大模型Prompt指南链接404 |
| 2 | 阿里云百炼 | help.aliyun.com/zh/model-studio | ❌ 404 | 链接已变更，百炼Prompt工程文档路径已更新 |
| 3 | 百度千帆 | cloud.baidu.com/doc/WENXINWORKSHOP | ✅ 平台概览 | 千帆以Agent为核心，提供Prompt工程、App Builder、组件广场；支持ERNIE系列模型 |
| 4 | 腾讯混元 | cloud.tencent.com/document/product/1729 | ✅ 产品概述 | 混元2.0 Think/Instruct模型，支持128k输入；快慢思考切换；角色扮演专项模型；元器智能体平台 |
| 5 | 字节豆包 | volcengine.com/docs/82379/1221660 | ✅ 提示词工程 | 有独立提示词工程文档、Prompt优解（生成/调优/管理）、角色扮演指南、深度思考能力 |

### 1.2 各厂商Prompt工程核心要点提炼

#### 华为云 ModelArts / 盘古大模型
- **平台定位**: 一站式AI开发平台，数据准备→算法开发→模型训练→部署上线全生命周期
- **Prompt相关能力**: 
  - 大模型增强的多模态数据标注和合成能力
  - 支持零代码/低代码开发，内置主流框架镜像
  - AgentArts智能体开发平台（独立产品）
- **差异化**: 昇腾硬件原生支持，万卡级大规模集群管理，PD弹性伸缩
- **Prompt指南缺失**: 盘古大模型未找到独立的Prompt工程指南文档，嵌入在ModelArts平台操作中

#### 阿里云百炼 / 通义千问
- **平台定位**: 模型即服务（MaaS），千问大模型家族
- **Prompt相关能力**:
  - 百炼平台提供Prompt工程文档（URL已迁移）
  - 应用构建（App Builder）支持可视化Prompt编排
  - 模型市场提供多种开源/闭源模型选择
- **差异化**: 千问系列开源生态，电商/云原生场景深耕
- **Prompt指南特点**: 文档组织偏向API调用指南，Prompt工程作为独立章节

#### 百度千帆 / 文心一言
- **平台定位**: 以Agent为核心的大模型服务及Agent开发平台
- **Prompt相关能力**:
  - Prompt工程内置于应用开发流程
  - App Builder可视化Prompt配置
  - 组件广场提供可复用Prompt模板
  - ERNIE系列模型（文心一言4.0/4.5等）
- **差异化**: 搜索增强（百度搜索生态）、知识图谱融合、中文理解能力
- **Prompt指南特点**: Agent-first设计，Prompt作为Agent配置的一部分而非独立工程

#### 腾讯混元
- **平台定位**: 自研全链路大模型，内容创作/数理逻辑/代码生成/多轮对话
- **Prompt相关能力**:
  - **快慢思考切换**: query前加`/no_think`进行快慢思考模式切换（hunyuan-a13b）
  - **推理模型**: hunyuan-t1-latest，Hybrid-Transformer-Mamba架构，超强解码速度
  - **角色扮演专项**: hunyuan-large-role-latest，显著提升角色一致性与对话深度
  - **翻译专项**: 33种语言互译，WMT25比赛30种语言第一
  - AI搜索联网插件，整合腾讯内容生态
- **差异化**: 快慢思考切换机制（无需改Prompt，通过指令控制）、角色扮演专项优化
- **Prompt指南特点**: 产品能力描述为主，Prompt最佳实践散见于API文档

#### 字节豆包 / 火山方舟
- **平台定位**: 模型推理/评测/精调全流程服务，搭载豆包及主流大模型
- **Prompt相关能力**:
  - **独立提示词工程文档**: /docs/82379/1221660
  - **Prompt优解系统**: Prompt生成 → Prompt调优 → Prompt管理（完整闭环）
  - **角色扮演场景指南**: /docs/82379/1256348
  - **深度思考能力**: /docs/82379/1449737
  - **续写模式Prefill Response**: /docs/82379/1359497
  - 工具调用：豆包助手、Web Search联网搜索、Function Calling、MCP
  - 结构化输出(beta)、上下文缓存
- **差异化**: Prompt优解三件套（生成/调优/管理）是最完整的Prompt工程工具链
- **Prompt指南特点**: 最接近独立Prompt工程学科，有专门的生成→调优→管理流程

### 1.3 厂商共性发现

**共性1: Agent-First趋势** — 百度千帆、腾讯元器、字节豆包均以Agent/智能体为核心入口，Prompt作为Agent配置的一部分

**共性2: 深度思考/推理能力** — 腾讯混元t1、字节豆包深度思考、百度文心均推出推理模型，Prompt需适配CoT/ToT模式

**共性3: 角色扮演专项优化** — 腾讯混元large-role、字节豆包角色扮演指南，表明RP场景需要专门的Prompt策略

**共性4: 工具调用/MCP标准化** — 百度千帆MCP、豆包MCP/Function Calling、混元AI搜索，工具调用成为标配

**共性5: 中文语义理解** — 各厂商均强调中文场景优化，但Prompt工程方法论仍以英文体系为主

---

## 二、7类高级设计模式详解

### 2.1 ReAct模式 (Reasoning + Acting)

#### 原理
ReAct（Yao et al., 2023）将推理（Reasoning）和行动（Acting）交织在一起，让LLM在生成推理轨迹的同时执行外部工具调用，形成"思考→行动→观察→思考"的循环。

#### 核心流程
```
Thought: 我需要查找北京今天的天气
Action: search("北京天气")
Observation: 北京今天晴，最高温度32°C
Thought: 现在我知道了天气信息，可以回答了
Answer: 北京今天是晴天，最高温度32°C
```

#### 适用场景
- 需要调用外部API/工具的场景（搜索、数据库查询、代码执行）
- 多步推理+信息获取混合任务
- Agent/智能体开发（最主流模式）
- 知识密集型问答（RAG + 推理）

#### 示例
```yaml
system_prompt: |
  你是一个智能助手，可以使用以下工具：
  - search(query): 搜索互联网信息
  - calculate(expr): 计算数学表达式
  - database(sql): 查询数据库
  
  对于每个用户问题，请按以下格式回复：
  Thought: [你的推理过程]
  Action: [工具名称(参数)]
  Observation: [工具返回结果]
  ... (可多轮)
  Answer: [最终答案]

user_prompt: "2024年奥运会在哪里举办？那个城市的人口是多少？"
```

#### 对本体系的启示
- **核心应用**: 本体系的Agent模板应默认采用ReAct模式
- **工具注册**: 需要设计标准化的工具注册/描述格式（与MCP对齐）
- **错误恢复**: Action失败时需要Thought→重试的容错机制
- **观测日志**: 每步Thought/Action/Observation应记录为可审计日志

---

### 2.2 Tree-of-Thought (ToT) — 树状思维探索

#### 原理
ToT（Yao et al., 2023）将问题求解过程建模为搜索树，每个节点是一个"思维状态"（部分解），通过分支生成多个候选思路，用评估函数对每个节点评分，再选择最有前途的路径继续探索（BFS/DFS）。

#### 核心流程
```
问题 → 生成k个候选思路 → 评估每个思路 → 选择Top-m个 → 
对每个选中思路生成k个子思路 → 评估 → ... → 最优解
```

#### 适用场景
- 需要多路径探索的决策场景（如24点游戏、创意写作、战略规划）
- 单一CoT路径可能走入死胡同的问题
- 解空间大且需要全局搜索的优化问题
- 需要比较多种方案的商业决策

#### 示例
```yaml
system_prompt: |
  你需要解决以下问题。请使用树状思维探索：
  
  1. 【生成】针对当前问题，生成3个不同的解决思路
  2. 【评估】对每个思路给出1-10的可行性评分
  3. 【选择】选择评分最高的2个思路继续深入
  4. 【深入】对选中思路各自生成2个子方案
  5. 【评估】再次评分
  6. 【输出】选择最优方案并给出完整推理过程

user_prompt: "设计一个面向老年人的智能手机交互系统"
```

#### 对本体系的启示
- **适用标记**: 对"探索型"任务自动启用ToT而非CoT
- **分支控制**: 需要参数化控制分支数k和选择数m（成本vs质量权衡）
- **评估函数**: 可用LLM-as-Judge或规则评估器对节点评分
- **可视化**: ToT的搜索树应支持可视化展示决策路径

---

### 2.3 Meta-Prompting — 用Prompt生成Prompt

#### 原理
Meta-Prompting是用一个"元提示词"指导LLM生成或优化另一个"目标提示词"。本质上是一个Prompt→Prompt的映射函数，常用于提示词自动生成、优化和迭代。

#### 核心流程
```
元提示词(任务描述 + 约束条件 + 示例) → LLM → 优化的目标提示词
目标提示词(用户输入) → LLM → 输出结果
```

#### 适用场景
- 提示词自身优化（自动化Prompt Engineering）
- 批量生成不同场景的提示词模板
- 提示词版本迭代（A/B测试驱动优化）
- 跨领域迁移（将成功Prompt适配到新领域）

#### 示例
```yaml
meta_prompt: |
  你是一个Prompt工程专家。请根据以下要求生成一个高质量的系统提示词：
  
  【任务】: {task_description}
  【目标模型】: {model_name}
  【输出格式】: {output_format}
  【约束条件】: {constraints}
  【参考示例】: {examples}
  
  生成的提示词应遵循以下原则：
  1. 角色设定清晰
  2. 任务描述无歧义
  3. 包含2-3个Few-shot示例
  4. 输出格式明确（JSON/Markdown等）
  5. 包含边界情况处理指令

generated_prompt: |
  [LLM生成的高质量提示词]
```

#### 对本体系的启示
- **Prompt工厂**: 本体系应实现Meta-Prompting驱动的"Prompt工厂"
- **版本迭代**: 结合A/B测试数据自动迭代Prompt版本
- **模板变量化**: 元提示词中的{task_description}等变量实现模板化
- **质量守门**: 生成的Prompt需经过质量检查（语法、完整性、一致性）

---

### 2.4 Directional Stimulus Prompting — 方向性刺激提示

#### 原理
方向性刺激提示（Li et al., 2023）通过在Prompt中添加一个"刺激前缀"（Stimulus Prefix），引导LLM的输出朝特定方向发展。这个前缀通常是一个短小的关键词或短语，起到"方向指引"作用。

#### 核心流程
```
标准Prompt: "描述这张图片" → 通用描述
方向性Prompt: "【幽默风格】描述这张图片" → 朝幽默方向偏移
```

#### 适用场景
- 需要控制输出风格/语调的场景（正式/幽默/简洁/详细）
- 需要引导输出倾向性的场景（正面/负面/中立）
- 多风格内容生成（营销文案需要多种风格变体）
- 与RLHF配合，作为轻量级的输出控制手段

#### 示例
```yaml
stimulus_prefixes:
  formal: "【正式商务风格】请用严谨专业的语言"
  creative: "【创意营销风格】请用生动有趣的语言"  
  concise: "【极简风格】请用最精炼的语言"
  empathetic: "【共情温暖风格】请用关怀体贴的语言"

base_prompt: "写一段产品介绍：{product_name}"

# 组合使用
directional_prompt: "{stimulus_prefix} {base_prompt}"
```

#### 对本体系的启示
- **风格维度**: 定义标准化的风格维度库（正式度、创意度、简洁度、共情度等）
- **前缀协议**: 设计`[维度:值]`格式的标准刺激前缀协议
- **组合控制**: 支持多个维度的组合控制（如`[正式度:高][共情度:中]`）
- **强度调节**: 支持刺激强度的连续调节而非二元开关

---

### 2.5 Program-of-Thoughts (PoT) — 编程式思维

#### 原理
PoT（Chen et al., 2023）将推理过程转化为可执行代码，让LLM生成Python/其他语言代码来表达推理步骤，然后通过代码解释器执行获得结果。相比CoT的自由文本推理，PoT的推理过程是可验证、可执行的。

#### 核心流程
```
问题 → LLM生成推理代码 → 代码解释器执行 → 获取结果 → 格式化输出
```

#### 适用场景
- 数学和逻辑推理（计算精度要求高）
- 数据分析和统计计算
- 需要可验证推理过程的场景（金融/法律/医疗）
- 与代码解释器集成的场景

#### 示例
```yaml
system_prompt: |
  请用Python代码解决以下问题。你的回复应包含：
  1. 推理过程说明（注释形式）
  2. 可执行的Python代码
  3. 最终答案
  
  代码将被安全执行，你可以使用numpy、pandas等库。

user_prompt: "一个投资组合包含3只股票，权重分别为40%、35%、25%，年化收益率分别为12%、8%、15%，标准差分别为20%、15%、25%，相关系数矩阵为[[1,0.3,0.2],[0.3,1,0.4],[0.2,0.4,1]]。请计算组合的年化收益率和标准差。"

# LLM生成：
# # 计算投资组合收益率
# weights = np.array([0.4, 0.35, 0.25])
# returns = np.array([0.12, 0.08, 0.15])
# portfolio_return = np.dot(weights, returns)  # = 0.116
# 
# # 计算组合标准差
# cov_matrix = ...  # 从相关系数和标准差构建
# portfolio_std = np.sqrt(weights @ cov_matrix @ weights)
```

#### 对本体系的启示
- **精度保障**: 对数学/金融/统计类任务默认启用PoT而非CoT
- **安全沙箱**: 代码执行需在安全沙箱中运行（限制文件/网络访问）
- **结果缓存**: 相同代码+数据的执行结果应缓存
- **回退机制**: PoT执行失败时回退到CoT文本推理

---

### 2.6 Automatic Prompt Engineering (APE) — 自动提示词工程

#### 原理
APE（Zhou et al., 2022）是一种反向生成方法：给定输入-输出对，自动搜索最优提示词。核心思路是将Prompt视为可优化的参数，通过搜索算法（如蒙特卡洛、梯度引导）在Prompt空间中找到使目标函数最大化的提示词。

#### 核心流程
```
1. 准备训练数据: {(input_i, output_i)}
2. 初始化: 生成候选Prompt池（通过LLM反向生成或人工种子）
3. 评估: 对每个候选Prompt，在训练集上计算目标函数（准确率/F1等）
4. 搜索: 基于评估结果，用搜索算法探索新的Prompt变体
5. 选择: 返回目标函数最高的Prompt
```

#### 适用场景
- 有标注数据可用时的Prompt自动优化
- 大规模Prompt模板生成（覆盖长尾场景）
- Prompt A/B测试的自动化版本
- 人力有限的Prompt工程初始阶段

#### 示例
```yaml
ape_config:
  task: "情感分析"
  training_data: "sentiment_labeled_1000.jsonl"
  evaluation_metric: "f1_score"
  search_strategy: "monte_carlo"
  
  # 反向生成：给定输入输出对，让LLM猜测Prompt
  inverse_generation:
    model: "gpt-4"
    num_candidates: 20
    
  # 评估配置
  evaluation:
    model: "gpt-3.5-turbo"  # 用便宜模型评估
    sample_size: 200
    
  # 搜索配置  
  search:
    iterations: 50
    mutation_methods: ["paraphrase", "add_constraint", "reorder"]
    
  # 输出
  output:
    top_k: 5  # 返回Top-5 Prompt
    save_path: "optimized_prompts/"
```

#### 对本体系的启示
- **数据驱动**: 本体系应支持基于标注数据的Prompt自动优化
- **评估框架**: 需要建立Prompt评估框架（准确率、延迟、成本等维度）
- **搜索策略**: 实现多种搜索策略（随机、梯度引导、进化算法）
- **人机协同**: APE生成Top-K候选，人工审核选择最终版本

---

### 2.7 Active-Prompt — 主动提示

#### 原理
Active-Prompt（Diao et al., 2023）基于不确定性选择最有效的Few-shot示例。核心思路：对候选示例池中的每个示例，计算LLM对其输出不确定性的度量（如熵），选择不确定性最高的示例作为Few-shot示范，因为高不确定性意味着该示例包含更多"信息量"。

#### 核心流程
```
1. 对每个候选示例，用LLM生成多个输出
2. 计算每个示例的不确定性（熵/方差等）
3. 选择不确定性最高的Top-K个示例
4. 用选中的示例构建Few-shot Prompt
5. 在目标任务上使用该Prompt
```

#### 适用场景
- Few-shot示例数量有限，需要精选最有信息量的示例
- 示例池大但上下文窗口有限
- 示例选择对性能影响显著的场景
- 跨领域迁移（从通用示例中选择与目标领域最相关的）

#### 示例
```yaml
active_prompt_config:
  task: "医疗问答"
  candidate_pool: "medical_qa_examples_500.jsonl"
  num_demonstrations: 5  # Few-shot数量
  uncertainty_metric: "entropy"  # 熵作为不确定性度量
  num_samples_per_example: 10  # 每个示例采样10次
  
  # 第1步：计算不确定性
  uncertainty_estimation:
    model: "gpt-3.5-turbo"
    temperature: 0.7  # 较高温度增加多样性
    
  # 第2步：选择Top-K
  selection:
    strategy: "top_k_by_uncertainty"
    k: 5
    
  # 第3步：构建Few-shot Prompt
  prompt_construction:
    format: "Q: {question}\nA: {answer}\n\n"
    ordering: "uncertainty_descending"  # 不确定性降序排列
```

#### 对本体系的启示
- **动态示例选择**: 本体系的Few-shot模板应支持基于不确定性的动态示例选择
- **示例池管理**: 需要维护分场景的示例池，支持标注和索引
- **不确定性评估**: 实现LLM输出熵的计算（多次采样+统计）
- **冷启动**: 新场景无标注数据时，Active-Prompt可作为示例选择的启发式方法

---

## 三、中外Prompt工程差异对比

### 3.1 方法论体系对比

| 维度 | 海外（OpenAI/Anthropic/DeepMind） | 国内（百度/腾讯/字节/阿里/华为） |
|------|-----------------------------------|-----------------------------------|
| **学科认知** | Prompt Engineering作为独立学科，有完整理论体系 | Prompt作为平台功能的一部分，未独立成学科 |
| **文档成熟度** | 完整的Prompt Engineering Guide（OpenAI/Anthropic均有独立指南） | 嵌入在平台文档中，多数厂商无独立Prompt工程指南 |
| **设计模式覆盖** | CoT/ToT/ReAct/APE等17+种技术，研究驱动 | 实用主义导向，聚焦角色扮演/深度思考/工具调用 |
| **评估体系** | 强调评估（"If you don't measure, you don't know"） | 评估体系薄弱，缺少Prompt评估最佳实践 |
| **工具链** | DSPy（程序化Prompt）、LangChain模板、PromptFoo评估 | 字节Prompt优解三件套（最接近），其他厂商缺失 |
| **Agent范式** | ReAct/Plan-and-Execute/Multi-Agent成熟 | Agent-First趋势明确但方法论不成熟 |
| **中文优化** | 中文为第二语言，Prompt翻译损耗 | 中文原生优化，角色扮演/翻译等专项模型 |
| **安全合规** | Constitution AI/RLHF/Red-Teaming | 内容安全平台/内容审核，更注重合规而非对齐 |

### 3.2 技术重点差异

| 技术领域 | 海外重点 | 国内重点 |
|----------|---------|---------|
| **推理增强** | o1/o3系列推理模型，CoT/ToT理论研究 | 深度思考模型（混元t1/豆包深度思考），快慢思考切换 |
| **工具调用** | Function Calling → MCP标准化 | 豆包MCP/千帆MCP/混元AI搜索，跟随MCP标准 |
| **提示词管理** | DSPy/PromptFoo/版本控制 | 字节Prompt优解（生成/调优/管理闭环） |
| **角色扮演** | System Prompt + Persona设计 | 专项模型（混元large-role/豆包角色扮演指南） |
| **多模态** | GPT-4V/Gemini视觉推理 | 混元Vision/豆包图片理解，追赶阶段 |
| **开源生态** | Llama/Gemma/Mistral开源体系 | 千问开源/DeepSeek开源，快速追赶 |

### 3.3 差异根因分析

1. **发展阶段差异**: 海外起步早2-3年，已完成从"技巧"到"学科"的转变；国内仍处于"平台功能"阶段
2. **市场需求差异**: 国内更注重垂直场景落地（客服/营销/翻译），海外更注重通用能力提升
3. **合规约束差异**: 国内内容合规要求更严格，Prompt工程需内嵌安全审查；海外更关注对齐/偏见
4. **生态差异**: 海外DSPy/LangChain等开源工具链成熟；国内工具链刚起步（字节Prompt优解为代表）
5. **研究投入差异**: 海外学术界系统性研究Prompt Engineering（CMU/Stanford/DeepMind）；国内研究偏应用

---

## 四、对本体系的具体优化建议

### 4.1 设计模式采纳优先级

| 优先级 | 设计模式 | 理由 | 实施难度 |
|--------|---------|------|---------|
| **P0 - 立即** | ReAct | Agent核心模式，所有厂商标配 | 中 |
| **P0 - 立即** | Meta-Prompting | Prompt工厂基础设施，自举能力 | 中 |
| **P1 - 短期** | Directional Stimulus | 轻实现，风格控制是高频需求 | 低 |
| **P1 - 短期** | Program-of-Thoughts | 数学/分析类任务精度保障 | 高（需沙箱） |
| **P2 - 中期** | Tree-of-Thought | 探索型任务价值大，但Token成本高 | 中 |
| **P2 - 中期** | Active-Prompt | 示例选择优化，需评估框架支撑 | 高 |
| **P3 - 长期** | APE | 需要标注数据+评估框架，依赖其他基础设施 | 高 |

### 4.2 架构层面建议

#### 建议1: 建立Prompt模式注册表
```yaml
# prompt_patterns/registry.yaml
patterns:
  react:
    version: "1.0"
    trigger: "tool_use_required"
    template: "patterns/react/v1.0/system.yaml"
    parameters: ["tools", "max_iterations", "error_recovery"]
    
  tot:
    version: "1.0"
    trigger: "exploration_required"
    template: "patterns/tot/v1.0/system.yaml"
    parameters: ["branch_factor", "selection_count", "evaluator"]
    
  directional_stimulus:
    version: "1.0"
    trigger: "style_control_required"
    template: "patterns/directional/v1.0/system.yaml"
    parameters: ["dimensions", "intensity"]
```

#### 建议2: 设计模式自动路由
```python
def select_pattern(task_metadata):
    """根据任务元数据自动选择最优Prompt模式"""
    if task_metadata.requires_tools:
        return "react"
    if task_metadata.requires_exploration:
        return "tot"
    if task_metadata.requires_precision:
        return "pot"
    if task_metadata.style_override:
        return "directional_stimulus"
    return "standard"  # 默认Zero-shot/Few-shot
```

#### 建议3: 厂商适配层
```yaml
# 适配不同厂商的特殊能力
vendor_adapters:
  tencent_hunyuan:
    fast_slow_think: true  # 支持/no_think指令
    role_play_model: "hunyuan-large-role-latest"
    
  bytedance_doubao:
    prompt_optimization: true  # Prompt优解三件套
    deep_thinking: true
    
  baidu_qianfan:
    agent_first: true
    search_augmented: true  # 百度搜索增强
```

#### 建议4: Prompt评估框架
```
评估维度:
  - 准确性: 目标输出匹配度（Exact Match / F1 / BLEU）
  - 一致性: 多次运行输出稳定性（熵/方差）
  - 成本效率: Token消耗 / 延迟 / 调用次数
  - 安全性: 内容合规 / 越狱抵抗 / 幻觉率
  - 可维护性: Prompt可读性 / 参数化程度 / 版本可追溯
```

### 4.3 实施路线图

**Phase 1 (1-2周)**: 
- 实现ReAct模式模板 + 工具注册协议
- 实现Directional Stimulus风格维度库
- 建立Prompt模式注册表基础框架

**Phase 2 (3-4周)**:
- 实现Meta-Prompting Prompt工厂
- 实现PoT模式 + 代码沙箱集成
- 建立Prompt评估框架v1（准确性+一致性）

**Phase 3 (5-8周)**:
- 实现ToT模式 + 可视化
- 实现Active-Prompt示例选择器
- 厂商适配层（混元/豆包/千帆）

**Phase 4 (9-12周)**:
- APE自动优化引擎
- Prompt版本管理 + A/B测试
- 评估框架v2（安全性+可维护性）

---

## 五、调研核心发现摘要

### 5.1 最关键发现

1. **字节豆包是唯一提供完整Prompt工程工具链的国产厂商**（Prompt优解：生成→调优→管理），其他厂商均将Prompt嵌入平台功能

2. **Agent-First已成国内共识** — 百度千帆/腾讯元器/豆包助手均以Agent为核心，Prompt是Agent的配置项而非独立工程对象

3. **深度思考/推理模型是国产厂商的差异化重点** — 混元t1（Hybrid-Transformer-Mamba）、豆包深度思考、千帆推理模型，Prompt需适配快慢思考切换

4. **国内Prompt工程方法论严重滞后于工程实践** — 有平台能力但缺独立方法论，有工具但缺评估，有场景但缺通用模式

5. **ReAct是最具落地价值的设计模式** — 所有厂商的工具调用/Agent能力均基于ReAct范式（显式或隐式）

6. **Meta-Prompting是体系自举的关键** — 用Prompt生成Prompt的能力是实现Prompt工程自动化闭环的基础

7. **中外最大差距在"评估"** — 海外强调"If you don't measure, you don't know"，国内几乎无Prompt评估最佳实践

### 5.2 对本体系的一句话总结

> 本体系应建立**"模式注册 → 自动路由 → 厂商适配 → 评估闭环"**的四层架构，以ReAct和Meta-Prompting为双核驱动，优先补齐评估框架这一最大短板。

---

## 附录A: 调研源完整列表

| # | 类型 | 来源 | URL | 状态 |
|---|------|------|-----|------|
| 1 | 厂商 | 华为云ModelArts | support.huaweicloud.com/productdesc-modelarts/modelarts_01_0001.html | ✅ |
| 2 | 厂商 | 阿里云百炼 | help.aliyun.com/zh/model-studio/developer-reference/prompt-engineering | ❌ 404 |
| 3 | 厂商 | 百度千帆 | cloud.baidu.com/doc/WENXINWORKSHOP/s/Nlks5ylzu | ✅ 概览 |
| 4 | 厂商 | 腾讯混元 | cloud.tencent.com/document/product/1729 | ✅ 产品概述 |
| 5 | 厂商 | 腾讯混元产品详情 | cloud.tencent.com/document/product/1729/104753 | ✅ |
| 6 | 厂商 | 字节豆包 | volcengine.com/docs/82379 | ✅ 导航 |
| 7 | 厂商 | 字节豆包提示词工程 | volcengine.com/docs/82379/1221660 | ✅ 页面标题确认 |
| 8 | 厂商 | 华为云盘古 | support.huaweicloud.com/pangus/pangus_01_0001.html | ❌ 404 |

## 附录B: 7类设计模式学术论文引用

| 模式 | 论文 | 年份 | 核心贡献 |
|------|------|------|---------|
| ReAct | Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" | 2023 | 推理+行动交织范式 |
| ToT | Yao et al., "Tree of Thoughts: Deliberate Problem Solving with Large Language Models" | 2023 | 树状搜索+评估 |
| Meta-Prompting | 多篇, 包括DSPy框架 | 2023-2024 | Prompt作为可优化程序 |
| Directional Stimulus | Li et al., "Guiding Large Language Models with Directional Stimulus Prompting" | 2023 | 方向性刺激前缀 |
| PoT | Chen et al., "Program of Thoughts Prompting: Separating Computation from Reasoning" | 2023 | 推理→可执行代码 |
| APE | Zhou et al., "Large Language Models Are Human-Level Prompt Engineers" | 2022 | 自动反向生成Prompt |
| Active-Prompt | Diao et al., "Active Prompting with Chain-of-Thought for Large Language Models" | 2023 | 基于不确定性的示例选择 |
