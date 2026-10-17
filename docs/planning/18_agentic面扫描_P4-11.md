# 18. agentic 面扫描设计（P4-11, 0 代码设计先行）

> R314 落盘（2026-10-16）。同 P4-06 路线文档先例：设计先行，实施在发布后
>（02 总板 P4-11 行；T6 发布窗口纪律：窗口期不开新目标类型）。

## 1. 背景与裁定依据（R312 调研证据）

2026 攻击主线从单文档 prompt 转向 agent 配置面：

| 证据 | 事实 |
|---|---|
| arXiv 2607.05744 | MCP 工具元数据投毒 8 技术中 **仅 TAG 块同时击穿 sanitizer+人工审批**（P269 已覆盖载体轴） |
| CSA Research Note（wunderwuzzi 2026-02） | **生产利用**: Claude Code/Copilot/Codex Skills/Gemini CLI 执行技能文件内 tag 块隐蔽 shell 指令；明示"标准工具链不覆盖技能文件/MCP 清单面" |
| ipi-check（MIT） | agent 指令文件面（AGENTS.md/CLAUDE.md/SKILL.md）IPI 静态扫描 + 技能安全审计（IPI401-411）; 字节轴/regex轴/语义轴三层 |
| nox | OWASP MCP Top 10 映射（我方映射面扩展=A2 项） |

本项目的 P260-P269 编码/注入族已覆盖**载体轴与模式轴**（P269 本轮刚落,
独立真实源 ≥4）——缺的是**目标类型**：这些规则只跑在 prompt 文本上，不跑在
MCP 清单/技能文件/指令文件上。本设计=同一规则引擎扩目标类型，非新引擎。

## 2. 目标类型（3 个, 按攻击证据强度排序）

| # | 目标 | 形态 | 解析要求 |
|---|---|---|---|
| T1 | **MCP manifest JSON**（server 配置/工具定义） | JSON: `tools[].name/description/inputSchema` + server 元数据 | 宽容解析（各 server schema 异质; 未知字段透传不报错; 解析失败=结构 finding 而非崩溃） |
| T2 | **SKILL.md**（agent 技能文件） | Markdown: frontmatter（name/description, 各平台方言）+ 正文指令 | frontmatter 容错（Claude Code/Codex/Gemini CLI 方言差异; 缺 frontmatter=按纯 markdown 处理） |
| T3 | **指令文件**（AGENTS.md/CLAUDE.md/.atomcode.md 类） | Markdown 正文 | 纯 markdown; 与 T2 同处理管线 |

**扫描单位**: 每个目标类型产出 per-field 文本切片（如 T1 每个 tool.description
= 一个扫描单元; T2/T3 = 全文+frontmatter 分片）, 复用 `lint_text()` 内核
（fuzz 面已验证的确定性入口, R304）。

## 3. 探测轴（ipi-check 三层参照 × 本项目既有资产映射）

| 轴 | 内容 | 本项目既有资产（复用, 零新代码） | 缺口 |
|---|---|---|---|
| 字节轴 | 不可见/载体字符 | **P260/P261**（零宽族）/ **P268**（全角 bypass）/ **P269**（tag 块）— 编码逃逸族完整 | 变体选择符 U+FE00–FE0F（P269 诚实残留已登记, 证据驱动） |
| regex 轴 | 注入模式 | 注入族 INJ-001~019/INJ-ZH-001~018 + **P178 逃生舱**（R288, 引用语境两级门禁） | MCP 描述/技能文件语境的 TP 探针（探针先行, 见 §4） |
| 语义轴 | 结构启发式（IPI 专属） | 无（新面） | 见 §4 候选规则（全部证据驱动, 不预支） |

**关键设计**: 语义轴不在本设计内预设规则集——T1 规则纪律（≥2 独立真实 TP +
逃生舱风险评估 + 双基线不回归）对 agentic 面同等适用, 每条候选规则单独取证
单独探针, 无证据不立规则。

## 4. 候选规则（登记, 不预支 — 各自 T1 证据门槛）

| 候选 | 面 | 证据需求（立规前） |
|---|---|---|
| **P270 技能文件 shell 指令嵌入**（T2: frontmatter/正文中 cp/mv/rm/curl/wget 形态的指令句） | 语义轴 | ≥2 独立真实案例（wunderwuzzi 生产利用是第 1 源, 需第 2 独立源）+ 良性 TN（合法运维文档技能）取证 + 60 干净集零新增 FP 验证 |
| **P271 MCP 工具描述指令覆盖**（T1: description 中 "always/never/you must" 类对调用方 agent 的指令句） | 语义轴 | ≥2 独立真实案例 + 良性 TN（正常工具说明含 must/should 的工程文档形态）取证 |
| 变体选择符族（字节轴补全） | 字节轴 | 真实攻击证据（当前 emoji 合法面 FP 未验证, 同 P261 ZWJ/BOM 排除先例） |

## 5. 方法论借鉴（不重复造轮子）

- **Whitney**: fixture + YAML 溯源——golden 探针 `note` 字段先例已等价, 新目标
  类型的探针沿用（每条带独立信源+轮次+场景）
- **ipi-check**: 三层轴划分=本设计 §3 骨架; 其 IPI401-411 编号面**不引入**
  （自有 P 编号体系单一, 编号体系不双轨）
- **A3 外部语料**（Garak/PINT 子集接入 golden, R313 清单 P1 项）: agentic 面
  新探针的语料来源候选, 逐条 license/provenance 审查纪律前置

## 6. 分期（实施排期, 发布后）

| 期 | 范围 | 依赖 | 新规则 |
|---|---|---|---|
| **Phase 1** | T1 MCP manifest JSON 目标类型（宽容解析+per-field 切片+既有 269 规则全量适用） | 发布后; 0 新规则=纯目标扩展 | 0（复用） |
| **Phase 2** | T2 SKILL.md + T3 指令文件目标类型 | Phase 1 管线 | P270/P271（若取证达标） |
| Phase 3（远期占位） | MCP Top 10 映射扩展（A2 项, 合规报告面）+ agentic 面 SARIF 输出 | Phase 1-2 | 0 |

**Phase 1 验收（DoD）**: ① 现有 mcp-lint（MCP-101~112 配置级）与新内容级
扫描的关系面文档化（配置级 vs 内容级, 两命令协同）② ≥2 个真实 MCP server
配置文件实跑（fixture 入 golden）③ 双基线不回归 ④ 确定性双跑逐字节。

## 7. 非目标（显式边界）

- **运行时行为**（rug pull 定义漂移）: 已有 mcp-lint MCP-112 配置级 baseline
  检测, 不重做
- **多 agent 信任边界**（llmpromptdefender 面）: 代码级面, 与 prompt 内容面不相交
- **ML 语义层**: 楔子互斥（R313 陷阱审计 A7 裁定）
- **npm/Web 端**: ICP 门控不变（D5 裁定）

## 8. 风险与残留

| 风险 | 缓解 |
|---|---|
| JSON schema 异质（各 MCP server 非统一） | 宽容解析+未知字段透传; 解析失败=结构 finding（P031 族）不崩溃 |
| 技能文件 frontmatter 方言漂移（各 agent 平台演进快） | 缺 frontmatter 降级纯 markdown; 方言差异登记不硬编码 |
| 新目标类型的 FP 面未知（工具描述天然含指令性语言） | 60 干净集扩展（agentic 面干净样本）+ P178 逃生舱语境机制复用 + 双基线棘轮 |
