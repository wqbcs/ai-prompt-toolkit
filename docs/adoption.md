# 采用指南 — Day 0 到门禁上线

确定性 Prompt 静态门禁的完整采用路径。设计原则：**先报告后拦截，先增量后存量**——
任何采用者都能在 10 分钟内看到价值，且老仓库不会被存量 findings 打回。

## 退出码契约（CI 编写前先知道这个）

| 退出码 | Verdict | 含义 |
|---|---|---|
| `0` | PASS | 无 critical/high findings，或仅 low/medium 且未超预算 |
| `1` | WARN | 有 findings 但未达 FAIL 线（可配置预算内） |
| `2` | FAIL | 有 critical/high findings 或超预算 —— **CI 应在此失败** |

---

## Day 0：10 分钟接入（只报告，不拦截）

目标：看到自己 prompt 库的体检报告，不阻塞任何 PR。

### 1. 本地跑一次

```bash
pip install ai-prompt-toolkit
prompt-cli lint -t ./prompts --format cli
prompt-cli baseline   # 顺带自证工具自身双基线（漏检0.00%/误报0.91%）
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
| 3. 预算收紧 | `--gate --max-warnings 10`（medium 超预算也 FAIL） | 稳定运行 2 周后 |

---

## 豁免（waiver）机制

个别 finding 确实误报或接受风险时，**在 prompt 文件内**加行内注释（文件级作用域）：

```markdown
# promptlint:ignore P107   ← 豁免单条规则
# lint-ignore: [P119, P120]  ← 豁免多条
```

纪律：
- waiver 必须有 owner 与复核日期（建议团队约定注释格式 `promptlint:ignore P107 @owner 2026-12-31`）
- `prompt-cli explain P107` 可查看规则说明与豁免方式，提示文案与实际能力一致（文件级）
- 定期审计 waiver：`grep -rn "promptlint:ignore\|lint-ignore" prompts/`

**反模式**：不要为了过门禁整体降级 severity —— 那等于把尺子掰弯。

---

## 双基线棘轮（可选，CI 上钉住检测能力）

规则引擎升级后，防"规则改动导致漏检/误报退化"无感发生：

```yaml
      - name: 双基线棘轮
        run: prompt-cli baseline --fail-above-miss 0.05 --fail-above-fp 0.01
        # 漏检率>5% 或 误报率>1% 即 CI 失败 — 棘轮只收紧不放松
```

样本（113 golden 探针 + 60 干净 prompt）随包分发，任何 runner 一条命令复现。

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
