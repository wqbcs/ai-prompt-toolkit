# 评估框架 v7.0

> **版本**: v7.0 | **日期**: 2026-07-12 | **升级**: v6→v7，新增A/B测试v2+D45+D46维度

---

## 一、版本升级摘要

| 项目 | v6 | v7 |
|------|-----|-----|
| 评估维度 | 44维度 | 46维度 |
| 新增维度 | - | D45 A/B测试 + D46 条件编译 |
| A/B测试 | v1（单模型） | v2（多模型并行对比） |
| 统计检验 | 无 | t检验 + Mann-Whitney U |
| 胜率矩阵 | 无 | M×N矩阵 |
| 最优匹配 | 无 | 自动推荐 |
| 场景模板 | 183 | 207 |

## 二、v6→v7迁移路径

### 2.1 兼容性保证

| 项目 | 兼容性 | 说明 |
|------|--------|------|
| v6评估配置 | ✅ 完全兼容 | v6配置可在v7框架中加载 |
| v6评估结果 | ✅ 完全兼容 | v6结果可在v7 Dashboard展示 |
| v6 API接口 | ✅ 完全兼容 | 所有v6接口在v7中保留 |
| v6回归测试 | ✅ 完全兼容 | v6测试用例在v7中可执行 |

### 2.2 迁移步骤

```
1. 读取v6评估配置
2. 补充A/B测试v2配置（可选，默认禁用）
3. 补充D45/D46维度评估（新增，不影响v6维度）
4. 执行v7全量评估
5. 对比v6与v7结果，确认无退化
```

### 2.3 Breaking Changes

无Breaking Changes。v7是v6的纯增量升级。

## 三、46维度184子维度评估框架

### 3.1 完整维度列表

| 维度编号 | 维度名称 | 子维度数 | 满分 | 新增 |
|----------|----------|----------|------|------|
| D1-D44 | (同v6) | 4 | 25 | 否 |
| D45 | A/B测试 | 4 | 25 | 是 |
| D46 | 条件编译 | 4 | 25 | 是 |

### 3.2 D45 A/B测试维度

| 子维度 | 名称 | 评分标准 | 满分 |
|--------|------|----------|------|
| D45.1 | 多模型对比能力 | 支持2-8个模型并行对比 | 6 |
| D45.2 | 统计显著性检验 | t检验/Mann-Whitney U/自动选择 | 7 |
| D45.3 | 胜率矩阵质量 | M×N矩阵+颜色编码+样本量标注 | 6 |
| D45.4 | 最优匹配推荐 | 基于胜率+显著性的推荐逻辑 | 6 |

### 3.3 D46 条件编译维度

| 子维度 | 名称 | 评分标准 | 满分 |
|--------|------|----------|------|
| D46.1 | 条件指令语法 | 三维度+4操作符+2逻辑符 | 6 |
| D46.2 | 编译正确性 | 三维度求值+嵌套处理+回退分支 | 7 |
| D46.3 | 缓存性能 | LRU缓存命中率≥80% | 6 |
| D46.4 | 编译报告 | 激活/忽略/未覆盖分支+告警 | 6 |

## 四、A/B测试v2集成

### 4.1 与评估框架的集成点

```
评估框架v7
    │
    ├── 核心评估（46维度×207场景）
    │
    ├── A/B测试v2引擎 ← 新增
    │   ├── 配置Schema (ab_test_v2_config.yaml)
    │   ├── 并行执行调度器 (parallel_executor.md)
    │   ├── 统计评估引擎 (statistical_engine.md)
    │   ├── 胜率矩阵生成器 (win_rate_matrix_template.md)
    │   ├── 最优匹配推荐器 (optimal_match_template.md)
    │   └── 对比报告模板 (comparison_report_template.md)
    │
    └── 回归测试框架v7
        ├── 核心场景回归 (12场景)
        ├── 全量结构回归 (207场景)
        └── 效果回归测试 (105用例，同v6)
```

### 4.2 评估流程

```
1. 执行46维度全量评估（基线）
2. 配置A/B测试v2（选择模型+模板+数据集）
3. 执行并行测试
4. 生成胜率矩阵
5. 生成最优匹配推荐
6. 生成对比报告
7. 更新评估Dashboard
```

## 五、集成测试用例

### 5.1 3模板×4模型端到端测试

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 加载测试配置 | 配置校验通过 |
| 2 | 并行调用4个模型 | 4模型均返回结果 |
| 3 | 6维评分 | 每个模型-模板对6维评分完整 |
| 4 | 统计检验 | 输出p值+置信区间 |
| 5 | 胜率矩阵 | 3×4矩阵完整，颜色标注正确 |
| 6 | 最优匹配 | 推荐逻辑正确，排除不稳定项 |
| 7 | 对比报告 | 报告包含所有6个章节 |

### 5.2 异常场景测试

| 场景 | 操作 | 预期结果 |
|------|------|----------|
| 单模型失败 | 模拟1个模型API失败 | 其余3模型正常，报告标注失败 |
| 样本不足 | 使用10个样本 | 标注"样本不足" |
| 全部超时 | 设置极短超时 | 报告标注"测试超时" |
| 评分不稳定 | 构造CV>0.5的评分 | 排除推荐，标注不稳定 |

## 六、评估Dashboard数据结构v7

```json
{
  "dashboard": {
    "version": "v7.0.0",
    "timestamp": "2026-07-12T12:00:00+08:00",
    "overall": {
      "mean_score": 23.50,
      "std_dev": 0.10,
      "total_scenarios": 207,
      "total_dimensions": 46,
      "total_subdimensions": 184
    },
    "dimensions": {
      "D1-D44": "(同v6，略)",
      "D45_ab_test": {
        "score": 23.00,
        "trend": "new",
        "subdimensions": {
          "D45.1_multi_model": 5.5,
          "D45.2_statistical": 6.0,
          "D45.3_win_rate": 5.8,
          "D45.4_optimal_match": 5.7
        }
      },
      "D46_conditional_compile": {
        "score": 23.00,
        "trend": "new",
        "subdimensions": {
          "D46.1_syntax": 5.5,
          "D46.2_correctness": 6.0,
          "D46.3_cache": 5.8,
          "D46.4_report": 5.7
        }
      }
    },
    "ab_test_v2": {
      "total_tests": 0,
      "completed_tests": 0,
      "latest_matrix": null,
      "latest_recommendations": null
    },
    "regression": {
      "total": 207,
      "passed": 207,
      "failed": 0
    }
  }
}
```

## 七、Promptfoo集成配置v7

```yaml
# _evaluations_v7/promptfoo/promptfooconfig_v7.yaml
description: "AI提示词体系v7.0.0评估配置"
providers:
  - id: "openai:gpt-4o"
    config:
      temperature: 0.7
      max_tokens: 4096
  - id: "anthropic:claude-3.5-sonnet"
    config:
      temperature: 0.7
      max_tokens: 4096

prompts: _evaluations_v7/promptfoo/prompts/
tests: _evaluations_v7/promptfoo/tests/

evaluateOptions:
  maxConcurrency: 4
  timeout: 30000

assertions:
  - type: "llm-rubric"
    value: "准确性评估"
  - type: "llm-rubric"
    value: "相关性评估"
  - type: "llm-rubric"
    value: "连贯性评估"
  - type: "llm-rubric"
    value: "完整性评估"
```
