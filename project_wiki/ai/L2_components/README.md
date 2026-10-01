# L2 组件/编辑器面（ai-prompt-toolkit）

> 本项目无 Web 前端 — "前端面"= 编辑器集成 + 终端 UI + 报告产物

## VS Code 扩展（vscode-prompt-lint/）

- 技术栈: TypeScript, VS Code API ^1.80.0, v0.5.0
- 语言: `prompt-markdown` (.prompt.md / .prompt), tmLanguage 语法高亮
- 激活: onLanguage:markdown / onLanguage:prompt-markdown
- 规模: src/extension.ts 单文件 1,349 行
- 能力: 安全扫描/条件编译/Lint/评估/Front Matter 验证（经 Python 侧执行）

## LSP Server（linter/lsp_server.py）

- 技术栈: pygls + lsprotocol（[lsp] extras）
- `prompt-cli lsp` 启动, 编辑器实时诊断

## 终端 UI

| 组件 | 文件 | 说明 |
|---|---|---|
| TUI 浏览器 | tui_browser.py | 模板浏览 |
| 增强 UX | ux_enhanced.py | rich 渲染增强 |
| 交互向导 | wizard.py | 引导式 Prompt 创建 |
| 进度 | progress.py | 进度条 |
| onboarding | onboarding/ | 首次使用引导 |

## 报告产物

| 格式 | 生成器 | 消费方 |
|---|---|---|
| SARIF | sarif_report.py | GitHub code scanning / CI |
| JUnit | junit-report 命令 | CI 测试面板 |
| HTML | html_report.py | 浏览器 |
| SVG badge | badge 命令 | README 嵌入 |
| LCov | linter/lcov_export.py | 覆盖率工具 |

## 平台栈选择记录

- 编辑器端: TypeScript (VS Code 扩展唯一可行栈) + Python LSP（进程解耦, 编辑器换栈不影响 Python 内核）
- 终端端: Python click+rich（CLI 事实标准）
- 该分层即"架构可演进"基础: 任意端技术栈迭代不影响业务内核（linter/security 纯 Python 内核零 UI 依赖）
