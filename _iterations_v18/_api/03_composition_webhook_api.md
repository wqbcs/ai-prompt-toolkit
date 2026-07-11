# O1-3：RESTful API规范 - 组合与Webhook接口

> **迭代编号**：O1-3 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## 组合接口 (Composition API)

### POST /api/v1/compose

**描述**：将多个场景提示词组合为工作流

**请求体**：
```json
{
  "name": "全栈代码审查工作流",
  "steps": [
    { "scenario_id": "code-review-001", "position": 1 },
    { "scenario_id": "security-audit-001", "position": 2 },
    { "scenario_id": "perf-benchmark-001", "position": 3 }
  ],
  "pipeline": {
    "mode": "sequential",
    "error_handling": "continue_on_error",
    "output_chaining": true
  }
}
```

**响应**：返回组合工作流ID + 执行计划

## Webhook通知接口

### POST /api/v1/webhooks/register

**描述**：注册Webhook接收事件通知

**请求体**：
```json
{
  "url": "https://your-server.com/webhook",
  "events": [
    "execution.completed",
    "evaluation.finished",
    "scenario.updated",
    "quality.threshold_breach"
  ],
  "secret": "whsec_abc123",
  "retry_policy": {
    "max_retries": 3,
    "backoff_ms": [1000, 5000, 15000]
  }
}
```

### 事件通知格式：
```json
{
  "event": "execution.completed",
  "timestamp": "2026-07-11T10:30:00Z",
  "data": {
    "execution_id": "exec_abc123",
    "scenario_id": "code-review-001",
    "status": "success",
    "latency_ms": 3200
  },
  "signature": "sha256=..."
}
```

### 支持的事件类型：
| 事件 | 触发条件 |
|------|---------|
| execution.completed | 提示词执行完成 |
| execution.failed | 执行失败 |
| evaluation.finished | 评估完成 |
| quality.threshold_breach | 质量分低于阈值 |
| scenario.published | 新场景发布 |
| workflow.completed | 工作流执行完成 |
