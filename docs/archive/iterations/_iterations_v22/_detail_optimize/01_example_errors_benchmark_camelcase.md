# S8-01~06 细节优化4项

> **迭代**：v22-S8-01~06 | **日期**：2026-07-12

---

## D1：所有场景模板添加"最小可执行示例"（复制即用）

### 规范定义

```json
{
  "minExecutableExample": {
    "spec": {
      "title": "最小可执行示例",
      "format": "fenced_code_block",
      "requiredSections": {
        "input": {
          "description": "最简输入参数",
          "format": "自然语言描述+参数值",
          "maxParams": 3
        },
        "prompt": {
          "description": "完整可复制提示词",
          "format": "直接可粘贴文本",
          "rules": [
            "包含角色定义+任务+约束+输出格式",
            "参数用{paramName}占位",
            "不依赖外部上下文",
            "预期token<4000"
          ]
        },
        "expectedOutput": {
          "description": "预期输出示例",
          "format": "JSON(优先)/Markdown/代码",
          "rules": [
            "使用camelCase键名",
            "包含2-5个核心字段",
            "值用真实示例非lorem ipsum"
          ]
        }
      },
      "qualityChecks": [
        "复制prompt→粘贴到LLM→获得expectedOutput格式结果",
        "无外部依赖可独立执行",
        "输入参数<=3个",
        "完整prompt+output token<4000"
      ]
    },
    "coverageTarget": "135/135场景模板(100%)",
    "currentStatus": "v22已覆盖场景: 20(本迭代新增)"
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 示例过于复杂不可复制即用 | P1 | 最多3参数+完整prompt+无外部依赖 |
| 2 | 输出格式与场景模板不一致 | P1 | 严格遵循场景outputSchema |
| 3 | 示例参数值不真实 | P2 | 使用真实业务值+常见场景 |
| 4 | 缺少预期输出 | P1 | 必须包含expectedOutput |
| 5 | 示例依赖特定模型 | P2 | 通用设计+标注推荐模型 |

---

## D2：所有场景模板添加"常见错误"章节（Top5错误+修复方法）

### 规范定义

```json
{
  "commonErrors": {
    "spec": {
      "title": "常见错误Top5",
      "format": "table",
      "requiredColumns": {
        "index": {"type": "number", "range": "1-5"},
        "error": {"type": "text", "maxLength": 50},
        "errorExample": {"type": "code", "maxLength": 100},
        "fixMethod": {"type": "text", "maxLength": 100}
      },
      "selectionCriteria": [
        "频率最高：用户最常犯的错误",
        "影响最大：导致最严重后果的错误",
        "隐蔽最深：不容易发现的错误",
        "修复最难：需要专业知识的错误",
        "通用性最广：跨场景常见错误"
      ],
      "qualityChecks": [
        "每个错误有具体错误示例（非抽象描述）",
        "每个修复方法可直接执行",
        "5个错误覆盖不同严重等级(P0-P2)",
        "错误示例可复现"
      ]
    },
    "coverageTarget": "135/135场景模板(100%)",
    "currentStatus": "v22已覆盖: 20(本迭代新增)"
  }
}
```

---

## D3：所有场景模板添加"性能基准"（预期token消耗/延迟/成本）

### 规范定义

```json
{
  "performanceBenchmark": {
    "spec": {
      "title": "性能基准",
      "format": "table",
      "metrics": {
        "tokenConsumption": {
          "unit": "tokens",
          "format": "range",
          "example": "3K-8K",
          "measurementMethod": "最近100次执行P50-P95"
        },
        "latency": {
          "unit": "seconds",
          "format": "range",
          "example": "2-5s",
          "measurementMethod": "最近100次执行P50-P99"
        },
        "costPerExecution": {
          "unit": "USD",
          "format": "range",
          "example": "$0.02-0.05/次",
          "measurementMethod": "token×模型单价"
        }
      },
      "modelBreakdown": {
        "gpt4": {"tokenMultiplier": 1.0, "costPer1kTokens": "$0.03"},
        "claude3opus": {"tokenMultiplier": 0.9, "costPer1kTokens": "$0.015"},
        "qwenMax": {"tokenMultiplier": 1.1, "costPer1kTokens": "$0.004"},
        "deepseekV3": {"tokenMultiplier": 1.1, "costPer1kTokens": "$0.001"}
      },
      "qualityChecks": [
        "3项指标齐全(token/延迟/成本)",
        "范围为P50-P95/P99实测值",
        "包含至少2种模型的估算",
        "成本按当前定价计算"
      ]
    },
    "coverageTarget": "135/135场景模板(100%)",
    "currentStatus": "v22已覆盖: 20(本迭代新增)"
  }
}
```

---

## D4：统一所有JSON输出示例的键名为camelCase

### 规范定义

```json
{
  "camelCaseConvention": {
    "spec": {
      "title": "JSON输出camelCase统一规范",
      "rules": [
        "所有JSON键名使用camelCase",
        "首字母小写，后续单词首字母大写",
        "不使用下划线(snake_case)或短横线(kebab-case)",
        "缩写词全小写(除首个)：imageUrl(非imageURL)"
      ],
      "conversionTable": {
        "snake_case → camelCase": {
          "success_rate": "successRate",
          "token_consumption": "tokenConsumption",
          "quality_score": "qualityScore",
          "error_message": "errorMessage",
          "created_at": "createdAt",
          "updated_at": "updatedAt",
          "is_active": "isActive",
          "max_retry_count": "maxRetryCount",
          "api_endpoint": "apiEndpoint",
          "input_schema": "inputSchema",
          "output_format": "outputFormat",
          "common_errors": "commonErrors",
          "performance_benchmark": "performanceBenchmark"
        }
      },
      "validationScript": {
        "language": "Python",
        "function": "validate_camel_case_keys(json_obj)",
        "autoFix": true,
        "report": "列出所有非camelCase键名+自动转换建议"
      },
      "exemptions": [
        "外部API规定的字段名(需标注来源)",
        "数据库列名映射(需标注映射关系)"
      ]
    },
    "coverageTarget": "所有v22新增JSON示例(100%)",
    "currentStatus": "v22已覆盖: 100%(本迭代所有新增内容)"
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 缩写词大小写不一致 | P1 | 统一规则：imageUrl非imageURL |
| 2 | 嵌套JSON内部键名未转换 | P1 | 递归检查+深度遍历 |
| 3 | API兼容性被破坏 | P0 | 外部API字段标注豁免+映射层 |
| 4 | 自动转换工具误转 | P1 | 白名单+人工审核+回滚 |
| 5 | 文档与代码不一致 | P1 | 自动生成文档+一致性检查 |

---

## S8验收统计

| 优化项 | 覆盖场景 | 规范完整性 | 验证脚本 | 陷阱 |
|--------|---------|-----------|---------|------|
| 最小可执行示例 | 20/135 | ✓ | ✓ | 5 |
| 常见错误Top5 | 20/135 | ✓ | ✓ | 0 |
| 性能基准 | 20/135 | ✓ | ✓ | 0 |
| camelCase统一 | 100%(v22新增) | ✓ | ✓ | 5 |
| **S8小计** | - | - | - | **10** |
