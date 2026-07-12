---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
tags: [changelog, template, version-diff, breaking-change]
applicable_models: [gpt-4o, claude-3.5-sonnet, qwen-max, pangu-large]
inheritance:
  enabled: false
---

# 版本变更日志模板

## 概述

本模板定义提示词体系变更日志的标准格式规范，确保版本演进过程的可追溯性和可读性。所有版本变更必须遵循此模板生成变更日志，输出格式符合 `version_diff_report.schema.json` 定义。

---

## 一、变更日志格式规范

### 1.1 文件命名

```
CHANGELOG-{template_id}.md
```

示例：`CHANGELOG-e1_deh.md`

### 1.2 整体结构

```markdown
# 变更日志 — {模板名称}

所有本模板的版本变更记录。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [{版本号}] - {发布日期}

### Breaking Changes
- **{影响范围}**：{变更描述}（#{关联Issue}）

### Features
- **{功能模块}**：{新增描述}（#{关联Issue}）

### Fixes
- **{修复模块}**：{修复描述}（#{关联Issue}）

---

## [1.0.0] - 2026-07-12

### Features
- **初始版本**：模板首次发布
```

### 1.3 变更条目格式

每条变更遵循统一格式：

```
- **{影响范围/模块}**：{变更描述}（#{可选关联}）
```

- **影响范围**：标注变更影响的模块或功能区域（如"陷阱5"、"安全2"、"YAML Front Matter"）
- **变更描述**：简洁描述具体变更内容，使用动词开头（新增/修改/删除/修复/回滚）
- **关联信息**：可选，关联 Issue/PR 编号或关联版本号

---

## 二、变更分类标准

### 2.1 Breaking Changes（破坏性变更）

**定义**：导致现有使用方式不兼容的变更，用户必须调整使用方式才能正常工作。

**判定标准**：

| 变更类型 | 判定为 Breaking 的条件 |
|---------|----------------------|
| 删除字段 | 删除 YAML Front Matter 中已有字段 |
| 删除章节 | 删除整个二级/三级标题章节 |
| 修改结构 | 调整模板的 5+5+3+5+3+3 结构顺序或数量 |
| 重命名 | 重命名标签、分类或核心术语 |
| 修改继承 | 修改 inheritance 配置导致继承链变更 |
| 类型变更 | 修改字段的数据类型（如 string → array） |

**示例**：

```markdown
### Breaking Changes
- **YAML Front Matter**：删除 `deprecated_field` 字段，迁移至 `new_field`（#42）
- **安全章节**：安全加固项从3项调整为4项，新增"运行时安全"分类
```

### 2.2 Features（功能新增）

**定义**：向后兼容的新增功能或增强。

**判定标准**：

| 变更类型 | 示例 |
|---------|------|
| 新增章节 | 新增"已知限制"章节 |
| 新增条目 | 陷阱项从5项增至6项 |
| 新增标签 | tags 中增加新标签 |
| 新增参数 | YAML Front Matter 增加可选字段 |
| 功能增强 | 现有条目增加子项或补充说明 |

**示例**：

```markdown
### Features
- **故障排查**：新增故障6"集群升级回滚失败"排查流程
- **替代方案**：新增成本对比维度，补充3年TCO分析
```

### 2.3 Fixes（问题修复）

**定义**：向后兼容的错误修正或内容纠正。

**判定标准**：

| 变更类型 | 示例 |
|---------|------|
| 技术纠错 | 修正错误的 API 路径或参数名 |
| 链接修复 | 修复失效的文档链接 |
| 描述修正 | 纠正不准确的性能数据或限制说明 |
| 格式修正 | 修复 Markdown 格式错误 |

**示例**：

```markdown
### Fixes
- **陷阱3**：修正资源超分建议，vCPU超分比例从3:1调整为2:1
- **替代方案表格**：修复SLA数据错误，DEH的SLA从99.99%修正为99.95%
```

---

## 三、版本差异报告格式

版本差异报告输出遵循 `_schemas/version_diff_report.schema.json` 定义，用于程序化处理版本对比结果。

### 3.1 报告结构

```json
{
  "report_id": "uuid-v4",
  "template_id": "e1_deh",
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "generated_at": "2026-07-12T10:30:00Z",
  "summary": {
    "total_changes": 8,
    "breaking_changes": 1,
    "features": 4,
    "fixes": 3,
    "stats": {
      "added_lines": 35,
      "removed_lines": 12,
      "modified_lines": 8,
      "unchanged_lines": 195
    }
  },
  "breaking_changes": [
    {
      "scope": "YAML Front Matter",
      "description": "删除 deprecated_field 字段",
      "migration_note": "迁移至 new_field 字段",
      "hunk_ref": "hunk_3",
      "lines_affected": [5, 6]
    }
  ],
  "features": [
    {
      "scope": "故障排查",
      "description": "新增故障6排查流程",
      "hunk_ref": "hunk_7",
      "lines_affected": [156, 170]
    }
  ],
  "fixes": [
    {
      "scope": "陷阱3",
      "description": "修正vCPU超分比例建议",
      "hunk_ref": "hunk_5",
      "lines_affected": [43]
    }
  ],
  "diff_engine": {
    "algorithm": "myers",
    "context_lines": 3,
    "hunks": [
      {
        "id": "hunk_1",
        "old_start": 1,
        "old_count": 9,
        "new_start": 1,
        "new_count": 9,
        "classification": "metadata"
      }
    ],
    "unified_diff": "--- 1.0.0\n+++ 1.1.0\n@@ -1,9 +1,9 @@\n..."
  }
}
```

### 3.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `report_id` | string | 是 | 报告唯一标识（UUID v4） |
| `template_id` | string | 是 | 模板标识 |
| `from_version` | string | 是 | 源版本号 |
| `to_version` | string | 是 | 目标版本号 |
| `generated_at` | string | 是 | 报告生成时间（ISO 8601） |
| `summary` | object | 是 | 变更汇总统计 |
| `breaking_changes` | array | 是 | 破坏性变更列表（可为空） |
| `features` | array | 是 | 新增功能列表（可为空） |
| `fixes` | array | 是 | 修复列表（可为空） |
| `diff_engine` | object | 是 | 差异引擎原始输出 |

### 3.3 变更条目字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scope` | string | 是 | 影响范围/模块 |
| `description` | string | 是 | 变更描述 |
| `migration_note` | string | 否 | 迁移说明（仅 Breaking Changes） |
| `hunk_ref` | string | 是 | 关联的 diff hunk 标识 |
| `lines_affected` | array[int] | 是 | 受影响的行号列表 |

---

## 四、变更日志模板实例

以下为完整的变更日志模板，供新模板复制使用：

```markdown
# 变更日志 — {模板名称}

所有本模板的版本变更记录。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Breaking Changes

### Features

### Fixes

---

## [1.0.0] - {发布日期}

### Features
- **初始版本**：模板首次发布，覆盖{覆盖范围简述}
```

### 使用说明

1. 新建模板时，复制上述模板实例
2. 填写 `[1.0.0]` 的发布日期和初始版本描述
3. 后续变更在 `[Unreleased]` 区段下对应分类中添加条目
4. 发布版本时，将 `[Unreleased]` 替换为 `[新版本号] - 发布日期`
5. 变更日志与版本快照同步存储于 `_versions/snapshots/` 目录
