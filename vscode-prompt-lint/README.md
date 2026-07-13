# vscode-prompt-lint

AI提示词质量检查 VS Code 扩展 — 安全扫描、条件编译、Prompt Lint、Front Matter验证

## 功能

- **Prompt Lint**: 保存时自动检查提示词质量（20条规则）
- **安全扫描**: 注入检测+继承链审计
- **条件编译**: 一键编译`{{#if}}`条件模板
- **Front Matter v3验证**: i18n_status/market_status/lint_score字段验证

## 安装

1. 确保已安装 `ai-prompt-toolkit`:
   ```bash
   pip install ai-prompt-toolkit
   ```

2. 在VS Code中安装此扩展

## 使用

- `Ctrl+Shift+P` → "Prompt Lint: 检查当前文件" — 手动执行Lint
- `Ctrl+Shift+P` → "Prompt Lint: 安全扫描当前文件" — 注入检测
- `Ctrl+Shift+P` → "Prompt Lint: 条件编译当前文件" — 编译模板
- 保存`.md`文件时自动执行Lint+安全扫描

## 配置

| 设置 | 默认值 | 说明 |
|------|--------|------|
| `promptLint.enable` | `true` | 启用/禁用 |
| `promptLint.lintOnSave` | `true` | 保存时自动Lint |
| `promptLint.lintOnType` | `false` | 输入时实时Lint |
| `promptLint.securityScan` | `true` | 同时执行安全扫描 |
| `promptLint.frontMatterValidation` | `true` | Front Matter v3验证 |
| `promptLint.severityOverrides` | `{}` | 规则严重级别覆盖 |
| `promptLint.cliPath` | `prompt-cli` | CLI路径 |

## 架构

参考 vscode-markdownlint 轻量模式：
- 直接调用 `prompt-cli lint/scan` CLI命令
- 通过 `vscode.DiagnosticCollection` 显示诊断信息
- 支持保存时/输入时触发
- 无需LSP，轻量零依赖
