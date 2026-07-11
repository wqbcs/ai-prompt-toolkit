# S1-01 提示词效果追踪Dashboard - 可视化看板

> **迭代**：v22-S1-01 | **日期**：2026-07-12

---

## 执行效果可视化看板

### 4维度实时看板

```json
{
  "dashboard": {
    "metrics": {
      "successRate": {
        "displayName": "执行成功率",
        "unit": "percentage",
        "refreshInterval": 300,
        "thresholds": {
          "green": ">=95%",
          "yellow": "80%-95%",
          "red": "<80%"
        },
        "aggregation": "rolling_7d_avg"
      },
      "qualityScore": {
        "displayName": "质量评分",
        "unit": "score_1_10",
        "refreshInterval": 300,
        "thresholds": {
          "green": ">=8.0",
          "yellow": "6.0-8.0",
          "red": "<6.0"
        },
        "aggregation": "weighted_avg"
      },
      "tokenConsumption": {
        "displayName": "Token消耗",
        "unit": "tokens",
        "refreshInterval": 60,
        "thresholds": {
          "green": "<=baseline",
          "yellow": "baseline-200%",
          "red": ">200%"
        },
        "aggregation": "sum_24h"
      },
      "latency": {
        "displayName": "响应延迟",
        "unit": "milliseconds",
        "refreshInterval": 60,
        "thresholds": {
          "green": "P99<=2000ms",
          "yellow": "P99 2000-5000ms",
          "red": "P99>5000ms"
        },
        "aggregation": "percentile_p99"
      }
    },
    "layout": {
      "type": "grid",
      "columns": 4,
      "widgets": [
        {
          "type": "gauge",
          "metric": "successRate",
          "position": {"row": 1, "col": 1}
        },
        {
          "type": "gauge",
          "metric": "qualityScore",
          "position": {"row": 1, "col": 2}
        },
        {
          "type": "counter",
          "metric": "tokenConsumption",
          "position": {"row": 1, "col": 3}
        },
        {
          "type": "histogram",
          "metric": "latency",
          "position": {"row": 1, "col": 4}
        }
      ]
    }
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 只看平均不看分布，掩盖P99异常 | P0 | 同时展示P50/P95/P99+直方图 |
| 2 | 刷新间隔过短导致数据抖动 | P1 | 最小300s聚合+指数平滑 |
| 3 | 成功率未区分软失败和硬失败 | P1 | 区分timeout/error/quality_fail三类 |
| 4 | Token消耗未归一化，不同模型不可比 | P2 | 按模型类型归一化+基线对比 |
| 5 | 看板信息过载，关键指标淹没 | P2 | 默认只展示4核心+可展开详情 |

### 性能5

| # | 优化项 | 效果 |
|---|--------|------|
| 1 | 数据预聚合+增量更新 | 查询延迟<100ms |
| 2 | WebSocket推送+本地缓存 | 看板刷新延迟<1s |
| 3 | 按时间粒度降采样（实时/5min/1h/1d） | 长期趋势查询<500ms |
| 4 | 虚拟滚动+懒加载 | 1000+指标流畅渲染 |
| 5 | 颜色编码+阈值告警 | 异常发现时间<30s |

### 最小可执行示例

```
输入：追踪"代码审查"场景模板的执行效果
提示词：
作为提示词效果追踪系统，请生成"代码审查"场景模板的效果看板数据：
- 执行成功率：最近7日数据（目标>=95%）
- 质量评分：LLM-as-Judge 1-10分（目标>=8.0）
- Token消耗：每次执行消耗统计（目标<=4000）
- 响应延迟：P50/P95/P99延迟（目标P99<=2000ms）
请以JSON格式输出，包含7日趋势和当日明细。

预期输出：
{
  "sceneId": "code-review",
  "period": "7d",
  "successRate": {"current": 0.962, "trend": "+0.3%", "daily": [...]},
  "qualityScore": {"current": 8.4, "trend": "+0.2", "daily": [...]},
  "tokenConsumption": {"avg": 3250, "trend": "-5%", "daily": [...]},
  "latency": {"p50": 850, "p95": 1800, "p99": 2400, "trend": "+3%"}
}
```

### 常见错误Top5

| # | 错误 | 错误示例 | 修复方法 |
|---|------|---------|---------|
| 1 | 指标定义模糊 | "效果很好" | 用具体数值：successRate>=95% |
| 2 | 阈值未校准 | 所有场景同一阈值 | 按场景类型设不同基线 |
| 3 | 缺少时间维度 | 只看当前值 | 加入7/30/90日趋势对比 |
| 4 | 异常未分级 | 所有异常同等处理 | P0立即告警/P1日汇总/P2周报 |
| 5 | 未设基线 | 无基准无法判断优劣 | 首次运行自动建立基线 |
