# L0 技术画像（ai-prompt-toolkit）

> 更新: R310 wiki 全量重扫 (2026-10-16) | 首版: R213 (2026-09-30)
> 事实来源: pyproject.toml / 代码运行时提取 / CLI --help 契约 / 门禁链实跑

## 运行时与依赖

- Python ≥3.10 (CI matrix 3.10/3.12, mypy target 3.10)
- **核心依赖仅 7 个**: click<9 / rich<16 / pyyaml<7 / jsonschema<5 / cachetools<8 /
  jinja2<4 (R225 eval-matrix HTML 渲染器) / tomli<3 (仅 py<3.11 回退)
- 可选 extras (R306 剔除 scipy/numpy——全 src/ 零 import 的死重依赖):
  - `dev`: pytest/pytest-cov/pytest-asyncio, ruff==0.16.10, mypy==2.1.0,
    redoctor==0.1.5 (ReDoS 审计), hypothesis (属性测试), fastapi, httpx (版本钉死=环境一致性硬门禁)
  - `ab_test`: httpx (A/B 真实依赖)
  - `lsp`: pygls, lsprotocol (LSP Server)
  - `full`: httpx, fastapi, uvicorn (Playground/市场 REST API)
- 构建: setuptools PEP 517 (不声明已弃用的 wheel 包, R222), src 布局;
  package-data 含 py.typed + data/*.json + clean_prompts + external_bench +
  templates/*.md + playground/static/*.html (pip 安装后运行时资产完整: R222/R224/R249)
- 入口: `prompt-cli` / `prompt` → `cli_core:main`; `python -m ai_prompt_toolkit`

## 规模（2026-10-16 实测）

| 指标 | R213 (2026-09-30) | R310 (2026-10-16) |
|---|---|---|
| src .py 文件 / LOC | 264 / 68,176 | 285 / 74,486 |
| tests .py 文件 / LOC | 209 / 32,855 | 269 / 42,368 |
| 测试用例 | 5,737 | 6,689 (全绿) |
| Lint 规则 | 256 (P001-P256) | 268 (P001-P268) |
| 可自动修复规则 | 196 | 196 (`linter/fixer.py` AUTO_FIXABLE_RULES 单一真源) |
| 评估维度 | 130 | 130 (D01-D130, 6 大类, 行业权重预设 7 种) |
| MCP 工具 | 73 | 73 (测试断言: test_mcp_server assert len(tools)==73) |
| 探针统一视图 | 116 | 116 (`get_global_probe_registry()`) |
| 红队探针框架 / 检测器 | 23 / 11 | 23 探针 / 173 payload / 11 检测器 |
| golden 攻击探针 | 113 | 667 (zh-Hans 544 / en 103 / ja 18 / zh-Hant 2; 379 期望命中单元) |
| 干净样本 | 56→60 | 60 (误报基线分母) |
| LLM Provider | 24 | 26 模块 (对外 25-provider 口径以 docs/provider-matrix.md 为准) |
| CI workflow | 11 | 7: prompt-ci / prompt-pr-gate / release (R306 +release-gate 作业) / owasp-llm-scan / codeql / daily-scorecard / ci-green-streak |
| 版本 | v67.28.0 | v67.34.96 |

> R319 delta (2026-10-17, R310 快照列不覆写): Lint 规则 268→269（P269 混排
> 子模式）/ golden 探针 667→686（zh-Hans 550/en 116/ja 18/zh-Hant 2; 384 单元）/
> 测试用例 6,689→6,762 / CI 7 作业（R319 新增 release-test: 发布链补 pytest）/
> 误报实际 0.82%→0.81% / 版本 v67.34.96→v67.34.105。

## 质量门禁棘轮（只收紧不放松）

| 棘轮 | 当前值 | 挂载 |
|---|---|---|
| mypy 基线 | 0 / 0 | release_gate + CI |
| mypy strict 注册表 | 286/286 (100%, R300 收口) | check_mypy_ratchet S1-S4 + `--update-strict` 唯一变更路径 |
| 误报率 | 阈值 0.01 (实际 0.81%, 60 样本) | check_false_positives --fail-above 0.01 |
| 漏检率 | 阈值 0.05 (实际 0.00%, 384/384 单元) | check_miss_rate --fail-above 0.05 |
| coverage | fail_under 75 (R216 实测 75.67% 锁定) | pyproject |
| 版本一致性 | pyproject / __init__ / README 徽章 / CHANGELOG 最新条目 | check_version_consistency |
| 环境一致性 | ruff 0.16.10 / mypy 2.1.0 / redoctor 0.1.5 钉版 | check_env_parity (漂移硬红) |
| 板 vs 代码 | 5 机器检查 (sha/CHANGELOG/规则引用/自相矛盾) | check_board_status (R243 脚本化, R294 补 check 4/5) |
| 分层 | L1 rules→io/adapters 禁入表 + L2 kernel 纯度 | check_layering (R254) |
| 性能楔子 | <100ms/文件 | check_lint_performance |
| 收口链 | release_gate.py 29 步 (CI 本地 `--skip 1,2`=27 步) | scripts/release_gate.py |
| 发布硬闸 | release-gate 作业 (门禁链 + tag↔pyproject 版本断言, R306) | .github/workflows/release.yml |

## 模块地图（src/ai_prompt_toolkit/, 2026-10-16）

| 层 | 模块 | 职责 |
|---|---|---|
| CLI | cli_core.py, cli/commands/ (10 簇文件: abtest/compile/dataset/dev/eval/lint/plugin/redteam/security/template) | 73 顶级命令 + 2 命令组 (dataset/plugin); 退出码 0/1/2/3 契约 |
| Lint 内核 | linter/ (80 文件: rules + rules_pXXX.py 族 + fixer/fix_suggestions/rule_explainer + baseline + token_analyzer + sarif + lcov_export + lsp_server) | 静态规则引擎, 零 LLM 调用, mypy strict 锁定 |
| 安全 | security/ (20 模块: injection_detector/zh_injection_rules/pii_detector/supply_chain_detector/unicode_guard/mcp_config_scanner/output_scanners/defender/engine/scanner/scorer/prompt_scorecard/health_score/huaweicloud_compliance/structural_analyzer/inheritance_auditor/anomaly_detector/finding_enhancer/badge/types) | 五维评分卡 + 四维健康分 + 注入/PII/供应链/MCP 配置检测 |
| 红队 | redteam/ (21), probe_framework.py, adversarial.py, attack_vault.py | 23 探针/173 payload/11 检测器 + OWASP LLM 映射 + 116 统一视图 |
| 评估 | evaluator.py, eval_*.py (9+), g_eval.py, discrete_eval.py, eval_store.py (SQLite), evaluator_registry.py | 130 维评估 + 基线 drift 检测 (维度级) |
| 编译 | compiler/ (7: lexer/parser/renderer/evaluator/cache/types) | 条件编译 (类 C 预处理器) |
| 优化 | gepa.py, opro.py, textgrad.py, opt_pipeline.py, prompt_optimizer.py | LLM 必需优化器 (可选能力, 隔离于 core) |
| A/B | ab_test/ (35: engine/judge/statistics/recommender/types + 26 provider 模块) | Thompson Sampling + SPRT + provider 矩阵 |
| 合规 | huawei_cloud/ (4), compliance_report.py, security/huaweicloud_compliance.py | 华为云 7 域加权 + 等保 2.0 |
| 分发 | mcp_server.py (73 工具 stdio JSON-RPC, 零依赖手写), market/ (6), playground/ (server.py FastAPI :8080 + static/index.html SPA), ci_integration.py, flow_dag.py, sarif_report.py | MCP / 市场 REST / Playground / SARIF |
| 数据/断言 | dataset.py, dataset_api.py, data_reader.py, assertion/ (3), eval_config.py, eval_baseline.py, baselines (根目录 3 JSON) | 数据集 + 断言引擎 + 增量门禁基线 |
| 编辑器 | linter/lsp_server.py, tui_browser.py, ux_enhanced.py, wizard.py, onboarding/, progress.py | LSP + TUI + 交互向导 |
| 辅助 | i18n/ (9), frontmatter/, report/ (4), data/ (60 clean + 667 golden + model_pricing + external_bench), easter_eggs.py | — |

## 周边产物

- `vscode-prompt-lint/` — VS Code 扩展 (TypeScript, **v0.6.0**, prompt-markdown 语言, 单文件 extension.ts)
- `action.yml` + `action/` — GitHub composite action (`--fail-on` 级别门禁, 产物断言)
- `Dockerfile` (多阶段含 playground :8080 + `prompt-cli --help` smoke, R306) + `docker-compose.yml`;
  ghcr 双通道 lockstep (release.yml docker-publish `needs: pypi-publish`, 3 tag)
- `web/index.html` — 落地页; `en/README.md` — 英文 README (独立, P1-07 English-first 未做);
  `marketing/` — 4 份推广文案草稿
- `_scenarios/` — 53 场景模板 (playground /api/templates 源)
- `baselines/` — gap-baseline.json / redos-audit.json / templates-baseline.json (增量门禁)
- `mypy_strict_registry.json` (286 模块) + `mypy_baseline.txt` (0 错误)
- `.github/workflows/` — 7 workflows; `.codearts/` + `.ci/` — 华为云 CodeArts 流水线 (双平台 CI)
- `scripts/` — 34 门禁/生成脚本 (release_gate.py 29 步链头)
- 28 个 `_` 前缀顶层目录 = 历史迭代工作区归档 (R213 卫生闭环, git 历史保留)

## 收口门禁链（release_gate.py 29 步, 本地=CI 27 步 `--skip 1,2`）

- 步骤 1/2 (本地跳过, CI 判定): pytest 全量 (-k "not slow") + coverage 棘轮 (fail_under 75)
- 核心 27 步 (族): ruff check / ruff format --check / mypy 棘轮 (0/0 基线 + strict 286/286
  注册表 S1-S4) / 双基线 (误报 0.01 / 漏检 0.05) / 依赖清单一致性 / 环境一致性快照 (钉版漂移
  硬红) / gen_rules_doc 重生成 + 268 每规则页 / sync_badges / 分语言基线核对 / README 组件统计 /
  板状态 5 检查 / 性能楔子 / 版本一致性 (四处) / 文档漂移 / ReDoS 审计 / 运营点数据页 ×2 /
  过防御基线 + 二阶信号 / 本地=CI 验证
- 发布硬闸 (R306): release-gate 作业先于 build/pypi/docker publish, 含 tag↔pyproject 版本断言
