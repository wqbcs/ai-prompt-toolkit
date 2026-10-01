# Q1-02 语法高亮设计

> **迭代**：v20-Q1-02 | **日期**：2026-07-12

---

## 一、TextMate语法定义

### 1.1 prompt.tmLanguage.json

```json
{
  "scopeName": "source.prompt",
  "name": "AI Prompt",
  "patterns": [
    {
      "include": "#comments"
    },
    {
      "include": "#variables"
    },
    {
      "include": "#directives"
    },
    {
      "include": "#roles"
    },
    {
      "include": "#constraints"
    },
    {
      "include": "#code-blocks"
    },
    {
      "include": "#strings"
    },
    {
      "include": "#numbers"
    },
    {
      "include": "#keywords"
    }
  ],
  "repository": {
    "comments": {
      "patterns": [
        {
          "name": "comment.line.double-slash.prompt",
          "match": "//.*$"
        },
        {
          "name": "comment.block.prompt",
          "begin": "/\\*",
          "end": "\\*/",
          "captures": {
            "0": { "name": "punctuation.definition.comment.prompt" }
          }
        }
      ]
    },
    "variables": {
      "patterns": [
        {
          "name": "variable.other.prompt",
          "begin": "\\{\\{",
          "end": "\\}\\}",
          "captures": {
            "0": { "name": "punctuation.definition.variable.prompt" }
          },
          "patterns": [
            {
              "name": "variable.parameter.prompt",
              "match": "[a-zA-Z_][a-zA-Z0-9_]*"
            },
            {
              "name": "keyword.operator.default.prompt",
              "match": "\\|"
            }
          ]
        }
      ]
    },
    "directives": {
      "patterns": [
        {
          "name": "meta.directive.prompt",
          "match": "(@system|@user|@assistant|@context|@constraint|@example|@output|@model|@temperature|@max_tokens)\\b",
          "captures": {
            "1": { "name": "keyword.control.directive.prompt" }
          }
        }
      ]
    },
    "roles": {
      "patterns": [
        {
          "name": "entity.name.role.prompt",
          "match": "(角色|Role|SYSTEM|USER|ASSISTANT):",
          "captures": {
            "1": { "name": "keyword.other.role.prompt" }
          }
        }
      ]
    },
    "constraints": {
      "patterns": [
        {
          "name": "meta.constraint.prompt",
          "begin": "(约束|Constraint|规则|Rule):",
          "end": "(?=\\n\\n|\\z)",
          "beginCaptures": {
            "1": { "name": "keyword.other.constraint.prompt" }
          },
          "patterns": [
            {
              "name": "markup.list.prompt",
              "match": "^\\s*[-*]\\s"
            }
          ]
        }
      ]
    },
    "code-blocks": {
      "patterns": [
        {
          "name": "markup.raw.code-block.prompt",
          "begin": "```([a-zA-Z0-9+.-]*)",
          "end": "```",
          "beginCaptures": {
            "1": { "name": "entity.other.attribute-name.language.prompt" }
          }
        }
      ]
    },
    "strings": {
      "patterns": [
        {
          "name": "string.quoted.double.prompt",
          "begin": "\"",
          "end": "\"",
          "patterns": [
            {
              "name": "constant.character.escape.prompt",
              "match": "\\\\."
            }
          ]
        },
        {
          "name": "string.quoted.single.prompt",
          "begin": "'",
          "end": "'"
        },
        {
          "name": "string.interpolated.prompt",
          "begin": "`",
          "end": "`"
        }
      ]
    },
    "numbers": {
      "patterns": [
        {
          "name": "constant.numeric.prompt",
          "match": "\\b\\d+(\\.\\d+)?\\b"
        }
      ]
    },
    "keywords": {
      "patterns": [
        {
          "name": "keyword.control.prompt",
          "match": "\\b(if|else|for|while|return|import|export|from|as|async|await)\\b"
        },
        {
          "name": "keyword.operator.prompt",
          "match": "(=>|&&|\\|\\||==|!=|>=|<=|\\+\\+|--)"
        },
        {
          "name": "constant.language.prompt",
          "match": "\\b(true|false|null|undefined|none)\\b"
        }
      ]
    }
  }
}
```

---

## 二、主题Token颜色定义

### 2.1 深色主题（prompt-dark.json）

```json
{
  "name": "Prompt IDE Dark",
  "type": "dark",
  "colors": {
    "editor.background": "#1e1e2e",
    "editor.foreground": "#cdd6f4"
  },
  "tokenColors": [
    {
      "scope": "comment.line.double-slash.prompt, comment.block.prompt",
      "settings": { "foreground": "#6c7086", "fontStyle": "italic" }
    },
    {
      "scope": "variable.other.prompt, variable.parameter.prompt",
      "settings": { "foreground": "#f9e2af", "fontStyle": "bold" }
    },
    {
      "scope": "punctuation.definition.variable.prompt",
      "settings": { "foreground": "#fab387" }
    },
    {
      "scope": "keyword.control.directive.prompt",
      "settings": { "foreground": "#cba6f7", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.role.prompt",
      "settings": { "foreground": "#89b4fa", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.constraint.prompt",
      "settings": { "foreground": "#f38ba8", "fontStyle": "bold" }
    },
    {
      "scope": "entity.other.attribute-name.language.prompt",
      "settings": { "foreground": "#a6e3a1" }
    },
    {
      "scope": "markup.raw.code-block.prompt",
      "settings": { "foreground": "#94e2d5", "background": "#313244" }
    },
    {
      "scope": "markup.list.prompt",
      "settings": { "foreground": "#89dceb" }
    },
    {
      "scope": "keyword.control.prompt",
      "settings": { "foreground": "#cba6f7" }
    },
    {
      "scope": "constant.numeric.prompt",
      "settings": { "foreground": "#fab387" }
    },
    {
      "scope": "string.quoted.double.prompt, string.quoted.single.prompt",
      "settings": { "foreground": "#a6e3a1" }
    }
  ]
}
```

### 2.2 浅色主题（prompt-light.json）

```json
{
  "name": "Prompt IDE Light",
  "type": "light",
  "colors": {
    "editor.background": "#faf4ed",
    "editor.foreground": "#575279"
  },
  "tokenColors": [
    {
      "scope": "comment.line.double-slash.prompt, comment.block.prompt",
      "settings": { "foreground": "#9890a3", "fontStyle": "italic" }
    },
    {
      "scope": "variable.other.prompt, variable.parameter.prompt",
      "settings": { "foreground": "#d7827e", "fontStyle": "bold" }
    },
    {
      "scope": "punctuation.definition.variable.prompt",
      "settings": { "foreground": "#ea9d34" }
    },
    {
      "scope": "keyword.control.directive.prompt",
      "settings": { "foreground": "#907aa9", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.role.prompt",
      "settings": { "foreground": "#286983", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.constraint.prompt",
      "settings": { "foreground": "#b4637a", "fontStyle": "bold" }
    },
    {
      "scope": "entity.other.attribute-name.language.prompt",
      "settings": { "foreground": "#56949f" }
    },
    {
      "scope": "markup.raw.code-block.prompt",
      "settings": { "foreground": "#797593", "background": "#f2e9e1" }
    }
  ]
}
```

### 2.3 高对比度主题（prompt-hc.json）

```json
{
  "name": "Prompt IDE High Contrast",
  "type": "hc-black",
  "colors": {
    "editor.background": "#000000",
    "editor.foreground": "#ffffff"
  },
  "tokenColors": [
    {
      "scope": "comment.line.double-slash.prompt, comment.block.prompt",
      "settings": { "foreground": "#7f7f7f", "fontStyle": "italic" }
    },
    {
      "scope": "variable.other.prompt, variable.parameter.prompt",
      "settings": { "foreground": "#ffff00", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.control.directive.prompt",
      "settings": { "foreground": "#ff00ff", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.role.prompt",
      "settings": { "foreground": "#00ffff", "fontStyle": "bold" }
    },
    {
      "scope": "keyword.other.constraint.prompt",
      "settings": { "foreground": "#ff0000", "fontStyle": "bold" }
    },
    {
      "scope": "markup.raw.code-block.prompt",
      "settings": { "foreground": "#00ff00", "background": "#1a1a1a" }
    }
  ]
}
```

---

## 三、语义高亮（Language Server扩展）

### 3.1 语义Token类型

```typescript
const semanticTokenTypes = [
  { id: 'promptVariable', description: '提示词变量 {{variable}}' },
  { id: 'promptDirective', description: '提示词指令 @directive' },
  { id: 'promptRole', description: '提示词角色标记' },
  { id: 'promptConstraint', description: '提示词约束条件' },
  { id: 'promptTemplate', description: '提示词模板引用' },
];

const semanticTokenModifiers = [
  { id: 'deprecated', description: '已废弃' },
  { id: 'recommended', description: '推荐使用' },
];
```

### 3.2 Token映射

| 语义Token | TextMate Scope | 深色颜色 | 浅色颜色 | HC颜色 |
|-----------|---------------|---------|---------|--------|
| promptVariable | variable.other.prompt | #f9e2af | #d7827e | #ffff00 |
| promptDirective | keyword.control.directive | #cba6f7 | #907aa9 | #ff00ff |
| promptRole | keyword.other.role | #89b4fa | #286983 | #00ffff |
| promptConstraint | keyword.other.constraint | #f38ba8 | #b4637a | #ff0000 |
| promptTemplate | entity.name.type | #a6e3a1 | #56949f | #00ff00 |

---

## 四、验收项

- [x] TextMate语法定义完整（9个pattern组：注释/变量/指令/角色/约束/代码块/字符串/数字/关键字）
- [x] 深色主题Token颜色定义
- [x] 浅色主题Token颜色定义
- [x] 高对比度主题Token颜色定义
- [x] 语义Token类型定义
- [x] Token映射表完整
