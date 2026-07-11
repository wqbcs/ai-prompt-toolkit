# O1-1：RESTful API规范 - 场景查询接口

> **迭代编号**：O1-1 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## 场景查询接口 (Scenario Query API)

### GET /api/v1/scenarios

**描述**：查询可用提示词场景列表

**请求参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 否 | 场景分类（planning/design/coding/testing/deploy/ops/security/perf/doc/manage/ai） |
| industry | string | 否 | 行业标签（financial/healthcare/ecommerce/saas/gaming） |
| tech_stack | string | 否 | 技术栈（harmonyos/flutter/go/rust/python） |
| keyword | string | 否 | 关键词搜索 |
| page | int | 否 | 页码（默认1） |
| page_size | int | 否 | 每页数量（默认20，最大100） |

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "total": 55,
    "page": 1,
    "page_size": 20,
    "scenarios": [
      {
        "id": "req-analysis-001",
        "name": "需求分析与PRD生成",
        "category": "planning",
        "industry": [],
        "tech_stack": [],
        "version": "v18.0.0",
        "quality_score": 20.00,
        "tags": ["PRD", "用户故事", "功能列表"]
      }
    ]
  }
}
```

### GET /api/v1/scenarios/{scenario_id}

**描述**：获取单个场景的完整提示词内容

**响应**：返回完整的Markdown提示词文档 + 元数据 + 输入输出模板
