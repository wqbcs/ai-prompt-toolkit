# 变更传播报告模板

> **版本**: v1.0.0 | **日期**: 2026-07-12

---

## 一、PropagationReport数据结构

```typescript
interface PropagationReport {
  parent_id: string;
  parent_name: string;
  changed_fields: FieldChange[];
  change_timestamp: string;  // ISO 8601
  impact_items: ImpactItem[];
  conflict_items: ConflictItem[];
  total_affected: number;
  max_depth: number;
}

interface FieldChange {
  field_path: string;
  old_value: any;
  new_value: any;
  change_type: "added" | "modified" | "removed";
}

interface ImpactItem {
  child_id: string;
  child_name: string;
  depth: number;                  // 距离父模板的继承深度
  affected_fields: string[];      // 受影响的字段路径
  impact_level: "high" | "medium" | "low";
  current_status: "active" | "broken" | "conflict";
}

interface ConflictItem {
  field_name: string;
  parent_new_value: any;
  child_current_value: any;
  conflict_type: "value_mismatch" | "semantic_contradiction" | "structure_inconsistency";
  suggestion: string;
}
```

## 二、影响级别判定规则

| 级别 | 条件 | 处理 |
|------|------|------|
| 高 | 父模板修改了被子模板覆盖的字段，且子模板未同步更新 | 需立即处理，可能导致子模板行为异常 |
| 中 | 父模板新增了子模板中已有的同名字段 | 需关注，可能导致语义冲突 |
| 低 | 父模板修改了子模板未覆盖的字段 | 自动传播，无需人工干预 |

### 2.1 影响级别判定算法

```
FOR each changed_field IN parent.changes:
    FOR each child IN parent.children:
        IF changed_field IN child.overrides:
            impact_level = "high"
            reason = "子模板覆盖了被修改的字段，需检查覆盖值是否仍有效"
        ELIF changed_field.field_path IN child.extensions:
            impact_level = "medium"
            reason = "子模板扩展了相关字段，需检查一致性"
        ELSE:
            impact_level = "low"
            reason = "修改自动传播到子模板"
```

## 三、影响分析报告模板

```markdown
# 变更传播影响分析报告

> 父模板: {parent_name} ({parent_id})
> 变更时间: {change_timestamp}
> 受影响模板总数: {total_affected}
> 最大影响深度: {max_depth}

---

## 一、变更字段清单

| 字段路径 | 变更类型 | 旧值 | 新值 |
|----------|----------|------|------|
| {field_path_1} | {change_type_1} | {old_1} | {new_1} |
| {field_path_2} | {change_type_2} | {old_2} | {new_2} |

## 二、受影响模板

### 高影响

| 子模板 | 深度 | 受影响字段 | 当前状态 | 建议操作 |
|--------|------|------------|----------|----------|
| {child_id} | {depth} | {affected_fields} | {status} | 检查覆盖值有效性 |

### 中影响

| 子模板 | 深度 | 受影响字段 | 当前状态 | 建议操作 |
|--------|------|------------|----------|----------|
| {child_id} | {depth} | {affected_fields} | {status} | 检查语义一致性 |

### 低影响

| 子模板 | 深度 | 受影响字段 | 当前状态 | 建议操作 |
|--------|------|------------|----------|----------|
| {child_id} | {depth} | {affected_fields} | {status} | 自动传播 |

## 三、冲突项

| 字段 | 父模板新值 | 子模板当前值 | 冲突类型 | 建议 |
|------|------------|--------------|----------|------|
| {field} | {parent_val} | {child_val} | {type} | {suggestion} |

## 四、传播路径

```
{parent_name} (变更源头)
├── {child_1} (高影响, depth=1)
│   ├── {grandchild_1} (中影响, depth=2)
│   └── {grandchild_2} (低影响, depth=2)
├── {child_2} (低影响, depth=1)
└── {child_3} (中影响, depth=1)
```

## 五、建议操作清单

- [ ] {action_1}
- [ ] {action_2}
- [ ] {action_3}

---

*报告由模板继承引擎自动生成 | {generated_at}*
```

## 四、变更传播触发机制

| 触发事件 | 处理方式 |
|----------|----------|
| 父模板内容修改 | 自动检测所有子模板影响，生成传播报告 |
| 父模板删除 | 所有子模板标记为broken，生成断裂报告 |
| 父模板废弃 | 通知所有子模板，建议迁移到新父模板 |
| 父模板恢复 | 检查broken子模板是否可恢复 |
