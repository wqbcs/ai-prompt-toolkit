# 外部集成API规范 v1.0

> **版本**：v1.0
> **日期**：2026-05-29
> **认证**：OAuth2.0 Bearer Token / API Key

---

## 一、API概览

| 端点分类 | 路径前缀 | 说明 |
|----------|----------|------|
| 场景管理 | /api/v1/scenarios | 场景查询与执行 |
| 评估服务 | /api/v1/evaluations | 评估结果与Dashboard |
| 工作流 | /api/v1/workflows | 工作流编排与执行 |
| 知识图谱 | /api/v1/knowledge | 术语/依赖/推荐查询 |
| 社区 | /api/v1/community | 贡献与评审 |

---

## 二、场景管理API

### 2.1 查询场景列表
```
GET /api/v1/scenarios
Query: ?document={doc_id}&industry={industry}&page={page}&size={size}
Response: {
  "total": 55,
  "items": [{"id": "04_A", "name": "代码审查", "document": "04", ...}]
}
```

### 2.2 查询场景详情
```
GET /api/v1/scenarios/{scenario_id}
Response: {
  "id": "04_A",
  "name": "代码审查",
  "document": "04_代码审查与质量保障",
  "input_schema": {...},
  "output_schema": {...},
  "checklist": [...],
  "adaptation_matrix": {...}
}
```

### 2.3 执行场景
```
POST /api/v1/scenarios/{scenario_id}/execute
Body: {
  "input": {...},
  "options": {
    "model": "gpt-4-turbo",
    "output_format": "json",
    "include_reasoning": true,
    "context": {}
  }
}
Response: {
  "execution_id": "...",
  "status": "completed",
  "output": {...},
  "metrics": {"latency_ms": 3200, "tokens_used": 1500}
}
```

---

## 三、评估服务API

### 3.1 查询评估列表
```
GET /api/v1/evaluations
Query: ?version={version}&scenario={scenario_id}&from={date}&to={date}
```

### 3.2 Dashboard数据
```
GET /api/v1/evaluations/dashboard
Response: {
  "version": "v6.0.0",
  "overall": {"mean_score": 18.5, "std_dev": 0.7},
  "dimensions": {...},
  "regression": {"total": 78, "passed": 78},
  "redteam": {"defense_rate": 0.99}
}
```

### 3.3 趋势数据
```
GET /api/v1/evaluations/trends?dimension={dim}&period={30d|90d|1y}
```

---

## 四、工作流API

### 4.1 查询工作流列表
```
GET /api/v1/workflows
```

### 4.2 执行工作流
```
POST /api/v1/workflows/{workflow_id}/execute
Body: {
  "initial_input": {...},
  "options": {"on_error": "skip", "checkpoint": true}
}
```

### 4.3 查询工作流状态
```
GET /api/v1/workflows/{workflow_id}/status
Response: {
  "status": "running",
  "current_step": "02_架构设计",
  "completed_steps": ["01_需求分析"],
  "checkpoint": {"resumable": true}
}
```

### 4.4 断点续传
```
POST /api/v1/workflows/{workflow_id}/resume
Body: {"from_step": "02_架构设计", "override_input": {...}}
```

---

## 五、知识图谱API

### 5.1 术语查询
```
GET /api/v1/knowledge/terms
Query: ?q={query}&category={category}
```

### 5.2 术语关系
```
GET /api/v1/knowledge/terms/{term_id}/relations
Query: ?type={SYNONYM|DEPENDS_ON|CONTAINS|CONFLICTS}
```

### 5.3 文档依赖
```
GET /api/v1/knowledge/documents/{doc_id}/dependencies
```

### 5.4 场景推荐
```
GET /api/v1/knowledge/recommend
Query: ?scenario={current_scenario}&keywords={k1,k2}&industry={industry}
Response: {
  "recommended": [
    {"scenario": "08_安全审计", "score": 0.87, "reason": "..."}
  ]
}
```

---

## 六、错误响应格式

```json
{
  "error": {
    "code": "SCENARIO_NOT_FOUND",
    "message": "场景ID不存在",
    "details": {}
  }
}
```

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| UNAUTHORIZED | 401 | 认证失败 |
| FORBIDDEN | 403 | 权限不足 |
| SCENARIO_NOT_FOUND | 404 | 场景不存在 |
| INVALID_INPUT | 400 | 输入校验失败 |
| EXECUTION_TIMEOUT | 408 | 执行超时 |
| INTERNAL_ERROR | 500 | 内部错误 |
