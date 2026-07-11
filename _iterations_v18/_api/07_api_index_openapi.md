# O1-7：API接口索引与OpenAPI规范

> **迭代编号**：O1-7 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## API接口索引

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 场景列表 | GET | /api/v1/scenarios | 查询可用场景 |
| 场景详情 | GET | /api/v1/scenarios/{id} | 获取单个场景 |
| 执行提示词 | POST | /api/v1/execute | 执行AI推理 |
| 评估结果 | POST | /api/v1/evaluate | 质量评估 |
| 组合工作流 | POST | /api/v1/compose | 组合场景 |
| 注册Webhook | POST | /api/v1/webhooks/register | 注册通知 |
| 删除Webhook | DELETE | /api/v1/webhooks/{id} | 删除通知 |
| 注册自定义场景 | POST | /api/v1/sdk/scenarios | SDK扩展 |
| 注册自定义评估器 | POST | /api/v1/sdk/evaluators | SDK扩展 |
| 注册自定义组合器 | POST | /api/v1/sdk/composers | SDK扩展 |

## OpenAPI 3.1 规范（精简版）

```yaml
openapi: 3.1.0
info:
  title: AI提示词体系API
  version: v18.0.0
  description: AI提示词体系的可编程接口

servers:
  - url: https://api.prompt-system.dev/v1
    description: 生产环境
  - url: http://localhost:3000/v1
    description: 开发环境

security:
  - BearerAuth: []

paths:
  /scenarios:
    get:
      summary: 查询可用场景
      parameters:
        - name: category
          in: query
          schema:
            type: string
            enum: [planning,design,coding,testing,deploy,ops,security,perf,doc,manage,ai]
        - name: keyword
          in: query
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScenarioListResponse'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
  schemas:
    ScenarioListResponse:
      type: object
      properties:
        code:
          type: integer
        data:
          type: object
          properties:
            total:
              type: integer
            scenarios:
              type: array
              items:
                $ref: '#/components/schemas/Scenario'
    Scenario:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        category:
          type: string
        quality_score:
          type: number
```
