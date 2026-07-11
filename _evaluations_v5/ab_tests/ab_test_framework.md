# A/B测试框架设计文档

> **版本**：v1.0.0
> **日期**：2026-05-29
> **用途**：为提示词版本间对比提供A/B测试框架

---

## 一、框架概述

A/B测试框架用于对比不同版本提示词（或不同模型适配策略）在相同测试集上的表现差异，为优化决策提供数据支撑。

### 1.1 核心原则
- **公平性**：A/B组使用完全相同的测试输入
- **可重复性**：测试过程可重复执行，结果可复现
- **统计显著性**：样本量足够，结果差异具有统计意义
- **单一变量**：每次A/B测试仅改变一个变量

---

## 二、测试配置结构

```yaml
# ab_test_config.yaml
test_id: "AB-001"
test_name: "04_代码审查场景A-国产模型适配效果对比"
created_at: "2026-05-29"

variants:
  variant_a:
    name: "原始提示词(无国产适配)"
    prompt_version: "v4.0.0"
    model: "gpt-4-turbo"
    prompt_file: "04_代码审查与质量保障提示词.md"
    scenario: "场景A"
    adaptation: "none"
    
  variant_b:
    name: "添加国产模型适配指令"
    prompt_version: "v4.0.0+domestic-adapt"
    model: "deepseek-v3"
    prompt_file: "04_代码审查与质量保障提示词.md"
    scenario: "场景A"
    adaptation: "deepseek_cot_zh"

test_dataset:
  source: "regression_test_cases"
  filters:
    scenario: "04-A"
    types: ["normal", "boundary"]
  sample_size: 20

evaluation:
  judge_model: "qwen-max"
  judge_template: "llm_judge_template_1"
  dimensions:
    - output_accuracy
    - structure_compliance
    - instruction_following
  sampling_count: 3
  aggregation: "median"

significance:
  confidence_level: 0.95
  min_sample_size: 20
  test_method: "paired_t_test"
```

---

## 三、测试执行流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1.加载配置   │ ──→ │  2.准备数据   │ ──→ │  3.执行Variant A│
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  6.生成报告   │ ←── │  5.统计检验   │ ←── │  4.执行Variant B│
└──────────────┘     └──────────────┘     └──────────────┘
```

### 3.1 详细步骤

1. **加载配置**：读取A/B测试配置YAML
2. **准备数据**：从回归测试用例中筛选匹配的测试集
3. **执行Variant A**：对每个测试输入执行A组prompt，收集输出
4. **执行Variant B**：对同一测试输入执行B组prompt，收集输出
5. **评估打分**：用LLM-as-Judge对A/B组输出分别打分
6. **统计检验**：计算差异显著性（配对t检验）
7. **生成报告**：汇总结果，给出优化建议

---

## 四、报告模板

```markdown
# A/B测试报告 [test_id]

## 测试概况
| 项目 | 值 |
|------|-----|
| 测试ID | AB-001 |
| 测试名称 | ... |
| Variant A | ... |
| Variant B | ... |
| 测试样本数 | 20 |
| 置信水平 | 95% |

## 八维度评分对比
| 维度 | A组均值 | B组均值 | 差异 | p值 | 显著性 |
|------|---------|---------|------|------|--------|
| 输出准确率 | 4.2 | 4.5 | +0.3 | 0.02 | ★ |
| 结构合规率 | 4.0 | 4.3 | +0.3 | 0.01 | ★ |
| 指令遵循率 | 3.8 | 4.1 | +0.3 | 0.03 | ★ |

## 结论
- [ ] Variant B显著优于A，建议采纳
- [ ] 差异不显著，需增加样本量
- [ ] Variant A更优，不建议变更

## 详细数据
[逐样本评分对比表]
```

---

## 五、已规划的A/B测试清单

| Test ID | 对比内容 | 优先级 | 状态 |
|---------|---------|--------|------|
| AB-001 | 04_代码审查A: DeepSeek适配vs原始 | P0 | 待执行 |
| AB-002 | 08_安全审计A: DeepSeek适配vs原始 | P0 | 待执行 |
| AB-003 | 01_需求分析A: 中文推理优化vs原始 | P1 | 待执行 |
| AB-004 | 04_代码审查A: Qwen-Max vs DeepSeek-V3 | P1 | 待执行 |
| AB-005 | 全场景: 国产模型整体vs国际模型 | P2 | 待执行 |

---

*本文档为C1批次迭代4产出，为后续C3批次国产模型适配效果验证提供A/B测试基础设施。*
