# L2 API 清单（ai-prompt-toolkit）

> 更新: R310 (2026-10-16) | 首版: R213
> 提取自代码实际定义: CLI `--help` 契约 / mcp_server.py 工具字面量 / FastAPI 路由装饰器 / 核心模块 grep，非文档推断

## 1. CLI 面（prompt-cli / prompt → cli_core:main）

**73 顶级命令 + 2 命令组**（2026-10-16 --help 契约）

| 命令簇 | 命令 |
|---|---|
| Lint (7) | lint, watch, upgrade-fm, rules-yaml, sarif-report, junit-report, explain |
| 门禁 (4) | baseline, audit-waivers, gap-report, stats |
| 安全 (9) | scan, score, badge, canary, probe, redteam, compliance, capture-failure, verify-failure |
| 评估 (9) | evaluate, eval-compare, eval-config, eval-history, eval-matrix, eval-multi, eval-registry, benchmark, contest-eval |
| 编译 (1) | compile |
| 优化/断言 (8, 需 LLM 可选) | optimize, prompt-optimize, gepa-optimize, opro-optimize, tgd-optimize, assert, judge, flow-run |
| A/B (1) | ab-test |
| 数据 (3) | dataset (组), data-generate, data-load |
| 模板/市场 (7) | prompt-template, prompt-merge, recommend, market, registry-pull, registry-push, registry-search |
| 版本 (3) | version, prompt-version, prompt-diff |
| 引擎 (6) | engine, serve, mcp, lsp, playground, i18n, locale |
| 开发工具 (15) | init, doctor, prompt-doctor, token, trace, cache, notify, feedback, wizard, mcp-lint, plugin (组), plugin-list, completion |

命令组子命令: **dataset** = add-case / create / delete / export / import / list / run；
**plugin** = disable / enable / list / load

**退出码契约（cli_helpers.determine_exit_code 单一真源, R306 修正）**:
`0=PASS / 1=WARN / 2=FAIL / 3=执行错误`（R213 版缺 3=执行错误, 已补）
- 默认门禁: critical>0 或 high>0 → FAIL(2); medium>3 或 score<60 → WARN(1)
- `--fail-on {critical|high|medium}`: 显式级别门禁
- export-rules 例外独立契约: 0=成功 / 1=导出面异常 / 2=参数错误 (R242-P2-14)

**输出格式**: 默认 rich 彩色; `--format json` (machine); `--format summary` (CI digest,
失败首行三要素); SARIF/JUnit/HTML/SVG 专用命令面

## 2. MCP Server（mcp_server.py, stdio JSON-RPC, 零依赖手写实现）

**73 工具**（字典 O(1) 路由; 测试断言 len(tools)==73; 已知 prompt_version_list 重复注册,
去重后口径 73; R306 加固: mcp_reload 动态导入限定 `ai_prompt_toolkit.` 前缀白名单）

| 族 | 数 | 工具名 |
|---|---|---|
| prompt_* | 39 | prompt_lint, prompt_lint_json_schema, prompt_scan, prompt_judge, prompt_evaluate, prompt_eval_matrix, prompt_engine, prompt_badge, prompt_token_analyze, prompt_redteam, prompt_compile, prompt_gepa_optimize, prompt_auto_optimize, prompt_sanitize, prompt_semantic_diff, prompt_diff, prompt_merge, prompt_template_render, prompt_version_save/create/list/diff/history, prompt_canary_inject/check, prompt_dataset_run, prompt_data_load, prompt_contest_eval, prompt_flow_run, prompt_doctor, prompt_junit_report, prompt_sarif_report, prompt_notify, prompt_plugin_list, prompt_cache_lookup/stats/invalidate, prompt_trace_export, prompt_scorecard |
| probe_* | 7 | probe_run, probe_list, probe_detect, probe_owasp_report, probe_owasp_summary, probe_detector_run, probe_ethics_scan |
| huaweicloud_* | 6 | huaweicloud_compliance, huaweicloud_ecs_info, huaweicloud_iam_auth, huaweicloud_modelarts_deploy/infer, huaweicloud_obs_upload |
| harmonyos_* | 4 | harmonyos_arkui_check, harmonyos_distributed_check, harmonyos_stage_model_check, harmonyos_template_generate |
| attack_vault_* | 2 | attack_vault_check, attack_vault_learn |
| pangu_* | 2 | pangu_compat_check, pangu_safety_audit |
| 无前缀 | 13 | eval_matrix, badge_generate_themed, config_hot_reload_status, deveco_config, fg_template_generate/list, html_report_generate, mcp_reload, multimodal_token_estimate, output_scan, rollback_safety_check, test_suite_run, weight_preset_list |

## 3. 核心 Python API（库模式消费, 2026-10-16 逐函数核实存在）

| API | 位置 | 用途 |
|---|---|---|
| `lint_template(name, text) -> LintResult` | linter/__init__.py | 单模板全规则检查（基线脚本/测试消费） |
| `compute_scorecard(findings, lint_score) -> PromptScorecard` | security/prompt_scorecard.py | 五维扣分评分 + A–F |
| `compute_health_score(findings, lint_score, text) -> dict` | security/health_score.py | 四维健康分（短板决定 overall_grade） |
| `estimate_tokens(text, model) -> TokenEstimate` | linter/token_analyzer.py | 纯 token 估算 |
| `analyze_prompt_tokens(text, model) -> TokenAnalysisResult` | linter/token_analyzer.py | token 估算 + 成本（R213 误记 TokenAnalysis, 实为 TokenAnalysisResult） |
| `get_global_probe_registry()` | redteam/registry | 116 探针统一视图（展示口径唯一事实源） |
| `get_all_explanations(include_metrics)` / `build_rules_export()` | linter/rule_explainer | 规则解释/导出（export-rules 数据源, R242; auto_fixable 口径真源） |
| `compile_template(template, ctx)` | compiler | 条件编译（playground /api/compile 消费） |
| `AUTO_FIXABLE_RULES` (set, 196) | linter/fixer.py | 可自动修复规则单一真源 |
| `InjectionDetector().detect(text, template_id)` | security/injection_detector | 注入检测（playground /api/scan 消费） |

## 4. HTTP API（`prompt-cli serve` → playground :8080, 需 [full] extras）

FastAPI playground server（playground/server.py）, 三方 router 挂载, 共 **37 端点**（API 35 + SPA 首页 1 + WebSocket 1）:

### 4.1 Playground 自持路由（17 API + 1 SPA 首页 + 1 WebSocket, /api/ 前缀, 限流 100 req/60s/client → 429）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/compile | 条件编译（template+context → compiled_text+report） |
| GET | /api/context-schema | 上下文 JSON Schema（model/language/industry + bool flags） |
| GET | /api/version | 版本号 |
| GET | /api/i18n/{locale} | 语言包（不支持→error 状态） |
| GET | /api/templates | 场景模板列表（源 _scenarios/ 53 项, frontmatter 解析） |
| POST | /api/lint | 单文本 lint（score+findings） |
| POST | /api/scan | 注入检测（InjectionDetector） |
| POST | /api/evaluate | 130 维评估（overall_score+dimension_scores） |
| GET | /api/traces | 追踪列表（Tracer 单例, 内存态） |
| GET | /api/traces/summary | 追踪摘要 |
| POST | /api/traces/export | 追踪导出（写 export_dir, JSON/trace） |
| POST | /api/eval-matrix | 多模板评估矩阵（空 templates→error 契约） |
| GET | /api/eval-history | 评估历史（EvalStore, 快照/趋势/告警） |
| GET | /api/eval-compare | 评估基线对比（维度级 drift） |
| POST | /api/scorecard | 五维评分卡 |
| POST | /api/engine | 模板引擎（编译+渲染管线） |
| POST | /api/badge | SVG badge 生成 |
| GET | / | SPA 首页（static/index.html, pip package-data 随包） |
| WS | /ws/compile | WebSocket 编译（JSON in/out, /api/compile 薄镜像; R311: 不入 hermetic 套件 — [dev] 未钉版 websockets, 真实会话留 Playwright） |

### 4.2 Market REST（market/api.py, APIRouter prefix=/api/market, 9 路由）

GET/POST /api/market/templates; GET /api/market/templates/{id}; POST /api/market/templates/{id}/rate,
/favorite, /review, /deploy; GET /api/market/categories; GET /api/market/tags

### 4.3 Dataset REST（dataset_api.py, APIRouter prefix=/api/datasets, 9 路由）

GET/POST /api/datasets（列表/创建）; GET/DELETE /api/datasets/{id}; POST /api/datasets/{id}/cases;
DELETE /api/datasets/{id}/cases/{case_id}; POST /api/datasets/{id}/import;
GET /api/datasets/{id}/export; POST /api/datasets/{id}/run

**认证**: 无（本地工具, 非公网服务面）; CORS 限 _PLAYGROUND_ORIGINS

## API 约定

- JSON 输出**只增不改**（新字段追加, 旧消费者不破 — R212-5 health 字段先例）
- 错误: cli_error_formatter 人话翻译（中文优先）
- HTTP 面无 /api/v1 版本前缀（CLI 为主, HTTP 面=本地 playground/市场/dataset）
- MCP: JSON-RPC 2.0 over stdio; tools/list → tools/call; 零外部依赖（手写协议层）
- HTTP 面测试: tests/test_r308_playground_api.py（14, R308）+ tests/test_r311_playground_api_gap.py
  （8, R311: eval-compare/scorecard/engine/badge + SPA 首页）= 16/17 API 路由 + 首页覆盖;
  /ws/compile 真实会话留发布后 Playwright（P3-18 登记面）; market 面 tests/test_market_api.py
