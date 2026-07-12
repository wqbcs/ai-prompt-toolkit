# 模板继承元数据Schema

> **版本**: v1.0.0 | **日期**: 2026-07-12 | **参考**: Fabric Pattern链式调用

---

## 一、InheritanceMeta数据结构

```typescript
interface InheritanceMeta {
  enabled: boolean;                    // 是否启用继承
  parent_template: string | null;      // 父模板ID（仅1个）
  depth: number;                       // 当前继承深度（0=根模板）
  overrides: OverrideField[];          // 覆盖字段列表
  extensions: ExtensionField[];        // 扩展字段列表
}

interface OverrideField {
  field_path: string;      // 字段路径（支持嵌套：section.subsection.field）
  parent_value: any;       // 父模板中的值
  child_value: any;        // 子模板覆盖后的值
  reason: string;          // 覆盖原因
}

interface ExtensionField {
  field_path: string;      // 新增字段路径
  value: any;              // 新增字段的值
  reason: string;          // 新增原因
}
```

## 二、单继承规则

### 2.1 基本约束

| 规则 | 说明 |
|------|------|
| 单继承 | 每个模板只能继承1个父模板 |
| 深度限制 | 继承链深度不超过5层 |
| 禁止循环 | 不允许A→B→A循环继承 |
| 根模板 | depth=0的模板无父模板 |

### 2.2 继承链示例

```
根模板(base-code-review)           depth=0
  └── 专项模板(go-code-review)     depth=1
       └── 行业模板(fin-go-review) depth=2  ✅ 深度≤5
```

```
根模板(base-code-review)           depth=0
  └── 专项模板(go-code-review)     depth=1
       └── 行业模板(fin-go-review) depth=2
            └── 合规模板(reg-go-review) depth=3
                 └── 区域模板(cn-reg-go-review) depth=4
                      └── 极致模板(cn-reg-go-review-v2) depth=5  ✅ 刚好≤5
                      　　└── 深度6模板 ✗ 不允许
```

## 三、覆盖字段规则

### 3.1 覆盖语义

- 子模板可以**覆盖**父模板中已存在的字段
- 覆盖时**子优先**：子模板的值覆盖父模板的值
- 覆盖必须提供`reason`说明覆盖原因

### 3.2 可覆盖字段类型

| 字段类型 | 覆盖方式 | 示例 |
|----------|----------|------|
| 字符串 | 完全替换 | 角色描述从"代码审查员"→"Go代码审查专家" |
| 数组 | 完全替换或追加 | 陷阱项从5个→7个 |
| 对象 | 深度合并 | 元数据中的tags字段 |
| 数字 | 完全替换 | max_tokens从4096→8192 |

### 3.3 覆盖示例

```yaml
inheritance:
  enabled: true
  parent_template: "base-code-review"
  depth: 1
  overrides:
    - field_path: "role_description"
      parent_value: "你是一名代码审查专家"
      child_value: "你是一名Go语言代码审查专家，精通Go并发模型和性能优化"
      reason: "Go语言特殊性需要强调并发和性能"
    - field_path: "traps[0]"
      parent_value: "代码逻辑错误"
      child_value: "goroutine泄露"
      reason: "Go特有的并发陷阱"
```

## 四、扩展字段规则

### 4.1 扩展语义

- 子模板可以**新增**父模板中不存在的字段
- 扩展是追加操作，不影响父模板已有内容
- 扩展必须提供`reason`说明新增原因

### 4.2 扩展示例

```yaml
inheritance:
  enabled: true
  parent_template: "base-code-review"
  depth: 1
  extensions:
    - field_path: "go_specific.traps"
      value:
        - "goroutine泄露"
        - "channel死锁"
        - "interface空指针"
      reason: "Go语言特有陷阱"
    - field_path: "go_specific.performance"
      value:
        - "GC压力"
        - "内存分配优化"
      reason: "Go性能优化专项"
```

## 五、YAML Front Matter示例模板

```yaml
---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
tags:
  - code-review
  - golang
  - concurrency
applicable_models:
  - gpt-4o
  - claude-3.5-sonnet
  - qwen-max
  - pangu-large
inheritance:
  enabled: true
  parent_template: "base-code-review"
  depth: 1
  overrides:
    - field_path: "role_description"
      reason: "Go语言专业性"
    - field_path: "tags"
      reason: "新增Go相关标签"
  extensions:
    - field_path: "go_specific"
      reason: "Go语言专项内容"
---
```

## 六、元数据校验规则

| 校验项 | 规则 | 错误级别 |
|--------|------|----------|
| parent_template存在性 | 父模板ID必须在模板仓库中存在 | error |
| 单继承 | parent_template最多1个 | error |
| 深度限制 | depth ≤ 5 | error |
| 循环继承 | 不允许A→B→A | error |
| overrides字段存在性 | field_path必须在父模板中存在 | warning |
| extensions字段唯一性 | field_path不能在父模板中已存在 | warning |
| reason必填 | 覆盖和扩展必须提供reason | warning |
| enabled一致性 | enabled=true时parent_template不能为null | error |
