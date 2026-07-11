# 术语关系图谱数据 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **来源**：从_glossary.md提取+人工补充关系

---

## 一、术语节点

### 1.1 提示词工程术语

| ID | 术语 | 英文 | 类别 | 定义来源 |
|----|------|------|------|----------|
| T001 | 系统提示词 | System Prompt | 提示词工程 | _glossary.md |
| T002 | 任务提示词 | Task Prompt | 提示词工程 | _glossary.md |
| T003 | 角色锚定 | Role Anchoring | 提示词工程 | _glossary.md |
| T004 | 少样本提示 | Few-shot Prompting | 提示词工程 | _glossary.md |
| T005 | 思维链 | Chain-of-Thought | 提示词工程 | _glossary.md |
| T006 | 提示注入 | Prompt Injection | 安全 | _glossary.md |
| T007 | Token泄漏 | Token Leakage | 安全 | _glossary.md |
| T008 | 上下文窗口 | Context Window | 提示词工程 | _glossary.md |
| T009 | 幻觉 | Hallucination | 安全 | _glossary.md |
| T010 | 分步执行 | Step-by-step Execution | 提示词工程 | _glossary.md |
| T011 | 自纠错 | Self-Correction | 提示词工程 | v5.0新增 |
| T012 | 程序思维 | Program-of-Thought | 提示词工程 | v5.0新增 |
| T013 | 主动提示 | Active-Prompt | 提示词工程 | v5.0新增 |
| T014 | Agent优先 | Agent-First | 提示词工程 | v5.0新增 |

### 1.2 架构设计术语

| ID | 术语 | 英文 | 类别 | 定义来源 |
|----|------|------|------|----------|
| T015 | 质量属性 | Quality Attributes | 架构 | _glossary.md |
| T016 | 架构模式 | Architecture Pattern | 架构 | _glossary.md |
| T017 | C4模型 | C4 Model | 架构 | _glossary.md |
| T018 | 技术债 | Technical Debt | 架构 | _glossary.md |
| T019 | 架构决策记录 | ADR | 架构 | _glossary.md |
| T020 | 架构漂移 | Architecture Drift | 架构 | _glossary.md |

### 1.3 安全防御术语(v6.0新增)

| ID | 术语 | 英文 | 类别 | 定义来源 |
|----|------|------|------|----------|
| T021 | 直接注入 | Direct Injection | 安全 | v6.0新增 |
| T022 | 间接注入 | Indirect Injection | 安全 | v6.0新增 |
| T023 | 多轮注入 | Multi-turn Injection | 安全 | v6.0新增 |
| T024 | 角色劫持 | Role Hijacking | 安全 | v6.0新增 |
| T025 | 数据投毒 | Data Poisoning | 安全 | v6.0新增 |
| T026 | 事实锚定 | Fact Anchoring | 防御 | v6.0新增 |
| T027 | 引用要求 | Citation Requirement | 防御 | v6.0新增 |
| T028 | 置信度标注 | Confidence Annotation | 防御 | v6.0新增 |
| T029 | 自洽性校验 | Consistency Check | 防御 | v6.0新增 |

### 1.4 互操作术语(v6.0新增)

| ID | 术语 | 英文 | 类别 | 定义来源 |
|----|------|------|------|----------|
| T030 | 场景互操作性 | Scenario Interoperability | 互操作 | v6.0新增 |
| T031 | 上下文传递 | Context Passing | 互操作 | v6.0新增 |
| T032 | 零损耗协议 | Zero-Loss Protocol | 互操作 | v6.0新增 |
| T033 | 断点续传 | Checkpoint Resume | 互操作 | v6.0新增 |
| T034 | 接口契约 | Interface Contract | 互操作 | v6.0新增 |
| T035 | 生态开放度 | Ecosystem Openness | 生态 | v6.0新增 |
| T036 | 知识图谱 | Knowledge Graph | 元数据 | v6.0新增 |
| T037 | 场景推荐 | Scenario Recommendation | 元数据 | v6.0新增 |

---

## 二、术语关系

### 2.1 同义关系(SYNONYM)

| 术语A | 术语B | 说明 |
|-------|-------|------|
| T001 | 系统提示词 | System Prompt的中文名 |
| T005 | 思维链 | Chain-of-Thought的中文名 |
| T019 | 架构决策记录 | ADR的全称 |

### 2.2 依赖关系(DEPENDS_ON)

| 源术语 | 目标术语 | 说明 |
|--------|----------|------|
| T002 | T001 | Task Prompt依赖System Prompt设定角色 |
| T003 | T001 | 角色锚定在System Prompt中实现 |
| T011 | T005 | Self-Correction依赖CoT推理链 |
| T012 | T005 | PoT依赖CoT进行程序化推理 |
| T022 | T006 | 间接注入是Prompt注入的子类 |
| T023 | T006 | 多轮注入是Prompt注入的子类 |
| T033 | T032 | 断点续传依赖零损耗协议 |
| T034 | T030 | 接口契约是互操作性的实现方式 |

### 2.3 包含关系(CONTAINS)

| 父术语 | 子术语 | 说明 |
|--------|--------|------|
| T006 | T021 | Prompt注入包含直接注入 |
| T006 | T022 | Prompt注入包含间接注入 |
| T006 | T023 | Prompt注入包含多轮注入 |
| T006 | T024 | Prompt注入包含角色劫持 |
| T006 | T025 | Prompt注入包含数据投毒 |
| T030 | T031 | 互操作性包含上下文传递 |
| T030 | T034 | 互操作性包含接口契约 |
| T030 | T032 | 互操作性包含零损耗协议 |
| T015 | T016 | 质量属性驱动架构模式选择 |

### 2.4 冲突关系(CONFLICTS)

| 术语A | 术语B | 说明 | 化解策略 |
|-------|-------|------|----------|
| 敏捷发布 | 变更冻结 | 敏捷要求快速发布，冻结阻止变更 | 发布窗口期冻结，非窗口期敏捷 |
| 强类型 | 动态类型 | 类型安全vs灵活性 | 关键路径强类型，非关键动态 |

---

## 三、文档依赖矩阵

| 文档 | 引用文档 | 被引用文档 | 依赖类型 |
|------|----------|-----------|----------|
| 01 | - | 02,11 | 被依赖(源头) |
| 02 | 01 | 03,06,10 | 上下游(枢纽) |
| 03 | 02 | 04,05 | 上下游 |
| 04 | 02,03 | 05,08 | 上下游 |
| 05 | 03,04 | 06 | 上下游 |
| 06 | 02,05 | 07,08 | 上下游 |
| 07 | 06 | 08,09,12 | 上下游 |
| 08 | 06,07 | 09,12 | 上下游 |
| 09 | 07,08 | 07 | 上下游(循环) |
| 10 | 02 | 11 | 下游 |
| 11 | 01,10 | - | 终端 |
| 12 | 07,08 | - | 终端 |
