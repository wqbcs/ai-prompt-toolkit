# 最优匹配推荐器

> **版本**: v2.0.0 | **日期**: 2026-07-12

---

## 一、数据结构

```typescript
interface OptimalMatch {
  template_id: string;
  model_id: string;
  win_rate: number;
  p_value: number | null;
  is_significant: boolean;
  avg_score: number;
  score_stability: "stable" | "moderate" | "unstable";
  composite_score: number;
  recommendation: "strong" | "moderate" | "weak" | "none";
  reason: string;
  excluded: boolean;
  exclusion_reason?: string;
}

interface MatchRecommendation {
  test_id: string;
  generated_at: string;  // ISO 8601
  criteria: "win_rate_significance" | "composite_score";
  matches: OptimalMatch[];
  summary: string;
}
```

## 二、推荐逻辑

### 2.1 胜率+显著性模式(win_rate_significance)

```
FOR each (template, model) pair:
  IF score_stability == "unstable":
    excluded = true
    exclusion_reason = "评分不稳定(CV>0.5)，不纳入推荐"
    CONTINUE

  IF win_rate > 0.6 AND is_significant == true:
    recommendation = "strong"
    reason = "胜率{win_rate}显著高于其他模型(p={p_value})"
  ELIF win_rate > 0.55 AND is_significant == true:
    recommendation = "moderate"
    reason = "胜率{win_rate}显著高于部分模型(p={p_value})"
  ELIF win_rate > 0.5:
    recommendation = "weak"
    reason = "胜率{win_rate}略高于平均，但统计不显著"
  ELSE:
    recommendation = "none"
    reason = "胜率{win_rate}低于平均"
```

### 2.2 综合评分模式(composite_score)

```
composite_score = (
  win_rate_weight × win_rate +
  significance_weight × significance_score +
  avg_score_weight × avg_score_normalized +
  efficiency_weight × efficiency_normalized
)

各权重默认值:
  win_rate_weight = 0.4
  significance_weight = 0.3
  avg_score_weight = 0.2
  efficiency_weight = 0.1

significance_score:
  p < 0.001 → 1.0
  p < 0.01 → 0.8
  p < 0.05 → 0.6
  p < 0.10 → 0.3
  p ≥ 0.10 → 0.0
  null → 0.0 (样本不足)

推荐判定:
  composite_score ≥ 0.7 → "strong"
  composite_score ≥ 0.5 → "moderate"
  composite_score ≥ 0.3 → "weak"
  composite_score < 0.3 → "none"
```

## 三、排除规则

| 规则 | 条件 | 处理 |
|------|------|------|
| 稳定性排除 | CV > 0.5 | 不纳入推荐，标注原因 |
| 样本量排除 | 有效样本 < 10 | 不纳入推荐，标注原因 |
| 全部失败排除 | 所有样本均失败 | 不纳入推荐，标注原因 |
| 安全性排除 | 安全性评分 < 2 | 不纳入推荐，标注安全风险 |

## 四、推荐理由生成规则

### 4.1 强推荐模板

```
"在{template_name}场景中，{model_name}表现最优：
 胜率{win_rate}，统计显著(p={p_value})，
 平均评分{avg_score}/5.0，
 {最强维度}维度得分{max_dim_score}。
 建议优先使用{model_name}执行此场景。"
```

### 4.2 弱推荐模板

```
"在{template_name}场景中，{model_name}胜率{win_rate}，
 但统计不显著(p={p_value})，
 建议增加样本量后重新评估。"
```

### 4.3 排除说明模板

```
"{model_name}在{template_name}场景中被排除推荐：
 原因: {exclusion_reason}，
 建议修复后重新测试。"
```

## 五、推荐报告示例

```markdown
## 最优匹配推荐报告

> 测试ID: ab-test-001 | 生成时间: 2026-07-12T11:00:00+08:00
> 推荐模式: win_rate_significance | 显著性水平: α=0.05

### 强推荐 ⭐⭐⭐

| 场景 | 推荐模型 | 胜率 | p值 | 平均分 | 理由 |
|------|----------|------|-----|--------|------|
| 代码审查 | gpt-4o | 0.78 | 0.003 | 4.12 | 准确性4.5，连贯性4.0，综合最优 |
| 架构设计 | claude-3.5 | 0.70 | 0.021 | 4.05 | 相关性4.3，完整性4.2 |

### 中等推荐 ⭐⭐

| 场景 | 推荐模型 | 胜率 | p值 | 平均分 | 理由 |
|------|----------|------|-----|--------|------|
| 安全审计 | pangu-large | 0.60 | 0.041 | 3.85 | 安全性4.5突出，但连贯性3.2需改进 |

### 弱推荐 ⭐

| 场景 | 推荐模型 | 胜率 | p值 | 平均分 | 理由 |
|------|----------|------|-----|--------|------|
| 代码审查 | qwen-max | 0.55 | 0.12 | 3.72 | 胜率略高但统计不显著 |

### 排除项

| 场景 | 模型 | 排除原因 |
|------|------|----------|
| 性能压测 | pangu-large | 评分不稳定(CV=0.62) |
```
