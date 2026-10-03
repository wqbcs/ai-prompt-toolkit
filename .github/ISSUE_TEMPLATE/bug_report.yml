---
name: Bug report
about: 报告 prompt-cli 的缺陷（请附版本与复现命令）
title: ''
labels: ['bug', 'needs-triage']
assignees: []
---

## 缺陷描述

<!-- 一句话：什么命令 + 什么输入 → 期望 vs 实际 -->

## 复现

```bash
# 精确到可复制粘贴
prompt-cli --version
# 输出: 67.x.x

# 复现命令
prompt-cli lint -s repro.prompt --format json
```

```
# 最小可复现 prompt（.prompt 文件内容）
```

## 环境

- 版本：`prompt-cli --version` 输出
- Python：`python --version`
- OS：
- 安装方式：pip / pipx / 源码 editable

## 期望 vs 实际

- 期望：
- 实际：

## 备注

- 若是**门禁误报**（clean prompt 报 critical/high）：请附 `prompt-cli baseline`
  输出与干净样本——误报是双基线棘轮守护的一等公民缺陷，会直接影响
  `check_false_positives.py` 阈值
- 若是**漏检**（已知攻击形态未报）：请附攻击样本与应命中的规则预期
- 本地验证命令：`python scripts/release_gate.py`（维护者用，报 bug 无需跑）
