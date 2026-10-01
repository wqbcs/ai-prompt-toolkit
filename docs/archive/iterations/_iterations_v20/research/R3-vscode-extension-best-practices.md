# 调研报告R3 - VS Code扩展开发最佳实践

> **日期**：2026-07-12 | **来源**：code.visualstudio.com/api + 社区最佳实践

---

## 一、VS Code扩展架构

### 1.1 核心组件
- **Extension Host**：独立进程运行扩展，不影响IDE性能
- **Language Server Protocol（LSP）**：语言服务标准协议
- **Webview**：HTML/CSS/JS自定义面板
- **Tree View**：侧栏树形数据展示

### 1.2 扩展清单（package.json）
```json
{
  "name": "prompt-ide",
  "displayName": "Prompt IDE",
  "engines": { "vscode": "^1.85.0" },
  "categories": ["Programming Languages", "Snippets"],
  "activationEvents": ["onLanguage:prompt"],
  "main": "./dist/extension.js",
  "contributes": {
    "languages": [{ "id": "prompt", "extensions": [".prompt"] }],
    "grammars": [{ "language": "prompt", "scopeName": "source.prompt", "path": "./syntaxes/prompt.tmLanguage.json" }],
    "snippets": [{ "language": "prompt", "path": "./snippets/prompt.json" }],
    "commands": [],
    "menus": [],
    "configuration": {}
  }
}
```

---

## 二、IDE插件4大核心功能

### 2.1 语法高亮
- **TextMate语法**：.tmLanguage.json定义Token类型
- **语义高亮**：Language Server提供语义Token
- **注入语法**：嵌入式语言（代码块内语法高亮）
- **主题适配**：Light/Dark/HC三种主题Token颜色定义

### 2.2 代码补全
- **Inline Completion**：行内补全（类似Copilot）
- **Snippet Completion**：代码片段补全
- **Trigger Characters**：触发字符（@ # {{ 等）
- **CompletionItem**：label+detail+documentation+insertText

### 2.3 预览面板
- **Webview Panel**：HTML渲染预览
- **Side-by-Side**：编辑器+预览并排
- **实时更新**：onDidChangeTextDocument监听
- **Markdown渲染**：marked/MarkdownIt库

### 2.4 调试集成
- **Debug Adapter Protocol（DAP）**：调试适配协议
- **自定义调试器**：StepRunner→DAP映射
- **断点管理**：vscode.breakpoints API
- **变量查看**：Debug Session变量树

---

## 三、JetBrains插件架构

### 3.1 IntelliJ Platform
- **Plugin.xml**：扩展点声明
- **Action System**：菜单/工具栏/快捷键动作
- **PsiTree**：抽象语法树
- **Annotator**：代码标注（错误/警告/高亮）
- **CompletionContributor**：代码补全

### 3.2 与VS Code差异
| 特性 | VS Code | JetBrains |
|------|---------|-----------|
| 语言 | TypeScript | Kotlin/Java |
| 语法树 | LSP外部 | PsiTree内置 |
| UI框架 | Webview HTML | Swing/JCEF |
| 调试 | DAP | 自定义调试器 |
| 发布 | Marketplace | JetBrains Marketplace |

---

## 四、CI/CD流水线模板

### 4.1 GitHub Actions
```yaml
name: Prompt CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm run lint
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
  publish:
    needs: [lint, test]
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run deploy
```

### 4.2 GitLab CI
```yaml
stages:
  - lint
  - test
  - publish
lint:
  stage: lint
  script: npm ci && npm run lint
test:
  stage: test
  script: npm test
publish:
  stage: publish
  only: [tags]
  script: npm run deploy
```

### 4.3 Jenkins
```groovy
pipeline {
  agent any
  stages {
    stage('Lint') { steps { sh 'npm ci && npm run lint' } }
    stage('Test') { steps { sh 'npm test' } }
    stage('Publish') {
      when { buildingTag() }
      steps { sh 'npm run deploy' }
    }
  }
}
```

---

## 五、提示词性能分析器设计

### 5.1 Token消耗分析
- 输入Token计数（tiktoken兼容）
- 输出Token计数
- Token消耗趋势图
- 按场景/模板/时间聚合

### 5.2 延迟分析
- 请求延迟（P50/P90/P99）
- 首Token延迟（TTFT）
- 生成速度（Token/s）
- 延迟分布直方图

### 5.3 成本估算
- 按模型定价计算
- 按场景/模板/时间段统计
- 预算告警
- 成本优化建议

---

## 六、提示词版本分支策略

### 6.1 分支类型
| 分支 | 命名 | 用途 |
|------|------|------|
| main | main | 稳定发布版 |
| develop | develop | 开发集成分支 |
| feature | feature/xxx | 新功能开发 |
| hotfix | hotfix/xxx | 紧急修复 |
| release | release/vX.Y | 发布准备 |

### 6.2 合并策略
- feature→develop：Squash Merge
- develop→release：Merge Commit
- release→main：Merge Commit
- hotfix→main+develop：Cherry-pick

---

## 七、V20提示词设计建议

1. IDE插件需同时覆盖VS Code和JetBrains双平台
2. 语法高亮需支持TextMate语法+语义高亮
3. CI/CD模板需覆盖GitHub Actions/GitLab CI/Jenkins三平台
4. 性能分析器需含Token/延迟/成本三维分析
5. 版本分支策略需含feature/hotfix/release完整流程
