# O1-2：RESTful API规范 - 执行与评估接口

> **迭代编号**：O1-2 | **维度**：功能增添-可编程接口 | **日期**：2026-07-11

---

## 执行接口 (Execution API)

### POST /api/v1/execute

**描述**：使用指定场景提示词执行AI推理

**请求体**：
```json
{
  "scenario_id": "code-review-001",
  "model": "qwen-max",
  "inputs": {
    "code_snippet": "...",
    "language": "dart",
    "review_focus": ["security", "performance"]
  },
  "options": {
    "temperature": 0.3,
    "max_tokens": 4096,
    "output_format": "json"
  }
}
```

**响应**：
```json
{
  "code": 200,
  "data": {
    "execution_id": "exec_abc123",
    "scenario_id": "code-review-001",
    "model": "qwen-max",
    "output": { "summary": "...", "issues": [], "score": 85 },
    "tokens_used": { "input": 1200, "output": 800 },
    "latency_ms": 3200
  }
}
```

## 评估接口 (Evaluation API)

### POST /api/v1/evaluate

**描述**：对提示词输出结果进行质量评估

**请求体**：
```json
{
  "scenario_id": "code-review-001",
  "outputs": [
    { "execution_id": "exec_abc123", "output": {...} }
  ],
  "evaluators": ["accuracy", "completeness", "consistency"],
  "baseline_version": "v17.0.0"
}
```

**响应**：
```json
{
  "code": 200,
  "data": {
    "evaluation_id": "eval_def456",
    "scores": {
      "accuracy": 19.5,
      "completeness": 20.0,
      "consistency": 19.8
    },
    "average": 19.77,
    "improvement_vs_baseline": "+0.5"
  }
}
```
