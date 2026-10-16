# L2 组件/前端面（ai-prompt-toolkit）

> 更新: R310 (2026-10-16) | 首版: R213
> 提取自代码实际定义: package.json / 路由装饰器 / 文件行数实测 / fetch 消费面盘点

## 技术栈定位（无构建式前端框架）

- Playground SPA: 单文件 vanilla JS（无 vue/react/svelte, 无构建链, pip package-data 随包分发）
- 落地页: 单文件静态 HTML
- 编辑器端: TypeScript（VS Code 扩展）
- 终端端: Python click + rich
- 该分层即"架构可演进"基础: 任意端技术栈迭代不影响业务内核（linter/security 纯 Python 内核零 UI 依赖）

## 1. Playground SPA（src/ai_prompt_toolkit/playground/static/index.html）

- 768 行单文件, 零框架（vanilla JS + 内联 CSS）
- 启动: `prompt-cli serve`（:8080, 需 [full] extras）或 Docker playground stage
- 消费 API 面（fetch 盘点）: /api/compile /api/lint /api/scan /api/evaluate /api/eval-matrix /api/scorecard /api/engine /api/badge /api/version /api/i18n/{locale} /api/datasets* /api/market/templates* /api/market/categories; WS: /ws/compile（new WebSocket ×1 实测）
- 状态: 内存 JS 状态（无状态管理库）; i18n 走 /api/i18n 运行时语言包
- 测试: tests/test_r308 + test_r311（22 TestClient e2e = HTTP 契约层, 16/17 API 路由 + SPA 首页）;
  /ws/compile 真实 WS 会话 + 浏览器渲染面待发布后 Playwright MCP 承接（P3-18 登记面）

## 2. 落地页（web/index.html）

- 347 行单文件静态 HTML, 无框架
- 定位: "AI Prompt Toolkit · 本地体验中心"（title 实测）; marketing/ 4 份推广文案草稿为并行资产

## 3. VS Code 扩展（vscode-prompt-lint/）

- 技术栈: TypeScript, VS Code API ^1.80.0, **v0.6.0**（R213 记录 v0.5.0）
- 结构: 单文件 src/extension.ts（1,349 行）→ dist/extension.js（main）; 无组件分层（单文件扩展模式）
- 语言贡献: prompt-markdown（syntaxes/prompt.tmLanguage.json）+ snippets（snippets/prompt-snippets.json）
- 激活: onLanguage:markdown / onLanguage:prompt-markdown（activationEvents）
- 能力: 安全扫描/条件编译/Lint/评估/Front Matter 验证（经 Python 侧执行, 进程解耦）

## 4. 终端 UI

| 组件 | 文件 | 说明 |
|---|---|---|
| TUI 浏览器 | tui_browser.py | 模板浏览 |
| 增强 UX | ux_enhanced.py | rich 渲染增强 |
| 交互向导 | wizard.py | 引导式 Prompt 创建（交互类, 不实跑验收） |
| 进度 | progress.py | 进度条 |
| 引导 | onboarding/ | 首次使用引导 |
| LSP Server | linter/lsp_server.py | pygls + lsprotocol（[lsp] extras）, 编辑器实时诊断 |

## 5. 报告产物

| 格式 | 生成器 | 消费方 |
|---|---|---|
| SARIF | sarif_report.py | GitHub code scanning / CI |
| JUnit | junit-report 命令 | CI 测试面板 |
| HTML | html_report.py + jinja2 渲染器（eval-matrix 完整渲染, R225 依赖声明） | 浏览器 |
| SVG badge | badge 命令 | README 嵌入 |
| LCov | linter/lcov_export.py | 覆盖率工具 |

## 平台栈选择记录

- 编辑器端: TypeScript（VS Code 扩展唯一可行栈）+ Python LSP（进程解耦, 编辑器换栈不影响 Python 内核）
- 终端端: Python click+rich（CLI 事实标准）
- Web 端: 零框架单文件 SPA（奥卡姆 — 本地工具无构建链诉求, pip 随包分发; 若演进为产品级前端再立构建, 内核不受影响）
