# PROJECT_WIKI — AI Prompt Toolkit（人看版）

> 更新: R310 wiki 全量重扫 (2026-10-16) | 首版: R213 | AI 消费版见 `project_wiki/ai/`

## 一句话说清这个项目

**ai-prompt-toolkit** = Prompt 工程的 ESLint：零 LLM 调用的静态工具链，覆盖
编写（wizard/模板/条件编译）→ 检查（268 规则 Lint）→ 安全（扫描/注入检测/消毒/水印）
→ 对抗（23 探针×173 payload 红队 / 11 检测器 / OWASP LLM Top 10）→ 评估（130 维）
→ 合规（华为云 7 域/等保 2.0）→ 分发（73 工具 MCP / 35 HTTP 路由 Playground / CI 门禁 /
SARIF / VS Code 扩展 / Docker ghcr）的全生命周期。

**定位锚点（每次改动前反问）**:
1. 核心价值 = **零 Token 成本的 Prompt 质量与安全门禁**（CI 可挂、不烧钱、可复现、逐字节一致、离线可跑）
2. 差异化 = 全生命周期覆盖 + 中文优先 + 双基线可信度（误报 0.82% / 漏检 0.00% @379 单元，对称度量）
3. 边界 = 不做动态红队/9 语言 i18n/core 新第三方依赖（需 LLM 的能力隔离在 extras）

## 数字看板（2026-10-16 实测）

| 指标 | 值 | 趋势 (R213→R310) |
|---|---|---|
| 版本 | v67.34.96 | v67.28.0 → |
| Lint 规则 | 268 (P001-P268, 196 可自动修复) | 256 → 268 |
| 全局误报率 | **0.82%** (60 样本, 棘轮阈值 0.01) | 0.96% → |
| 全局漏检率 | **0.00%** (379 单元, 棘轮阈值 0.05) | 9.52% (41 探针) → |
| golden 探针 | 667 (zh-Hans 544 / en 103 / ja 18 / zh-Hant 2) | 113 → 667 |
| 测试 | 6,689 全绿 | 5,737 → |
| mypy | 基线 0/0 + strict 286/286 (100%) | 0/0 → +strict 全量收口 (R300) |
| coverage | 75.67% (fail_under 75 锁定) | 68.49% → 75 |
| MCP 工具 | 73 (测试断言) | 73 → 73 |
| HTTP 端点 | 37 (Playground 17 API+WS+首页 / Market 9 / Dataset 9) | 9 (仅 market) → 37 |
| CI workflow | 7 (release-gate 发布硬闸, R306) | 11 → 7 (重构合并) |
| 收口门禁 | release_gate.py 29 步链 | — → R306 定型 |

## 目录导航（人从哪里读起）

| 我想… | 读这里 |
|---|---|
| 了解技术栈/模块地图/棘轮 | `project_wiki/ai/L0_profile.md` |
| 查 CLI (73 命令) / MCP (73 工具) / HTTP (35 路由) / Python API | `project_wiki/ai/L2_api/README.md` |
| 查数据模型/注册表/持久化面/生产者消费者 | `project_wiki/ai/L2_data/README.md` |
| 查前端面 (Playground SPA/落地页/VS Code 扩展) / 终端 UI / 报告产物 | `project_wiki/ai/L2_components/README.md` |
| 查硬性约束（改动前必看） | `project_wiki/ai/L3_constraints.md` |
| 查已知欠账/开放项 | `project_wiki/ai/L3_unknown.md` |
| 查历史决策 | `CHANGELOG.md`（每轮 R 条目含验证数据） |
| 查任务总板（权威状态） | `docs/planning/02_任务总板.md`（114 行, /board 命令可一键查漂移） |
| 查规则基线 | `docs/规则误报率基线.md` / `docs/规则漏检率基线.md` |
| 查规则清单 | `docs/rules.md` + `docs/rules/P*.md`（gen_rules_doc 生成, 勿手改） |

## 迭代机制（如何推进这个项目）

每轮 R = ①现状扫描（本 wiki + 双基线 + /board）→ ②改进清单（含定位反问/对抗审查/
低价值陷阱识别）→ ③批次落码（代码+测试+文档, 新规则探针先行 TP+TN 各≥2）→ ④全量验证
（release_gate.py 29 步链）→ ⑤收口（round-close skill: **CHANGELOG 段先行于门禁** →
升版三处+徽章 → gen_rules_doc → 板回写带可验证引用 → 00 交接 → commit trailer → push）
→ 下一轮。

工作流 skill: `existing-project-mode`（主流程）+ `wiki-scan`/`memory-recall`（现状）
+ `code-reviewer`/`security-reviewer`（审查）+ `round-close`（收口）+ `gen-test`（测试约定）。

## R310 重扫发现（本轮）

- wiki 7 文件全量刷新（R213→R310, 16 天/约 30 轮变更）, 全部数字对盘真源
  （CLI --help 契约 / dataclasses 运行时内省 / 路由装饰器 grep / 注册表实载）
- **漂移发现**: README:375 目录树注释 "fixer.py # 自动修复(71条AUTO_FIXABLE)" 陈旧
  （真源 `fixer.AUTO_FIXABLE_RULES`=196）→ 登记 L3_unknown #1, 下一轮一行修复
- 旧 wiki 内部不一致修正: L0 "56 干净样本" vs L2_data "60"（统一 60）; MCP 工具历史记忆
  "53" vs 测试断言 73（统一 73, 以测试为准）
- 退出码契约补全: 0=PASS / 1=WARN / 2=FAIL / **3=执行错误**（R213 版缺 3, R306 已修真源,
  本 wiki 同步）
- 路由面补全: Playground 自持实为 17 API + SPA 首页 + /ws/compile（R308 测试面只覆盖 13）→ R311 补齐:
  scorecard/engine/badge/eval-compare 4 路由 + SPA 首页 8 TestClient 测试（test_r311, hermetic; WS 不入
  套件 — [dev] 未钉版 websockets, R223 纪律）, 余 /ws/compile 真实会话并入 L3_unknown Playwright 面
