# 模板合并引擎

> **版本**: v1.0.0 | **日期**: 2026-07-12 | **参考**: Fabric Pattern合并策略

---

## 一、合并策略

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| 子优先覆盖 | 子模板已有字段覆盖父模板同名字段 |
| 扩展追加 | 子模板新增字段追加到父模板内容之后 |
| 深度合并 | 对象类型字段递归合并 |
| 数组策略 | 数组默认完全替换，可配置为追加 |

### 1.2 合并顺序

```
1. 读取父模板完整内容
2. 应用子模板的覆盖字段（overrides）
3. 应用子模板的扩展字段（extensions）
4. 执行Token限制检查
5. 执行冲突检测
6. 生成合并结果
```

## 二、YAML Front Matter合并规则

### 2.1 字符串字段

```
规则: 完全替换
父: version: "1.0.0"
子: overrides: [{field_path: "version", child_value: "2.0.0"}]
结果: version: "2.0.0"
```

### 2.2 数组字段

```
规则: 默认完全替换，可配置追加
父: tags: ["code-review", "golang"]
子: overrides: [{field_path: "tags", child_value: ["code-review", "golang", "concurrency"]}]
结果: tags: ["code-review", "golang", "concurrency"]

追加模式:
子: extensions: [{field_path: "tags", value: ["concurrency"], strategy: "append"}]
结果: tags: ["code-review", "golang", "concurrency"]
```

### 2.3 对象字段

```
规则: 深度合并
父: applicable_models: {primary: "gpt-4o", secondary: "claude-3.5"}
子: overrides: [{field_path: "applicable_models.secondary", child_value: "qwen-max"}]
结果: applicable_models: {primary: "gpt-4o", secondary: "qwen-max"}
```

## 三、正文内容合并规则

### 3.1 章节合并

```
规则:
- 父子共有章节: 子模板内容覆盖父模板
- 父有子无的章节: 保留父模板内容
- 子有父无的章节: 追加到末尾

示例:
父模板章节: [概述, 陷阱, 性能, 安全, 故障排查, 替代方案]
子模板覆盖: [陷阱(新增2项), 性能(完全替换)]
结果: [概述(父), 陷阱(子), 性能(子), 安全(父), 故障排查(父), 替代方案(父)]
```

### 3.2 陷阱项合并

```
父模板陷阱5项: [T1, T2, T3, T4, T5]
子模板覆盖陷阱项: [T2', T3'] (覆盖第2、3项)
子模板扩展陷阱项: [T6, T7] (新增第6、7项)
结果: [T1, T2', T3', T4, T5, T6, T7]
```

## 四、Token限制检查

### 4.1 检查规则

```
合并后Token数 = 父模板Token数 - 被覆盖字段Token数 + 覆盖字段Token数 + 扩展字段Token数

IF 合并后Token数 > 模型Token上限:
    标注: "⚠️ 合并后Token数({merged_tokens})超出模型上限({model_limit})"
    建议: "考虑裁剪以下章节: {suggested_cuts}"
    严重度: warning (不阻止合并)
```

### 4.2 裁剪建议策略

```
1. 优先裁剪"替代方案"章节（信息密度最低）
2. 其次裁剪"已知限制"章节（非核心内容）
3. 最后裁剪"故障排查"章节的部分条目
4. 保留"陷阱"和"性能"章节（核心价值最高）
```

## 五、冲突检测

### 5.1 冲突类型

| 冲突类型 | 说明 | 示例 |
|----------|------|------|
| 字段值冲突 | 父模板新增字段与子模板已有字段同名 | 父新增tags中"security"，子已有"security"但值不同 |
| 语义冲突 | 覆盖内容与父模板其他内容语义矛盾 | 子覆盖角色为"安全审计"，但父模板陷阱项全关于性能 |
| 结构冲突 | 扩展字段导致结构不一致 | 父模板3层结构，子扩展导致4层 |

### 5.2 冲突检测逻辑

```
FOR each override in child.overrides:
    parent_field = getNestedField(parent, override.field_path)
    IF parent_field == null:
        标注: "覆盖字段{field_path}在父模板中不存在，应为扩展"
        severity: warning

FOR each extension in child.extensions:
    parent_field = getNestedField(parent, extension.field_path)
    IF parent_field != null:
        标注: "扩展字段{field_path}在父模板中已存在，应为覆盖"
        severity: error

FOR each field in parent (after parent update):
    IF field在child.overrides中:
        检查新值是否与child其他内容矛盾
```

### 5.3 冲突报告格式

```markdown
## 合并冲突报告

> 模板: {child_id} | 父模板: {parent_id} | 检测时间: {timestamp}

### 错误级冲突

| 字段 | 冲突类型 | 父模板值 | 子模板值 | 建议 |
|------|----------|----------|----------|------|
| {field} | {type} | {parent_val} | {child_val} | {suggestion} |

### 警告级冲突

| 字段 | 冲突类型 | 说明 | 建议 |
|------|----------|------|------|
| {field} | {type} | {description} | {suggestion} |
```

## 六、合并性能

| 指标 | 目标 | 说明 |
|------|------|------|
| 合并响应时间 | ≤ 200ms | 单次合并操作 |
| 深度合并递归 | ≤ 5层 | 对应继承深度限制 |
| 内存占用 | ≤ 50MB | 单次合并 |
| 缓存合并结果 | 可选 | 相同继承链不重复计算 |
