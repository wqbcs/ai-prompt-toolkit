---
version: "1.0.0"
author: "AI提示词体系"
updated_at: "2026-07-12"
tags: [dashboard, tracker, anomaly, ranking, moving-average]
applicable_models: [gpt-4o, claude-3.5-sonnet, qwen-max, pangu-large]
inheritance:
  enabled: false
---

# 效果追踪设计

## 概述

EffectTracker 是 `_dashboard` 引擎的核心追踪组件，负责从各引擎采集运行指标、检测异常波动、计算效果趋势并生成模板排行榜。通过 7 日移动平均线平滑指标噪声，2σ 告警阈值捕捉异常波动，为运维决策提供数据支撑。

---

## 一、EffectTracker 架构

### 1.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    EffectTracker                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Collector │  │ Detector │  │  Ranker  │              │
│  │  采集器   │  │  检测器   │  │  排行器   │              │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘              │
│        │             │             │                     │
│        ▼             ▼             ▼                     │
│  ┌──────────────────────────────────────┐               │
│  │           Metrics Store              │               │
│  │            指标存储                   │               │
│  └──────────────────┬───────────────────┘               │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────┐               │
│  │          Trend Calculator            │               │
│  │          趋势计算器                   │               │
│  └──────────────────┬───────────────────┘               │
│                     │                                    │
│                     ▼                                    │
│  ┌──────────────────────────────────────┐               │
│  │           Alert Dispatcher           │               │
│  │           告警分发器                  │               │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

### 1.2 组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Collector（采集器） | 从各引擎周期性采集运行指标 | 引擎原始数据 | 标准化指标序列 |
| Detector（检测器） | 基于统计阈值检测异常波动 | 指标序列 + σ 阈值 | 异常事件列表 |
| Ranker（排行器） | 按使用频次和效果评分生成排行榜 | 模板使用统计 | 排行数据 |
| Metrics Store（指标存储） | 持久化存储时序指标数据 | 标准化指标 | 查询结果 |
| Trend Calculator（趋势计算器） | 计算移动平均线和趋势方向 | 原始指标序列 | 平滑趋势序列 |
| Alert Dispatcher（告警分发器） | 分发告警至配置的通知渠道 | 异常事件 | 告警通知 |

### 1.3 数据流

```
1. Collector 按 refresh_interval_seconds 周期采集各引擎指标
2. 采集数据写入 Metrics Store（带时间戳）
3. Detector 从 Metrics Store 读取最近 N 个样本，计算均值和标准差
4. 若最新值偏离均值超过 2σ，生成异常事件
5. Trend Calculator 对历史数据计算 7 日移动平均线
6. Ranker 定期（每日）汇总模板使用频次和效果评分
7. Alert Dispatcher 将异常事件分发至配置的告警渠道
```

---

## 二、效果趋势可视化

### 2.1 指标类型

| 指标类别 | 具体指标 | 采集源 | 单位 |
|---------|---------|--------|------|
| 编译质量 | compile_success_rate | _compiler | % |
| 编译性能 | compile_time_ms | _compiler | ms |
| 缓存效率 | cache_hit_rate | _compiler | % |
| 实验完成率 | test_completion_rate | _ab_tests | % |
| 推荐采纳率 | recommendation_adoption_rate | _ab_tests | % |
| 安全通过率 | scan_pass_rate | _security | % |
| 高危阻断数 | high_severity_block_count | _security | 次 |
| 版本发布频率 | version_publish_frequency | _versions | 次/周 |
| 锁定时长 | lock_duration_hours | _versions | 小时 |

### 2.2 趋势图类型

| 图表类型 | 适用指标 | 说明 |
|---------|---------|------|
| 折线图 | 所有时序指标 | 展示指标随时间变化趋势，叠加移动平均线 |
| 面积图 | 累积型指标（如发布频率） | 折线图下方填充面积，突出累积效果 |
| 柱状图 | 离散型指标（如阻断次数） | 按时间区间聚合展示 |
| 散点图 | 异常事件 | 标注异常点位置，颜色表示严重程度 |

### 2.3 趋势方向判定

```
趋势方向 = sign(MA7_latest - MA7_3days_ago)

- 上升趋势：趋势方向 > 0 且持续 3 天以上
- 下降趋势：趋势方向 < 0 且持续 3 天以上
- 平稳：|趋势方向| < 阈值 或 方向频繁变化
```

---

## 三、异常波动 2σ 告警

### 3.1 检测算法

```
异常检测规则：

1. 计算最近 N 个样本的均值 μ 和标准差 σ
   N = min_sample_for_trend（默认 10）

2. 若最新观测值 x 满足：
   |x - μ| > threshold_sigma × σ
   
   则判定为异常波动
   threshold_sigma 默认 2.0

3. 异常等级：
   - 警告（warn）：2σ < |x - μ| ≤ 3σ
   - 严重（critical）：|x - μ| > 3σ
```

### 3.2 告警事件格式

```json
{
  "alert_id": "uuid-v4",
  "timestamp": "2026-07-12T10:30:00Z",
  "metric_name": "compile_success_rate",
  "source_engine": "_compiler",
  "observed_value": 72.5,
  "expected_range": {
    "mean": 95.2,
    "std_dev": 3.1,
    "lower_bound": 89.0,
    "upper_bound": 101.4
  },
  "deviation_sigma": 7.32,
  "severity": "critical",
  "direction": "below",
  "context": {
    "template_id": "e1_deh",
    "version": "1.2.0",
    "recent_changes": ["1.2.0 发布于 2 小时前"]
  }
}
```

### 3.3 告警抑制

- **重复抑制**：同一指标同一方向在 30 分钟内仅触发一次告警
- **维护窗口**：标记为维护窗口的时间段内抑制告警
- **级联抑制**：若上游引擎异常已触发告警，下游引擎的关联告警自动抑制

### 3.4 告警渠道

| 渠道 | 最低严重级别 | 配置项 |
|------|------------|--------|
| 日志 | warn | `alert_channels[type=log]` |
| Webhook | critical | `alert_channels[type=webhook]` |
| 邮件 | critical | `alert_channels[type=email]` |

---

## 四、模板排行榜

### 4.1 排行维度

排行榜按双维度综合评分：

```
综合评分 = 0.4 × 使用频次归一化分 + 0.6 × 效果评分归一化分
```

#### 使用频次

| 统计项 | 计算方式 |
|--------|---------|
| 调用次数 | 最近 30 天内模板被引用/使用的总次数 |
| 活跃用户数 | 最近 30 天内使用该模板的去重用户数 |
| 增长率 | (本周调用次数 - 上周调用次数) / 上周调用次数 |

#### 效果评分

| 统计项 | 计算方式 |
|--------|---------|
| 问题解决率 | 使用模板后成功解决问题的比例 |
| 用户满意度 | 基于反馈的正向评价比例 |
| 覆盖完整度 | 模板覆盖的场景数 / 总场景数 |

### 4.2 排行榜输出格式

```json
{
  "generated_at": "2026-07-12T00:00:00Z",
  "period": "30d",
  "rankings": [
    {
      "rank": 1,
      "template_id": "e1_deh",
      "template_name": "华为云DEH（专属主机）",
      "composite_score": 92.5,
      "usage_score": {
        "invocations": 1580,
        "active_users": 42,
        "growth_rate": 0.12,
        "normalized": 88.0
      },
      "effect_score": {
        "resolution_rate": 0.94,
        "satisfaction_rate": 0.97,
        "coverage_rate": 0.85,
        "normalized": 95.3
      }
    }
  ]
}
```

### 4.3 排行榜刷新

- 每日 00:00 UTC 自动计算并刷新
- 支持手动触发刷新
- 历史排行榜快照保留 90 天

---

## 五、移动平均线（7 日窗口）

### 5.1 算法定义

```
MA7(t) = (1/7) × Σ[x(t-i)]  其中 i = 0, 1, ..., 6

即最近 7 个数据点的简单移动平均
```

### 5.2 窗口选择依据

| 窗口大小 | 适用场景 | 本系统选择 |
|---------|---------|-----------|
| 3 日 | 高频指标，需快速响应 | - |
| **7 日** | **通用场景，平衡噪声过滤和响应速度** | **默认** |
| 14 日 | 低频指标，需强平滑 | - |
| 30 日 | 长期趋势分析 | 可选 |

7 日窗口的选择理由：

- 对应一个自然周，消除工作日/休息日周期性波动
- 平滑单日异常值的影响，同时保留趋势变化信息
- 与 `min_sample_for_trend: 10` 配合，确保统计显著性

### 5.3 移动平均线计算规则

- **数据点不足**：当历史数据少于 7 个点时，使用已有数据计算（实际窗口 = 数据点数）
- **缺失值处理**：采集间隔内的缺失值使用前值填充（last observation carried forward）
- **异常值处理**：被 Detector 标记为异常的值，在计算 MA7 时可选择排除或保留
  - 默认保留（反映真实波动）
  - 配置 `exclude_anomalies_from_ma: true` 可排除

### 5.4 趋势信号

基于 MA7 的交叉信号：

```
短期趋势信号：
  MA3 上穿 MA7 → 上升趋势确认
  MA3 下穿 MA7 → 下降趋势确认

长期趋势信号：
  当前 MA7 > 7天前 MA7 → 长期上升趋势
  当前 MA7 < 7天前 MA7 → 长期下降趋势
```

---

## 六、配置参考

效果追踪的所有参数均可通过 `_dashboard/config.yaml` 配置：

```yaml
anomaly_threshold_sigma: 2.0          # 异常检测 σ 阈值
min_sample_for_trend: 10              # 趋势分析最小样本数
moving_average_window: 7              # 移动平均窗口（天）
refresh_interval_seconds: 60          # 数据刷新间隔（秒）
data_retention_days: 90               # 数据保留天数
ranking_refresh_cron: "0 0 * * *"     # 排行榜刷新 cron
alert_suppression_window_minutes: 30  # 告警抑制窗口（分钟）
exclude_anomalies_from_ma: false      # MA 计算是否排除异常值
```
