# 提示词商店技术架构

> 版本：v16.0.0

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    Client Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │   CLI    │  │  Web UI  │  │  IDE Extension   │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
└───────┼──────────────┼─────────────────┼────────────┘
        │              │                 │
┌───────┴──────────────┴─────────────────┴────────────┐
│                   API Gateway                        │
│         (Rate Limit + Auth + Routing)               │
└───────┬──────────────┬─────────────────┬────────────┘
        │              │                 │
┌───────┴────┐  ┌─────┴─────┐  ┌───────┴───────────┐
│  Package   │  │  Search   │  │  Review & Rating  │
│  Service   │  │  Service  │  │  Service          │
│            │  │           │  │                    │
│ - CRUD     │  │ - Index   │  │ - Comment         │
│ - Version  │  │ - Query   │  │ - Rating          │
│ - Install  │  │ - Suggest │  │ - Moderation      │
└─────┬──────┘  └─────┬─────┘  └────────┬──────────┘
      │               │                  │
┌─────┴───────────────┴──────────────────┴──────────┐
│                  Data Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │PostgreSQL│  │Elastic-  │  │    Redis         │ │
│  │(元数据)  │  │search    │  │  (缓存+会话)    │ │
│  └──────────┘  │(索引)    │  └──────────────────┘ │
│                └──────────┘                        │
│  ┌──────────┐  ┌──────────┐                       │
│  │   S3     │  │  CDN     │                       │
│  │(包存储)  │  │(分发加速)│                       │
│  └──────────┘  └──────────┘                       │
└────────────────────────────────────────────────────┘
```

## 2. 服务详细设计

### 2.1 Package Service

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python(FastAPI) | 与SDK同语言 |
| ORM | SQLAlchemy 2.0 | 异步ORM |
| 存储 | PostgreSQL 15+ | 元数据+版本+统计 |
| 包存储 | S3兼容 | 提示词包文件(.tar.gz) |
| CDN | CloudFront/Aliyun CDN | 全球分发加速 |

### 2.2 Search Service

| 组件 | 技术 | 说明 |
|------|------|------|
| 搜索引擎 | Elasticsearch 8.x | 全文搜索+聚合 |
| 索引策略 | 变更时增量索引 | 包发布/更新时触发 |
| 搜索字段 | name, description, tags, categories | 多语言分词 |
| 排序 | 评分/下载量/更新时间/相关度 | 多维度排序 |

### 2.3 Review & Rating Service

| 组件 | 技术 | 说明 |
|------|------|------|
| 语言 | Python(FastAPI) | 同Package Service |
| 存储 | PostgreSQL | 评论+评分 |
| 缓存 | Redis | 评分聚合缓存 |
| 审核 | 自动敏感词+人工审核 | 评论区治理 |

## 3. 包格式规范

### 3.1 包结构

```
@scope/prompt-name/
├── manifest.yaml        # 包清单
├── README.md            # 说明文档
├── CHANGELOG.md         # 变更日志
├── LICENSE              # 许可证
├── scenarios/           # 场景文件
│   ├── S01_*.yaml
│   ├── S02_*.yaml
│   └── ...
├── tests/               # 测试用例
│   ├── S01_test.yaml
│   └── ...
├── i18n/                # 多语言
│   ├── en/
│   ├── zh-Hans/
│   └── ...
└── examples/            # 使用示例
    ├── example1.yaml
    └── ...
```

### 3.2 Manifest格式

```yaml
name: "@official/code-review"
version: "1.0.0"
description:
  zh-Hans: "代码审查与质量保障场景"
  en: "Code Review & Quality Assurance"
author: "pea-alliance"
license: "Apache-2.0"
categories: ["engineering", "quality"]
tags: ["code-review", "static-analysis", "security"]
languages: ["zh-Hans", "en", "ja", "ko", "de", "fr"]
compatibility:
  min_sdk_version: "1.0.0"
  models: ["gpt-4", "claude-3", "qwen-max", "deepseek-v3"]
scenarios:
  - id: S04
    file: scenarios/S04_code_review.yaml
    languages: ["zh-Hans", "en"]
quality:
  test_coverage: 95%
  security_scan: "passed"
  lint_score: 98
```

## 4. 搜索索引设计

### 4.1 Elasticsearch Mapping

```json
{
  "mappings": {
    "properties": {
      "name": {"type": "keyword"},
      "description_zh": {"type": "text", "analyzer": "ik_max_word"},
      "description_en": {"type": "text", "analyzer": "english"},
      "description_ja": {"type": "text", "analyzer": "kuromoji"},
      "categories": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "languages": {"type": "keyword"},
      "author": {"type": "keyword"},
      "stats.downloads": {"type": "long"},
      "stats.stars": {"type": "float"},
      "quality.score": {"type": "float"},
      "version": {"type": "keyword"},
      "updated_at": {"type": "date"}
    }
  }
}
```

## 5. 推荐引擎(MVP后)

### 5.1 推荐策略

| 策略 | 描述 | 权重 |
|------|------|------|
| 协同过滤 | 相似用户也安装了 | 0.3 |
| 内容相似 | 基于标签/分类的相似度 | 0.25 |
| 热门趋势 | 下载量增速 | 0.2 |
| 个人偏好 | 基于用户历史评分 | 0.15 |
| 新包推荐 | 新发布高质量包加权 | 0.1 |

## 6. 性能目标

| 指标 | 目标 |
|------|------|
| 搜索延迟 | P95 < 200ms |
| 安装延迟 | < 2s(含下载) |
| 发布延迟 | < 30s(含审核) |
| 并发搜索 | 1000 QPS |
| 并发安装 | 500 QPS |
| 可用性 | 99.9% |
