# A/B测试v2对比报告模板

> **版本**: v2.0.0 | **日期**: 2026-07-12

---

# A/B测试v2对比报告: {test_name}

> **测试ID**: {test_id}
> **执行时间**: {started_at} ~ {completed_at}
> **状态**: {status}
> **模型数量**: {model_count}
> **模板数量**: {template_count}
> **样本量**: {sample_count}

---

## 一、测试概览

| 项目 | 值 |
|------|-----|
| 测试名称 | {test_name} |
| 评估维度 | 准确性/相关性/连贯性/完整性/效率/安全性 |
| 统计方法 | {test_method} (自动选择) |
| 显著性水平 | α = {significance_level} |
| 最小显著样本量 | {min_samples_for_significance} |

### 1.1 参测模型

| 模型 | Provider | 样本量 | 成功率 | 平均延迟(ms) |
|------|----------|--------|--------|-------------|
| {model_1} | {provider_1} | {n_1} | {success_rate_1}% | {latency_1} |
| {model_2} | {provider_2} | {n_2} | {success_rate_2}% | {latency_2} |
| {model_3} | {provider_3} | {n_3} | {success_rate_3}% | {latency_3} |

### 1.2 参测模板

| 模板 | 来源文档 | 场景类型 |
|------|----------|----------|
| {template_1} | {source_1} | {category_1} |
| {template_2} | {source_2} | {category_2} |

---

## 二、6维评估结果

### 2.1 各模板×各模型评分矩阵

#### 准确性(Accuracy)

| 模板\模型 | {model_1} | {model_2} | {model_3} |
|-----------|-----------|-----------|-----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} |

#### 相关性(Relevance)

| 模板\模型 | {model_1} | {model_2} | {model_3} |
|-----------|-----------|-----------|-----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} |

#### 连贯性(Coherence)

| 模板\模型 | {model_1} | {model_2} | {model_3} |
|-----------|-----------|-----------|-----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} |

#### 完整性(Completeness)

| 模板\模型 | {model_1} | {model_2} | {model_3} |
|-----------|-----------|-----------|-----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} |

#### 效率(Efficiency)

| 模板\模型 | {model_1} | {model_2} | {model_3} | Token消耗 | 延迟(ms) |
|-----------|-----------|-----------|-----------|-----------|----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} | {tokens_1} | {latency_1} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} | {tokens_2} | {latency_2} |

#### 安全性(Safety)

| 模板\模型 | {model_1} | {model_2} | {model_3} | 违规次数 |
|-----------|-----------|-----------|-----------|----------|
| {tpl_1} | {score_1_1} | {score_1_2} | {score_1_3} | {violations_1} |
| {tpl_2} | {score_2_1} | {score_2_2} | {score_2_3} | {violations_2} |

### 2.2 综合加权评分

| 模板\模型 | {model_1} | {model_2} | {model_3} |
|-----------|-----------|-----------|-----------|
| {tpl_1} | {weighted_1_1} | {weighted_1_2} | {weighted_1_3} |
| {tpl_2} | {weighted_2_1} | {weighted_2_2} | {weighted_2_3} |

> 加权公式: accuracy×0.25 + relevance×0.20 + coherence×0.20 + completeness×0.15 + efficiency×0.10 + safety×0.10

---

## 三、胜率矩阵

{win_rate_matrix_content}

---

## 四、最优匹配推荐

{optimal_match_content}

---

## 五、统计显著性汇总

### 5.1 显著性检验结果

| 对比对 | 检验方法 | 统计量 | p值 | 显著性 | Cohen's d | 效果量 |
|--------|----------|--------|-----|--------|-----------|--------|
| {tpl_1}: {model_1} vs {model_2} | t-test | t={t_val} | {p_val} | {sig} | {d_val} | {effect} |
| {tpl_1}: {model_1} vs {model_3} | Mann-Whitney | U={u_val} | {p_val} | {sig} | {d_val} | {effect} |
| {tpl_2}: {model_2} vs {model_3} | t-test | t={t_val} | {p_val} | {sig} | {d_val} | {effect} |

### 5.2 置信区间

| 对比对 | 95%CI下界 | 95%CI上界 | 包含0 |
|--------|-----------|-----------|-------|
| {pair_1} | {lower_1} | {upper_1} | {contains_zero_1} |
| {pair_2} | {lower_2} | {upper_2} | {contains_zero_2} |

---

## 六、异常标注

### 6.1 测试失败

| 模型 | 模板 | 失败样本 | 失败率 | 失败原因 |
|------|------|----------|--------|----------|
| {model_x} | {tpl_y} | {fail_count}/{total} | {fail_rate}% | {reason} |

### 6.2 评分不稳定

| 模型 | 模板 | CV值 | 稳定性 | 建议 |
|------|------|------|--------|------|
| {model_x} | {tpl_y} | {cv_val} | {stability} | {suggestion} |

### 6.3 样本不足

| 模型 | 模板 | 有效样本 | 最小要求 | 状态 |
|------|------|----------|----------|------|
| {model_x} | {tpl_y} | {actual} | {required} | 样本不足 |

---

## 七、结论与建议

### 7.1 核心发现

1. {finding_1}
2. {finding_2}
3. {finding_3}

### 7.2 推荐行动

1. {action_1}
2. {action_2}

### 7.3 后续测试建议

1. {next_test_1}
2. {next_test_2}

---

*报告由A/B测试v2引擎自动生成 | {generated_at}*
