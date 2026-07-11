# 提示词贡献指南 v1.0

> **版本**：v1.0
> **日期**：2026-05-29

---

## 欢迎贡献！

感谢您对AI提示词体系的贡献兴趣。本指南将帮助您了解如何有效贡献。

## 贡献类型

| 类型 | 说明 | 评审级别 |
|------|------|----------|
| new-scenario | 新增场景模板 | L1(全审) |
| variant | 行业/技术变体 | L2(速审) |
| improvement | 优化建议 | L2(速审) |
| bugfix | 错误修正 | L3(快审) |
| translation | i18n翻译 | L3(快审) |

## 贡献流程

1. Fork仓库 → 2. 创建分支 → 3. 修改 → 4. 自检 → 5. 提交PR → 6. CI自动检查 → 7. 人工评审 → 8. 合并

## 自检清单(必须全部通过)

- [ ] 场景模板5要素完整(身份/输入/步骤/输出/验收)
- [ ] 检查清单≥8项
- [ ] 约束覆盖技术/业务/安全/性能4维度
- [ ] 无Prompt注入风险
- [ ] 无隐私/敏感信息泄露
- [ ] 术语使用符合_glossary.md
- [ ] 与现有场景无冲突(知识图谱检测)
- [ ] 至少1个模型验证通过
- [ ] 接口定义与上下游兼容
- [ ] CHANGELOG已更新

## 场景模板格式

```yaml
contribution:
  type: "<类型>"
  contributor:
    name: "<名称>"
    expertise: "<专业领域>"
  scenario:
    name: "<场景名>"
    document: "<目标文档>"
    description: "<描述>"
    input:
      required: []
      optional: []
    output:
      format: "<格式>"
      schema: {}
    checklist: []
    validation_criteria: []
  adaptation_matrix:
    gpt4: "S/A/B/C"
    claude: "S/A/B/C"
    deepseek: "S/A/B/C"
```

## 评审标准

- L1(全审)：功能+安全+兼容+文档+评估
- L2(速审)：功能+安全+兼容
- L3(快审)：功能+安全

## 安全审查

所有贡献必须通过安全审查：
- Prompt注入风险检测
- 隐私/敏感信息检测
- 合规风险检测
