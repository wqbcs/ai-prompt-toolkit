# S2-02 提示词模板市场v2 - 发布/安装/评分/认证

> **迭代**：v22-S2-02 | **日期**：2026-07-12

---

## 模板市场v2

### 第三方模板发布

```json
{
  "templateMarketV2": {
    "publishing": {
      "channels": ["cli", "api", "web"],
      "cliPublish": {
        "command": "prompt-market publish --template ./my-template.yaml",
        "validation": [
          "schema_check",
          "security_scan",
          "performance_benchmark",
          "anti_pattern_check",
          "copyright_check"
        ],
        "reviewProcess": "auto_review → human_review(可选) → publish"
      },
      "templateSchema": {
        "requiredFields": [
          "name", "version", "description", "author",
          "category", "tags", "inputSchema", "outputSchema",
          "promptTemplate", "minExecutableExample",
          "commonErrors", "performanceBenchmark"
        ],
        "optionalFields": [
          "license", "homepage", "dependencies",
          "modelCompatibility", "i18n"
        ]
      }
    },
    "installation": {
      "command": "prompt-market install {template-name}@{version}",
      "dependencyResolution": {
        "strategy": "semver_compatible",
        "conflictResolution": "latest_compatible",
        "autoUpdate": "patch_only"
      },
      "verification": ["integrity_check", "signature_verify", "compatibility_check"],
      "rollbackOnFailure": true
    },
    "rating": {
      "dimensions": {
        "usefulness": {"weight": 0.3, "scale": "1-5"},
        "quality": {"weight": 0.3, "scale": "1-5"},
        "documentation": {"weight": 0.2, "scale": "1-5"},
        "performance": {"weight": 0.2, "scale": "1-5"}
      },
      "metrics": {
        "totalDownloads": true,
        "weeklyDownloads": true,
        "adoptionRate": true,
        "avgRating": true,
        "reviewCount": true
      },
      "comments": {
        "maxLength": 500,
        "moderation": "post_publish",
        "sentimentAnalysis": true
      }
    },
    "certification": {
      "levels": {
        "basic": {
          "name": "基础认证",
          "requirements": ["schema_valid", "no_critical_security", "has_example"],
          "badge": "✓",
          "autoGrant": true
        },
        "security": {
          "name": "安全认证",
          "requirements": ["basic+", "security_scan_pass", "no_data_leak", "input_sanitized"],
          "badge": "🛡️",
          "autoGrant": false
        },
        "performance": {
          "name": "性能认证",
          "requirements": ["basic+", "latency_p99_2s", "token_efficient", "benchmark_pass"],
          "badge": "⚡",
          "autoGrant": false
        }
      }
    }
  }
}
```

### 陷阱5

| # | 陷阱 | 严重等级 | 修复方法 |
|---|------|---------|---------|
| 1 | 恶意模板注入 | P0 | 安全扫描+沙箱测试+人工审核 |
| 2 | 依赖循环导致安装失败 | P0 | 依赖图分析+循环检测+最大深度限制 |
| 3 | 评分刷量 | P1 | 评分去重+行为分析+权重衰减 |
| 4 | 版本兼容性未声明 | P1 | 强制semver+兼容性矩阵自动测试 |
| 5 | 版权侵权 | P2 | 版权声明+扫描+举报机制 |

### 性能5

| # | 优化项 | 效果 |
|---|--------|------|
| 1 | 模板索引CDN加速 | 搜索延迟<50ms |
| 2 | 安装包差量传输 | 下载大小减少70% |
| 3 | 评分实时聚合 | 评分更新延迟<1s |
| 4 | 安全扫描并行 | 发布验证<30s |
| 5 | 认证流水线自动化 | 基础认证<1min |

### 最小可执行示例

```
输入：发布一个"Go API文档生成"模板到市场
提示词：
作为模板市场发布系统，请验证并准备发布"Go API文档生成"模板：
1. 检查必填字段完整性
2. 运行安全扫描
3. 生成性能基准
4. 确定可获得的认证等级
5. 输出发布状态

预期输出：
{
  "templateName": "go-api-doc-gen",
  "version": "1.0.0",
  "validation": {
    "schemaValid": true,
    "securityScan": "pass",
    "performanceBenchmark": {"avgLatency": 1200, "avgTokens": 2800}
  },
  "certificationEligible": ["basic", "security"],
  "publishStatus": "ready_to_publish",
  "nextStep": "prompt-market publish --template go-api-doc-gen@1.0.0"
}
```

### 常见错误Top5

| # | 错误 | 错误示例 | 修复方法 |
|---|------|---------|---------|
| 1 | 缺少最小示例就发布 | 用户安装后不会用 | 强制require minExecutableExample |
| 2 | 未声明模型兼容性 | 只在GPT-4有效 | 声明modelCompatibility+自动测试 |
| 3 | 版本号不遵循semver | 1.0→1.1破坏兼容 | 强制semver+破坏性变更必须major |
| 4 | 未设依赖版本范围 | 依赖最新版随时可能崩 | 声明依赖semver范围 |
| 5 | 缺少卸载清理方案 | 卸载后残留配置 | 提供uninstall hook+清理脚本 |
