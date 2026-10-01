# R2-05 提示词国际化工具-自动化流水线

> **迭代**：v21-R2-05 | **日期**：2026-07-12

---

## 一、国际化自动化流水线

### CI/CD集成

```yaml
# .github/workflows/i18n-pipeline.yml
name: i18n Pipeline
on:
  push:
    paths:
      - 'prompts/**'
      - '_glossary.md'
      - '_i18n/**'

jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: 提取待翻译文本
        run: i18n-tool extract --source zh-CN --output _i18n/pending/
  
  translate:
    needs: extract
    runs-on: ubuntu-latest
    strategy:
      matrix:
        language: [en-US, ja-JP, ko-KR, zh-TW]
    steps:
      - name: 机器翻译
        run: i18n-tool translate --target ${{ matrix.language }} --method hybrid
      - name: 术语一致性检查
        run: i18n-tool check-consistency --language ${{ matrix.language }}
      - name: 文化适配检查
        run: i18n-tool check-culture --language ${{ matrix.language }}
  
  review:
    needs: translate
    runs-on: ubuntu-latest
    steps:
      - name: 生成审核清单
        run: i18n-tool generate-review-list
      - name: 质量评估
        run: i18n-tool quality-report
```

### 自动化步骤

| 步骤 | 触发 | 工具 | 产出 |
|------|------|------|------|
| 文本提取 | 源语言变更 | extract | 待翻译文本列表 |
| 机器翻译 | 提取完成 | translate | 初版翻译 |
| 术语一致性 | 翻译完成 | check-consistency | 一致性报告 |
| 文化适配 | 翻译完成 | check-culture | 适配建议 |
| 人工审核 | 自动化完成 | review | 审核清单 |
| 质量报告 | 全流程完成 | quality-report | 综合质量报告 |

## 二、翻译记忆库

### 记忆库结构

```typescript
interface TranslationMemory {
  entries: TranslationMemoryEntry[]
  totalEntries: number
  hitRate: number                  // 命中率
  lastUpdated: string
}

interface TranslationMemoryEntry {
  sourceHash: string               // 源文本哈希
  sourceText: string
  sourceLanguage: string
  targetText: string
  targetLanguage: string
  matchType: 'exact' | 'fuzzy_95' | 'fuzzy_85' | 'fuzzy_75'
  usageCount: number
  lastUsed: string
  approvedBy: string
}
```

### 匹配策略

| 匹配类型 | 相似度 | 处理 |
|---------|--------|------|
| 精确匹配 | 100% | 直接使用 |
| 高模糊匹配 | 95-99% | 使用+人工确认 |
| 中模糊匹配 | 85-94% | 使用+人工修改 |
| 低模糊匹配 | 75-84% | 参考+重新翻译 |
| 无匹配 | <75% | 新翻译 |

## 三、国际化测试

### 测试类型

| 类型 | 说明 | 自动化 |
|------|------|--------|
| 完整性测试 | 所有段落均已翻译 | ✓ |
| 一致性测试 | 术语翻译一致 | ✓ |
| 格式测试 | Markdown/代码块格式保留 | ✓ |
| 链接测试 | 超链接有效 | ✓ |
| 截断测试 | 无文本截断/溢出 | ✓ |
| 术语保护测试 | 不翻译术语正确保留 | ✓ |
| 文化敏感测试 | 无文化不当内容 | 半自动 |

### 测试报告

```typescript
interface I18nTestReport {
  language: string
  totalTests: number
  passed: number
  failed: number
  warnings: number
  details: {
    completeness: { passed: boolean; coverage: number }
    consistency: { passed: boolean; score: number; conflicts: string[] }
    format: { passed: boolean; issues: string[] }
    links: { passed: boolean; broken: string[] }
    truncation: { passed: boolean; truncated: string[] }
    termProtection: { passed: boolean; violations: string[] }
    culturalSensitivity: { passed: boolean; issues: string[] }
  }
}
```

## 四、验收项

- [x] 国际化CI/CD流水线（6步骤）
- [x] 翻译记忆库+5种匹配策略
- [x] 7种国际化测试类型
- [x] 测试报告数据结构
