# AI Prompt工具链开源项目调研报告 v1.0

> 调研日期：2026-07-18  
> 调研范围：GitHub开源项目、行业痛点、赛事信息、VSCode插件

---

## 一、AI Prompt工具链相关开源项目（按星数排序）

### 1. prompt-optimizer（提示词优化器）
| 属性 | 详情 |
|------|------|
| **项目名** | prompt-optimizer |
| **GitHub** | https://github.com/linshenkx/prompt-optimizer |
| **星数** | 32.3k |
| **核心功能** | 一键prompt优化、双模式优化（系统/用户prompt）、分析与对比评估、多模型集成（OpenAI/Gemini/DeepSeek/Grok等）、图片生成（T2I/I2I）、模板变量、多轮对话测试、Function Calling支持、Prompt收藏与版本历史、MCP协议支持 |
| **技术栈** | TypeScript、Vue、Next.js、Electron、Chrome Extension |
| **部署方式** | Web应用、桌面应用、Chrome扩展、Docker |
| **与ai-prompt-toolkit差距** | 专注"优化"而非全生命周期管理；缺少linting/security/CI集成；无VSCode插件；纯客户端架构，无服务端协作能力 |

### 2. langfuse（LLM工程平台）
| 属性 | 详情 |
|------|------|
| **项目名** | langfuse |
| **GitHub** | https://github.com/langfuse/langfuse |
| **星数** | 31.3k |
| **核心功能** | LLM应用可观测性（Tracing）、Prompt管理（版本控制/协作迭代）、LLM评估（LLM-as-judge/代码评估器/用户反馈）、数据集管理、LLM Playground、OpenTelemetry集成 |
| **技术栈** | TypeScript、Next.js、ClickHouse、Python SDK、JS/TS SDK |
| **部署方式** | 云服务、自托管（Docker/K8s/Helm） |
| **与ai-prompt-toolkit差距** | 偏重可观测性和评估，非开发者本地工具链；缺少prompt linting/security扫描；无CLI/VSCode集成；企业级平台而非轻量工具包 |

### 3. promptfoo（LLM测试与红队）
| 属性 | 详情 |
|------|------|
| **项目名** | promptfoo |
| **GitHub** | https://github.com/promptfoo/promptfoo |
| **星数** | 23.4k |
| **核心功能** | Prompt/Agent/RAG测试、红队/渗透测试/漏洞扫描、多模型对比（GPT/Claude/Gemini/DeepSeek等）、CI/CD集成、声明式配置、代码扫描、Web查看器 |
| **技术栈** | TypeScript（97.2%）、Node.js、CLI |
| **部署方式** | npm/brew/pip安装，CLI为主 |
| **与ai-prompt-toolkit差距** | 专注测试评估，缺少linting/优化/版本管理/安全防护；无VSCode插件；已被OpenAI收购但保持MIT开源 |

### 4. mlflow（AI工程平台）
| 属性 | 详情 |
|------|------|
| **项目名** | mlflow |
| **GitHub** | https://github.com/mlflow/mlflow |
| **星数** | 27.1k |
| **核心功能** | ML/AI模型调试、评估、监控、优化；Agent管理；LLM评估；可观测性；模型管理 |
| **技术栈** | Python |
| **与ai-prompt-toolkit差距** | 偏重ML全生命周期管理，非prompt专用工具；无prompt linting/security；重量级平台 |

### 5. opik（LLM评估与监控）
| 属性 | 详情 |
|------|------|
| **项目名** | opik |
| **GitHub** | https://github.com/comet-ml/opik |
| **星数** | 20.7k |
| **核心功能** | LLM应用调试/评估/监控、Tracing、自动评估、生产仪表盘、Playground |
| **技术栈** | Python |
| **与ai-prompt-toolkit差距** | 专注可观测性和评估，非prompt工程工具；缺少linting/security |

### 6. LangGPT（结构化提示词框架）
| 属性 | 详情 |
|------|------|
| **项目名** | LangGPT |
| **GitHub** | https://github.com/langgptai/LangGPT |
| **星数** | 12.4k |
| **核心功能** | 结构化提示词范式、元提示词（Meta-Prompt）、提示词模板、提示词方法论 |
| **技术栈** | Jupyter Notebook（教学为主） |
| **与ai-prompt-toolkit差距** | 教学框架而非工具；无CLI/CI/VSCode集成；无linting/testing/security |

### 7. Agenta（LLMOps平台）
| 属性 | 详情 |
|------|------|
| **项目名** | agenta |
| **GitHub** | https://github.com/Agenta-AI/agenta |
| **星数** | 4.3k |
| **核心功能** | Prompt Playground、Prompt管理（版本控制/分支/环境）、LLM评估（20+预置评估器/LLM-as-judge）、LLM可观测性、OpenTelemetry集成 |
| **技术栈** | TypeScript（57.7%）、Python（41.2%）、Docker |
| **与ai-prompt-toolkit差距** | 企业平台而非轻量工具；缺少linting/security扫描；无CLI/VSCode集成 |

### 8. Pezzo（开发者优先LLMOps）
| 属性 | 详情 |
|------|------|
| **项目名** | pezzo |
| **GitHub** | https://github.com/pezzolabs/pezzo |
| **星数** | 3.3k |
| **核心功能** | Prompt设计、版本管理、即时交付、协作、A/B测试、可观测性、成本追踪 |
| **技术栈** | TypeScript、Node.js |
| **与ai-prompt-toolkit差距** | 偏重Prompt管理和协作，缺少linting/security；功能覆盖面较窄 |

### 9. OpenLit（AI工程平台）
| 属性 | 详情 |
|------|------|
| **项目名** | openlit |
| **GitHub** | https://github.com/openlit/openlit |
| **星数** | 2.6k |
| **核心功能** | OpenTelemetry原生LLM可观测性、GPU监控、Guardrails、评估、Prompt管理 |
| **技术栈** | TypeScript、Python、ClickHouse、Grafana |
| **与ai-prompt-toolkit差距** | 偏重可观测性和监控；prompt管理为辅；缺少linting/testing |

### 10. PromptHub（Prompt/Skill/Agent管理工具箱）
| 属性 | 详情 |
|------|------|
| **项目名** | PromptHub |
| **GitHub** | https://github.com/legeling/PromptHub |
| **星数** | 1.5k |
| **核心功能** | Prompt管理（文件夹/标签/收藏/变量/FTS5搜索）、Skill商店与一键分发（15+平台）、Rules管理、AI测试与多模型对比、版本控制与历史、WebDAV同步、备份恢复、MCP管理 |
| **技术栈** | TypeScript、React、Electron、TailwindCSS、SQLite |
| **部署方式** | 桌面应用（macOS/Windows/Linux）、Web自托管 |
| **与ai-prompt-toolkit差距** | 功能最接近的国内项目！缺少linting/security扫描；无CI/CD集成；无CLI工具（虽有CLI但需自编译） |

---

## 二、Prompt Linter开源项目

### 1. lintlang（最顶配的Prompt Linter）
| 属性 | 详情 |
|------|------|
| **项目名** | lintlang |
| **GitHub** | https://github.com/hermes-labs-ai/lintlang |
| **星数** | 49 |
| **核心功能** | AI Agent配置/工具描述/系统Prompt的静态Linter；7个结构化检测器（H1-H7）；零LLM调用；CI集成；JSON输出 |
| **7大检测器** | H1-工具描述模糊性、H2-缺失约束脚手架、H3-Schema-Intent不匹配、H4-上下文边界侵蚀、H5-隐式指令失败、H6-模板格式契约违反、H7-角色混淆 |
| **技术栈** | Python 3.10+，仅依赖pyyaml |
| **性能** | ~2ms/文件，0 LLM调用 |
| **与ai-prompt-toolkit差距** | **核心参考项目！** 可借鉴其7大检测器设计、CI集成模式、verdict-based gating机制 |

### 2. kereva-scanner
| 属性 | 详情 |
|------|------|
| **项目名** | kereva-scanner |
| **GitHub** | https://github.com/kereva-dev/kereva-scanner |
| **星数** | 78 |
| **核心功能** | Prompt和LLM调用问题扫描、安全检查、评估 |
| **技术栈** | Python |

### 3. PromptSage
| 属性 | 详情 |
|------|------|
| **项目名** | promptsage |
| **GitHub** | https://github.com/alexmavr/promptsage |
| **星数** | 24 |
| **核心功能** | LLM Prompt构建器、Linter和消毒器，内置guardrails |
| **技术栈** | Python |

### 4. prompt-template-linter
| 属性 | 详情 |
|------|------|
| **项目名** | prompt-template-linter |
| **GitHub** | https://github.com/0xelitesystem/prompt-template-linter |
| **星数** | 0 |
| **核心功能** | 粘贴Prompt模板获取本地报告：未填充变量、Token/长度估算、标记prompt-injection模式 |
| **技术栈** | HTML |

### 5. skill-anthropic-grade-optimizer
| 属性 | 详情 |
|------|------|
| **项目名** | skill-anthropic-grade-optimizer |
| **GitHub** | https://github.com/l0z4n0-a1/skill-anthropic-grade-optimizer |
| **星数** | 14 |
| **核心功能** | 审计Claude相关制品（CLAUDE.md/SKILL.md等）对照189条Anthropic规则 |
| **技术栈** | Python |

---

## 三、Prompt Security开源项目

### 1. prompt-guard
| 属性 | 详情 |
|------|------|
| **项目名** | prompt-guard |
| **GitHub** | https://github.com/seojoonkim/prompt-guard |
| **星数** | 170 |
| **核心功能** | 高级Prompt注入防御系统、多语言检测、严重性评分、安全审计 |
| **技术栈** | Python |

### 2. agent-security-scanner-mcp
| 属性 | 详情 |
|------|------|
| **项目名** | agent-security-scanner-mcp |
| **GitHub** | https://github.com/sinewaveai/agent-security-scanner-mcp |
| **星数** | 117 |
| **核心功能** | AI编码Agent安全扫描器MCP服务、Prompt注入防火墙、包幻觉检测（4.3M+包）、1000+漏洞检查 |
| **技术栈** | JavaScript |

### 3. ClawdSecbot
| 属性 | 详情 |
|------|------|
| **项目名** | ClawdSecbot |
| **GitHub** | https://github.com/secnova-ai/ClawdSecbot |
| **星数** | 91 |
| **核心功能** | AI Bot安全防护、实时威胁检测、Prompt注入防御 |
| **技术栈** | Go |

### 4. llmtrace
| 属性 | 详情 |
|------|------|
| **项目名** | llmtrace |
| **GitHub** | https://github.com/techlab-innov/llmtrace |
| **星数** | 54 |
| **核心功能** | 零代码LLM安全与可观测性代理、实时Prompt注入检测、PII扫描、成本控制 |
| **技术栈** | Python、Rust |

### 5. AegisGate
| 属性 | 详情 |
|------|------|
| **项目名** | AegisGate |
| **GitHub** | https://github.com/ax128/AegisGate |
| **星数** | 50 |
| **核心功能** | LLM API开源安全网关、Prompt注入检测、PII脱敏、危险响应净化、审计日志 |
| **技术栈** | Python |

### 6. whitney
| 属性 | 详情 |
|------|------|
| **项目名** | whitney |
| **GitHub** | https://github.com/transilienceai/whitney |
| **星数** | 32 |
| **核心功能** | 开源静态AI安全扫描器、15种源类型的Prompt注入检测、LLM-as-judge破损检测、AI依赖SBOM |
| **技术栈** | Python |

### 7. pytector
| 属性 | 详情 |
|------|------|
| **项目名** | pytector |
| **GitHub** | https://github.com/MaxMLang/pytector |
| **星数** | 45 |
| **核心功能** | LLM Prompt注入检测与输入消毒、支持本地模型和API模型 |
| **技术栈** | Python |

### 8. augustus
| 属性 | 详情 |
|------|------|
| **项目名** | augustus |
| **GitHub** | https://github.com/praetorian-inc/augustus |
| **星数** | 258 |
| **核心功能** | LLM安全测试框架、190+探测、28种Provider、单Go二进制 |
| **技术栈** | Go |

### 9. LLMMap
| 属性 | 详情 |
|------|------|
| **项目名** | LLMMap |
| **GitHub** | https://github.com/Hellsender01/LLMMap |
| **星数** | 201 |
| **核心功能** | 自动化Prompt注入测试框架、双LLM架构 |
| **技术栈** | Python |

---

## 四、Prompt A/B Testing开源项目

> **重要发现**：Prompt A/B Testing是一个非常空白的市场！搜索结果仅12个仓库，绝大多数星数为0-2。

### 现有项目（均非常早期）
| 项目名 | GitHub | 星数 | 说明 |
|--------|--------|------|------|
| llm-ab | https://github.com/Mattbusel/llm-ab | 2 | C++单头文件A/B测试框架 |
| llm-ab-tester | https://github.com/stef41/llm-ab-tester | 1 | JS/TS A/B测试框架含统计 |
| llm-ab-test | https://github.com/stef41/llm-ab-test | 1 | Python A/B测试框架含统计分析 |
| ab_explorer | https://github.com/Kos-M/ab_explorer | 1 | 遗传算法A/B测试prompt进化 |
| prompt-ab-testing-platform | https://github.com/gtamizhs14/prompt-ab-testing-platform | 0 | 生产级Prompt版本+AB测试平台 |

**关键结论**：Prompt A/B Testing是**蓝海赛道**，目前没有成熟的开源方案。Langfuse/Agenta等平台的评估功能可部分覆盖，但缺乏专门的A/B测试统计显著性分析工具。

---

## 五、Prompt版本管理开源项目

### 1. PromptHub（中国团队）
| 详情见上方第一部分 |
|------|
| 唯一一个实现完整Prompt版本管理（自动历史、差异对比、一键回滚）的开源桌面工具 |

### 2. Langfuse
| 详情见上方第一部分 |
|------|
| 服务端Prompt版本管理，支持协作迭代，强缓存 |

### 3. Pezzo
| 详情见上方第一部分 |
|------|
| 开发者优先的Prompt版本管理和即时交付 |

### 4. Agenta
| 详情见上方第一部分 |
|------|
| Prompt版本控制+分支+环境 |

**关键结论**：Prompt版本管理仍以服务端平台（Langfuse/Agenta）为主，本地优先+轻量化的方案只有PromptHub。没有类似Git的Prompt专用版本管理CLI工具。

---

## 六、VSCode Prompt插件

> **重要发现**：这是一个极度空白的市场！

### 现有插件
| 项目名 | GitHub | 星数 | 说明 |
|--------|--------|------|------|
| vscode-gpt-kit | https://github.com/rwsci/vscode-gpt-kit | 0 | VS Code extension toolkit for GPT prompt files (.gpt, .prompt, .gptx) |
| copy-for-ai-vscode-extension | https://github.com/sadolano/copy-for-ai-vscode-extension | 0 | "Copy for AI"右键菜单 |

**关键结论**：VSCode Prompt编辑/lint插件市场几乎为**零**！这是一个重大机会窗口。

---

## 七、Prompt Engineering行业痛点

### 综合分析（来自Medium/Dev.to/知乎/掘金/CSDN等）

1. **Prompt质量无法量化**：写完prompt不知道好不好，只能靠"感觉"和反复试错
2. **Prompt版本管理混乱**：prompt散落在代码、文档、聊天记录各处，没有统一管理
3. **Prompt安全风险**：prompt injection攻击频发，但缺乏系统性防护工具
4. **Prompt测试成本高**：每次修改prompt都需要大量人工测试，缺乏自动化回归
5. **跨模型兼容性差**：同一个prompt在不同模型表现差异大，但缺乏对比工具
6. **团队协作困难**：非技术人员（PM/业务专家）难以参与prompt优化
7. **Prompt Drift**：生产环境中prompt被悄悄修改，缺乏变更追踪
8. **缺乏CI/CD集成**：prompt变更无法像代码一样走CI/CD流程
9. **Token成本不可控**：优化prompt对token消耗的影响缺乏评估
10. **中文生态缺失**：绝大多数工具只支持英文，中文prompt工程工具几乎空白

### 用户最迫切的需求（按优先级）
1. 一键检测prompt质量（类似ESLint for Prompt）
2. Prompt安全扫描（检测injection风险）
3. 自动化A/B测试（统计显著性）
4. 版本管理+diff对比+回滚
5. VSCode内编辑+实时lint
6. 多模型对比测试
7. CI/CD集成

---

## 八、赛事贴合分析

### OSC 2026 开源大赛 / MoonBit开源大赛

> 注：具体赛事信息因搜索限制未能完整获取，以下基于已知信息整理

**已知赛事特征**：
- 面向中国开源生态
- MoonBit国产编程语言生态
- 评分标准通常包括：创新性、实用性、代码质量、社区活跃度、文档完整度

**ai-prompt-toolkit参赛优势**：
1. **创新性高**：目前没有"Prompt工具链全生命周期"的开源项目，大多数只覆盖单一环节
2. **痛点明确**：Prompt Linter + Security Scanner + A/B Testing 三大空白赛道
3. **VSCode插件**：几乎零竞争的蓝海
4. **国产生态**：中文优先、适配国内LLM（DeepSeek/通义千问/智谱等）
5. **可演示性强**：CLI + VSCode插件 + Web Dashboard 三端可展示

**建议差异化方向**：
- 以MoonBit重写核心引擎（如果参赛要求MoonBit生态）
- 强调"零LLM调用"的静态分析能力（对标lintlang）
- 强调中文prompt特有检测规则（中文分词、文化敏感词等）

---

## 九、关键结论与行动建议

### 市场空白（ai-prompt-toolkit的机会）

| 功能领域 | 竞争程度 | 代表项目 | 机会评级 |
|----------|----------|----------|----------|
| Prompt Linter | ⭐ 极低 | lintlang(49⭐) | 🔴 蓝海 |
| Prompt Security | ⭐ 低 | prompt-guard(170⭐) | 🟠 早期 |
| Prompt A/B Testing | ⭐ 极低 | 无成熟方案 | 🔴 蓝海 |
| Prompt版本管理(本地) | ⭐⭐ 低 | PromptHub(1.5k⭐) | 🟠 早期 |
| VSCode Prompt插件 | ⭐ 极低 | 几乎为零 | 🔴 蓝海 |
| Prompt全生命周期工具链 | ⭐ 极低 | 无 | 🔴 蓝海 |
| Prompt优化 | ⭐⭐⭐⭐ 高 | prompt-optimizer(32.3k⭐) | 🟡 红海 |
| LLM评估/可观测性 | ⭐⭐⭐⭐⭐ 高 | langfuse(31.3k⭐) | 🟡 红海 |

### 核心参考项目排序

1. **lintlang** - Prompt Linter设计最佳参考（7大检测器、零LLM、CI集成）
2. **promptfoo** - 测试框架架构参考（声明式配置、CLI、CI/CD）
3. **prompt-guard** - Security检测规则参考
4. **PromptHub** - 本地优先架构参考（Electron+SQLite）
5. **langfuse** - Prompt管理+评估平台架构参考

### 建议ai-prompt-toolkit功能优先级

1. **P0（核心差异化）**：Prompt Linter（参考lintlang的7大检测器，扩展中文特有规则）
2. **P0（核心差异化）**：Prompt Security Scanner（参考prompt-guard，增加中文injection模式）
3. **P1（高价值）**：VSCode扩展（实时lint、语法高亮、快捷操作）
4. **P1（高价值）**：CLI工具（CI/CD集成，参考promptfoo的声明式配置）
5. **P2（完善生态）**：Prompt A/B Testing（统计显著性、LLM-as-judge）
6. **P2（完善生态）**：Prompt版本管理（本地Git-like，diff+回滚）
7. **P3（增强体验）**：Web Dashboard（可视化结果、团队协作）

---

*报告结束*
