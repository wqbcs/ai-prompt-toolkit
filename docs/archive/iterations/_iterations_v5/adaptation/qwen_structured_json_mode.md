# Qwen-Max 结构化输出+JSON模式适配指令

> **版本**：v1.0.0
> **日期**：2026-05-29
> **迭代**：C10-迭代48
> **适用场景**：01_需求分析/02_架构设计/03_编码规范

---

## 一、适配原理

Qwen-Max核心优势在于中文理解(97分)和结构化输出(90分)，且原生支持JSON mode。结构化输出+JSON模式策略可确保Qwen输出Schema合规的结构化结果，同时利用其中文推理优势生成高质量的业务分析内容。

---

## 二、场景适配指令

### 2.1 01_需求分析场景A(PRD生成) 结构化输出+JSON模式

```markdown
<!-- Qwen-Max 适配指令 -->
【Qwen-Max 结构化输出+JSON模式优化】

**JSON模式启用**：请以严格的JSON格式输出PRD，输出必须符合以下JSON Schema：

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["product_info", "requirements", "constraints", "acceptance_criteria"],
  "properties": {
    "product_info": {
      "type": "object",
      "required": ["name", "version", "target_users", "core_value"],
      "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "target_users": {"type": "string"},
        "core_value": {"type": "string"}
      }
    },
    "requirements": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "priority", "description", "acceptance"],
        "properties": {
          "id": {"type": "string", "pattern": "^REQ-\\d{3}$"},
          "title": {"type": "string"},
          "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
          "description": {"type": "string"},
          "acceptance": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "constraints": {
      "type": "object",
      "properties": {
        "technical": {"type": "array", "items": {"type": "string"}},
        "business": {"type": "array", "items": {"type": "string"}},
        "security": {"type": "array", "items": {"type": "string"}},
        "performance": {"type": "array", "items": {"type": "string"}}
      }
    },
    "acceptance_criteria": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "metric": {"type": "string"},
          "threshold": {"type": "string"},
          "measurement_method": {"type": "string"}
        }
      }
    }
  }
}

**中文深度推理增强**：
请按以下步骤深度推理：
1. 【需求理解】用中文逐步解析用户需求，识别隐含需求
2. 【竞品对标】分析竞品功能覆盖，识别差异化需求
3. 【优先级决策】基于Kano模型分类：基本型/期望型/兴奋型
4. 【约束提取】显式提取技术/业务/安全/性能四维约束
5. 【验收量化】每个需求给出可量化的验收标准

确保输出为合法JSON，所有中文字段使用UTF-8编码。不要在JSON前后添加任何文字。
```

### 2.2 02_架构设计场景A(架构评审) 结构化输出+JSON模式

```markdown
<!-- Qwen-Max 适配指令 -->
【Qwen-Max 架构评审结构化输出+JSON模式优化】

**JSON模式启用**：请以严格的JSON格式输出架构评审报告，符合以下Schema：

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["architecture_overview", "quality_attributes", "risk_analysis", "improvement_plan"],
  "properties": {
    "architecture_overview": {
      "type": "object",
      "required": ["style", "components", "interactions"],
      "properties": {
        "style": {"type": "string"},
        "components": {"type": "array", "items": {"type": "object"}},
        "interactions": {"type": "array", "items": {"type": "object"}}
      }
    },
    "quality_attributes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["attribute", "current_score", "target_score", "gap_analysis"],
        "properties": {
          "attribute": {"type": "string", "enum": ["性能", "可用性", "安全性", "可扩展性", "可维护性", "可测试性"]},
          "current_score": {"type": "number", "minimum": 0, "maximum": 10},
          "target_score": {"type": "number", "minimum": 0, "maximum": 10},
          "gap_analysis": {"type": "string"}
        }
      }
    },
    "risk_analysis": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["risk", "probability", "impact", "mitigation"],
        "properties": {
          "risk": {"type": "string"},
          "probability": {"type": "string", "enum": ["高", "中", "低"]},
          "impact": {"type": "string", "enum": ["严重", "重大", "一般"]},
          "mitigation": {"type": "string"}
        }
      }
    },
    "improvement_plan": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["phase", "actions", "expected_outcome"],
        "properties": {
          "phase": {"type": "string"},
          "actions": {"type": "array", "items": {"type": "string"}},
          "expected_outcome": {"type": "string"}
        }
      }
    }
  }
}

**中文推理增强**：
1. 【架构理解】用中文分析当前架构模式及其适用场景
2. 【质量评估】基于ATAM方法逐项评估6大质量属性
3. 【风险识别】识别单点故障/扩展瓶颈/安全漏洞/技术债
4. 【改进方案】按优先级排序，给出分阶段改进路线图
```

### 2.3 03_编码规范场景A(编码规范) 结构化输出+JSON模式

```markdown
<!-- Qwen-Max 适配指令 -->
【Qwen-Max 编码规范结构化输出+JSON模式优化】

**JSON模式启用**：请以严格的JSON格式输出编码规范，符合以下Schema：

{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["language", "naming_conventions", "code_structure", "best_practices", "anti_patterns"],
  "properties": {
    "language": {"type": "string"},
    "naming_conventions": {
      "type": "object",
      "properties": {
        "classes": {"type": "string"},
        "methods": {"type": "string"},
        "variables": {"type": "string"},
        "constants": {"type": "string"},
        "packages": {"type": "string"}
      }
    },
    "code_structure": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["rule", "description", "example_good", "example_bad"],
        "properties": {
          "rule": {"type": "string"},
          "description": {"type": "string"},
          "example_good": {"type": "string"},
          "example_bad": {"type": "string"}
        }
      }
    },
    "best_practices": {
      "type": "array",
      "items": {"type": "object"}
    },
    "anti_patterns": {
      "type": "array",
      "items": {"type": "object"}
    }
  }
}
```

---

## 三、Qwen-Max JSON mode 调用配置

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-dashscope-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-max",
    messages=[
        {"role": "system", "content": system_prompt_with_schema},
        {"role": "user", "content": user_input}
    ],
    response_format={"type": "json_object"},
    temperature=0.1
)
```

---

## 四、适配效果预期

| 维度 | 适配前 | 适配后 | 提升 |
|------|--------|--------|------|
| 结构化输出合规率 | 85 | 96 | +11 |
| Schema一致性 | 82 | 95 | +13 |
| 中文推理深度 | 88 | 93 | +5 |
| 指令遵循率 | 90 | 94 | +4 |

---

*本文件为C10批次迭代48产出，为Qwen-Max在01/02/03场景的结构化输出+JSON模式适配指令。*
