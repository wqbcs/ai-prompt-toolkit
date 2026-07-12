# 调研报告 - Maturity R8（v24→v25）

> **轮次**: R8 | **日期**: 2026-07-12 | **版本**: v1.0

---

## R1. 开源Prompt工程工具调研

### 调研目标
了解当前主流开源Prompt工程工具的功能特性、架构设计和最佳实践，为A/B测试v2、模板继承、条件编译等新功能提供参考。

### 调研对象

| 项目 | Stars | 定位 | 关键特性 |
|------|-------|------|----------|
| danielmiessler/fabric | 30k+ | AI增强框架 | 100+预制Pattern、链式调用、自定义策略、多模型支持 |
| microsoft/promptflow | 10k+ | LLM应用开发工具 | 端到端开发、评估调试、VS Code扩展、批量测试 |
| promptfoo/promptfoo | 5k+ | LLM评估与红队 | 多模型对比、统计评估、CI/CD集成、红队测试 |
| pezzolabs/pezzo | 2k+ | 云原生LLMOps | 提示词管理、可观测性、缓存、成本优化 |

### 关键发现

1. **Fabric的Pattern体系**:
   - 每个Pattern是一个独立的Markdown文件，包含系统提示词
   - 支持Pattern链式调用（Chain），将多个Pattern串联处理
   - 支持Per-Pattern模型映射，不同Pattern可使用不同模型
   - 这为本项目F3条件编译的"按模型条件编译"提供了参考

2. **PromptFlow的评估框架**:
   - 提供内置评估器（Accuracy、Relevance、Coherence等）
   - 支持批量测试和对比评估
   - VS Code可视化流程设计器
   - 这为本项目F1 A/B测试v2的多模型并行对比提供了参考

3. **Promptfoo的多模型对比**:
   - 支持同时对比OpenAI/Anthropic/Azure/Bedrock/Ollama等多个模型
   - 提供Web Viewer可视化对比矩阵
   - 已加入OpenAI，生态成熟
   - 这为本项目F1的胜率矩阵和统计显著性检验提供了直接参考

4. **Pezzo的LLMOps能力**:
   - 提示词版本管理和协作
   - 实时可观测性（延迟、Token消耗、成本）
   - 缓存机制降低成本
   - 这为本项目U3使用效率热力图和U2模板预览提供了参考

### 对需求的指导

| 需求项 | 参考项目 | 借鉴点 |
|--------|----------|--------|
| F1 A/B测试v2 | Promptfoo | 多模型并行对比、统计评估方法、对比矩阵 |
| F2 模板继承 | Fabric | Pattern链式调用、模块化组合 |
| F3 条件编译 | Fabric | Per-Pattern模型映射 |
| U1 代码片段复制 | Fabric | Pattern格式化输出 |
| U2 模板预览 | PromptFlow | 流程可视化预览 |
| U3 效率热力图 | Pezzo | 可观测性、成本追踪 |

---

## R2. 华为云服务文档调研

### 调研目标
了解华为云DEH/BMS/AS/ELB四大服务的功能特性和典型应用场景，为赛事贴合度提升提供专业内容支撑。

### 调研对象

| 服务 | 文档URL | 核心定位 |
|------|---------|----------|
| DEH（专属主机） | https://support.huaweicloud.com/deh/index.html | 用户独享的专属物理主机资源 |
| BMS（裸金属服务器） | https://support.huaweicloud.com/bms/index.html | 兼具虚拟机弹性和物理机性能 |
| AS（弹性伸缩） | https://support.huaweicloud.com/as/index.html | 自动调整资源的弹性伸缩服务 |
| ELB（弹性负载均衡） | https://support.huaweicloud.com/api-elb/ | 四层/七层负载均衡服务 |

### 关键发现

1. **华为云DEH（专属主机）**:
   - 用户独享物理主机，云服务器创建在专属主机上
   - 满足隔离性、安全性、性能的更高要求
   - 适用场景: 金融核心系统、政府合规要求、高性能计算
   - 关键特性: 主机自动分配/手动分配、可用区感知、资源池管理

2. **华为云BMS（裸金属服务器）**:
   - 兼具虚拟机弹性和物理机性能的计算类服务
   - 适用场景: 核心数据库、关键应用系统、高性能计算、大数据
   - 关键特性: 物理机级性能、虚拟机级弹性、专属云部署
   - 与DEH的区别: BMS是独立的裸金属服务器，DEH是承载ECS的物理主机

3. **华为云AS（弹性伸缩）**:
   - 根据业务需求和策略自动调整资源
   - 支持定时、周期、告警策略
   - 关键特性: 伸缩组/伸缩配置/伸缩策略/健康检查/冷却时间
   - 适用场景: Web应用弹性伸缩、批处理任务调度、定时扩缩容

4. **华为云ELB（弹性负载均衡）**:
   - 提供四层（TCP/UDP）和七层（HTTP/HTTPS）负载均衡
   - 关键特性: 监听器/后端服务器组/健康检查/会话保持/SSL卸载
   - 适用场景: 高可用Web服务、微服务流量分发、跨可用区容灾

### 对需求的指导

| 场景 | 关键内容方向 |
|------|-------------|
| E1 DEH场景 | 专属主机分配策略、合规隔离最佳实践、资源池管理、性能调优 |
| E2 BMS场景 | 裸金属创建与配置、高性能计算优化、安全加固、与虚拟化对比 |
| E3 AS场景 | 伸缩策略设计、告警阈值配置、冷却时间调优、健康检查机制 |
| E4 ELB场景 | 监听器配置、后端服务器管理、健康检查策略、会话保持配置 |

---

## R3. 可观测性/混沌工程/GitOps/平台工程行业趋势调研

### 调研目标
了解云原生四大热门领域（可观测性、混沌工程、GitOps、平台工程）的最新发展趋势和最佳实践，为20个新场景模板提供权威内容支撑。

### 调研对象

| 领域 | 代表项目/标准 | 成熟度 |
|------|-------------|--------|
| 可观测性 | OpenTelemetry/Jaeger/Prometheus/Grafana | 成熟（CNCF毕业项目） |
| 混沌工程 | Chaos Mesh/Litmus/华为云Chaos | 成长（CNCF孵化项目） |
| GitOps | ArgoCD/Flux/Terraform | 成熟（CNCF毕业项目） |
| 平台工程 | Backstage/Port/Crossplane | 热门（CNCF孵化项目） |

### 关键发现

1. **可观测性趋势**:
   - OpenTelemetry已成为可观测性数据采集的事实标准
   - 三支柱（Metrics/Logs/Traces）整合是行业共识
   - AI应用可观测性是新赛道: LLM调用链追踪、Token消耗监控、幻觉检测
   - SLO/SLI/错误预算框架被广泛采用
   - 华为云APM提供全链路APM能力

2. **混沌工程趋势**:
   - 从Netflix原则演进到云原生生态
   - Chaos Mesh和Litmus是两大主流开源工具
   - 稳态假设（Steady State Hypothesis）是核心方法论
   - 安全护栏（Safety Guardrails）是实践底线
   - 渐进式实验: 从小爆炸半径开始逐步扩大

3. **GitOps趋势**:
   - ArgoCD和Flux是两大主流实现
   - Progressive Delivery（渐进式交付）成为新焦点
   - 与平台工程深度融合
   - 声明式配置+自动同步+漂移检测是三大核心能力
   - Secret管理是痛点，External Secrets Operator是主流方案

4. **平台工程趋势**:
   - 2024-2026最热门云原生趋势
   - Backstage成为IDP（内部开发者平台）的事实标准
   - DORA指标（部署频率/变更前置时间/变更失败率/恢复时间）是平台度量核心
   - 开发者体验（Developer Experience, DevEx）成为关键竞争力
   - 平台可组合性（Composability）是设计原则

5. **LangChain生态洞察**:
   - LangChain已发展为"Agent Engineering Platform"
   - 新推Deep Agents包，支持规划、子代理、文件系统
   - LangSmith提供评估、可观测性和调试能力
   - LangGraph用于构建可控Agent工作流
   - 这为AI应用可观测性场景提供了参考

### 对需求的指导

| 场景组 | 参考项目/标准 | 场景设计方向 |
|--------|-------------|-------------|
| C1 可观测性 | OpenTelemetry/Jaeger/Prometheus/SkyWalking | 链路追踪+指标监控+日志聚合+系统设计+AI应用 |
| C2 混沌工程 | Chaos Mesh/Litmus/华为云Chaos | 基础+网络+资源+依赖+数据层 |
| C3 GitOps | ArgoCD/Flux/Terraform/华为云ROS | 基础+工具+IaC+配置+安全 |
| C4 平台工程 | Backstage/Port/Crossplane | IDP+自助服务+编排+组合+度量 |

---

## 调研总结

| 维度 | 调研次数 | 关键收获 | 需求影响 |
|------|---------|----------|----------|
| 开源Prompt工具 | 4个项目 | A/B测试/模板继承/条件编译的业界实践 | F1/F2/F3功能设计 |
| 华为云服务 | 4个服务 | DEH/BMS/AS/ELB的功能特性和应用场景 | E1-E4赛事场景 |
| 云原生趋势 | 4个领域 | 可观测性/混沌/GitOps/平台工程最新发展 | C1-C4内容场景 |
| **合计** | **3次调研** | **12个对象** | **覆盖5大维度** |
