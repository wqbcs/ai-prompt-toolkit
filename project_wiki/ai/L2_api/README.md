# L2 API 清单（ai-prompt-toolkit）

> 提取自代码实际定义（cli_core 程序化提取 + mcp_server.py + 核心 Python API）, 非文档推断

## 1. CLI 面（prompt-cli / prompt）

**62 个顶级命令 + 2 个命令组**（dataset: add-case/create/delete/export/import/list/run; plugin: disable/enable/list/load）

| 命令簇 | 命令 | 说明 |
|---|---|---|
| Lint | lint, rules-yaml, sarif-report, junit-report, watch, upgrade-fm | 规则检查/门禁/SARIF/JUnit/watch |
| 安全 | scan, score, badge, canary, probe, redteam, compliance, verify-failure, capture-failure | 扫描/评分/水印/红队/合规 |
| 评估 | evaluate, eval-compare, eval-config, eval-history, eval-matrix, eval-multi, eval-registry, benchmark, stats | 130 维评估 |
| 编译 | compile | 条件编译 |
| 优化 | optimize, prompt-optimize, gepa-optimize, opro-optimize, tgd-optimize, assert, judge, flow-run | 优化器 + 断言（需 LLM, 可选依赖） |
| A/B | ab-test | 贝叶斯统计 |
| 数据 | dataset (组), data-generate, data-load, contest-eval | 数据集 |
| 模板 | prompt-template, prompt-merge, recommend, registry-pull/push/search, market | 模板市场/注册表 |
| 版本 | version, prompt-version, prompt-diff | Git-like 语义 Diff |
| 引擎 | engine, serve, mcp, lsp, playground, tui (内嵌) | 运行时 |
| 开发工具 | baseline, gap-report, export-rules | 双基线自证/缺口报告/规则数据 JSON 导出（R242-P2-14，多端数据前置；`--lang zh/en/both` `--with-metrics`） |
| 工具 | init, doctor, prompt-doctor, i18n, locale, token, trace, cache, notify, feedback, wizard, plugin-list, plugin (组), completion | 基础设施 |

**退出码约定**: 0=PASS, 1=有 finding(非门禁), 2=门禁 FAIL (`--fail-on`/`--gate`)
（export-rules 例外：0=成功, 1=导出面异常, 2=参数错误 — R242-P2-14 独立契约）

**输出格式**: 默认 rich 彩色; `--format json` (machine); SARIF/JUnit 专用命令

## 2. MCP Server（mcp_server.py, stdio JSON-RPC）

73 个工具, 字典 O(1) 路由。工具名模式 `prompt_*`:
prompt_lint, prompt_scan, prompt_judge, prompt_canary_inject/check, prompt_evaluate,
prompt_dataset_run, prompt_scorecard, prompt_engine, prompt_badge, prompt_token_analyze,
prompt_redteam, prompt_compile, prompt_gepa_optimize …（完整清单见 mcp_server.py TOOL 注册段）

## 3. 核心 Python API（库模式消费）

| API | 位置 | 用途 |
|---|---|---|
| `lint_template(name, text) -> LintResult` | linter/__init__ | 单模板全规则检查（基线脚本/测试消费） |
| `compute_scorecard(findings, lint_score) -> PromptScorecard` | security/prompt_scorecard | 五维扣分评分 + A–F |
| `compute_health_score(findings, lint_score, text) -> dict` | security/health_score (R212-5) | 四维健康分(短板决定) |
| `analyze_prompt_tokens(text, model) -> TokenAnalysis` | linter/token_analyzer | token 估算 + 成本 |
| `get_global_probe_registry()` | redteam/registry | 116 探针统一视图（展示口径唯一事实源, R212-7） |
| `estimate_tokens(text, model) -> TokenEstimate` | linter/token_analyzer | 纯 token 估算 |

## 4. HTTP API（market/, 需 [full] extras）

FastAPI: 模板发布/评审/灰度部署（`prompt-cli serve` 启动, 端点见 market/ 路由）

## API 约定

- JSON 输出**只增不改**（新字段追加, 旧消费者不破 — R212-5 health 字段先例）
- 错误: cli_error_formatter 人话翻译（中文优先）
- 无 /api/v1 前缀（CLI 为主, HTTP 面仅 market）
