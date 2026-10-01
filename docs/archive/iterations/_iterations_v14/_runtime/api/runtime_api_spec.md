# 运行时API接口规范

> 版本：v14.0.0 | 日期：2026-05-29

---

## 1. API总览

| 类别 | 接口数 | 协议 | 说明 |
|------|--------|------|------|
| 执行API | 5 | REST/gRPC | 提示词执行核心 |
| 评估API | 4 | REST | 24维度评估 |
| 优化API | 3 | REST | 提示词优化 |
| 组合API | 3 | REST | 提示词组合 |
| 管理API | 6 | REST | 生命周期管理 |
| 安全API | 4 | REST | 安全操作 |

---

## 2. 执行API

### POST /api/v1/execute
执行提示词
```json
// Request
{
  "prompt_id": "prompt://code-review/v2",
  "prompt_version": "2.1.0",  // 可选，默认最新
  "context": {
    "code": "...",
    "language": "python"
  },
  "options": {
    "model": "gpt-4",         // 可选，覆盖默认
    "temperature": 0.1,
    "max_tokens": 2048,
    "timeout": 30
  },
  "security_context": {
    "user": "user@example.com",
    "clearance": "L2"
  }
}

// Response
{
  "execution_id": "exec-abc123",
  "status": "success",
  "output": { ... },
  "metrics": {
    "duration_ms": 2300,
    "tokens_input": 800,
    "tokens_output": 450,
    "model": "gpt-4"
  },
  "audit_id": "audit-xyz789",
  "timestamp": "2026-05-29T10:30:00Z"
}
```

### POST /api/v1/execute/batch
批量执行
### POST /api/v1/execute/stream
流式执行(SSE)
### GET /api/v1/execute/{execution_id}
获取执行结果
### POST /api/v1/execute/dry-run
干运行(仅解析+验证，不执行)

---

## 3. 评估API

### POST /api/v1/evaluate
24维度评估
```json
// Request
{
  "prompt_id": "prompt://code-review/v2",
  "dimensions": ["all"],      // 或 ["D1", "D5", "D14"]
  "context": { ... },
  "options": {
    "include_recommendations": true,
    "compare_with": "prompt://code-review/v1"  // 可选
  }
}

// Response
{
  "evaluation_id": "eval-abc123",
  "prompt_id": "prompt://code-review/v2",
  "dimensions": {
    "D1": {"score": 20.00, "sub_dimensions": {"D1.1": 5.00, "D1.2": 5.00, "D1.3": 5.00, "D1.4": 5.00}},
    "D2": {"score": 20.00, "sub_dimensions": {...}},
    // ... D3-D24
  },
  "total_score": 20.00,
  "standard_deviation": 0.00,
  "passed": true,
  "recommendations": []
}
```

### GET /api/v1/evaluate/{evaluation_id}
### POST /api/v1/evaluate/compare
### GET /api/v1/evaluate/history

---

## 4. 优化API

### POST /api/v1/optimize
提示词优化
```json
// Request
{
  "prompt_id": "prompt://code-review/v2",
  "target_dimensions": ["D1", "D3"],
  "strategy": "gradient_free",  // 或 "evolutionary", "bayesian"
  "constraints": {
    "max_iterations": 10,
    "min_score": 19.0,
    "preserve_security": true
  }
}

// Response
{
  "optimization_id": "opt-abc123",
  "original_prompt_id": "prompt://code-review/v2",
  "optimized_prompt_id": "prompt://code-review/v2-opt-1",
  "improvement": {"D1": +1.5, "D3": +0.8},
  "iterations": 7,
  "status": "converged"
}
```

### GET /api/v1/optimize/{optimization_id}
### POST /api/v1/optimize/ab-test

---

## 5. 组合API

### POST /api/v1/compose
提示词组合
```json
// Request
{
  "prompts": ["prompt://analyze", "prompt://review", "prompt://report"],
  "strategy": "sequential",  // 或 "parallel", "conditional", "pipeline"
  "data_flow": "chain",      // 或 "broadcast", "reduce"
  "options": {
    "error_handling": "fail_fast",  // 或 "continue", "retry"
    "max_parallel": 3
  }
}
```

### GET /api/v1/compose/{composition_id}
### POST /api/v1/compose/validate

---

## 6. 管理API

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 注册 | POST | /api/v1/prompts | 注册新提示词 |
| 查询 | GET | /api/v1/prompts/{id} | 查询提示词 |
| 版本列表 | GET | /api/v1/prompts/{id}/versions | 版本列表 |
| 状态变更 | PUT | /api/v1/prompts/{id}/status | 变更状态 |
| 依赖图 | GET | /api/v1/prompts/{id}/dependencies | 依赖关系 |
| 搜索 | GET | /api/v1/prompts/search | 搜索提示词 |

---

## 7. 安全API

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 扫描 | POST | /api/v1/security/scan | 安全扫描 |
| 注入测试 | POST | /api/v1/security/injection-test | 注入测试 |
| 审计日志 | GET | /api/v1/security/audit | 审计日志 |
| 安全报告 | GET | /api/v1/security/report | 安全报告 |
