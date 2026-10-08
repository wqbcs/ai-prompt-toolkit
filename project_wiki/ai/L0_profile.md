# L0 技术画像（ai-prompt-toolkit）

> 生成: R213 现状扫描 (2026-09-30) | 事实来源: pyproject.toml / 代码实际提取 / git 历史

## 运行时与依赖

- Python ≥3.10 (CI matrix 3.10/3.12, mypy target 3.10)
- **核心依赖仅 5 个**: click / rich / pyyaml / jsonschema / cachetools
- 可选 extras:
  - `ab_test`: httpx, scipy, numpy (A/B 统计)
  - `lsp`: pygls, lsprotocol (LSP Server)
  - `full`: ab_test + fastapi, uvicorn (模板市场 REST API)
- 构建: setuptools, src 布局
- 入口: `prompt-cli` / `prompt` → `cli_core:main`; `python -m ai_prompt_toolkit` (R212-1 修复)

## 规模（2026-09-30 实测）

| 指标 | 数值 |
|---|---|
| src 文件数 / LOC | 264 / 68,176 |
| tests 文件数 / LOC | 209 / 32,855 |
| 测试用例 | 5,737 (全绿) |
| Lint 规则 | 256 (P001-P256, 196 条可自动修复) |
| 评估维度 | 130 (D01-D130) |
| MCP 工具 | 73 |
| 红队探针 / 检测器 | 23 / 11 |
| LLM Provider | 24 (ab_test/providers/) |
| 干净样本 / golden 攻击探针 | 56 / 41 |

## 模块地图（src/ai_prompt_toolkit/）

| 层 | 模块 | 职责 |
|---|---|---|
| CLI | cli_core.py, cli/commands/ (11 簇) | 62 顶级命令 + dataset(7)/plugin(4) 两组 |
| Lint 内核 | linter/ (33 规则文件 + linter.py) | 静态规则引擎, 零 LLM 调用 |
| 安全 | security/ (prompt_scorecard, health_score) | 五维评分卡 + 四维健康分 |
| 红队 | redteam/, probe_framework.py, adversarial.py, attack_vault.py | 静态探针 + 检测器 + OWASP 映射 |
| 评估 | evaluator.py, eval_*.py (10+), g_eval.py, discrete_eval.py | 130 维评估引擎 |
| 编译 | compiler/ (lexer/parser/renderer/evaluator) | 条件编译(类 C 预处理器) |
| 优化 | gepa.py, opro.py, textgrad.py, opt_pipeline.py, prompt_optimizer.py | 优化器(需 LLM, 可选) |
| A/B | ab_test/ (engine/judge/statistics + 24 providers) | Thompson Sampling + SPRT |
| 合规 | huawei_cloud/, compliance_report.py | 7 域加权 + 等保 2.0 |
| 分发 | mcp_server.py, market/, ci_integration.py, sarif_report.py | MCP stdio / FastAPI / SARIF |
| 编辑器 | linter/lsp_server.py, tui_browser.py, ux_enhanced.py | LSP + TUI |
| 模板 | templates/, builtin_templates.py, template_*.py | 内置模板 + 继承/推荐/升级 |
| 数据 | dataset.py, data_reader.py, eval_store.py, version_store.py | 数据集/版本持久化 |
| 其他 | i18n/, frontmatter/, playground/, onboarding/, wizard.py, report/ | 辅助 |

## 周边产物

- `vscode-prompt-lint/` — VS Code 扩展 (TS, v0.5.0, language: prompt-markdown)
- `action/action.yml` — GitHub Action
- `Dockerfile` + `docker-compose.yml`
- `.github/workflows/` — 11 个 CI workflow
- `scripts/` — 棘轮/同步/生成脚本 (check_mypy_ratchet / check_false_positives / check_miss_rate / check_version_consistency / check_board_status / check_lint_performance / check_ci_green_streak / check_sarif_schema / verify_local_ci_parity / gen_rules_doc / sync_badges / sync_readme_metrics)

## CI 门禁（prompt-ci.yml 为准）

1. ruff check + format --check
2. pytest 全量 (-k "not slow") + coverage (fail_under 68, R176 基线 68.49%)
3. gen_rules_doc.py --check (规则文档漂移)
4. check_mypy_ratchet.py (0/0 棘轮)
5. check_false_positives.py --fail-above 0.01 (R212-C 挂载)
6. check_miss_rate.py --fail-above 0.10 (R212-C 挂载, R213 盲区修复后收紧 0.05)
