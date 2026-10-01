# VS Code扩展规范 v1.0

> **版本**：v1.0 | **日期**：2026-05-29 | **扩展名**：prompt-engineer

---

## 1. 功能清单

| 功能 | 描述 | 优先级 | 快捷键 |
|------|------|--------|--------|
| 语法高亮 | .prompt文件的语法着色 | P0 | - |
| 代码片段 | 28原则/5层结构/9工作流片段 | P0 | Ctrl+Shift+P |
| 实时Lint | 28反模式实时检测+28原则合规检查 | P0 | - |
| 预览面板 | 侧边实时预览AI输出 | P1 | Ctrl+Shift+V |
| 模型切换 | 7大模型快速切换+适配层 | P1 | Ctrl+Shift+M |
| 评估集成 | promptfoo一键评估+结果面板 | P1 | Ctrl+Shift+E |
| 门禁检查 | 17项门禁一键检查 | P2 | Ctrl+Shift+G |
| 模板库 | 55场景+10行业模板浏览 | P2 | Ctrl+Shift+T |
| Diff视图 | 版本间Diff+语义Diff | P2 | Ctrl+Shift+D |
| 市场集成 | 提示词市场v2浏览+安装 | P3 | Ctrl+Shift+S |

---

## 2. 语言规范

### 2.1 文件格式

```
.prompt    - 提示词主文件
.promptrc  - 项目配置
.promptlib/ - 提示词库目录
```

### 2.2 语法结构

```prompt
---
# 提示词元数据(YAML frontmatter)
name: code-review
version: 1.0.0
model: gpt-4-turbo
principles: [P1, P2, P3, P4, P8]
industry: financial
tags: [review, security, compliance]
---

# 角色
@role: 你是一位高级代码审查工程师

# 指令
@instruction: 审查以下代码，重点关注安全漏洞和合规问题

# 上下文
@context:
  - 语言: {{language}}
  - 框架: {{framework}}
  - 行业: {{industry}}

# 示例
@example:
  - input: |
      function login(user, pass) {
        return db.query(`SELECT * FROM users WHERE name='${user}' AND pass='${pass}'`);
      }
    output: |
      发现SQL注入漏洞。建议使用参数化查询。

# 约束
@constraints:
  - 必须覆盖OWASP Top 10
  - 不遗漏任何安全漏洞
  - 输出格式: JSON

# 输出格式
@output:
  type: json
  schema: |
    {
      "vulnerabilities": [{"type": "", "severity": "", "line": 0, "fix": ""}],
      "compliance": [{"rule": "", "status": ""}],
      "summary": ""
    }
```

### 2.3 语法高亮规则

| 元素 | 颜色 | 说明 |
|------|------|------|
| @role | 蓝色粗体 | 角色声明 |
| @instruction | 绿色粗体 | 指令声明 |
| @context | 青色 | 上下文声明 |
| @example | 黄色 | 示例块 |
| @constraints | 红色粗体 | 约束声明 |
| @output | 紫色 | 输出格式 |
| {{variable}} | 橙色斜体 | 模板变量 |
| # 注释 | 灰色 | 注释 |
| --- | 灰色 | YAML边界 |

---

## 3. Lint规则

### 3.1 反模式检测(28条)

```yaml
lint_rules:
  A1_role_drift:
    severity: error
    message: "检测到角色漂移：指令与@role定义不一致"
    detection: "语义相似度分析(@role vs @instruction)"
  A2_missing_constraints:
    severity: error
    message: "约束缺失：未声明@constraints"
    detection: "检查@constraints是否存在"
  A3_no_schema:
    severity: error
    message: "输出无Schema：未定义@output"
    detection: "检查@output.type和@output.schema"
  A4_over_instruction:
    severity: warning
    message: "过度指令：@instruction超过500字"
    detection: "字数统计"
  A5_model_coupling:
    severity: warning
    message: "模型耦合：硬编码模型特定语法"
    detection: "检测模型专有语法(gpt-4-only)"
  # ... A6-A28类似
```

### 3.2 原则合规检查(28条)

```yaml
principle_checks:
  P1_single_responsibility:
    message: "单一职责：@instruction应聚焦一个目标"
    check: "检测@instruction是否包含多个不相关目标"
  P2_structured_output:
    message: "结构化输出：应定义@output"
    check: "检查@output是否定义"
  P3_constraints_first:
    message: "约束前置：@constraints应在@instruction前"
    check: "检查声明顺序"
  # ... P4-P28类似
```

---

## 4. 代码片段

```json
{
  "prompt-basic": {
    "prefix": "prompt-basic",
    "body": [
      "---",
      "name: ${1:prompt-name}",
      "version: 1.0.0",
      "model: ${2|gpt-4-turbo,claude-3-opus,gemini-pro,qwen-max,deepseek-v3|}",
      "---",
      "",
      "@role: ${3:角色定义}",
      "@instruction: ${4:指令内容}",
      "@context:",
      "  - ${5:上下文信息}",
      "@constraints:",
      "  - ${6:约束条件}",
      "@output:",
      "  type: ${7|json,yaml,markdown|}"
    ]
  },
  "prompt-cot": {
    "prefix": "prompt-cot",
    "body": [
      "@instruction: |",
      "  请按以下步骤思考：",
      "  1. 理解问题：${1:问题理解}",
      "  2. 分析条件：${2:条件分析}",
      "  3. 推理过程：${3:推理步骤}",
      "  4. 验证结果：${4:结果验证}",
      "  5. 输出答案：${5:最终答案}"
    ]
  }
}
```

---

## 5. package.json核心配置

```json
{
  "name": "prompt-engineer",
  "displayName": "Prompt Engineer",
  "description": "提示词工程IDE支持",
  "version": "1.0.0",
  "engines": {"vscode": "^1.80.0"},
  "categories": ["Programming Languages", "Linters", "Snippets"],
  "activationEvents": ["onLanguage:prompt"],
  "main": "./dist/extension.js",
  "contributes": {
    "languages": [{
      "id": "prompt",
      "extensions": [".prompt"],
      "aliases": ["Prompt", "prompt"]
    }],
    "grammars": [{
      "language": "prompt",
      "scopeName": "source.prompt",
      "path": "./syntaxes/prompt.tmLanguage.json"
    }],
    "snippets": [{
      "language": "prompt",
      "path": "./snippets/prompts.json"
    }],
    "commands": [
      {"command": "prompt.preview", "title": "Preview Prompt"},
      {"command": "prompt.evaluate", "title": "Evaluate Prompt"},
      {"command": "prompt.guard", "title": "Run Gate Checks"},
      {"command": "prompt.switchModel", "title": "Switch Model"}
    ]
  }
}
```
