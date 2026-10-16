# 采用指南 — Day 0 到长期运营

确定性 Prompt 静态门禁的完整采用路径。设计原则：**先报告后拦截，先增量后存量**——
任何采用者都能在 10 分钟内看到价值，且老仓库不会被存量 findings 打回。

## 退出码契约（CI 编写前先知道这个）

| 退出码 | Verdict | 含义（默认阈值，均可配置） |
|---|---|---|
| `0` | PASS | 无 critical/high，medium ≤3，评分 ≥60 |
| `1` | WARN | medium >3 或评分 <60 —— 可合并 |
| `2` | FAIL | critical >0 或 high >0 —— **CI 应在此失败** |

---

## Day 0：10 分钟接入（只报告，不拦截）

目标：看到自己 prompt 库的体检报告，不阻塞任何 PR。

### 1. 本地跑一次

```bash
pip install ai-prompt-toolkit
prompt-cli lint -t ./prompts --format cli
prompt-cli baseline   # 顺带自证工具自身双基线（漏检率/误报率现值由命令实时输出）
```

### 2. 放入 GitHub Actions（report-only）

`.github/workflows/prompt-ci.yml`：

```yaml
name: Prompt CI
on:
  pull_request:
    paths: ["**/*.md", "prompts/**", ".github/workflows/prompt-ci.yml"]

jobs:
  prompt-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ai-prompt-toolkit
      # report-only: 不带 --gate, 退出码恒为0, 只产出SARIF进code scanning
      - run: prompt-cli lint -t ./prompts --format sarif -o prompt-lint.sarif
      - uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: prompt-lint.sarif
```

**为什么 report-only 先行**：SARIF 进 GitHub Code Scanning 后，存量问题在
`Security > Code scanning` 里可见、可逐条标注（`false positive` / `won't fix`），
团队先消化存量，再开拦截——避免"一开门禁 500 条存量红"的采用死结。

### 3. 本地 pre-commit（可选，<100ms 不拖慢提交）

`.pre-commit-config.yaml`：

```yaml
repos:
  - repo: local
    hooks:
      - id: prompt-lint
        name: prompt-lint
        entry: prompt-cli lint -s {0} --gate
        language: system
        files: \.(md|txt)$
```

---

## Day 1：开门禁（增量拦截）

存量消化得差不多后（Code Scanning 里无未处理存量，或团队接受存量共存），加 `--gate`：

```yaml
      - run: prompt-cli lint -t ./prompts --format sarif -o prompt-lint.sarif --gate
        # --gate: exit 2 (FAIL) 时 CI 红灯, exit 1 (WARN) 不挡合并
```

**分阶段收紧建议**（照抄即可）：

| 阶段 | 配置 | 时机 |
|---|---|---|
| 1. 报告 | 无 `--gate`，SARIF 入 Code Scanning | Day 0，立即 |
| 2. 硬拦截 critical | `--gate`（默认 critical/high 即 FAIL） | 存量清零或豁免后 |
| 3. 预算收紧 | `--gate --fail-on medium`（medium 新增也硬拦） | 稳定运行 2 周后 |

---

## 豁免（waiver）机制

个别 finding 确实误报或接受风险时，**在 prompt 文件内**加行内注释（文件级作用域）：

```markdown
# promptlint:ignore P107   ← 豁免单条规则
# lint-ignore: [P119, P120]  ← 豁免多条
```

纪律：
- waiver 必须有 owner 与复核日期（注释格式 `promptlint:ignore P107 @owner 2026-12-31`）
- `prompt-cli explain P107` 可查看规则说明与豁免方式，提示文案与实际能力一致（文件级）
- 定期审计 waiver（机器可查，不用 grep）：

```bash
prompt-cli audit-waivers -t ./prompts                  # 列全仓声明: ok/no_owner/expired/unknown_rule
prompt-cli audit-waivers -t ./prompts --fail-on expired --format json   # 进 CI: 过期 waiver 即红
```

- 严格 CI 可加 `prompt-cli lint -t ./prompts --fail-on-waiver`：任何豁免生效即 FAIL（禁新增豁免期）

**反模式**：不要为了过门禁整体降级 severity —— 那等于把尺子掰弯。

---

## Brownfield 接入：存量不清零也能开门禁（增量门禁）

老仓库第一次跑 `prompt-cli lint` 可能有几十上百条存量 finding。
**不要**为了开 `--gate` 先花几周全量清零——那样采用永远停在 Day 0。
用增量门禁：基线锁存量，门禁只拦**新增**：

```bash
# Day 1: 保存基线(锁定当前全部 finding 为 PRE-EXISTING)
prompt-cli lint -t ./prompts --baseline prompts.base.json --baseline-save

# CI: 增量门禁 — 只判定 NEW findings, 存量放行
prompt-cli lint -t ./prompts --baseline prompts.base.json --incremental --gate
```

行为契约：

| 场景 | 增量门禁行为 |
|---|---|
| PR 只改文档，无新 finding | PASS（存量不判） |
| PR 引入新的 critical/high | FAIL，报错只列新增的那几条 |
| PR 顺手修掉存量 | PASS，且"已修复: N"单列展示（鼓励还债） |
| 规则引擎升级导致新 finding 涌现 | 会被当作 NEW 拦下 —— 用 `--baseline-save` 重存基线并在 PR 里说明（棘轮纪律见下） |

**给 CI/CD 集成的结构化 diff（`--json-diff`）**：增量门禁的退出码是裁决真源；如果 CI 管线还需要机器可读的裁决载荷（自定义看板、verdict 历史归档、下游检查消费），加 `--json-diff`（与 `--baseline` 配合使用）：

```bash
# CI: 增量门禁 + 结构化 diff JSON
prompt-cli lint -t ./prompts --baseline prompts.base.json --incremental --gate \
  --json-diff reports/lint-diff.json
```

输出结构（字段真源 = `linter/structured_diff.py`）：

```json
{
  "verdict": "FAIL",
  "summary": {
    "baseline_total": 42, "current_total": 44, "delta": 2,
    "new_count": 3, "fixed_count": 1, "regression_count": 1, "unchanged_count": 41
  },
  "rule_level": [
    {"rule_id": "P001", "baseline_count": 5, "current_count": 6, "delta": 1, "status": "regression"}
  ],
  "new_findings": [], "fixed_findings": [], "regressions": []
}
```

两条契约：
- `verdict` ∈ PASS（无回归且 delta≥0）/ FAIL（有回归）/ IMPROVED（delta<0），与 `--gate` 裁决**同构**——同一 `compare_baseline` 真源，JSON 是裁决的报告面，不是第二套裁决
- `rule_level[].status` ∈ fixed/new/regression/improved/unchanged（按规则计数对比）
- `timestamp` 字段为墙钟时间，属报告面信息（不在字节级确定性楔子内；裁决结构同输入同输出）

**基线棘轮纪律**（防"基线重存 = 藏 bug"）：
- 重存基线必须是独立 commit，消息说明理由（如"规则 v67.34.15 新增 P261，补基线"）
- 修复存量后定期重存，让基线只减不增
- 配合 `--fail-on critical` 可只硬拦 critical 新增，high/medium 走 Code Scanning 消化

## 双基线棘轮（可选，CI 上钉住检测能力）

规则引擎升级后，防"规则改动导致漏检/误报退化"无感发生：

```yaml
      - name: 双基线棘轮
        run: prompt-cli baseline --fail-above-miss 0.05 --fail-above-fp 0.01
        # 漏检率>5% 或 误报率>1% 即 CI 失败 — 棘轮只收紧不放松
```

样本（golden 探针 + 60 干净 prompt）随包分发，任何 runner 一条命令复现。

---

## Day 30：预算收紧 + waiver 审计 cron（纪律变零操心）

稳定运行两周到一个月，目标：把"一次性配置"变成"自己跑"。

**1. 拦截预算收紧到最严级**（真实机制=级别门禁 `--fail-on`——本工具没有
`--max-warnings` 式预算参数，勿从别的工具抄）：

严格度递进（单向收紧，棘轮只紧不松）：

| 级别 | 配置 | FAIL 线 |
|---|---|---|
| 宽 | `--gate --fail-on critical` | 仅 critical 新增 |
| 中 | `--gate`（默认，等价 `--fail-on high`） | critical/high 新增 |
| 严 | `--gate --fail-on medium` | medium/high/critical 新增（最严） |

按 Day 1 分阶段收紧表在中级稳定 2 周后收紧到严级。放松不默认允许：
特殊时期需放松走显式 PR+限期，期满自动回严——waiver 审计 cron（下）
会自然复核问责面。

**2. waiver 审计 cron（每周，零操心）**：

```yaml
      - name: waiver 周审
        run: |
          prompt-cli audit-waivers -t ./prompts --fail-on no_owner  # 无 owner 豁免=问责不成立, 即红
          prompt-cli audit-waivers -t ./prompts --fail-on expired   # 超过复核日期=过期, 即红
          prompt-cli audit-waivers -t ./prompts --format json > waiver-weekly.json
```

建议由周度 `schedule` 作业跑（如 `cron: "0 2 * * 1"`）。状态语义：
`ok`（有 owner+未过期）/ `no_owner` / `expired` / `unknown_rule`（未注册
ID 或通配符）。`unknown_rule` 不立即红：规则 ID 打错=该豁免没生效在
任何 finding 上（无害），通配符需人工判断——先 JSON 报告，再裁决。

---

## Day 90：债务基线化（基线=债务台账）

运行 90 天，基线文件不再是技术工件，而是团队的**债务台账**：

1. **基线只减不增**：每轮修复存量后 `--baseline-save` 重存让台账变小
   （基线棘轮纪律见 Brownfield 节）。Day 90 基线与 Day 1 的 finding 数
   相同="还债"没发生——这个数字机器可查（数基线文件里的 findings）。
2. **钉住检测能力（强烈推荐）**：CI 上跑双基线棘轮（见上节）——规则引擎
   升级后漏检/误报退化即红，"尺子本身"不能无感退化。
3. **季度复核**：`prompt-cli audit-waivers -t ./prompts --format json`
   全量 waiver 复核（过期撤、无 owner 补、unknown_rule 逐条裁决），
   重存基线=独立 commit+理由。

---

## 多语言 / 多模型仓库

- 语言自动识别（BCP-47 标签），zh-Hans/zh-Hant/en/ja/ko 均有独立规则与基线分语言口径
- 特定模型/行业的条件编译模板：`prompt-cli compile -s tpl.md -c context.json`
- 华为云/等保合规场景追加：`prompt-cli compliance -t ./prompts --format sarif`

## 常见问答

**Q: 和 promptfoo 什么关系？会冲突吗？**
不冲突。promptfoo 做 LLM 输出评估（non-deterministic，要 repeat 采样对冲），
本工具做 prompt 静态门禁（deterministic，可复现裁决）。CI 里先跑本工具（秒级），
通过后再跑 LLM 评估（分钟级），成本最低。

**Q: 纯静态检测的盲区在哪？**
诚实声明：语义层攻击（创意越狱/间接注入的对抗性改写）是静态检测的机制上限。
双基线保证范围是静态可检测面（注入标记/编码混淆/不可见字符/结构/合规声明）。
语义层请组合运行时防护（LLM Guard 类工具），本工具 README 有适用域划分表。

**Q: 我们的 prompt 是 .txt/.yaml/代码字符串里，不是 .md？**
`-s` 单文件任意文本格式；代码内嵌 prompt 用 `prompt-cli scan` 的代码字符串提取。

**Q: air-gap / 无外网环境？**
零 LLM 调用、零运行时外联。`pip install --no-index --find-links <本地wheel>` 即可，
wheel 内带全部规则数据与基线样本。
