# 胜率矩阵生成器

> **版本**: v2.0.0 | **日期**: 2026-07-12 | **参考**: promptfoo Web Viewer对比矩阵

---

## 一、数据结构

### 1.1 WinRateMatrix

```typescript
interface WinRateMatrix {
  test_id: string;
  templates: TemplateRef[];
  models: ModelRef[];
  cells: MatrixCell[][];
  generated_at: string;  // ISO 8601
  config: {
    significance_level: number;
    min_samples_for_significance: number;
  };
}

interface TemplateRef {
  id: string;
  name: string;
  source: string;
}

interface ModelRef {
  id: string;
  provider: string;
}
```

### 1.2 MatrixCell

```typescript
interface MatrixCell {
  template_id: string;
  model_id: string;
  win_rate: number;          // 0.0 - 1.0
  sample_size: number;       // 有效样本数
  p_value: number | null;    // 统计显著性p值，null=样本不足
  is_significant: boolean;   // p < 0.05
  confidence_interval: {
    lower: number;
    upper: number;
  } | null;
  avg_score: number;         // 6维加权平均分
  score_stability: "stable" | "moderate" | "unstable";  // CV判定
  dimension_scores: {
    accuracy: number;
    relevance: number;
    coherence: number;
    completeness: number;
    efficiency: number;
    safety: number;
  };
}
```

## 二、胜率计算逻辑

### 2.1 配对比较法

```
对于每个样本 s:
  IF score_model_A(s) > score_model_B(s):
    model_A 胜出次数 +1
  ELIF score_model_A(s) < score_model_B(s):
    model_B 胜出次数 +1
  ELSE:
    平局，各 +0.5

胜率 = 胜出次数 / 总对比次数
```

### 2.2 多模型胜率

当模型数 > 2时，采用**多轮两两对比**：

```
对于 N 个模型:
  对比轮次 = C(N,2) = N×(N-1)/2
  每个模型的综合胜率 = 该模型胜出次数 / (总对比次数 × 每轮样本数)
```

### 2.3 样本量不足处理

```
IF sample_size < min_samples_for_significance:
    p_value = null
    is_significant = false
    标注: "样本不足，统计显著性不可判定"
```

## 三、矩阵可视化模板

### 3.1 Markdown表格模板

```markdown
## 胜率矩阵: {test_name}

> 生成时间: {generated_at} | 显著性水平: α={significance_level}

| 模板\模型 | {model_1} | {model_2} | {model_3} | {model_4} |
|-----------|-----------|-----------|-----------|-----------|
| {tpl_1} | 🟢 0.72*** | 🟡 0.55 | 🔴 0.38* | 🟢 0.68** |
| {tpl_2} | 🟡 0.50 | 🟢 0.65** | 🟢 0.70*** | 🔴 0.35** |
| {tpl_3} | 🟢 0.80*** | 🔴 0.42* | 🟡 0.48 | 🟢 0.75*** |

**图例**: 🟢 胜率>0.6 | 🟡 胜率0.4-0.6 | 🔴 胜率<0.4
*** p<0.001 | ** p<0.01 | * p<0.05 | 无标注=不显著

**颜色编码**: 🟩显著胜出 | 🟨平局 | 🟥显著落后 | ⬜样本不足
```

### 3.2 矩阵Cell详细视图

```markdown
### {template_id} × {model_id}

| 指标 | 值 |
|------|-----|
| 胜率 | 0.72 |
| 样本量 | 150 |
| p值 | 0.003 |
| 显著性 | ✅ 显著 |
| 95%置信区间 | [0.64, 0.80] |
| 平均分 | 4.12 |
| 稳定性 | 稳定 (CV=0.18) |
| 准确性 | 4.5 |
| 相关性 | 4.2 |
| 连贯性 | 4.0 |
| 完整性 | 3.8 |
| 效率 | 4.5 |
| 安全性 | 3.7 |
```

## 四、胜率矩阵示例

### 4.1 3模板×4模型矩阵

```markdown
## 胜率矩阵: 代码审查+架构设计提示词效果对比

> 生成时间: 2026-07-12T10:30:00+08:00 | 显著性水平: α=0.05

| 模板\模型 | gpt-4o | claude-3.5 | qwen-max | pangu-large |
|-----------|--------|------------|----------|-------------|
| 代码审查 | 🟢 0.78*** | 🟢 0.72** | 🟡 0.55 | 🟡 0.48 |
| 架构设计 | 🟢 0.65* | 🟢 0.70** | 🟢 0.62 | 🔴 0.40 |
| 安全审计 | 🟡 0.52 | 🟢 0.68** | 🟡 0.50 | 🟢 0.60 |

### 统计显著性汇总

| 对比 | 胜者 | p值 | Cohen's d | 效果量 |
|------|------|-----|-----------|--------|
| 代码审查: gpt-4o vs claude-3.5 | gpt-4o | 0.003 | 0.45 | 小 |
| 架构设计: claude-3.5 vs qwen-max | claude-3.5 | 0.021 | 0.38 | 小 |
| 安全审计: pangu-large vs qwen-max | pangu-large | 0.041 | 0.52 | 中等 |
```

### 4.2 样本量不足标注

```markdown
| 性能压测 | 🟢 0.85** | ⬜ N/A | ⬜ N/A | 🟡 0.50 |
|         | (n=50)   | (n=8) | (n=5) | (n=45)  |

> ⬜ 标注: 样本不足(min≥30)，统计显著性不可判定
```
