# 社区生态开放体系 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **适用**：提示词贡献+评审+发布+集成

---

## 一、贡献模板(CONTRIBUTING.md)

### 1.1 贡献类型

| 贡献类型 | 标识 | 说明 | 评审级别 |
|----------|------|------|----------|
| 新场景模板 | new-scenario | 新增场景模板 | L1(全审) |
| 场景变体 | variant | 现有场景的行业/技术变体 | L2(速审) |
| 改进建议 | improvement | 对现有模板的优化建议 | L2(速审) |
| Bug修复 | bugfix | 模板中的错误修正 | L3(快审) |
| 翻译 | translation | i18n翻译贡献 | L3(快审) |
| 文档 | documentation | 文档补充/修正 | L3(快审) |

### 1.2 贡献提交流程

```
贡献者 → Fork → 修改 → 自检(检查清单) → 提交PR → 自动CI → 人工评审 → 合并/退回
```

### 1.3 贡献模板格式

```yaml
contribution:
  type: "<贡献类型>"
  contributor:
    name: "<贡献者名称>"
    email: "<邮箱>"
    expertise: "<专业领域>"
  scenario:
    name: "<场景名称>"
    document: "<目标文档编号>"
    description: "<场景描述>"
    input:
      required: ["<必填输入>"]
      optional: ["<选填输入>"]
    output:
      format: "<输出格式>"
      schema: "<Schema定义>"
    checklist:
      - item: "<检查项>"
        method: "<检查方法>"
        risk_level: "<风险等级>"
    validation_criteria:
      - "<验收标准1>"
      - "<验收标准2>"
  adaptation_matrix:
    gpt4: "S"
    claude: "S"
    deepseek: "A"
    qwen: "A"
  self_check:
    - [ ] 5要素完整(身份/输入/步骤/输出/验收)
    - [ ] 检查清单≥8项
    - [ ] 约束覆盖4维度
    - [ ] 无注入风险
    - [ ] 无隐私泄露
    - [ ] 术语使用规范(glossary)
    - [ ] 与现有场景无冲突
    - [ ] 至少1个模型验证通过
```

---

## 二、外部集成API规范

### 2.1 API版本策略

- 基础路径：`/api/v1/`
- 版本化：`/api/v1/` → `/api/v2/`(破坏性变更)
- 认证：OAuth2.0 Bearer Token / API Key

### 2.2 场景查询API

```
GET /api/v1/scenarios
GET /api/v1/scenarios/{scenario_id}
GET /api/v1/scenarios?document={doc_id}&industry={industry}
POST /api/v1/scenarios/{scenario_id}/execute
```

**场景执行请求**：
```json
{
  "scenario_id": "04_code_review_A",
  "input": {
    "code": "...",
    "language": "python",
    "context": {}
  },
  "options": {
    "model": "gpt-4-turbo",
    "output_format": "json",
    "include_reasoning": true
  }
}
```

### 2.3 评估结果API

```
GET /api/v1/evaluations
GET /api/v1/evaluations/{eval_id}
GET /api/v1/evaluations/dashboard
GET /api/v1/evaluations/trends?dimension={dim}&period={period}
```

### 2.4 工作流执行API

```
GET /api/v1/workflows
POST /api/v1/workflows/{workflow_id}/execute
GET /api/v1/workflows/{workflow_id}/status
POST /api/v1/workflows/{workflow_id}/resume
```

### 2.5 知识图谱查询API

```
GET /api/v1/knowledge/terms
GET /api/v1/knowledge/terms/{term_id}/relations
GET /api/v1/knowledge/documents/{doc_id}/dependencies
GET /api/v1/knowledge/recommend?scenario={scenario_id}
```

---

## 三、版本发布自动化

### 3.1 Changelog自动生成规则

```yaml
changelog:
  format: "keep-a-changelog"
  categories:
    - name: "新增"
      label: "feat"
    - name: "改进"
      label: "improve"
    - name: "修复"
      label: "fix"
    - name: "破坏性变更"
      label: "breaking"
    - name: "安全"
      label: "security"
    - name: "评估"
      label: "eval"
  auto_generate:
    from: "iteration_traces"
    fields: ["batch", "iteration", "scenario", "dimension", "delta"]
  breaking_change_detection:
    - interface_field_removed
    - output_schema_changed
    - workflow_step_removed
```

### 3.2 版本号规则

- 主版本(MAJOR)：体系架构变更(如新增评估维度)
- 次版本(MINOR)：新增场景/工作流/行业适配
- 修订版(PATCH)：场景模板优化/bug修复
- 示例：v6.0.0 → v6.1.0(新增场景) → v6.1.1(优化修复)

### 3.3 发布检查清单

- [ ] 全量回归测试通过
- [ ] 十维度评估均分≥18.5
- [ ] 注入防御测试通过
- [ ] 互操作性端到端验证通过
- [ ] CHANGELOG已更新
- [ ] 方法论文档已同步
- [ ] 知识图谱已更新
- [ ] API文档已同步
- [ ] 基线数据已归档
