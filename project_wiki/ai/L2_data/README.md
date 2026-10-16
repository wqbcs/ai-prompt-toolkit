# L2 数据模型（ai-prompt-toolkit）

> 更新: R310 (2026-10-16) | 首版: R213
> 提取自代码实际定义: dataclasses.fields 运行时内省 / 持久层 grep / golden schema 实载

## 架构形态

核心引擎无状态（文件入 → Finding[] 出）；持久化面=**本地 SQLite + JSON**（无网络数据库，
无 ORM）：用户级 `~/.ai-prompt-toolkit/` 或路径可配；双基线 fixture 以包内文件作单一真源
（R224-P0-1 从 tests/fixtures 移入，原位置留符号链接）。

## 核心值对象（2026-10-16 运行时内省核实）

### Finding（types.py, dataclass）

| 字段 | 类型 | 说明 |
|---|---|---|
| rule_id | str | P001-P268 |
| severity | Severity | 枚举（可排序） |
| description | str | |
| location | str | R218+ 行:列契约（parse_location/build_location/loc_from_match 单一事实源, types.py） |
| remediation | str | |
| details | dict[str, Any] | 默认 {} |

### Severity（Enum, 带排序）
INFO(0) < LOW(1) < MEDIUM(2) < HIGH(3) < CRITICAL(4)

### ReportStatus（Enum）
SUCCESS / PARTIAL / FAILED / BLOCKED / PASSED

### TokenEstimate（linter/token_analyzer.py）
estimated_tokens: int; estimated_input_cost_usd / estimated_output_cost_usd: float
（= tokens × 单 token 单价, 即"单次调用"成本 — R212-5 修正过的量纲）

### 评分对象
- PromptScorecard（security/prompt_scorecard.py）: 五维扣分制, overall_score + A–F（90/75/60/40 边界）;
  结构规则集单一事实源 = `_STRUCTURE_RULE_IDS`（health_score 直接复用, 不新造规则集）
- health dict（security/health_score.py）: security/quality/completeness/cost 四维,
  overall_grade = **最低档**（短板决定）

### LintRule（linter/rules.py, dataclass; 268 条注册）
rule_id / name / category / severity / description / remediation / description_en /
remediation_en / family / owasp_refs / status / deprecated_since / removal_version
（**无 fixable 字段** — "可自动修复"口径 = `linter/fixer.py` AUTO_FIXABLE_RULES 成员资格(196),
经 rule_explainer.auto_fixable 汇入 gen_rules_doc/README 指标, 单一链条无多处硬编码）

## 注册表（事实源）

| 注册表 | 位置 | 规模 |
|---|---|---|
| 规则 | linter/rules.py + rules_pXXX.py 族 → `get_all_rules()` | 268 (P001-P268) |
| 自动修复 | linter/fixer.py `AUTO_FIXABLE_RULES` | 196 |
| 规则解释/导出 | linter/rule_explainer.py `get_all_explanations()` / `build_rules_export()` | 268 (export-rules / gen_rules_doc 数据源, R242) |
| 探针（框架） | probe_framework `_PROBE_REGISTRY`（dict 条目） | 23 探针 / 173 payload |
| 探针（全局视图） | redteam/registry `get_global_probe_registry()` | 116（展示口径唯一事实源, R212-7） |
| 检测器 | redteam/（11） | 越狱/泄露/注入/编码/伦理/偏见/误导/拒绝/Agent/多模态/链式 |
| 评估维度 | evaluator_registry.py | 130 (D01-D130, 6 大类, 7 行业权重预设) |
| 模型定价 | data/model_pricing.json | token 成本估算数据源 |
| MCP 工具 | mcp_server.py 工具字面量 | 73（测试断言） |

## 数据资产（包内单一真源, pip 用户可用）

| 资产 | 位置 | Schema |
|---|---|---|
| golden 攻击探针 ×667 | src/.../data/golden_attacks.json | `{version, description, probes:[{name, category, lang, text, expected}]}`; lang = zh-Hans 544 / en 103 / ja 18 / zh-Hant 2; 379 期望命中单元 |
| 干净样本 ×60 | src/.../data/clean_prompts/（.md/.txt） | 误报基线分母（R221 对称扩样: 英文/长文/Agent/模板/代码块/多语言） |
| 外部基准 | src/.../data/external_bench/（NotInject/deepset） | 过防御基线（R249 进包） |
| 场景模板 ×53 | 仓库根 `_scenarios/*.md` | frontmatter: author/tags/template_type/lint_score（playground /api/templates 源） |
| 内置模板 ×26 | src/.../templates/*.md | pip package-data |

## 持久化面（SQLite / JSON）

| 面 | 模块 | 默认位置 | 形态 |
|---|---|---|---|
| 评估历史 | eval_store.py | `~/.ai-prompt-toolkit/eval_history.db` | SQLite（快照/趋势/告警; `--save`/`--baseline-save` 写入） |
| Prompt 版本 | version_store.py | `~/.ai-prompt-toolkit/prompt_versions.db` | SQLite（prompt-version 命令族） |
| 模板市场 | market/api.py `MarketDB` | `_DEFAULT_DB_PATH`（代码内定义, db_path 可配） | SQLite（WAL + `_schema_version` 迁移表） |
| 攻击库 | attack_vault.py | `save(path)` 指定 | JSON（attack_vault_learn 学习面） |
| 追踪导出 | tracing.py `save_traces(export_dir)` | export_dir 指定 | JSON/trace 文件 |
| 增量门禁基线 ×3 | 仓库根 `baselines/` | gap-baseline.json `{avg_gap_rate, avg_quality, file_count, updated_at, note}`; redos-audit.json `{schema, engine, entries}`; templates-baseline.json `{created_at, template_id, total_findings, score, findings}` | JSON（`--incremental --baseline` 消费, R306 P1-03 板引用面） |
| 质量棘轮 | 仓库根 | mypy_baseline.txt（0 错误）/ mypy_strict_registry.json（286 模块, 100%） | 棘轮文件（strict 唯一变更路径 `--update-strict`） |
| 评估基线 | `.eval-baseline.json`（`--baseline-save`） | 工作目录 | JSON（维度级 drift 检测, `--baseline` 对比, 阈值 `--drift-threshold` 默认 1.5） |

（SQLite 表级 schema 见各模块 `_ensure_schema` — R310 未展开, 非 wiki 面）

## 数据流（典型）

```
prompt 文件 → frontmatter 解析 → 268 规则(静态, 零 LLM) → Finding[]
     → scorecard(扣分) + health(四维) + 门禁裁决(0/1/2/3)
     → 输出: rich / --format json / --format summary / SARIF / JUnit / SVG badge / HTML
并行面:
  scan     → InjectionDetector → Finding[](注入族, /api/scan 同引擎)
  probe    → 23 探针 × 173 payload → 检出报告(116 统一视图展示)
  evaluate → 130 维 → overall/dimension/category 分(SQLite 历史可选)
  redteam  → 11 检测器 → 检出报告(OWASP LLM 映射)
```

## 字段生产者/消费者（关键链路）

| 字段 | 生产者 | 消费者 |
|---|---|---|
| Finding.rule_id | 规则检查器（rules_pXXX.py） | scorecard/health/sarif/waiver/增量基线/漏检率棘轮 |
| Finding.severity | 规则定义（LintRule.severity） | determine_exit_code（门禁裁决）/ scorecard 扣分 / summary top5 |
| Finding.location | 检查器（R218+ 行:列, parse_location 单一事实源） | 行级 waiver（开放, 见 L3_unknown）/ LSP 诊断 / SARIF physicalLocation |
| golden probes[].expected | 探针先行登记（TP+TN 各≥2, T1 纪律） | check_miss_rate（379 单元棘轮）/ fuzz seed（scripts/fuzz_lint.py, R304） |
| AUTO_FIXABLE_RULES | linter/fixer.py | rule_explainer.auto_fixable → gen_rules_doc → README 指标（单链） |
| lint_score | linter（100 分扣分制） | scorecard / health / 门禁（--gate score<60 → WARN） |
| __version__ | __init__.py | 徽章 / CHANGELOG / check_version_consistency（四处一致） |
| mypy_strict_registry | check_mypy_ratchet --update-strict | 门禁 S1-S4 / 红线钩子（redline-guard 拦截面） |
