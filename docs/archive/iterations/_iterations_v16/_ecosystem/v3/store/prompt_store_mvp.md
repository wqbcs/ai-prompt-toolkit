# 提示词商店MVP设计

> 版本：v16.0.0 | 日期：2026-05-29

---

## 1. MVP功能范围

### 1.1 核心功能(必须)

| # | 功能 | 优先级 | 描述 |
|---|------|--------|------|
| F1 | 浏览 | P0 | 按分类/语言/行业浏览提示词 |
| F2 | 搜索 | P0 | 关键词+标签+全文搜索 |
| F3 | 安装 | P0 | 一键安装到项目(类似npm install) |
| F4 | 评分 | P0 | 1-5星评分+评分分布 |
| F5 | 评论 | P1 | 文字评论+回复+点赞 |
| F6 | 版本管理 | P1 | 语义化版本+升级提示+回退 |
| F7 | 发布 | P1 | 贡献者发布新提示词到商店 |
| F8 | 审核 | P1 | 质量审核+安全扫描+合规检查 |

### 1.2 扩展功能(MVP后)

| # | 功能 | 优先级 | 描述 |
|---|------|--------|------|
| F9 | 推荐 | P2 | 基于使用历史+相似用户的推荐引擎 |
| F10 | 收藏 | P2 | 收藏夹+收藏数统计 |
| F11 | 统计 | P2 | 下载量+使用量+成功率 |
| F12 | 集成 | P2 | IDE插件+CI/CD集成 |
| F13 | 变现 | P3 | 免费增值+企业许可 |

## 2. 商店数据模型

### 2.1 PromptPackage(提示词包)

```yaml
PromptPackage:
  id: string(ulid)
  name: string  # 唯一包名(@scope/name)
  version: string(semver)
  description:
    zh-Hans: string
    en: string
    # ...其他语言
  author: string(userId)
  license: string(SPDX)
  categories: [string]  # 行业/场景分类
  tags: [string]
  languages: [string]   # 支持的语言代码
  scenarios: [ScenarioRef]
  compatibility:
    min_sdk_version: string
    max_sdk_version: string
    models: [string]    # 兼容模型
  stats:
    downloads: number
    stars: number
    reviews: number
    last_updated: datetime
  quality:
    score: number       # 0-100
    security_scan: string  # pass/fail/pending
    test_coverage: number
  pricing:
    type: enum(free/freemium/paid)
    price: number
```

### 2.2 Review(评审)

```yaml
Review:
  id: string(ulid)
  package_id: string
  user_id: string
  rating: number(1-5)
  comment: string
  created_at: datetime
  helpful_count: number
  verified: boolean  # 确认实际使用后评论
```

### 2.3 Version(版本)

```yaml
Version:
  package_id: string
  version: string(semver)
  changelog: string
  created_at: datetime
  downloads: number
  breaking_changes: boolean
  migration_guide: string  # 升级指南
```

## 3. CLI接口设计

```bash
# 搜索
prompt-store search "code review" --lang zh-Hans --category engineering

# 浏览
prompt-store browse --category security --sort downloads

# 安装
prompt-store install @official/code-review
prompt-store install @community/financial-audit@1.2.0

# 评分
prompt-store rate @official/code-review 5 --comment "Excellent quality"

# 发布
prompt-store publish ./my-prompt-package

# 更新
prompt-store update @official/code-review  # 更新到最新
prompt-store update --all                  # 更新所有

# 卸载
prompt-store uninstall @community/financial-audit

# 信息
prompt-store info @official/code-review
```

## 4. API设计

### 4.1 REST API

```
GET    /api/v1/packages                    # 列表(分页+过滤+排序)
GET    /api/v1/packages/:id                # 详情
GET    /api/v1/packages/:id/versions       # 版本列表
GET    /api/v1/packages/:id/versions/:ver  # 特定版本
POST   /api/v1/packages                    # 发布新包
PUT    /api/v1/packages/:id                # 更新包信息
DELETE /api/v1/packages/:id                # 下架(仅Maintainer)

GET    /api/v1/packages/:id/reviews        # 评论列表
POST   /api/v1/packages/:id/reviews        # 提交评论
PUT    /api/v1/reviews/:id                 # 更新评论
DELETE /api/v1/reviews/:id                 # 删除评论

POST   /api/v1/packages/:id/install       # 记录安装(统计)
POST   /api/v1/packages/:id/rate          # 评分

GET    /api/v1/search?q=&category=&lang=   # 搜索
GET    /api/v1/categories                  # 分类列表
GET    /api/v1/trending                    # 趋势排行
```

### 4.2 认证

```yaml
auth:
  publish: JWT(贡献者Silver级+)
  rate: JWT(任何注册用户)
  install: API Key或匿名
  admin: JWT(Maintainer级)
```
