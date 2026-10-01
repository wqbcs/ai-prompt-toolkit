# Q1-01 VS Code扩展架构设计

> **迭代**：v20-Q1-01 | **日期**：2026-07-12

---

## 一、扩展总体架构

### 1.1 目录结构

```
prompt-ide-vscode/
├── package.json
├── tsconfig.json
├── src/
│   ├── extension.ts
│   ├── language/
│   │   ├── promptLanguageClient.ts
│   │   ├── promptCompletionProvider.ts
│   │   ├── promptHoverProvider.ts
│   │   └── promptDiagnostics.ts
│   ├── preview/
│   │   ├── previewPanel.ts
│   │   └── previewRenderer.ts
│   ├── debug/
│   │   ├── promptDebugAdapter.ts
│   │   └── promptDebugSession.ts
│   ├── commands/
│   │   ├── runPrompt.ts
│   │   ├── debugPrompt.ts
│   │   ├── previewPrompt.ts
│   │   └── analyzePrompt.ts
│   └── utils/
│       ├── tokenCounter.ts
│       └── templateManager.ts
├── syntaxes/
│   └── prompt.tmLanguage.json
├── snippets/
│   └── prompt.json
├── themes/
│   ├── prompt-dark.json
│   ├── prompt-light.json
│   └── prompt-hc.json
└── resources/
    └── preview/
        ├── preview.html
        └── preview.css
```

### 1.2 package.json

```json
{
  "name": "prompt-ide",
  "displayName": "Prompt IDE - AI提示词开发环境",
  "description": "AI提示词语法高亮、代码补全、实时预览、调试执行一体化开发环境",
  "version": "1.0.0",
  "publisher": "ai-prompt-system",
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": [
    "Programming Languages",
    "Snippets",
    "Debuggers"
  ],
  "keywords": [
    "prompt",
    "ai",
    "llm",
    "chatgpt",
    "copilot"
  ],
  "activationEvents": [
    "onLanguage:prompt",
    "onCommand:prompt-ide.run",
    "onCommand:prompt-ide.debug",
    "onCommand:prompt-ide.preview",
    "onCommand:prompt-ide.analyze"
  ],
  "main": "./dist/extension.js",
  "contributes": {
    "languages": [
      {
        "id": "prompt",
        "aliases": ["Prompt", "AI Prompt"],
        "extensions": [".prompt", ".pmt"],
        "configuration": "./language-configuration.json"
      }
    ],
    "grammars": [
      {
        "language": "prompt",
        "scopeName": "source.prompt",
        "path": "./syntaxes/prompt.tmLanguage.json"
      }
    ],
    "snippets": [
      {
        "language": "prompt",
        "path": "./snippets/prompt.json"
      }
    ],
    "commands": [
      {
        "command": "prompt-ide.run",
        "title": "Prompt IDE: 执行提示词"
      },
      {
        "command": "prompt-ide.debug",
        "title": "Prompt IDE: 调试提示词"
      },
      {
        "command": "prompt-ide.preview",
        "title": "Prompt IDE: 预览提示词"
      },
      {
        "command": "prompt-ide.analyze",
        "title": "Prompt IDE: 性能分析"
      }
    ],
    "menus": {
      "editor/context": [
        {
          "when": "resourceLangId == prompt",
          "command": "prompt-ide.run",
          "group": "navigation"
        },
        {
          "when": "resourceLangId == prompt",
          "command": "prompt-ide.debug",
          "group": "navigation"
        }
      ]
    },
    "configuration": {
      "title": "Prompt IDE",
      "properties": {
        "prompt-ide.defaultModel": {
          "type": "string",
          "default": "gpt-4o",
          "enum": ["gpt-4o", "gpt-4o-mini", "claude-3.5-sonnet", "qwen-max", "deepseek-chat"],
          "description": "默认执行模型"
        },
        "prompt-ide.autoPreview": {
          "type": "boolean",
          "default": true,
          "description": "自动预览提示词渲染结果"
        },
        "prompt-ide.tokenWarningThreshold": {
          "type": "number",
          "default": 4000,
          "description": "Token消耗告警阈值"
        }
      }
    },
    "themes": [
      {
        "id": "prompt-dark",
        "label": "Prompt IDE Dark",
        "uiTheme": "vs-dark",
        "path": "./themes/prompt-dark.json"
      },
      {
        "id": "prompt-light",
        "label": "Prompt IDE Light",
        "uiTheme": "vs",
        "path": "./themes/prompt-light.json"
      },
      {
        "id": "prompt-hc",
        "label": "Prompt IDE High Contrast",
        "uiTheme": "hc-black",
        "path": "./themes/prompt-hc.json"
      }
    ]
  },
  "dependencies": {
    "vscode-languageclient": "^9.0.1"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "typescript": "^5.3.0",
    "esbuild": "^0.19.0"
  }
}
```

### 1.3 核心模块交互

```
┌─────────────────────────────────────────────────────────┐
│                    Prompt IDE Extension                    │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ 语法高亮  │  │ 代码补全  │  │ 预览面板  │  │ 调试器  │ │
│  │ TextMate │  │ Provider │  │ Webview  │  │  DAP    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │             │             │             │       │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐  │
│  │              Prompt Language Client                 │  │
│  │    (语法分析 + 语义理解 + 模板管理 + 执行调度)      │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                  │
│  ┌────────────────────┴───────────────────────────────┐  │
│  │              Shared Services                        │  │
│  │  TokenCounter | TemplateManager | ConfigStore      │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 1.4 语言配置

```json
{
  "comments": {
    "lineComment": "//",
    "blockComment": ["/*", "*/"]
  },
  "brackets": [
    ["{{", "}}"],
    ["[", "]"],
    ["(", ")"]
  ],
  "autoClosingPairs": [
    { "open": "{{", "close": "}}" },
    { "open": "[", "close": "]" },
    { "open": "\"", "close": "\"", "notIn": ["string"] },
    { "open": "`", "close": "`", "notIn": ["string"] }
  ],
  "surroundingPairs": [
    ["{{", "}}"],
    ["[", "]"],
    ["\"", "\""],
    ["`", "`"]
  ],
  "folding": {
    "markers": {
      "start": "^\\s*///\\s*#region",
      "end": "^\\s*///\\s*#endregion"
    }
  },
  "wordPattern": "({{[a-zA-Z_][a-zA-Z0-9_]*}})|[a-zA-Z_][a-zA-Z0-9_]*"
}
```

---

## 二、扩展入口（extension.ts）

```typescript
import { ExtensionContext, languages, workspace } from 'vscode';
import { PromptCompletionProvider } from './language/promptCompletionProvider';
import { PromptHoverProvider } from './language/promptHoverProvider';
import { PreviewPanel } from './preview/previewPanel';
import { PromptDebugAdapter } from './debug/promptDebugAdapter';
import { TokenCounter } from './utils/tokenCounter';
import { TemplateManager } from './utils/templateManager';

export function activate(context: ExtensionContext) {
  const tokenCounter = new TokenCounter();
  const templateManager = new TemplateManager(context);

  languages.registerCompletionItemProvider(
    { language: 'prompt' },
    new PromptCompletionProvider(templateManager),
    '@', '#', '{{', '/'
  );

  languages.registerHoverProvider(
    { language: 'prompt' },
    new PromptHoverProvider()
  );

  const previewPanel = new PreviewPanel(context);
  context.subscriptions.push(
    previewPanel
  );

  const debugAdapter = new PromptDebugAdapter(context);
  context.subscriptions.push(
    debugAdapter
  );

  workspace.onDidChangeTextDocument((e) => {
    if (e.document.languageId === 'prompt') {
      const tokens = tokenCounter.count(e.document.getText());
      previewPanel.update(e.document, tokens);
    }
  });
}

export function deactivate() {}
```

---

## 三、验收项

- [x] 扩展目录结构设计完整
- [x] package.json配置完整（语言+语法+代码片段+命令+菜单+配置+主题）
- [x] 核心模块交互图清晰
- [x] 语言配置文件定义
- [x] 扩展入口代码框架
- [x] 5个核心命令注册
- [x] 3个主题声明
