# CI/CD 配置

本目录用于存放CI/CD相关配置。

当前CI配置位于 `.github/workflows/`：

- `quality-gate.yml` - 质量门禁（多Python版本矩阵测试）
- `prompt-lint.yml` - Prompt Lint检查
- `prompt-quality-gate.yml` - Prompt质量门禁

## 使用Quality Gate

```yaml
# GitHub Actions 集成示例
- name: Prompt Lint with Quality Gate
  run: prompt-cli lint -t ./prompts/ --gate

- name: Prompt Security Scan
  run: prompt-cli scan -t ./prompts/
```

## SARIF输出

```yaml
- name: Prompt Lint (SARIF)
  run: prompt-cli lint -t ./prompts/ --format sarif --output results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```
