# AI Prompt Toolkit 开源调研报告 v1.0

> 调研时间：2026-07-21
> 调研范围：AI Prompt安全、LLM开发工具、用户体验、鸿蒙生态、赛事贴合

---

## 一、AI Prompt安全领域最新趋势 (2025-2026)

### 1.1 Prompt Injection Defense

| 项目 | Stars | 语言 | 许可证 | 核心特性 | 借鉴价值 |
|------|-------|------|--------|---------|---------|
| **prompt-armor** | 10 | Python | Apache 2.0 | 5层融合检测(L1 Regex→L5 负选择)，训练元分类器，~24ms延迟，离线运行，MCP Server，CI/CD exit codes，8类攻击分类 | **最直接竞品/参考**，5层融合+元分类器架构与我们高度重合，可参考其L3对比学习FAISS、L4结构分析(Cialdini操控栈)、L5 IsolationForest、炎症级联(threshold jitter)等创新设计 |
| **garak** (NVIDIA) | 8.5k | Python | Apache 2.0 | LLM漏洞扫描器，支持DAN/encoding/promptinject/XSS等20+探测模块，多LLM后端(OpenAI/HF/Replicate/Bedrock)，harness架构，可扩展probe/detector/evaluator | **红队探测引擎参考**，probe-detector-harness插件架构非常适合我们红队功能，探测模块分类(dan/encoding/badchars/gcg等)可直接复用 |
| **LLM Guard** (Protect AI) | 3.2k | Python | MIT | 35+独立scanner(输入/输出)，PromptInjection/Anonymize/Secrets/Toxicity/InvisibleText等，Playground Web UI | **⚠️ 已归档(2026-07)**，但其scanner分类和PII检测设计值得参考，特别是Anonymize/Deanonymize配对、InvisibleText隐写检测 |
| **Rebuff** (Protect AI) | 1.5k | TS/Python | Apache 2.0 | 4层防御(启发式/LLM检测/VectorDB/Canary Token)，自硬化机制 | **⚠️ 已归档(2025-05)**，Canary Token泄漏检测和VectorDB攻击签名学习思路可借鉴 |
| **NeMo Guardrails** (NVIDIA) | 6.8k | Python | Apache 2.0 | 5类Guardrails(输入/对话/检索/执行/输出)，Colang DSL对话流建模，VS Code扩展，LangChain集成 | **Guardrails架构参考**，输入→对话→检索→执行→输出的全链路Guardrail思路、Colang DSL对话流建模、VS Code扩展开发可借鉴 |
| Lakera Guard | - | 闭源SaaS | 商业 | ~50ms延迟，专有检测 | 黑盒不可审计，不能离线运行——prompt-armor已在其对比表中 |

#### 关键趋势洞察

1. **多层融合检测成为主流**：从单层scanner(LLM Guard) → 多层独立(Rebuff) → 多层融合+元分类器(prompt-armor)，架构演进明显
2. **离线+无LLM依赖**是新方向：prompt-armor完全不用LLM，用ONNX+FAISS替代，避免"用LLM检测LLM攻击"的循环依赖
3. **MCP Server集成**：prompt-armor已原生支持MCP Server，可直接接入Claude Desktop/Cursor
4. **CI/CD exit codes**：prompt-armor的语义化退出码(0=allow, 1=warn, 2=block)非常适合CI集成
5. **Canary Token**机制(Rebuff)：在prompt模板中插入canary word，检测输出中是否泄漏，实现自硬化

### 1.2 LLM安全评估框架

| 项目 | Stars | 语言 | 特性 | 借鉴价值 |
|------|-------|------|------|---------|
| **promptfoo** | 23.5k | TypeScript | Prompt评估+红队，声明式YAML配置，CLI+Web viewer，CI/CD集成，支持100+ LLM，红队Dashboard，已加入OpenAI | **Prompt评估+红队参考**，声明式配置模式、A/B测试矩阵、Web viewer、red team dashboard设计非常成熟 |
| **Langfuse** | 31.5k | TS/Python | LLM可观测性平台，Tracing+Eval+Dataset+Playground+Prompt管理，OpenTelemetry，MCP Server | **全栈参考**，Prompt管理+Playground+评估一体化设计，@observe()装饰器模式、Prompt版本控制+缓存设计 |
| **Arize Phoenix** | 10.6k | Python | AI可观测性+评估，OpenTelemetry Tracing，LLM Eval，Dataset/Experiment，Playground，MCP Server | **可观测性参考**，OpenTelemetry-based tracing、PXI(AI工程Agent)、Remote MCP Server设计 |

### 1.3 MCP Server安全扫描

| 项目 | Stars | 特性 | 借鉴价值 |
|------|-------|------|---------|
| **prompt-armor MCP** | 10 | analyze_prompt工具，stdio传输，Claude Desktop/Cursor集成 | **直接参考**，MCP Server实现模式，如何将检测引擎暴露为MCP工具 |
| **Phoenix MCP** | 10.6k | Remote MCP Server(/mcp endpoint)，查询traces/datasets/experiments | Remote MCP模式参考 |
| **Langfuse MCP** | 31.5k | 通过CLI集成Claude Code/Cursor | MCP集成模式参考 |

### 1.4 Agent安全审计

| 项目/资源 | 描述 |
|-----------|------|
| **OWASP Top 10 for LLM Applications (2025)** | LLM应用安全风险标准，涵盖Prompt Injection、Supply Chain、PII等 |
| **OWASP dep-scan** (1.3k stars) | 供应链安全扫描，SBOM+VDR，CSAF VEX文档，可达性分析 | 供应链扫描+SARIF/CSAF报告格式参考 |
| **MITRE ATLAS** | AI系统对抗战术知识库，红队方法论参考 |

---

## 二、LLM应用开发工具

### 2.1 Prompt管理平台

| 项目 | Stars | 核心特性 | 借鉴价值 |
|------|-------|---------|---------|
| **promptfoo** | 23.5k | 声明式YAML配置，prompt对比矩阵，web viewer，CI/CD | Prompt A/B测试+评估框架设计 |
| **Langfuse** | 31.5k | Prompt版本管理，@observe装饰器，Prompt Playground，自动缓存 | Prompt管理+版本控制+缓存设计 |
| **Phoenix** | 10.6k | Prompt管理，Experiment tracking，Playground | Prompt实验追踪+迭代工作流 |

### 2.2 A/B测试和评估

| 项目 | 特性 | 借鉴价值 |
|------|------|---------|
| **promptfoo** | 声明式配置对比多模型/多prompt，自动化断言，打分矩阵 | **首选参考**，其Web viewer的对比矩阵UI设计非常适合我们的Playground |
| **Langfuse** | LLM-as-judge评估，代码评估器，用户反馈收集，手动标注 | 评估pipeline设计参考 |
| **Phoenix** | LLM Eval(RAG相关性、答案相关性)，Dataset+Experiment | 评估指标体系参考 |

### 2.3 LLM可观测性

| 项目 | Stars | 核心特性 | 借鉴价值 |
|------|-------|---------|---------|
| **Langfuse** | 31.5k | OpenTelemetry Tracing，@observe装饰器，Session追踪，评分卡 | **首选参考**，Tracing+评分卡一体化 |
| **Phoenix** | 10.6k | OpenTelemetry Tracing，Inferences分析，Embedding可视化，MCP Server | Tracing+Embedding可视化参考 |

---

## 三、用户体验和UI设计

### 3.1 Playground/IDE设计参考

| 产品 | 核心设计特点 | 借鉴价值 |
|------|------------|---------|
| **Cursor** | AI-first IDE，内联编辑，Chat+Cmd+K模式，Context管理 | **Playground UX参考**，内联安全提示、安全评分卡实时展示 |
| **v0.dev** | 自然语言→UI生成，实时预览，组件化 | Playground实时预览模式 |
| **bolt.new** | 全栈AI开发环境，实时部署 | 端到端体验设计 |
| **promptfoo Web Viewer** | 对比矩阵表格，红绿标记，过滤排序 | **评估结果可视化直接参考** |
| **Rebuff Playground** | 输入prompt→实时安全评分→攻击分类→证据展示 | **安全Playground原型参考**，输入→分析→结果展示的工作流 |
| **LLM Guard Playground** (HuggingFace) | 在线Scanner测试，输入/输出双面板 | Scanner测试UI参考 |

### 3.2 实时协作编辑

| 项目 | Stars | 核心特性 | 借鉴价值 |
|------|-------|---------|---------|
| **Yjs** | 22.2k | CRDT框架，共享类型(Map/Array/Text)，离线编辑，版本快照，undo/redo，共享光标 | **首选**，CRDT协作编辑引擎，支持ProseMirror/CodeMirror/Monaco绑定 |
| **Liveblocks** | - | 托管Yjs后端，WebSocket+持久存储，REST API，DevTools | 托管CRDT服务参考 |
| **Hocuspocus** | - | Yjs服务器，SQLite持久化，Webhooks，认证 | 自托管CRDT服务参考 |

### 3.3 可视化报告

| 项目/库 | 特性 | 借鉴价值 |
|---------|------|---------|
| **ECharts** | Apache开源，丰富图表类型，深色主题，大数据量 | **SARIF报告+安全评分卡可视化**，雷达图(多维度评分)、仪表盘(0-100分)、桑基图(攻击流向) |
| **Recharts** | React原生，声明式，轻量 | React Playground嵌入 |
| **Vega/Vega-Lite** | 声明式可视化规范，JSON→图表 | SARIF报告标准化可视化 |
| **prompt-armor CLI** | Rich终端输出，风险评分条+置信度+决策+分类+延迟表格 | **CLI报告格式直接参考** |

---

## 四、鸿蒙/华为云生态

### 4.1 HarmonyOS NEXT AI开发工具

| 资源 | 描述 |
|------|------|
| **HarmonyOS NEXT SDK** | 鸿蒙原生应用开发套件，ArkTS语言 |
| **HMS Core AI** | 华为AI服务套件，文本识别/语音/翻译等 |
| **MindSpore** | 华为深度学习框架，支持端侧推理 |
| **ArkCompiler** | 方舟编译器，ArkTS运行时 |

### 4.2 华为云ModelArts/Pangu集成

| 资源 | 描述 |
|------|------|
| **ModelArts** | 华为云AI开发平台，支持模型训练/部署/推理 |
| **Pangu Models** | 盘古大模型系列(NLP/CV/多模态/科学计算) |
| **Huawei Cloud EI** | 企业智能服务，含自然语言处理/图像识别 |

### 4.3 ArkTS代码检查

| 资源 | 描述 |
|------|------|
| **ArkTS Linter** | 鸿蒙官方代码检查工具，集成在DevEco Studio |
| **hvigor** | 鸿蒙构建工具，类似Gradle |

**差异化机会**：目前鸿蒙生态缺乏AI Prompt安全扫描工具，可将Toolkit的Prompt Lint/安全扫描能力适配到ArkTS/DevEco Studio扩展中。

---

## 五、赛事贴合

### 5.1 OSC 2026开源大赛

| 赛道 | 相关性 | 参赛策略 |
|------|--------|---------|
| **MoonBit国产开源生态** | 可用MoonBit重写核心检测引擎 | 参考 osc2026-guide skill |
| **AI安全** | 直接对口 | 以Prompt安全为切入点，突出红队探测+SARIF+MCP Server |

### 5.2 AI安全相关赛事

| 赛事 | 描述 |
|------|------|
| **DEF CON AI Village** | garak团队已参加，LLM红队攻防 |
| **AI Safety Challenge** | 多个安全竞赛 |
| **OWASP LLM Top 10 社区** | 非赛事但可增加项目曝光度 |

---

## 六、可复用组件和架构模式总结

### 6.1 核心架构模式

| 模式 | 来源 | 应用场景 |
|------|------|---------|
| **5层融合+元分类器** | prompt-armor | 我们的多层融合检测引擎，可参考其fusion.py + gate逻辑 |
| **Probe-Detector-Harness插件** | garak | 红队探测引擎的插件架构 |
| **Input→Dialog→Retrieval→Exec→Output Guardrails** | NeMo Guardrails | 全链路Guardrail设计 |
| **Scanner Pipeline(输入/输出分离)** | LLM Guard | Prompt/Output Scanner分离 |
| **Canary Token自硬化** | Rebuff | 动态攻击签名学习 |
| **Inflammation Cascade(炎症级联)** | prompt-armor | 会话级威胁感知，检测迭代探测攻击 |
| **Threshold Jitter** | prompt-armor | 防止对抗性阈值优化 |

### 6.2 可复用代码/组件

| 组件 | 来源 | 复用方式 |
|------|------|---------|
| `prompt-armor/src/prompt_armor/layers/` | prompt-armor | L1-L5检测层架构设计参考 |
| `prompt-armor/src/prompt_armor/fusion.py` | prompt-armor | 元分类器融合逻辑 |
| `garak/garak/probes/` | garak | 20+红队探测模块(DAN/encoding/badchars等) |
| `garak/garak/detectors/` | garak | 检测器插件 |
| `LLM Guard` scanner体系 | LLM Guard | 35+scanner分类和实现 |
| `prompt-armor/data/rules/default_rules.yml` | prompt-armor | 40+正则规则数据 |
| `prompt-armor/data/attacks/known_attacks.jsonl` | prompt-armor | 25K攻击样本数据 |
| `OWASP dep-scan` SARIF/CSAF报告 | dep-scan | 报告格式生成参考 |

### 6.3 差异化定位

| 维度 | 现有项目 | 我们的差异化 |
|------|---------|-------------|
| **Prompt Lint(55规则)** | prompt-armor只有40+正则 | 更多lint规则，覆盖prompt工程最佳实践 |
| **安全评分卡(0-100)** | prompt-armor只有risk_score(0-1) | 更细粒度评分+可视化Dashboard |
| **SARIF报告** | 无项目原生支持 | 企业级SARIF+CSAF VEX双格式 |
| **条件编译** | 无 | 独创，支持环境变量/Feature Flag控制扫描行为 |
| **Playground Web UI** | Rebuff有基础版 | 更完整的交互式安全测试体验 |
| **MCP Server** | prompt-armor有 | 扩展更多tools(不仅是analyze) |
| **VS Code扩展** | NeMo Guardrails有 | 专注Prompt安全的轻量扩展 |
| **红队探测** | garak有 | 集成到统一Toolkit而非独立工具 |
| **供应链扫描** | dep-scan有 | 专注AI/LLM供应链(pip/conda/model) |
| **鸿蒙适配** | 无 | 蓝海市场 |

---

## 七、痛点需求汇总

1. **现有安全工具太慢**：LLM Guard 200-500ms，NeMo Guardrails 1-3s → 我们目标<30ms
2. **评分不够细粒度**：多数工具只有binary safe/unsafe → 我们0-100评分卡+分类+置信度
3. **无统一工具链**：安全扫描(prompt-armor)、红队(garak)、Lint(flake8等)、评估(promptfoo)各自独立 → 我们All-in-One
4. **SARIF集成缺失**：安全工具不输出SARIF，无法与GitHub Code Scanning集成 → 我们原生SARIF
5. **MCP生态安全缺口**：MCP Server缺乏安全扫描能力 → 我们MCP Server
6. **条件编译无人做**：CI环境需要轻量扫描，生产需要全量扫描 → 条件编译
7. **鸿蒙AI安全空白**：鸿蒙生态无Prompt安全工具 → 差异化切入

---

## 八、下一步行动建议

1. **深度研读 prompt-armor 源码**：5层融合+元分类器+炎症级联，与我们架构最接近，可直接借鉴设计模式
2. **复用 garak 的probe体系**：将其20+探测模块适配为我们的红队引擎插件
3. **参考 promptfoo 的评估矩阵UI**：声明式配置+Web Viewer设计
4. **参考 Langfuse 的Prompt管理**：版本控制+缓存+Playground一体化
5. **SARIF格式参考 OWASP dep-scan**：CSAF VEX+SARIF双格式
6. **Yjs集成评估**：如需协作编辑功能，Yjs是首选CRDT框架
7. **鸿蒙适配规划**：ArkTS Lint规则+DevEco Studio扩展，填补市场空白
