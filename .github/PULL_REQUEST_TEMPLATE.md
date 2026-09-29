# Prompt 变更说明

<!-- 仅当本PR修改了 .prompt / .prompt.md 文件时, 以下检查项为必填 -->

## 变更类型

- [ ] 新增 Prompt 模板
- [ ] 修改现有 Prompt
- [ ] 删除 Prompt
- [ ] 仅非 Prompt 变更（跳过下方检查）

## 质量门禁结果（必填）

```bash
# 本地已运行并确认通过:
prompt-cli lint -t <changed-prompt-path>        # 0 CRITICAL/HIGH
prompt-cli scan -t <changed-prompt-path> --depth standard   # 无 CRITICAL 漏洞
prompt-cli evaluate -t <changed-prompt-path>     # 均分不低于变更前
```

| 检查项 | 变更前 | 变更后 | 结果 |
|--------|--------|--------|------|
| Lint 严重/高危数 | | | |
| 安全评分 | | | |
| 评估均分 | | | |

## 影响范围

- 使用该 Prompt 的下游服务/Agent: 
- 是否需要协调变更（API/输出格式）: 是 / 否

## 回滚方案

- [ ] 变更已提交 git（可 `git revert` 回退）
- [ ] 已通知下游负责人（如适用）
