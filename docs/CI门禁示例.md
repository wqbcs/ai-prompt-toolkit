# R203: CI 门禁与 Code Scanning 示例

## 1. 最小 CI 工作流（fail-on 门禁 + SARIF 上传）

`.github/workflows/prompt-gate.yml`：

```yaml
name: Prompt Quality Gate
on: [push, pull_request]

jobs:
  prompt-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install
        run: pip install ai-prompt-toolkit

      # 门禁: high及以上有finding → 退出码2 → 构建失败
      - name: Lint with fail-on gate
        run: prompt-cli lint -t prompts/ --fail-on high --ci

      # SARIF 上传 GitHub Code Scanning（findings出现在PR Checks）
      - name: Generate SARIF
        run: prompt-cli lint -t prompts/ --format sarif -o prompt-lint.sarif

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v4
        if: always()
        with:
          sarif_file: prompt-lint.sarif

      # 误报基线棘轮: 全局误报率上升超阈值 → 失败（防止规则质量劣化）
      - name: False-positive baseline
        run: python scripts/check_false_positives.py --fail-above 0.10
```

## 2. 退出码语义（与 QualityGate 对齐）

| 退出码 | 语义 | 触发条件 |
|---|---|---|
| 0 | PASS | 无目标级别及以上 finding / verdict=pass |
| 1 | WARN | 仅 medium 级 finding / verdict=warn / 执行层警告 |
| 2 | FAIL | `--fail-on` 级别命中 / verdict=fail / high+ finding（默认模式） |
| 3 | ERROR | 执行层异常（文件不可读、配置错误） |

## 3. 基线回归（Drift Sentinel 最小用法）

```bash
# 首次: 保存基线
prompt-cli lint -t prompts/ --baseline-save

# 此后每次CI: 对比基线（新增/修复/回归三类diff）
prompt-cli lint -t prompts/ --baseline .baseline.json
```

基线文件 `.baseline.json` 建议入库（随 prompt 一起版本化）。

## 4. 误报基线脚本

```bash
python scripts/check_false_positives.py            # 人类可读报告
python scripts/check_false_positives.py --json     # 机器可读
python scripts/check_false_positives.py --fail-above 0.10  # 棘轮门禁
```

样本集: `tests/fixtures/clean_prompts/`（32个干净prompt，新增干净prompt应同步入库）。
