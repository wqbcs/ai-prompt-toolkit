# JSON Schema 定义

本目录用于存放Prompt模板的JSON Schema定义文件。

## 可用Schema

详细的Schema定义请参考 `_schemas/` 目录：

| Schema文件 | 用途 |
|-----------|------|
| `prompt-v3.schema.json` | Prompt模板Front Matter验证 |
| `compile-context.schema.json` | 条件编译上下文验证 |
| `ab-test-config.schema.json` | A/B测试配置验证 |
| `evaluation-config.schema.json` | 评估配置验证 |
| `security-scan.schema.json` | 安全扫描配置验证 |

## 使用方式

```bash
# 使用jsonschema验证
python -m jsonschema -i template.yaml _schemas/prompt-v3.schema.json
```
