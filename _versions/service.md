---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
tags: [version, semver, diff, rollback, lock]
applicable_models: [gpt-4o, claude-3.5-sonnet, qwen-max, pangu-large]
inheritance:
  enabled: false
---

# 版本管理服务设计

## 概述

版本管理服务（VersionService）是 `_versions` 引擎的核心服务层，提供提示词模板全生命周期的版本控制能力。基于语义化版本号（SemVer）追踪变更历史，支持行级差异对比、安全回滚与状态锁定机制。

---

## 一、VersionService 接口定义

### 1.1 create — 创建版本

```
create(template_id: str, content: str, change_type: ChangeType, message: str) -> Version
```

- **入参**：
  - `template_id`：模板唯一标识
  - `content`：模板内容全文
  - `change_type`：变更类型枚举（`major` / `minor` / `patch`）
  - `message`：变更说明
- **行为**：
  - 基于当前最新版本号，按 `change_type` 递增生成新版本号
  - 存储完整内容快照至版本存储层
  - 生成差异增量（与上一版本的 diff）
  - 若当前最新版本处于 `review` 或 `canary` 锁定状态，拒绝创建并返回 `VersionLockError`
- **输出**：`Version` 对象（含 `version_id`, `version_number`, `created_at`, `diff_from_previous`）
- **异常**：
  - `VersionLockError`：当前版本已锁定
  - `InvalidChangeTypeError`：change_type 不合法
  - `TemplateNotFoundError`：template_id 不存在

### 1.2 list — 版本列表

```
list(template_id: str, page: int = 1, page_size: int = 20, order: SortOrder = DESC) -> VersionList
```

- **入参**：
  - `template_id`：模板唯一标识
  - `page` / `page_size`：分页参数
  - `order`：排序方向（`DESC` 默认最新在前，`ASC` 最早在前）
- **行为**：
  - 查询指定模板的所有版本记录
  - 返回分页结果，每条记录包含版本号、创建时间、变更类型、锁定状态、变更摘要
- **输出**：`VersionList`（含 `items`, `total`, `page`, `page_size`）

### 1.3 get — 获取版本

```
get(template_id: str, version_number: str) -> VersionDetail
```

- **入参**：
  - `template_id`：模板唯一标识
  - `version_number`：语义化版本号（如 `1.2.3`）
- **行为**：
  - 返回指定版本的完整详情，包括内容全文、元数据、锁定状态
- **输出**：`VersionDetail`（含 `content`, `metadata`, `lock_status`, `snapshot_ref`）
- **异常**：
  - `VersionNotFoundError`：版本号不存在

### 1.4 diff — 版本差异对比

```
diff(template_id: str, from_version: str, to_version: str, context_lines: int = 3) -> DiffResult
```

- **入参**：
  - `template_id`：模板唯一标识
  - `from_version`：源版本号
  - `to_version`：目标版本号
  - `context_lines`：差异上下文行数
- **行为**：
  - 调用 DiffEngine 执行行级差异计算
  - 输出符合 `version_diff_report.schema.json` 格式的差异报告
- **输出**：`DiffResult`（含 `added`, `modified`, `removed`, `unified_diff`, `stats`）
- **异常**：
  - `VersionNotFoundError`：任一版本号不存在

### 1.5 rollback — 版本回滚

```
rollback(template_id: str, target_version: str, reason: str) -> Version
```

- **入参**：
  - `template_id`：模板唯一标识
  - `target_version`：回滚目标版本号
  - `reason`：回滚原因
- **行为**：
  - 从目标版本恢复内容，创建新版本（版本号继续递增，不重复使用旧版本号）
  - 目标版本内容不可删除，仅创建新版本指向旧内容
  - 在变更日志中标记为 `rollback` 类型，关联源版本和目标版本
  - 若当前版本处于锁定状态，拒绝回滚并返回 `VersionLockError`
- **输出**：新 `Version` 对象
- **异常**：
  - `VersionLockError`：当前版本已锁定
  - `VersionNotFoundError`：目标版本不存在
  - `RollbackToCurrentError`：目标版本即为当前版本

---

## 二、语义化版本号（SemVer）

### 2.1 版本号格式

遵循 [Semantic Versioning 2.0.0](https://semver.org/) 规范：

```
MAJOR.MINOR.PATCH
```

- **MAJOR**：不兼容的 API 变更（Breaking Change）
- **MINOR**：向后兼容的功能新增
- **PATCH**：向后兼容的问题修复

### 2.2 递增规则

| 变更类型 | 递增规则 | 示例 |
|---------|---------|------|
| `major` | MAJOR+1，MINOR/PATCH 归零 | 1.2.3 → 2.0.0 |
| `minor` | MINOR+1，PATCH 归零 | 1.2.3 → 1.3.0 |
| `patch` | PATCH+1 | 1.2.3 → 1.2.4 |
| `rollback` | PATCH+1（内容回退到目标版本） | 1.2.4 → 1.2.5（内容同 1.2.3） |

### 2.3 预发布标识

支持预发布版本标注：

```
MAJOR.MINOR.PATCH-PRERELEASE
```

- `1.0.0-alpha`：内部测试
- `1.0.0-beta`：公测
- `1.0.0-rc.1`：候选发布

预发布版本不参与锁定机制，不触发快照归档。

---

## 三、行级差异对比（DiffEngine）

### 3.1 算法选择

基于 Myers diff 算法实现行级差异计算，特点：

- 最小化编辑脚本（最短差异优先）
- 时间复杂度 O(ND)，N 为文件总行数，D 为差异行数
- 对提示词模板场景（通常 < 2000 行）性能优异

### 3.2 Diff 输出格式

```json
{
  "from_version": "1.1.0",
  "to_version": "1.2.0",
  "stats": {
    "added_lines": 15,
    "removed_lines": 3,
    "modified_lines": 7,
    "unchanged_lines": 180
  },
  "hunks": [
    {
      "old_start": 42,
      "old_count": 5,
      "new_start": 42,
      "new_count": 8,
      "lines": [
        {"type": "context", "content": "## 概述"},
        {"type": "removed", "content": "旧内容行"},
        {"type": "added", "content": "新内容行"},
        {"type": "context", "content": "## 详情"}
      ]
    }
  ],
  "unified_diff": "--- 1.1.0\n+++ 1.2.0\n@@ -42,5 +42,8 @@\n..."
}
```

### 3.3 Diff 分类标注

差异行自动分类标注：

| 标注 | 说明 | 匹配规则 |
|------|------|---------|
| `breaking` | 破坏性变更 | 删除或修改 YAML Front Matter 字段、删除章节标题 |
| `feature` | 功能新增 | 新增章节、新增 YAML 字段 |
| `fix` | 修复 | 替换陷阱/故障排查中的具体技术内容 |
| `refactor` | 重构 | 段落移动、措辞调整但语义不变 |

---

## 四、版本回滚机制

### 4.1 核心原则

- **禁止删除历史**：任何版本的快照数据不可物理删除，确保审计追溯完整性
- **回滚即新建**：回滚操作不修改历史版本，而是创建新版本指向目标版本的内容
- **回滚链追踪**：变更日志中记录完整的回滚链路（`rollback_from` → `rollback_to`）

### 4.2 回滚流程

```
当前版本: 1.3.0（存在问题）
目标版本: 1.2.0（已知稳定）

执行 rollback(template_id, "1.2.0", "1.3.0 引入兼容性问题"):

1. 校验当前版本未锁定
2. 读取 1.2.0 版本内容快照
3. 创建新版本 1.3.1，内容 = 1.2.0 内容副本
4. 变更日志记录:
   - version: 1.3.1
   - change_type: rollback
   - rollback_from: 1.3.0
   - rollback_to: 1.2.0
   - reason: "1.3.0 引入兼容性问题"
5. 1.3.0 版本标记为 rollback_source，但内容保留
```

### 4.3 回滚保护

- 连续回滚检测：若新版本创建后 5 分钟内再次回滚，触发人工确认
- 回滚深度限制：不支持跨 MAJOR 版本回滚（如从 2.x 回滚到 1.x），需走迁移流程
- 回滚后验证：回滚完成后自动运行验证测试，确认内容一致性

---

## 五、锁定机制

### 5.1 锁定状态

| 状态 | 触发条件 | 锁定范围 | 解锁条件 |
|------|---------|---------|---------|
| `review` | 版本提交评审 | 禁止创建新版本、禁止回滚 | 评审通过/驳回 |
| `canary` | 版本进入灰度 | 禁止创建新版本、禁止回滚 | 灰度完成（全量/回退） |
| `released` | 版本正式发布 | 禁止修改内容（可创建新版本） | 无需解锁 |

### 5.2 锁定行为

```
lock(template_id: str, version_number: str, status: LockStatus) -> LockResult
unlock(template_id: str, version_number: str, reason: str) -> LockResult
```

- 锁定期间 `create` 和 `rollback` 接口返回 `VersionLockError`
- `get` 和 `list` 接口不受锁定影响
- 锁定操作本身记录审计日志

### 5.3 锁定超时

- `review` 锁定默认超时 72 小时，超时后自动解锁并通知提交者
- `canary` 锁定默认超时 7 天，超时后自动回退灰度并解锁
- 超时策略可通过 `config.yaml` 的 `lock_timeout` 配置项调整

---

## 六、版本快照存储

### 6.1 存储结构

```
_versions/
├── snapshots/
│   └── {template_id}/
│       ├── {version_number}.json      # 版本快照
│       └── {version_number}.diff.json # 增量差异
└── indexes/
    └── {template_id}.index.json       # 版本索引
```

### 6.2 快照格式

```json
{
  "version_number": "1.2.0",
  "template_id": "e1_deh",
  "content_hash": "sha256:abc123...",
  "content": "完整模板内容...",
  "metadata": {
    "change_type": "minor",
    "message": "新增NUMA亲和性优化章节",
    "author": "AI提示词体系",
    "created_at": "2026-07-12T10:00:00Z"
  },
  "lock_status": null,
  "diff_from_previous": {
    "added_lines": 25,
    "removed_lines": 0,
    "modified_lines": 3
  },
  "snapshot_created_at": "2026-07-12T10:00:00Z"
}
```

### 6.3 存储策略

- **完整快照**：每个版本存储完整内容副本（空间换时间，O(1) 读取）
- **增量差异**：同时存储与上一版本的 diff（用于快速差异浏览）
- **内容去重**：相同 `content_hash` 的快照共享存储（回滚场景复用）
- **保留策略**：
  - MAJOR 版本：永久保留
  - MINOR 版本：保留最近 10 个
  - PATCH 版本：保留最近 20 个
  - 超出保留数量的旧版本归档至冷存储，但仍可通过 `get` 接口访问

### 6.4 一致性保证

- 快照写入采用原子操作（write + rename），避免半写状态
- 快照内容不可变（immutable），写入后任何接口均不可修改
- 定期校验 `content_hash`，检测存储层静默损坏
