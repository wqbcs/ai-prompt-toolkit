# 跨域共性模式与通用框架 v1.0

> **日期**：2026-05-29

---

## 7个跨域共性模式

### 模式1：术语锁定

```yaml
pattern: term_lock
description: "领域术语不可替换，必须原样使用"
domains: [法律, 医疗, 教育, 科研]
implementation: |
  1. 建立领域术语表(术语→定义→不可替换标记)
  2. 提示词中注入术语锁定指令
  3. 输出验证检查术语是否被替换
example: |
  [MUST] 以下术语必须原样使用，不可替换：
  - "缔约过失责任"(不可替换为"签合同出问题的责任")
  - "禁忌症"(不可替换为"不能用的情况")
```

### 模式2：合规清单

```yaml
pattern: compliance_checklist
description: "每个场景必须有合规检查清单"
domains: [法律, 医疗, 教育, 科研]
implementation: |
  1. 建立领域合规清单(合规项→法规依据→检查方法)
  2. 提示词中注入合规检查指令
  3. 输出必须包含合规状态报告
example: |
  [MUST] 执行合规检查清单：
  - [ ] 个人信息保护(个保法第5-10条)
  - [ ] 数据跨境传输(个保法第38条)
  ...
```

### 模式3：安全红线

```yaml
pattern: safety_redline
description: "高风险领域硬约束，不可违反"
domains: [法律, 医疗]
implementation: |
  1. 定义安全红线项目(零容忍项)
  2. 提示词中[MUST]标记安全红线
  3. 违反红线时拒绝执行+告警
example: |
  [MUST] 安全红线：
  - 药物剂量不得超过最大安全剂量
  - 禁忌症药物绝对不可开具
  - 过敏史药物绝对不可使用
```

### 模式4：不确定性表达

```yaml
pattern: uncertainty_expression
description: "不确定性必须显式标注，分级表达"
domains: [法律, 医疗, 科研]
implementation: |
  1. 定义置信度等级(高/中/低)
  2. 提示词中要求标注置信度
  3. 低置信度结果必须提供不确定性来源
example: |
  [MUST] 每个诊断/结论必须标注置信度：
  - 高(>90%): 强推荐
  - 中(70-90%): 弱推荐，建议进一步验证
  - 低(<70%): 仅参考，必须人工确认
```

### 模式5：多模式输出

```yaml
pattern: multi_mode_output
description: "根据受众适配输出模式"
domains: [医疗, 教育]
implementation: |
  1. 定义输出模式(专业/通俗/教学)
  2. 提示词中注入模式选择指令
  3. 同一内容提供多模式输出
example: |
  [SHOULD] 提供双模式输出：
  - 专业模式(医生间交流): 使用标准医学术语
  - 通俗模式(医生-患者): 使用通俗语言+比喻
```

### 模式6：批判性思维

```yaml
pattern: critical_thinking
description: "批判分析>简单总结"
domains: [法律, 教育, 科研]
implementation: |
  1. 提示词中注入批判性思维指令
  2. 要求分析局限性/偏见/替代解释
  3. 禁止仅做简单总结
example: |
  [MUST] 必须包含批判性分析：
  - 局限性分析(方法/数据/结论)
  - 替代解释(是否有其他解释)
  - 偏见评估(选择偏见/确认偏见)
  [MUST] 不可仅做简单总结
```

### 模式7：版本追溯

```yaml
pattern: version_traceability
description: "变更完整追溯链"
domains: [法律, 医疗, 科研]
implementation: |
  1. 每次变更记录(时间+原因+影响)
  2. 维护变更历史链
  3. 支持回溯到任意版本
example: |
  [MUST] 记录变更追溯：
  - 变更时间: 2026-05-29
  - 变更原因: 法规更新(个保法修正案)
  - 影响范围: 数据保护合规检查
  - 前版本: v1.2.3
```

---

## 通用跨域模板框架

```yaml
cross_domain_template:
  structure:
    - role: "领域专家角色定义"
    - constraints: "[MUST/SHOULD/MAY]约束指令"
    - safety_redlines: "安全红线(如适用)"
    - compliance_checklist: "合规检查清单"
    - input_spec: "输入规范"
    - output_format: "输出格式(Schema)"
    - term_lock: "术语锁定表"
    - examples: "示例(5个)"
    - glossary: "领域术语表"
    - compliance: "合规清单"
  
  domain_config:
    type: "yaml"
    fields:
      - domain_name: "领域名称"
      - term_glossary: "术语表文件路径"
      - compliance_list: "合规清单文件路径"
      - safety_redlines: "安全红线文件路径"
      - bloom_level: "布鲁姆层级(教育)"
      - regulation_system: "法规体系(法律)"
      - safety_standard: "安全标准(医疗)"
      - academic_standard: "学术标准(科研)"
  
  adaptation_guide:
    steps:
      - "1. 选择最接近的领域模板"
      - "2. 替换领域配置(domain_config.yaml)"
      - "3. 自定义术语表和合规清单"
      - "4. 调整安全红线(如适用)"
      - "5. 测试5个示例场景"
      - "6. 验证合规清单覆盖"
```
