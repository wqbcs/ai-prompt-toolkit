# R1-04 提示词A/B测试引擎-框架设计

> **迭代**：v21-R1-04 | **日期**：2026-07-12

---

## 一、A/B测试框架架构

### 核心概念

```
┌──────────────────────────────────────────────┐
│              A/B 测试引擎                      │
├──────────────┬──────────────┬────────────────┤
│  实验管理     │  执行引擎     │  统计分析       │
│              │              │                │
│ · 创建实验   │ · 并行执行   │ · 显著性检验    │
│ · 定义变体   │ · 随机分配   │ · 效果量计算    │
│ · 配置指标   │ · 结果收集   │ · 置信区间      │
│ · 设置参数   │ · 异常处理   │ · 可视化报告    │
└──────────────┴──────────────┴────────────────┘
```

### 数据结构

```typescript
interface ABTestExperiment {
  id: string
  name: string
  description: string
  hypothesis: string
  status: 'draft' | 'running' | 'paused' | 'completed' | 'archived'
  variants: ABTestVariant[]
  metrics: ABTestMetric[]
  sampleSize: number
  significanceLevel: number        // 默认0.05
  minimumDetectableEffect: number   // 默认0.1
  startDate: string
  endDate?: string
  results?: ABTestResult
}

interface ABTestVariant {
  id: string
  name: string                     // 'control' | 'variant_A' | 'variant_B'
  promptContent: string
  isControl: boolean
  trafficPercent: number           // 流量分配百分比
  metadata: Record<string, unknown>
}

interface ABTestMetric {
  name: string
  type: 'quality' | 'latency' | 'cost' | 'token_count' | 'user_rating' | 'faithfulness' | 'relevancy'
  direction: 'higher_is_better' | 'lower_is_better'
  weight: number                   // 权重0-1
  evaluationMethod: 'automatic' | 'llm_judge' | 'human'
  threshold?: number
}
```

## 二、执行引擎

### 执行流程

```
1. 随机分配样本 → control / variant_A / variant_B
2. 并行执行提示词 → 收集原始输出
3. 评估输出质量 → 7类指标计算
4. 统计分析 → 显著性检验
5. 生成报告 → 推荐最优变体
```

### 评估方法

| 方法 | 说明 | 适用指标 |
|------|------|---------|
| 自动评估 | 代码/结构/格式检查 | quality, token_count, latency, cost |
| LLM-as-Judge | 大模型评判质量 | faithfulness, relevancy, quality |
| 人工评估 | 人类专家评分 | user_rating, quality |

### LLM-as-Judge评估模板

```markdown
你是一位专业的提示词输出质量评估专家。请对比以下两组提示词输出。

## 评估维度
1. 准确性（0-10）：输出是否准确回答了问题
2. 完整性（0-10）：输出是否覆盖了所有要求
3. 结构性（0-10）：输出是否结构清晰格式规范
4. 可操作性（0-10）：输出是否可直接投入使用
5. 安全性（0-10）：输出是否无安全隐患

## 变体A输出
{variant_a_output}

## 变体B输出
{variant_b_output}

## 请输出
1. 各维度评分（JSON格式）
2. 总体偏好（A/B/平局）
3. 偏好原因（50字以内）
```

## 三、统计分析

### 统计方法

| 方法 | 适用 | 说明 |
|------|------|------|
| t检验 | 连续指标 | 均值差异显著性 |
| Mann-Whitney U | 非正态分布 | 非参数检验 |
| 卡方检验 | 分类指标 | 比例差异显著性 |
| 贝叶斯检验 | 小样本 | 后验概率比较 |
| Bonferroni校正 | 多指标 | 多重比较校正 |

### 统计指标

```typescript
interface ABTestResult {
  experimentId: string
  totalSamples: number
  variantResults: VariantResult[]
  statisticalTests: StatisticalTest[]
  recommendation: {
    winner: string
    confidence: number
    improvementPercent: number
    reason: string
  }
}

interface VariantResult {
  variantId: string
  metrics: Record<string, {
    mean: number
    median: number
    std: number
    min: number
    max: number
    sampleSize: number
  }>
}

interface StatisticalTest {
  metric: string
  testType: string
  pValue: number
  effectSize: number          // Cohen's d
  confidenceInterval: [number, number]
  isSignificant: boolean
  power: number
}
```

## 四、报告生成

### A/B测试报告模板

```markdown
# A/B测试报告: {实验名称}

## 实验概要
| 项目 | 值 |
|------|-----|
| 假设 | {hypothesis} |
| 样本量 | {totalSamples} |
| 显著性水平 | {significanceLevel} |
| 运行周期 | {startDate} ~ {endDate} |

## 变体对比
| 指标 | Control | Variant A | Variant B | 最优 |
|------|---------|-----------|-----------|------|
| {metric} | {mean}±{std} | {mean}±{std} | {mean}±{std} | {winner} |

## 统计显著性
| 指标 | p值 | 效果量 | 显著? | 置信区间 |
|------|-----|--------|-------|---------|
| {metric} | {pValue} | {effectSize} | {isSignificant} | {CI} |

## 推荐结论
**最优变体**: {winner} (置信度: {confidence}%)
**提升幅度**: {improvementPercent}%
**推荐原因**: {reason}
```

## 五、验收项

- [x] A/B测试框架3层架构
- [x] 实验管理数据结构（Experiment/Variant/Metric）
- [x] 执行引擎5步流程+3种评估方法
- [x] LLM-as-Judge评估模板
- [x] 5种统计方法+统计指标数据结构
- [x] A/B测试报告模板
