# S1-02 提示词效果追踪Dashboard - 趋势图+异常告警

> **迭代**：v22-S1-02 | **日期**：2026-07-12

---

## 趋势图系统

### 3级时间粒度

```json
{
  "trendChart": {
    "granularities": {
      "7d": {
        "interval": "1h",
        "dataPoints": 168,
        "metrics": ["successRate", "qualityScore", "tokenConsumption", "latency"],
        "comparison": "prev_7d",
        "chartType": "line_with_band"
      },
      "30d": {
        "interval": "6h",
        "dataPoints": 120,
        "metrics": ["successRate", "qualityScore", "tokenConsumption", "latency"],
        "comparison": "prev_30d",
        "chartType": "line_with_area"
      },
      "90d": {
        "interval": "1d",
        "dataPoints": 90,
        "metrics": ["successRate", "qualityScore", "tokenConsumption", "latency"],
        "comparison": "prev_90d",
        "chartType": "candlestick"
      }
    },
    "features": {
      "zoomAndPan": true,
      "annotations": true,
      "exportPng": true,
      "drillDown": true,
      "correlationAnalysis": true
    }
  }
}
```

## 异常告警系统

### 4类告警规则

```json
{
  "alertRules": {
    "effectDrop": {
      "name": "效果突降告警",
      "condition": "successRate < prev_7d_avg * 0.9",
      "severity": "critical",
      "cooldown": 3600,
      "channels": ["email", "webhook", "dashboard"],
      "message": "场景{sceneId}成功率从{prev}%降至{current}%，降幅{drop}%"
    },
    "latencySpike": {
      "name": "延迟飙升告警",
      "condition": "latency_p99 > 5000",
      "severity": "warning",
      "cooldown": 1800,
      "channels": ["webhook", "dashboard"],
      "message": "场景{sceneId} P99延迟达{latency}ms，超过5000ms阈值"
    },
    "tokenOveruse": {
      "name": "Token超标告警",
      "condition": "tokenConsumption > baseline * 2.0",
      "severity": "warning",
      "cooldown": 3600,
      "channels": ["webhook", "dashboard"],
      "message": "场景{sceneId} Token消耗{tokens}，超基线{overuse}%"
    },
    "qualityDegrade": {
      "name": "质量下降告警",
      "condition": "qualityScore < 6.0",
      "severity": "critical",
      "cooldown": 1800,
      "channels": ["email", "webhook", "dashboard"],
      "message": "场景{sceneId}质量评分降至{score}，低于6.0阈值"
    }
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 告警风暴：一条异常触发N条告警 | P0 | 告警聚合+去重+冷却期 |
| 2 | 同比环比未考虑周期性 | P1 | 季节性分解+同周对比 |
| 3 | 趋势图采样丢失毛刺 | P1 | 异常点保留+标注采样策略 |
| 4 | 告警阈值硬编码不自适应 | P2 | 动态阈值+基线学习+手动覆盖 |
| 5 | 告警缺少上下文 | P2 | 附带关联指标+最近变更+建议动作 |

### 性能5

| # | 优化项 | 效果 |
|---|--------|------|
| 1 | 时序数据库存储指标 | 写入>10K/s，查询<50ms |
| 2 | 告警规则预编译+增量计算 | 告警延迟<5s |
| 3 | 趋势图数据降采样 | 90日趋势查询<200ms |
| 4 | 告警分组+静默规则 | 告警降噪80% |
| 5 | 异常检测流式计算 | 实时检测延迟<1s |

### 最小可执行示例

```
输入：监控"API文档生成"场景的异常告警
提示词：
作为提示词异常告警系统，请检查"API文档生成"场景最近7日数据：
- 成功率是否突降>10%
- P99延迟是否>5000ms
- Token消耗是否超基线200%
- 质量评分是否<6.0
如有异常，请输出告警详情：告警类型/严重等级/当前值/阈值/建议动作。
如无异常，输出"ALL CLEAR"+各项当前状态。

预期输出：
{
  "sceneId": "api-doc-generation",
  "checkTime": "2026-07-12T10:30:00Z",
  "status": "ALERT",
  "alerts": [
    {
      "type": "effectDrop",
      "severity": "critical",
      "current": 0.82,
      "threshold": 0.855,
      "drop": "13.7%",
      "suggestion": "检查最近3次变更，回退至稳定版本"
    }
  ],
  "metrics": {
    "successRate": 0.82,
    "latencyP99": 3200,
    "tokenRatio": 1.1,
    "qualityScore": 7.2
  }
}
```

### 常见错误Top5

| # | 错误 | 错误示例 | 修复方法 |
|---|------|---------|---------|
| 1 | 同比基数太小导致误报 | 1次→2次=100%增长 | 设最低样本量阈值(>=30) |
| 2 | 未排除已知维护窗口 | 维护期告警干扰 | 维护日历+告警静默 |
| 3 | 告警只有通知无动作 | 只发邮件不自动处理 | 附带自动修复建议+一键执行 |
| 4 | 趋势图Y轴截断夸大变化 | 95%-96%看起来巨大 | Y轴从0开始+标注绝对变化 |
| 5 | 未关联变更事件 | 效果下降不知道为什么 | 变更日志关联+根因分析 |
