# L2 数据模型（ai-prompt-toolkit）

> 无数据库（纯文件/内存工具链）— "数据模型"= 核心值对象 + 注册表 + 基线 fixture

## 核心值对象（types.py / 各模块）

### Finding（通用发现项, dataclass）
| 字段 | 类型 | 约束 |
|---|---|---|
| rule_id | str | P001-P256 |
| severity | Severity | 枚举 |
| description | str | |
| location | str | 默认 "" |
| remediation | str | 默认 "" |
| details | dict | 默认 {} |

### Severity（Enum, 带排序）
INFO(0) < LOW(1) < MEDIUM(2) < HIGH(3) < CRITICAL(4) — 支持 >=/<= 比较

### ReportStatus（Enum）
success / partial / failed / blocked / passed

### TokenEstimate（token_analyzer.py）
estimated_tokens: int; estimated_input_cost_usd / estimated_output_cost_usd: float
（= tokens × 单 token 单价, 即"单次调用"成本 — R212-5 修正过的量纲）

### 评分对象
- PromptScorecard: 五维扣分制, overall_score + A–F 级（90/75/60/40 边界）
- health_score dict: security/quality/completeness/cost 四维, overall_grade=**最低档**（短板决定）
- _STRUCTURE_RULE_IDS = {P001, P002, P003, P005, P025, P026}（completeness 单一事实源）

## 注册表（事实源）

| 注册表 | 位置 | 规模 | 说明 |
|---|---|---|---|
| 规则 | linter/rules.py `_RULE_MAP` + rules_p0XX_p0YY.py | 256 | 编号顺延, 文档由 gen_rules_doc.py 生成（CI 漂移检查） |
| 探针（兼容层） | probe_framework `_PROBE_REGISTRY` | 23 | ProbeRunner 消费 |
| 探针（全局） | redteam/registry `get_global_probe_registry()` | 116 | 展示口径唯一事实源（R212-7） |
| 检测器 | redteam/ | 11 | 越狱/泄露/注入/编码/伦理/偏见/误导/拒绝/Agent/多模态/链式 |
| 模型定价 | data/model_pricing.json | — | token 成本估算数据源 |
| 评估器 | evaluator_registry.py | 130 维 | D01-D130, 6 大类 |

## 基线 fixture（可信度资产）

| Fixture | 位置 | 口径 |
|---|---|---|
| 干净样本 ×56 | tests/fixtures/clean_prompts/ | 误报基线分母; 32→56 扩样(R210) 覆盖英文/长文/Agent/模板/代码块/多语言 |
| golden 攻击 ×41 | tests/fixtures/golden_attacks.json | 漏检基线; 每条标注 expected 规则集 + note（"已知否定盲区"前缀单列） |

## 数据流（典型）

```
prompt 文件 → frontmatter 解析 → 256 规则(静态) → Finding[]
     → scorecard(扣分) + health(四维) + quality_gate(PASS/WARN/FAIL)
     → 输出: rich 彩色 / --format json / SARIF / JUnit / SVG badge / HTML 报告
```
