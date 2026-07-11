# 术语表 (Glossary)

> **版本**：v1.1.0  
> **定位**：定义本提示词体系中使用的核心术语，确保跨文档用语一致  
> **适用**：所有项目提示词文档的术语参考  
> **更新**：随提示词体系演进持续补充

---

## 优先级/严重度定义

| 等级 | 标签 | 定义 | 响应要求 |
|------|------|------|----------|
| P0 | 致命/Critical | 导致系统崩溃、数据丢失、安全漏洞、核心功能完全不可用 | 必须立即修复，否则禁止上线 |
| P1 | 严重/Major | 导致核心功能部分不可用、数据错误、性能严重下降 | 上线前 24 小时内必须修复 |
| P2 | 一般/Minor | 导致非核心功能问题、体验严重不佳 | 上线后 1 周内修复 |
| P3 | 轻微/Cosmetic | UI 瑕疵、文案错误、非功能性小问题 | 上线后 1 个月内修复或纳入迭代 |

## AI 模型与提示词工程术语

| 术语 | 说明 | 相关文档 |
|------|------|----------|
| System Prompt | 设定 AI 角色、行为边界和输出格式的顶层指令 | 00 总览附录 B |
| Task Prompt | 描述具体任务场景的提示词，通常包含输入结构和输出模板 | 各文档场景模板 |
| 角色锚定 (Role Anchoring) | 在 System Prompt 中定义 AI 的身份、能力边界和行为规范 | 一、前置身份与能力锚定 |
| Few-shot Prompting | 提供少量输入-输出示例，引导 AI 理解期望的输出格式 | 各文档模板中的输出示例 |
| Chain-of-Thought (CoT) | 引导 AI 分步推理，而非直接给出结论，提高复杂任务准确性 | 04_审查保障中的推理步骤 |
| Prompt 注入 | 通过用户输入诱导 LLM 执行非预期操作或泄露系统提示词 | 12_AI时代开发的四 |
| Token 泄漏 | AI 意外输出 System Prompt 中的敏感信息或指令 | 12_AI时代开发的四.3 |
| 上下文窗口 | LLM 一次能处理的最大 Token 数量，超出部分会被截断 | 12_AI时代开发的六 |
| 幻觉 (Hallucination) | AI 生成看似合理但实际错误的内容 | 12_AI时代开发的三.2 |
| 分步执行 | 将复杂任务拆分为多个独立 Prompt 依次执行，避免上下文窗口溢出 | 00 总览附录 B |

## 文档结构术语

| 术语 | 说明 | 示例 |
|------|------|------|
| System Prompt | 设定 AI 角色、行为边界和输出格式的顶层指令 | 「你是一位 15 年工业级全栈 Bug 猎手…」 |
| Task Prompt | 描述具体任务场景的提示词，通常包含输入结构和输出模板 | 「请对以下功能做全量 Bug 检查：…」 |
| 场景 (Scene) | 文档中定义的某一类具体使用场景 | 01_需求分析中的场景 A「新项目需求调研」 |
| 检查清单 | 可逐项勾选的检查点列表 | 03_编码规范 五、代码质量检查清单 |
| 验收标准 | 判断任务是否完成的检查点集合 | 每个文档末尾的验收标准 |
| 身份定义 | 文档开篇定义 AI 在该任务中扮演的角色 | 各文档「一、身份定义」 |

## 架构设计术语

| 术语 | 说明 |
|------|------|
| 质量属性 (Quality Attributes) | 系统的非功能性特征：可用性、性能、安全性、可维护性、可扩展性、可测试性 |
| 架构模式 | 微服务、单体、事件驱动、CQRS、六边形架构、整洁架构等 |
| C4 模型 | Context→Container→Component→Code 四层架构可视化模型 |
| 技术债 | 为短期速度牺牲长期代码质量的累积代价 |
| ADR | Architecture Decision Record，架构决策记录 |
| 架构漂移 | 实现偏离原始架构设计的现象 |

## 项目管理术语

| 术语 | 说明 |
|------|------|
| PRD | Product Requirements Document，产品需求文档 |
| MVP | Minimum Viable Product，最小可行产品 |
| RACI | Responsible/Accountable/Consulted/Informed，责任分配矩阵 |
| WBS | Work Breakdown Structure，工作分解结构 |
| OKR | Objectives and Key Results，目标和关键结果 |
| NFR | Non-Functional Requirements，非功能性需求 |
| 用户故事 (User Story) | 「作为<角色>，我希望<功能>，以便<价值>」格式的需求描述 |
| 验收条件 (Acceptance Criteria) | 用户故事可被接受的明确条件 |

## 质量保障术语

| 术语 | 说明 |
|------|------|
| 冒烟测试 | Smoke Test，核心功能的快速验证 |
| 回归测试 | Regression Test，修改后验证旧功能未受影响 |
| 集成测试 | Integration Test，验证模块间交互 |
| E2E 测试 | End-to-End Test，端到端全链路测试 |
| 压测 | Stress Test / Load Test，压力测试 |
| 渗透测试 | Penetration Test，安全攻击模拟测试 |
| 金丝雀发布 | Canary Release，小比例灰度发布 |
| 蓝绿部署 | Blue-Green Deployment，零宕机切换部署 |
| TDD | Test-Driven Development，测试驱动开发 |
| 覆盖率 | 代码被测试用例执行到的比例（行/分支/函数覆盖率） |
| 变异测试 (Mutation Testing) | 通过修改代码检查测试能否检测到变更 |

## 运维与可靠性术语

| 术语 | 说明 |
|------|------|
| SLA | Service Level Agreement，服务等级协议 |
| SLO | Service Level Objective，服务等级目标 |
| SLI | Service Level Indicator，服务等级指标 |
| MTTR | Mean Time To Repair，平均修复时间 |
| MTBF | Mean Time Between Failures，平均无故障时间 |
| 可观测性 (Observability) | 通过日志/指标/链路追踪理解系统内部状态的能力 |
| OpenTelemetry | CNCF 可观测性标准，统一 Logs/Metrics/Traces 采集 |

## 安全术语

| 术语 | 说明 |
|------|------|
| XSS | Cross-Site Scripting，跨站脚本攻击 |
| CSRF | Cross-Site Request Forgery，跨站请求伪造 |
| SQL 注入 | SQL Injection，通过输入注入 SQL 语句 |
| SSRF | Server-Side Request Forgery，服务端请求伪造 |
| RCE | Remote Code Execution，远程代码执行 |
| OWASP Top 10 | 开放式 Web 应用安全项目发布的十大安全风险 |
| Prompt 注入 | Prompt Injection，通过输入诱导 LLM 执行非预期操作 |
| 纵深防御 (Defense in Depth) | 多层安全防护策略 |

## 编码与工具术语

| 术语 | 说明 |
|------|------|
| Lint | 静态代码分析，检查代码风格和潜在 Bug |
| Linter | 执行 Lint 的工具（如 ESLint、Pylint、Clippy） |
| Formatter | 自动格式化工具（如 Prettier、Black、rustfmt、gofmt） |
| Pre-commit Hook | 代码提交前自动触发的检查脚本（如 husky、pre-commit） |
| Git Flow | 基于 Git 的分支管理策略 |
| Conventional Commits | 约定式提交，规范化 Commit Message 格式 |
| CI/CD | Continuous Integration / Continuous Deployment，持续集成/持续部署 |

---

*本术语表会随提示词体系演进持续更新。*
