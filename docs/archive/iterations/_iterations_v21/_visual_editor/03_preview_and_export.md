# R1-03 提示词可视化编辑器-实时预览与导出

> **迭代**：v21-R1-03 | **日期**：2026-07-12

---

## 一、实时预览系统

### 预览渲染管线

```
节点配置 → 模板引擎 → Markdown中间层 → 渲染器 → 预览面板
    ↑                              ↓
    └────── 差量更新 ←────── Diff引擎
```

### 三种预览模式

| 模式 | 说明 | 延迟 |
|------|------|------|
| 即时预览 | 每次变更300ms后刷新 | 300ms |
| 节省模式 | 手动点击刷新 | 手动 |
| 分屏预览 | 左编辑右预览同步滚动 | 实时 |

### 预览内容验证

```typescript
interface PreviewValidation {
  tokenCount: number          // Token计数
  tokenWarning: boolean       // >4000告警
  structureComplete: boolean  // 结构完整性
  missingSections: string[]   // 缺失章节
  placeholderRemains: boolean // 未替换占位符
  estimatedCost: number       // 预估成本
  estimatedLatency: number    // 预估延迟
}
```

## 二、导出系统

### 5种导出格式

| 格式 | 说明 | 文件扩展名 |
|------|------|-----------|
| Markdown | GFM格式 | .md |
| JSON | 结构化数据 | .json |
| YAML | 声明式配置 | .yaml |
| PDF | 排版输出 | .pdf |
| UPPL | 提示词编程语言 | .uppl |

### 导出模板

```typescript
interface ExportTemplate {
  format: 'markdown' | 'json' | 'yaml' | 'pdf' | 'uppl'
  header?: string
  sectionOrder: string[]
  includeMetadata: boolean
  includeTableOfContents: boolean
  includeChangelog: boolean
  customFields: Record<string, string>
}
```

### Markdown导出示例

```markdown
---
title: "{场景名}"
version: "1.0.0"
category: "{分类}"
author: "{作者}"
created: "{日期}"
tokens: {token数}
---

# {场景名}

## 前置知识
{前置知识内容}

## 场景描述
{场景内容}

## 常见陷阱
| # | 陷阱 | 严重等级 | 规避方案 |
|---|------|---------|---------|

## 性能提示
| # | 提示 | 效果 | 实施难度 |
|---|------|------|---------|

## 安全提示
| # | 提示 | 威胁类型 | 严重等级 |
|---|------|---------|---------|

## 请输出
1. {输出项1}（格式：{格式要求}）
2. {输出项2}（格式：{格式要求}）

## 扩展阅读
- [{资源名}]({URL})
```

## 三、版本管理

### 自动版本控制

```typescript
interface EditorVersion {
  version: string           // 语义化版本
  parentVersion?: string    // 父版本
  changelog: string         // 变更说明
  diff?: string             // 与父版本Diff
  createdAt: string
  author: string
  tags: string[]
}
```

### 版本操作

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 保存版本 | Ctrl+S | 自动递增补丁版本 |
| 保存主版本 | Ctrl+Shift+S | 手动指定版本号 |
| 历史浏览 | Ctrl+H | 版本时间线 |
| 版本对比 | Ctrl+D | Diff视图 |
| 回滚版本 | Ctrl+Z | 恢复到指定版本 |
| 分支创建 | Ctrl+B | 从当前版本创建分支 |

## 四、验收项

- [x] 实时预览3种模式+渲染管线
- [x] 预览内容验证8项指标
- [x] 5种导出格式+模板系统
- [x] Markdown导出完整模板
- [x] 版本管理6种操作+数据结构
