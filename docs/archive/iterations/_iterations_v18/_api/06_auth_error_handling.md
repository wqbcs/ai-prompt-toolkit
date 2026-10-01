# O1-6：API认证与错误处理规范

> **迭代编号**：O1-6 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## 认证规范

### API Key认证
```
Authorization: Bearer pk_live_xxxxxxxxxxxxx
```

### 认证级别：
| 级别 | 速率限制 | 功能范围 |
|------|---------|---------|
| free | 100次/天 | 查询+执行 |
| pro | 1000次/天 | 查询+执行+评估 |
| enterprise | 无限制 | 全部+组合+Webhook |

## 错误码规范

| HTTP状态码 | 错误码 | 说明 |
|-----------|--------|------|
| 400 | INVALID_INPUT | 请求参数无效 |
| 401 | UNAUTHORIZED | 认证失败 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | SCENARIO_NOT_FOUND | 场景不存在 |
| 409 | CONFLICT | 版本冲突 |
| 422 | VALIDATION_FAILED | 输入验证失败 |
| 429 | RATE_LIMITED | 速率超限 |
| 500 | INTERNAL_ERROR | 内部错误 |
| 503 | MODEL_UNAVAILABLE | 模型不可用 |

### 错误响应格式：
```json
{
  "code": 422,
  "error": {
    "type": "VALIDATION_FAILED",
    "message": "输入验证失败",
    "details": [
      { "field": "code_snippet", "message": "代码片段不能为空" }
    ],
    "request_id": "req_xxx",
    "documentation_url": "https://docs.prompt-system.dev/errors/422"
  }
}
```

## 分页规范

所有列表接口统一分页格式：
```json
{
  "pagination": {
    "total": 55,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```
