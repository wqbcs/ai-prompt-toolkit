# 条件编译指令语法规范

> **版本**: v1.0.0 | **日期**: 2026-07-12 | **参考**: C预处理器+Handlebars语法

---

## 一、基本语法

### 1.1 条件指令格式

```
{{#if condition}}
  ...条件为真时包含的内容...
{{#else}}
  ...条件为假时包含的内容（可选）...
{{/if}}
```

### 1.2 语法元素

| 元素 | 格式 | 说明 |
|------|------|------|
| 条件开始 | `{{#if condition}}` | 条件为真时渲染此块 |
| 否则分支 | `{{#else}}` | 条件为假时渲染此块（可选） |
| 条件结束 | `{{/if}}` | 标记条件块结束 |

## 二、三维度条件

### 2.1 model维度

```
用途: 按AI模型选择不同的提示词内容
维度值: 模型ID（如gpt-4o, claude-3.5-sonnet, qwen-max, pangu-large）

示例:
{{#if model == "gpt-4o"}}
请使用JSON Mode输出结构化结果。
{{#else if model == "claude-3.5-sonnet"}}
请使用XML标签输出结构化结果。
{{#else}}
请使用Markdown格式输出结果。
{{/if}}
```

### 2.2 language维度

```
用途: 按输出语言选择不同的提示词内容
维度值: 语言代码（如zh, en, ja, ko）

示例:
{{#if language == "zh"}}
请使用中文输出，术语采用中文行业标准译法。
{{#else if language == "en"}}
Please output in English using industry-standard terminology.
{{#else}}
请使用{language}语言输出。
{{/if}}
```

### 2.3 industry维度

```
用途: 按行业选择不同的提示词内容
维度值: 行业代码（如financial, healthcare, education, manufacturing, government）

示例:
{{#if industry == "financial"}}
特别注意：金融场景需遵守银保监会合规要求，输出不得包含投资建议。
{{#else if industry == "healthcare"}}
特别注意：医疗场景需遵守HIPAA/个人信息保护法，输出不得包含诊断建议。
{{/if}}
```

## 三、条件操作符

| 操作符 | 语法 | 说明 | 示例 |
|--------|------|------|------|
| 等于 | `==` | 精确匹配 | `model == "gpt-4o"` |
| 不等于 | `!=` | 不匹配 | `model != "pangu-large"` |
| 包含 | `in` | 值在列表中 | `model in ["gpt-4o", "claude-3.5-sonnet"]` |
| 不包含 | `not_in` | 值不在列表中 | `industry not_in ["government", "military"]` |

## 四、逻辑操作符

| 操作符 | 语法 | 说明 | 示例 |
|--------|------|------|------|
| 与 | `&&` | 两个条件都为真 | `model == "gpt-4o" && language == "zh"` |
| 或 | `||` | 任一条件为真 | `model == "gpt-4o" || model == "claude-3.5-sonnet"` |

### 4.1 逻辑操作符优先级

```
优先级: && > ||
即: A || B && C 等价于 A || (B && C)

建议: 复杂条件使用括号明确优先级
{{#if (model == "gpt-4o" || model == "claude-3.5-sonnet") && language == "zh"}}
```

## 五、嵌套规则

### 5.1 最大嵌套层数: 3层

```
{{#if model == "gpt-4o"}}              ← 第1层
  {{#if language == "zh"}}             ← 第2层
    中文GPT-4o专属内容
    {{#if industry == "financial"}}    ← 第3层 ✅ 最大层数
      金融合规内容
    {{/if}}
  {{/if}}
{{/if}}
```

```
{{#if model == "gpt-4o"}}              ← 第1层
  {{#if language == "zh"}}             ← 第2层
    {{#if industry == "financial"}}    ← 第3层
      {{#if xxx == "yyy"}}            ← 第4层 ❌ 超出限制
      {{/if}}
    {{/if}}
  {{/if}}
{{/if}}
```

### 5.2 嵌套校验

```
IF 嵌套深度 > 3:
    编译错误: "条件编译嵌套深度超出限制(最大3层)"
    建议: "重构条件逻辑，使用逻辑操作符减少嵌套"
```

## 六、回退分支规则

### 6.1 else分支

```
{{#if model == "gpt-4o"}}
  GPT-4o专属内容
{{#else}}
  通用内容（所有非GPT-4o模型）
{{/if}}
```

### 6.2 else if链式分支

```
{{#if model == "gpt-4o"}}
  GPT-4o专属内容
{{#else if model == "claude-3.5-sonnet"}}
  Claude专属内容
{{#else if model == "qwen-max"}}
  通义千问专属内容
{{#else}}
  其他模型通用内容
{{/if}}
```

### 6.3 无else分支的处理

```
{{#if model == "gpt-4o"}}
  GPT-4o专属内容
{{/if}}

当model != "gpt-4o"时:
- 该条件块不输出任何内容
- 如果整个模板只有这一个条件块，编译结果可能为空
- 编译器会发出"编译结果为空"告警
```

## 七、禁止项

| 禁止项 | 说明 | 原因 |
|--------|------|------|
| 禁止API调用 | 条件中不得包含HTTP请求 | 副作用导致不可预测行为 |
| 禁止文件写入 | 条件中不得包含文件操作 | 编译阶段不应修改文件系统 |
| 禁止随机数 | 条件中不得包含random() | 编译结果不可复现 |
| 禁止时间函数 | 条件中不得包含now()/date() | 编译结果不可复现 |
| 禁止全局变量 | 条件中不得引用全局可变状态 | 编译结果不可预测 |

## 八、语法示例

### 8.1 单维度条件

```markdown
{{#if model == "pangu-large"}}
## 华为云盘古模型专属优化

由于盘古模型在中文理解方面的优势，以下内容可直接使用中文术语：
- 服务名称使用华为云官方命名
- API路径使用华为云规范
{{/if}}
```

### 8.2 多维度组合条件

```markdown
{{#if model == "gpt-4o" && language == "zh"}}
请使用中文输出，优先使用JSON Mode结构化输出。
{{#else if model == "gpt-4o" && language == "en"}}
Please output in English, prefer JSON Mode structured output.
{{#else if model in ["qwen-max", "pangu-large"] && language == "zh"}}
请使用中文输出，优先使用Markdown格式输出。
{{#else}}
请使用{language}语言输出，格式不限。
{{/if}}
```

### 8.3 嵌套条件

```markdown
{{#if industry == "financial"}}
## 金融行业合规要求
{{#if language == "zh"}}
请遵守银保监会相关法规，输出不得包含投资建议。
{{#else}}
Please comply with relevant financial regulations. No investment advice.
{{/if}}
{{#if model == "pangu-large"}}
特别提示：使用盘古模型时，请启用合规过滤插件。
{{/if}}
{{/if}}
```
