# 编译报告模板

> **版本**: v1.0.0 | **日期**: 2026-07-12

---

## 一、CompilationReport数据结构

```typescript
interface CompilationReport {
  template_id: string;
  template_name: string;
  compilation_context: CompilationContext;
  activated_branches: BranchInfo[];
  ignored_branches: BranchInfo[];
  uncovered_conditions: UncoveredCondition[];
  has_fallback: boolean;            // 是否有else分支兜底
  result_is_empty: boolean;         // 编译结果是否为空
  cache_hit: boolean;               // 是否命中缓存
  compilation_time_ms: number;      // 编译耗时
  syntax_errors: SyntaxError[];
  generated_at: string;             // ISO 8601
}

interface BranchInfo {
  condition: string;          // 条件表达式
  line_start: number;
  line_end: number;
  nesting_level: number;      // 嵌套层级(1-3)
  content_preview: string;    // 内容预览(前100字符)
}

interface UncoveredCondition {
  condition: string;          // 无匹配的条件表达式
  dimension: "model" | "language" | "industry";
  expected_values: string[]; // 该条件期望的值
  actual_value: string;      // 当前编译上下文的实际值
  severity: "warning" | "error";
  suggestion: string;
}

interface SyntaxError {
  line: number;
  column: number;
  message: string;
  type: "unclosed_directive" | "invalid_operator" | "invalid_dimension" | "nesting_exceeded" | "side_effect_detected";
}
```

## 二、编译报告模板

```markdown
# 条件编译报告

> 模板: {template_name} ({template_id})
> 编译上下文: model={model}, language={language}, industry={industry}
> 编译时间: {compilation_time_ms}ms
> 缓存命中: {cache_hit}

---

## 一、编译概况

| 项目 | 值 |
|------|-----|
| 激活分支数 | {activated_count} |
| 忽略分支数 | {ignored_count} |
| 未覆盖条件 | {uncovered_count} |
| 有兜底分支 | {has_fallback} |
| 结果为空 | {result_is_empty} |
| 语法错误 | {error_count} |

## 二、激活分支

| # | 条件 | 行范围 | 嵌套层级 | 内容预览 |
|---|------|--------|----------|----------|
| 1 | `model == "gpt-4o"` | L12-L18 | 1 | 请使用JSON Mode输出... |
| 2 | `language == "zh"` | L20-L25 | 1 | 请使用中文输出... |

## 三、忽略分支

| # | 条件 | 行范围 | 嵌套层级 | 原因 |
|---|------|--------|----------|------|
| 1 | `model == "pangu-large"` | L19-L23 | 1 | 当前model=gpt-4o |
| 2 | `language == "en"` | L26-L30 | 1 | 当前language=zh |

## 四、未覆盖条件

{{#if uncovered_count > 0}}
| 条件 | 维度 | 期望值 | 实际值 | 严重度 | 建议 |
|------|------|--------|--------|--------|------|
| {condition} | {dimension} | {expected} | {actual} | {severity} | {suggestion} |
{{#else}}
无未覆盖条件 ✅
{{/if}}

## 五、语法错误

{{#if error_count > 0}}
| 行 | 列 | 错误信息 | 类型 |
|----|-----|----------|------|
| {line} | {col} | {message} | {type} |
{{#else}}
无语法错误 ✅
{{/if}}

## 六、编译后内容预览

```
{compiled_content_first_500_chars}...
```
```

## 三、未覆盖条件告警规则

### 3.1 告警触发

| 条件 | 告警级别 | 消息 |
|------|----------|------|
| 无匹配分支且无else | error | "编译结果为空：所有条件分支均未匹配，且无else兜底" |
| 部分条件未覆盖 | warning | "以下条件未匹配: {uncovered_list}，建议添加else分支" |
| 行业条件未指定 | info | "未指定行业(industry)，行业相关条件将被忽略" |

### 3.2 告警示例

```
⚠️ WARNING: 编译结果为空

模板 "financial-code-review" 在以下上下文中编译结果为空:
  - model: gpt-4o
  - language: zh
  - industry: (未指定)

原因: 模板中所有内容均包含 {{#if industry == "financial"}} 条件，
     但当前编译上下文未指定行业。

建议:
1. 指定 industry="financial" 重新编译
2. 在模板中添加 else 分支提供通用内容
```

## 四、预览模式

### 4.1 预览功能

```
1. 用户选择编译上下文(model/language/industry)
2. 编译器渲染模板，显示编译后内容
3. 同时显示被忽略的分支(灰色标注)
4. 用户可切换上下文实时预览
5. 预览不修改原始模板
```

### 4.2 预览界面布局

```
┌──────────────────────────────────────────────┐
│ 编译上下文: [model▾] [language▾] [industry▾] │
├──────────────────────────────────────────────┤
│                                               │
│  编译后内容 (激活部分)                         │
│  ────────────────────                         │
│  请使用中文输出，优先使用JSON Mode...          │
│                                               │
│  ── 被忽略的分支 (灰色) ──────────            │
│  ⬚ Please output in English...               │
│  ⬚ 请使用华为云盘古模型专属优化...             │
│                                               │
├──────────────────────────────────────────────┤
│ [导出编译结果] [切换上下文] [查看完整报告]     │
└──────────────────────────────────────────────┘
```

## 五、语法校验功能

### 5.1 校验项

| 校验项 | 规则 | 错误级别 |
|--------|------|----------|
| 未闭合指令 | `{{#if}}`缺少对应`{{/if}}` | error |
| 无效操作符 | 使用了非`==`/`!=`/`in`/`not_in`操作符 | error |
| 无效维度 | 使用了非`model`/`language`/`industry`维度 | error |
| 嵌套超限 | 嵌套深度超过3层 | error |
| 副作用检测 | 条件包含API调用/文件操作等 | error |
| 孤立else | `{{#else}}`没有对应的`{{#if}}` | error |
| 空条件 | `{{#if}}`后无条件表达式 | error |

### 5.2 校验流程

```
1. 词法分析：检查Token格式正确性
2. 语法分析：检查指令配对和嵌套
3. 语义分析：检查维度、操作符、值有效性
4. 副作用检测：检查条件内容安全性
5. 生成校验报告
```
