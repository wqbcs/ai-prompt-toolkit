# PROJECT_WIKI — AI Prompt Toolkit（人看版）

> 生成: R213 现状扫描 (2026-09-30) | AI 消费版见 `project_wiki/ai/`

## 一句话说清这个项目

**ai-prompt-toolkit** = Prompt 工程的 ESLint：零 LLM 调用的静态工具链，覆盖
编写（wizard/模板/条件编译）→ 检查（256 规则 Lint）→ 安全（扫描/消毒/水印）
→ 对抗（23 探针红队/OWASP LLM Top 10）→ 评估（130 维）→ 合规（华为云 7 域/等保 2.0）
→ 分发（73 工具 MCP/CI 门禁/SARIF/VS Code 扩展）的全生命周期。

**定位锚点（每次改动前反问）**:
1. 核心价值 = **零 Token 成本的 Prompt 质量与安全门禁**（CI 可挂、不烧钱、可复现）
2. 差异化 = 全生命周期覆盖 + 中文优先 + 双基线可信度（误报 0.96% / 漏检 9.52% 对称度量）
3. 边界 = 不做动态红队/9 语言 i18n/新第三方依赖（需 LLM 的能力隔离在 extras）

## 数字看板（2026-09-30 实测）

| 指标 | 值 | 趋势 |
|---|---|---|
| 版本 | v67.28.0 (R212) | — |
| Lint 规则 | 256 (196 可自动修复) | +1 (P256) |
| 全局误报率 | **0.96%** (56 样本) | 8.38%→0.96%, 高误报 41→**0** |
| 全局漏检率 | 9.52% (41 golden 探针) | 首版, 4 条=已知否定盲区, 排除后 0% |
| 测试 | 5,737 全绿 | +30 (R212-C) |
| mypy | 0 错误 (棘轮) | 443→0 |
| coverage | 68.49% (fail_under 68) | 待 70+ |

## 目录导航（人从哪里读起）

| 我想… | 读这里 |
|---|---|
| 了解技术栈/模块地图 | `project_wiki/ai/L0_profile.md` |
| 查 CLI/MCP/Python API | `project_wiki/ai/L2_api/README.md` |
| 查数据模型/注册表 | `project_wiki/ai/L2_data/README.md` |
| 查编辑器/报告面 | `project_wiki/ai/L2_components/README.md` |
| 查硬性约束（改动前必看） | `project_wiki/ai/L3_constraints.md` |
| 查已知欠账 | `project_wiki/ai/L3_unknown.md` |
| 查历史决策 | `CHANGELOG.md`（2160 行, 每轮 R 条目含验证数据） |
| 查规则基线 | `docs/规则误报率基线.md` / `docs/规则漏检率基线.md` |
| 查改进方案脉络 | `docs/archive/iterations/70-改进-R70改进清单` → `docs/R190/R202/R207/R212/R213-改进方案与开源调研` |

## 迭代机制（如何推进这个项目）

每轮 R = ①现状扫描（本 wiki + 基线）→ ②改进清单（含定位反问/对抗审查/低价值陷阱识别）
→ ③批次落码（每批: 代码+测试+文档）→ ④全量验证（回归/ruff/mypy/双棘轮）→ ⑤提交
→ 下一轮。工作流 skill: `existing-project-mode`（主流程）+ `wiki-scan`/`memory-recall`
（现状）+ `code-reviewer`/`security-reviewer`（审查）。

## 本轮（R213）已知入口

- 4 条否定盲区修复（否定前缀剥离, 复用 `_strip_negated_data`）→ 漏检棘轮 0.10→0.05
- 仓库卫生: 根目录 30+ 调研文档 + 20+ _iterations_* 归档
- README 数字漂移（255/15+8 过期表述）
- 联网调研竞品现状 → 改进方案 v2（见 R213 方案文档）
