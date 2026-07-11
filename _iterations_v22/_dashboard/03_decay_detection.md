# S1-03 提示词效果追踪Dashboard - 效果衰减检测

> **迭代**：v22-S1-03 | **日期**：2026-07-12

---

## 效果衰减检测引擎

### 检测算法

```json
{
  "decayDetector": {
    "algorithm": "sliding_window_linear_regression",
    "windowSize": 7,
    "metrics": {
      "successRateDecay": {
        "slopeThreshold": -0.005,
        "rSquaredMin": 0.6,
        "action": "trigger_optimization"
      },
      "qualityScoreDecay": {
        "slopeThreshold": -0.05,
        "rSquaredMin": 0.5,
        "action": "trigger_quality_review"
      },
      "latencyCreep": {
        "slopeThreshold": 50,
        "rSquaredMin": 0.6,
        "action": "trigger_performance_review"
      },
      "tokenInflation": {
        "slopeThreshold": 50,
        "rSquaredMin": 0.6,
        "action": "trigger_compression"
      }
    },
    "detectionFlow": [
      "1. 收集7日滑动窗口指标数据",
      "2. 线性回归计算趋势斜率和R²",
      "3. 斜率超过阈值且R²满足最小值→标记衰减",
      "4. 结合突变检测(3σ)识别急性衰减",
      "5. 生成衰减报告+自动触发优化流程"
    ],
    "decayLevels": {
      "gradual": {
        "name": "渐进衰减",
        "detection": "斜率<阈值且持续>7日",
        "severity": "warning",
        "action": "加入优化队列"
      },
      "acute": {
        "name": "急性衰减",
        "detection": "3σ突变检测+7日不恢复",
        "severity": "critical",
        "action": "立即优化"
      },
      "seasonal": {
        "name": "周期波动",
        "detection": "STL分解后趋势<阈值",
        "severity": "info",
        "action": "标记观察"
      }
    }
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 窗口太小导致噪声误判 | P1 | 最小7日窗口+R²>0.6过滤 |
| 2 | 忽略季节性波动误判为衰减 | P1 | STL季节性分解+趋势分量分析 |
| 3 | 模型更新导致基线漂移 | P1 | 变更事件标记+基线重置 |
| 4 | 只检测不自动修复 | P2 | 检测→诊断→自动优化闭环 |
| 5 | 衰减报告缺少根因 | P2 | 关联分析(变更/模型/数据/环境) |

### 性能5

| # | 优化项 | 效果 |
|---|--------|------|
| 1 | 增量回归计算 | 检测延迟<10s |
| 2 | 多指标并行检测 | 4指标同时检测<30s |
| 3 | 异常分数缓存 | 历史查询<100ms |
| 4 | 衰减预测模型 | 提前3日预警准确率>80% |
| 5 | 自动触发优化 | 衰减发现到优化启动<5min |

### 最小可执行示例

```
输入：检测"单元测试生成"场景是否存在效果衰减
提示词：
作为效果衰减检测引擎，请分析"单元测试生成"场景最近30日数据：
1. 计算7日滑动窗口线性回归斜率
2. 检测是否存在渐进/急性/周期衰减
3. 如存在衰减，输出衰减类型/持续时间/根因分析/优化建议
4. 如不存在衰减，输出当前趋势判断

预期输出：
{
  "sceneId": "unit-test-gen",
  "analysisPeriod": "30d",
  "decayStatus": "gradual_decay_detected",
  "decayType": "gradual",
  "metric": "successRate",
  "slope": -0.008,
  "rSquared": 0.72,
  "duration": "12d",
  "rootCause": "model_update_20260701",
  "suggestion": "回退至6月30日版本或重新优化提示词"
}
```

### 常见错误Top5

| # | 错误 | 错误示例 | 修复方法 |
|---|------|---------|---------|
| 1 | 把正常波动当衰减 | 1日下降5%就告警 | 需持续7日+R²>0.6确认 |
| 2 | 忽略慢衰减积累 | 每日-0.1%觉得没事 | 年累计-36.5%，需提前预警 |
| 3 | 未区分模型衰减和提示词衰减 | 模型升级导致衰减 | 分别追踪模型/提示词/数据维度 |
| 4 | 检测后无行动 | 只报告不处理 | 自动加入优化队列+SLA保障 |
| 5 | 未设衰减容忍度 | 任何衰减都零容忍 | 设可接受范围(如斜率>-0.003) |
