# R2-04 提示词国际化工具-多语言模板与文化适配

> **迭代**：v21-R2-04 | **日期**：2026-07-12

---

## 一、多语言模板系统

### 模板结构

```typescript
interface LocalizedTemplate {
  id: string
  baseLanguage: string
  localizations: Record<string, TemplateLocalization>
  sharedAssets: SharedAsset[]
  variables: TemplateVariable[]
}

interface TemplateLocalization {
  language: string
  title: string
  description: string
  sections: LocalizedSection[]
  examples: LocalizedExample[]
  culturalNotes: string[]
  lastUpdated: string
  translator: string
  reviewStatus: 'pending' | 'in_review' | 'approved'
}

interface LocalizedSection {
  key: string                    // 章节标识(语言无关)
  title: string                  // 本地化标题
  content: string                // 本地化内容
  format: 'markdown' | 'table' | 'code' | 'list'
  variables: string[]            // 引用的变量名
}

interface TemplateVariable {
  name: string
  type: 'text' | 'number' | 'date' | 'currency' | 'select'
  localizations: Record<string, {
    label: string
    placeholder: string
    options?: { value: string; label: string }[]
  }>
  formatByLocale: boolean        // 是否按地区格式化
}
```

### 支持语言（8种）

| 语言 | 代码 | 优先级 | 说明 |
|------|------|--------|------|
| 简体中文 | zh-CN | P0 | 源语言 |
| 美式英语 | en-US | P0 | 国际通用 |
| 日语 | ja-JP | P1 | 亚洲市场 |
| 韩语 | ko-KR | P1 | 亚洲市场 |
| 繁体中文 | zh-TW | P1 | 港澳台 |
| 德语 | de-DE | P2 | 欧洲市场 |
| 法语 | fr-FR | P2 | 欧洲市场 |
| 西班牙语 | es-ES | P2 | 拉美市场 |

## 二、文化适配建议引擎

### 适配规则库

```typescript
interface CulturalAdaptationRule {
  id: string
  sourceCulture: string
  targetCulture: string
  category: 'example' | 'metaphor' | 'naming' | 'format' | 'etiquette'
  original: string
  adapted: string
  reason: string
  confidence: number
}

// 示例适配规则
const CULTURAL_ADAPTATION_RULES = [
  {
    sourceCulture: 'zh-CN',
    targetCulture: 'en-US',
    category: 'example',
    original: '张三使用Python开发FastAPI应用',
    adapted: 'Alice develops a FastAPI application using Python',
    reason: '使用目标文化常见人名',
    confidence: 0.95
  },
  {
    sourceCulture: 'zh-CN',
    targetCulture: 'ja-JP',
    category: 'etiquette',
    original: '请输出以下内容',
    adapted: '以下の内容を出力してください',
    reason: '日语敬语规范(丁寧語)',
    confidence: 0.90
  }
]
```

### 自动适配流程

```
1. 提取源语言模板中的文化相关元素
2. 匹配适配规则库
3. 生成目标文化适配版本
4. 标记低置信度适配(需人工审核)
5. 应用术语保护规则
6. 生成文化适配报告
```

## 三、国际化质量评估

### 质量指标

| 指标 | 计算方式 | 阈值 |
|------|---------|------|
| 术语一致性 | 一致术语数/总术语数 | ≥95% |
| 翻译完整率 | 已翻译段落数/总段落数 | 100% |
| 文化适配率 | 已适配元素数/文化元素数 | ≥90% |
| 术语保护率 | 保护术语正确保留数/保护术语数 | 100% |
| 人工审核率 | 已审核翻译数/总翻译数 | ≥30% |
| 格式保持率 | 格式正确保留数/总格式元素 | ≥98% |

### 质量等级

| 等级 | 术语一致性 | 翻译完整率 | 人工审核率 |
|------|-----------|-----------|-----------|
| A+ | ≥98% | 100% | ≥50% |
| A | ≥95% | 100% | ≥30% |
| B | ≥90% | ≥95% | ≥20% |
| C | ≥85% | ≥90% | ≥10% |
| D | <85% | <90% | <10% |

## 四、验收项

- [x] 多语言模板系统（8种语言支持）
- [x] 文化适配建议引擎（5类适配规则）
- [x] 自动适配6步流程
- [x] 国际化质量评估6指标+5等级
