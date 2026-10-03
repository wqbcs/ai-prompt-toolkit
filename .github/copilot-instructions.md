# Copilot 指令 — AI Prompt Toolkit

本仓库：AI Prompt Toolkit（`prompt-cli`），确定性的 LLM 提示词静态门禁
（prompt 的 ESLint）。楔子：裁决逐字节一致、零 LLM、<100ms/文件、离线可跑。

## 关键约束

1. **Prompt 文件受门禁**：`src/ai_prompt_toolkit/templates/` 与 `_scenarios/`
   的 prompt 变更由 CI 增量门禁拦截新增 critical/high finding
   （`--incremental --baseline baselines/templates-baseline.json --gate`）。
   修改 prompt 后本地跑 `prompt-cli lint -s <file>` 验证。
2. **收口门禁链**：`python scripts/release_gate.py` 全绿才可提交。禁止管道
   包裹（吞退出码假绿）。
3. **探针先行**：新增 Lint 规则必须先加探针（TP+TN 各 ≥2）再写规则；
   双基线（误报 <1%、漏检 <5%）不得回归。
4. **升版序**：版本 3 处 → `gen_rules_doc.py`（非 --check）→ sync 脚本 →
   版本一致性 → commit。
5. **反清单**：不往门禁路径加 LLM 调用；不抬 mypy/基线阈值；不为凑数加规则。

## 常用命令

```bash
prompt-cli lint -t <dir> --gate              # 门禁
prompt-cli baseline                          # 双基线自证
python scripts/release_gate.py               # 收口 13 步
python scripts/check_env_parity.py           # 环境一致性
```
