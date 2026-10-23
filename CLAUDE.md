# CLAUDE.md — AI Prompt Toolkit 仓库约定

本仓库是 **AI Prompt Toolkit**（`prompt-cli`）：确定性的 LLM 提示词静态门禁
（prompt 的 ESLint）。核心楔子：每次裁决逐字节一致 + 零 LLM 成本 + <100ms/文件
+ 离线可跑。

## 修改 prompt 文件

`src/ai_prompt_toolkit/templates/*.md` 与 `_scenarios/` 下的 prompt 文件由 CI
增量门禁检查。你修改的 prompt 会过 `prompt-cli lint --incremental --baseline
baselines/templates-baseline.json --gate`——新增 critical/high finding 会红 CI。

改完本地验证：

```bash
prompt-cli lint -s <file>          # 单文件
python scripts/release_gate.py     # 收口全链（13 步）
```

存量 finding 锁定在基线文件，**不要**为重存基线让 gate 通过；重存必须独立
commit + 理由。

## 新增 Lint 规则（探针先行）

1. 探针 TP+TN 各 ≥2 进 `data/golden_attacks.json`
2. 规则进 `linter/rules_pXXX_pYYY.py`，必须带 OWASP 映射
3. 双基线不回归：`scripts/check_false_positives.py --fail-above 0.01`、
   `scripts/check_miss_rate.py --fail-above 0.05`

无探针支撑的规则禁止合入。

## 硬性纪律

- 收口一律 `python scripts/release_gate.py`，禁止管道吞退出码
- 升版后必跑 `gen_rules_doc.py`（非 --check）
- mypy 棘轮基线=0 禁抬；双基线棘轮只收紧不放松
- 门禁命令禁止引入 LLM 调用（确定性楔子）
- 环境一致性：`scripts/check_env_parity.py` 对 dev 工具链（ruff/mypy）版本漂移
  硬红——不要改它们的钉版

## 代码风格

- Python 3.10+，ruff check + ruff format（CI 版本 0.17.0 钉死）
- mypy 棘轮：新模块零错误
- 中文注释合法且被保留；新代码标识符用英文
