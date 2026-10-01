# 发布自动化规范

> 版本：v14.0.0 | 日期：2026-05-29

---

## 1. Semantic Release配置

### 1.1 版本确定规则
| 提交类型 | 示例 | 版本变更 |
|---------|------|---------|
| feat: | feat: add UPPL compiler | MINOR |
| fix: | fix: injection defense edge case | PATCH |
| feat!: / BREAKING CHANGE | feat!: redesign runtime API | MAJOR |
| perf: | perf: optimize evaluation engine | PATCH |
| docs: | docs: update API reference | 无 |
| refactor: | refactor: restructure adapters | 无 |
| test: | test: add UPPL parser tests | 无 |
| ci: | ci: update GitHub Actions | 无 |

### 1.2 配置(.releaserc.json)
```json
{
  "branches": ["main", "next", {"name": "beta", "prerelease": true}],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github",
    "@semantic-release/exec"
  ]
}
```

### 1.3 自动Changelog生成
- 基于Conventional Commits自动分类
- feat→Features, fix→Bug Fixes, perf→Performance
- BREAKING CHANGE→Breaking Changes
- 关联Issue/PR号+作者

---

## 2. CI/CD流水线

### 2.1 PR流水线
```yaml
name: PR Check
on: pull_request
jobs:
  lint:
    - ruff check (Python)
    - eslint (TypeScript)
  type-check:
    - mypy --strict (Python)
    - tsc --noEmit (TypeScript)
  test:
    - pytest --cov (Python)
    - jest --coverage (TypeScript)
  security:
    - bandit (Python)
    - npm audit (TypeScript)
    - injection-defense-test
  evaluation:
    - 24维度评估(变更提示词)
    - 门禁19项检查
  cla:
    - CLA-Assistant检查
```

### 2.2 发布流水线
```yaml
name: Release
on: push to main
jobs:
  test: (同PR流水线)
  release:
    - semantic-release
    - PyPI发布
    - npm发布
    - GitHub Release
    - Docker镜像发布
    - 文档站点更新
  notify:
    - Slack通知
    - CHANGELOG更新
```

---

## 3. 发布检查清单

- [ ] 所有测试通过(单元+集成+端到端)
- [ ] 安全扫描无高危漏洞
- [ ] 24维度评估均分≥18.00
- [ ] 门禁19项全部通过
- [ ] API文档更新
- [ ] CHANGELOG生成
- [ ] 版本号符合SemVer
- [ ] 向下兼容验证
- [ ] CLA签署检查
- [ ] 发布签名(GPG)
