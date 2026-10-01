# 调研报告R1：AI Agent框架对比（AutoGen/CrewAI/LangGraph）

> **日期**：2026-07-12 | **版本**：v21-R1

---

## 一、框架概览

### 1. Microsoft AutoGen

| 特性 | 详情 |
|------|------|
| 开发者 | Microsoft Research |
| 语言 | Python 3.10+ / .NET |
| Stars | 45k+ |
| 架构 | 事件驱动（Core）+ 对话式（AgentChat）+ 可视化（Studio） |
| 核心组件 | AgentChat / Core / Extensions / Studio |
| 许可证 | MIT |

**核心能力**：
- **AgentChat**：对话式单/多Agent应用框架，AssistantAgent+ToolUse
- **Core**：事件驱动可扩展多Agent系统，Actor模型+消息传递
- **Extensions**：MCP工具+OpenAI Assistant+Docker执行器+gRPC分布式
- **Studio**：Web UI零代码原型开发，`autogenstudio ui --port 8080`
- **代码执行**：Docker沙箱安全执行LLM生成代码
- **分布式**：gRPC Worker Runtime支持跨进程/跨机器Agent

**设计模式**：
- Sequential Agent Conversation
- Group Chat（RoundRobin/Selector）
- Human-in-the-Loop
- Code Execution with Docker
- Distributed Agent Runtime

### 2. CrewAI

| 特性 | 详情 |
|------|------|
| 开发者 | CrewAI Inc |
| 语言 | Python 3.10-3.13 |
| Stars | 55.4k+ |
| 架构 | Crews（自主协作）+ Flows（事件驱动工作流） |
| 核心组件 | Crews / Flows / Tools / Memory / Knowledge |
| 许可证 | MIT |

**核心能力**：
- **Crews**：角色驱动Agent团队，自主决策+动态任务委派
- **Flows**：事件驱动工作流，@start/@listen/@router装饰器+or_/and_逻辑
- **Agent配置**：role/goal/backstory/tools/LLM/memory/guardrails
- **任务配置**：description/expected_output/output_pydantic/output_json/human_input
- **结构化输出**：Pydantic模型/JSON模式
- **工具集成**：SerperDev/RAG/自定义工具/MCP/A2A
- **企业版AMP**：控制面板+可观测性+安全+治理
- **YAML配置**：agents.yaml+tasks.yaml声明式定义

**设计模式**：
- Sequential Process
- Hierarchical Process（自动Manager）
- Crew+Flow组合
- Conditional Routing
- Human Input on Execution

### 3. LangGraph（参考）

| 特性 | 详情 |
|------|------|
| 开发者 | LangChain |
| 语言 | Python / TypeScript |
| 架构 | 图状态机（State Graph） |
| 核心组件 | StateGraph / Node / Edge / Conditional Edge |
| 许可证 | MIT |

**核心能力**：
- 图结构工作流定义
- 状态持久化+检查点
- 人工审批节点
- 子图嵌套
- 流式输出
- 时间旅行调试

---

## 二、框架对比矩阵

| 维度 | AutoGen | CrewAI | LangGraph |
|------|---------|--------|-----------|
| **设计哲学** | 事件驱动+对话式 | 角色协作+流程控制 | 图状态机 |
| **学习曲线** | 中 | 低 | 中高 |
| **代码量** | 中 | 低（YAML声明式） | 高 |
| **灵活性** | 高（Core底层） | 中高 | 高 |
| **生产就绪** | Core级 | Flows级 | 成熟 |
| **可观测性** | Studio | AMP | LangSmith |
| **分布式** | gRPC原生 | AMP Cloud | 无原生 |
| **结构化输出** | ✓ | Pydantic/JSON | ✓ |
| **人工介入** | ✓ | ✓ | ✓ |
| **MCP支持** | ✓ | ✓ | ✓ |
| **代码执行** | Docker沙箱 | 无原生 | 无原生 |
| **可视化** | Studio Web UI | 无原生 | LangGraph Studio |
| **中文生态** | 弱 | 弱 | 中 |
| **华为云适配** | 需定制 | 需定制 | 需定制 |

---

## 三、提示词体系适配建议

### 场景1：Agent框架选型提示词
- 用户描述业务需求→推荐最适Agent框架→给出架构方案
- 对比维度：团队规模/技术栈/预算/部署环境

### 场景2：AutoGen多Agent协作提示词
- AgentChat对话编排→Group Chat模式→Human-in-the-Loop
- 代码执行安全沙箱配置→gRPC分布式部署

### 场景3：CrewAI角色协作提示词
- YAML声明式Agent定义→role/goal/backstory最佳实践
- Flows事件驱动编排→@start/@listen/@router装饰器模式

### 场景4：LangGraph状态机提示词
- StateGraph定义→Node/Edge/Conditional Edge编排
- 检查点持久化→人工审批节点→时间旅行调试

### 场景5：混合框架集成提示词
- AutoGen+CrewAI互操作→LangGraph编排→统一可观测性
- 华为云ModelArts/AgentArts集成→国产模型适配

---

## 四、关键发现

1. **AutoGen**最适合需要代码执行和分布式部署的场景
2. **CrewAI**最适合快速原型和角色驱动的业务流程自动化
3. **LangGraph**最适合需要精细状态控制和长时间运行的工作流
4. 三者均可通过MCP协议互通工具
5. 华为云AgentArts可作为企业级控制平面
