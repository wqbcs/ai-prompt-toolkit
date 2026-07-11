# Q2-05~07 提示词版本分支策略

> **迭代**：v20-Q2-05~07 | **日期**：2026-07-12

---

## 一、分支策略设计（Q2-05）

### 1.1 分支类型

```
┌─────────────────────────────────────────────────────────────┐
│                     提示词版本分支策略                         │
│                                                              │
│  main ──────────────────────────────────────────── v20.0.0   │
│    │                                            ╱            │
│    ├─ develop ──────────────────────────────╱                │
│    │   │                                  ╱                  │
│    │   ├─ feature/python-scenarios ────╱                      │
│    │   ├─ feature/frontend-scenarios ─╱                      │
│    │   ├─ feature/database-scenarios ─                       │
│    │   └─ feature/ide-plugin ─                               │
│    │                                                          │
│    ├─ release/v20.0.0 ──────────────────                    │
│    │                                                          │
│    └─ hotfix/v20.0.1 ────────────────                       │
│         │                                                     │
│         └─→ main + develop (cherry-pick)                     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 分支命名规范

| 分支类型 | 命名规则 | 生命周期 | 示例 |
|---------|---------|---------|------|
| main | main | 永久 | main |
| develop | develop | 永久 | develop |
| feature | feature/{area}-{description} | 合并后删除 | feature/python-fastapi-scenarios |
| hotfix | hotfix/v{version}-{description} | 合并后删除 | hotfix/v20.0.1-fix-template-vars |
| release | release/v{major}.{minor}.{patch} | 合并后删除 | release/v20.0.0 |

### 1.3 分支规则

```yaml
branch_rules:
  main:
    protection:
      required_reviews: 2
      required_checks: [lint, validate, security, quality-gate]
      no_direct_push: true
      require_signed_commits: true
    merge_strategy: merge_commit
    tag_pattern: "v*.*.*"

  develop:
    protection:
      required_reviews: 1
      required_checks: [lint, validate]
      no_direct_push: true
    merge_strategy: squash_merge
    auto_delete_after_merge: true

  feature:
    protection:
      required_checks: [lint]
      no_direct_push: false
    merge_strategy: squash_merge
    auto_delete_after_merge: true
    naming_pattern: "^feature/[a-z0-9-]+$"

  hotfix:
    protection:
      required_reviews: 1
      required_checks: [lint, validate, security]
      no_direct_push: true
    merge_strategy: cherry_pick
    auto_delete_after_merge: true
    naming_pattern: "^hotfix/v[0-9]+\\.[0-9]+\\.[0-9]+-[a-z0-9-]+$"

  release:
    protection:
      required_reviews: 2
      required_checks: [lint, validate, security, performance, quality-gate]
      no_direct_push: true
    merge_strategy: merge_commit
    auto_delete_after_merge: true
    naming_pattern: "^release/v[0-9]+\\.[0-9]+\\.[0-9]+$"
```

---

## 二、合并策略+兼容性矩阵（Q2-06）

### 2.1 合并策略

| 源→目标 | 策略 | 原因 |
|---------|------|------|
| feature→develop | Squash Merge | 保持develop历史清晰，一个feature一个commit |
| develop→release | Merge Commit | 保留完整开发历史 |
| release→main | Merge Commit | 保留发布历史 |
| hotfix→main | Cherry-pick | 紧急修复，只包含必要改动 |
| hotfix→develop | Cherry-pick | 同步修复到开发分支 |
| release→develop | Merge Commit | 发布后的修复同步回开发 |

### 2.2 兼容性矩阵

```typescript
interface CompatibilityMatrix {
  versions: VersionEntry[];
  templates: TemplateCompatibility[];
  models: ModelCompatibility[];
  tools: ToolCompatibility[];
}

interface VersionEntry {
  version: string;
  release_date: string;
  min_engine_version: string;
  breaking_changes: string[];
  deprecated_features: string[];
  new_features: string[];
}

interface TemplateCompatibility {
  template_id: string;
  template_version: string;
  engine_compatibility: {
    min_version: string;
    max_version: string;
    tested_versions: string[];
  };
  model_compatibility: {
    supported_models: string[];
    incompatible_models: string[];
    notes: string[];
  };
}

interface ModelCompatibility {
  model_id: string;
  api_version: string;
  input_format: string;
  output_format: string;
  max_context: number;
  features: string[];
  limitations: string[];
}

interface ToolCompatibility {
  tool_id: string;
  tool_version: string;
  engine_version_range: [string, string];
  dependencies: Record<string, string>;
}
```

### 2.3 兼容性矩阵示例

| 模板 | v18 | v19 | v20 |
|------|-----|-----|-----|
| 01_需求分析 | ✓ | ✓ | ✓ |
| 02_架构设计 | ✓ | ✓ | ✓ |
| Go微服务 | - | ✓ | ✓ |
| Rust异步 | - | ✓ | ✓ |
| Python FastAPI | - | - | ✓ |
| React场景 | - | - | ✓ |
| GaussDB | - | - | ✓ |
| 鸿蒙NEXT | - | ✓(基础) | ✓(深化) |

---

## 三、分支保护+发布工作流（Q2-07）

### 3.1 分支保护规则

```yaml
protection_rules:
  main:
    require_pull_request: true
    required_approving_review_count: 2
    require_status_checks: true
    required_status_checks:
      - lint
      - validate
      - security-scan
      - quality-gate
    require_signed_commits: true
    require_linear_history: false
    allow_force_pushes: false
    allow_deletions: false
    required_conversation_resolution: true

  develop:
    require_pull_request: true
    required_approving_review_count: 1
    require_status_checks: true
    required_status_checks:
      - lint
      - validate
    require_signed_commits: false
    allow_force_pushes: false
    allow_deletions: false
```

### 3.2 发布工作流

```typescript
interface ReleaseWorkflow {
  prepareRelease(version: string): ReleasePreparation;
  runQualityChecks(): QualityCheckResult;
  generateChangelog(from: string, to: string): Changelog;
  createReleaseTag(version: string): TagResult;
  publishRelease(version: string, artifacts: string[]): PublishResult;
  announceRelease(version: string, channels: string[]): AnnouncementResult;
}

interface ReleasePreparation {
  version: string;
  release_branch: string;
  feature_list: string[];
  breaking_changes: string[];
  migration_notes: string[];
  quality_check_status: 'pending' | 'passed' | 'failed';
}

interface Changelog {
  version: string;
  date: string;
  sections: {
    added: string[];
    changed: string[];
    deprecated: string[];
    removed: string[];
    fixed: string[];
    security: string[];
  };
}
```

### 3.3 发布检查清单

| # | 检查项 | 验证方式 | 阻断 |
|---|--------|---------|------|
| 1 | 版本号正确 | 语义化版本校验 | ✓ |
| 2 | CHANGELOG已更新 | CHANGELOG.md含当前版本 | ✓ |
| 3 | 所有测试通过 | CI绿色 | ✓ |
| 4 | 安全扫描通过 | 0 critical/high | ✓ |
| 5 | 性能基准通过 | 无>10%回归 | ✓ |
| 6 | 兼容性矩阵更新 | 新模板/模型条目 | ✓ |
| 7 | 文档同步更新 | README/API Doc | ✓ |
| 8 | 迁移指南编写 | 破坏性变更 | ✓ |
| 9 | Git标签创建 | v{major}.{minor}.{patch} | ✓ |
| 10 | 发布公告发送 | 邮件/Slack/社区 | - |

---

## 四、Q2总结

### Q2交付物清单

| # | 迭代 | 交付物 | 状态 |
|---|------|--------|------|
| 8 | Q2-01 | Token消耗分析器 | ✓ |
| 9 | Q2-02 | 延迟分析器 | ✓ |
| 10 | Q2-03 | 成本估算引擎 | ✓ |
| 11 | Q2-04 | 性能报告生成器+优化建议引擎 | ✓ |
| 12 | Q2-05 | 版本分支策略设计 | ✓ |
| 13 | Q2-06 | 合并策略+兼容性矩阵 | ✓ |
| 14 | Q2-07 | 分支保护+发布工作流 | ✓ |

---

## 五、验收项

- [x] 5种分支类型定义（main/develop/feature/hotfix/release）
- [x] 分支命名规范
- [x] 分支保护规则
- [x] 6种合并策略
- [x] 兼容性矩阵（模板×版本）
- [x] 发布工作流（10步检查清单）
- [x] CHANGELOG自动生成
- [x] Q2全部7次迭代完成
