# R2-03 提示词国际化工具-翻译与术语一致性

> **迭代**：v21-R2-03 | **日期**：2026-07-12

---

## 一、国际化工具架构

### 核心组件

```
┌──────────────────────────────────────────┐
│          提示词国际化工具 (i18n Tool)       │
├──────────┬──────────┬────────────────────┤
│ 翻译引擎  │ 术语管理  │ 文化适配            │
│          │          │                    │
│ · 自动翻译 │ · 术语表  │ · 文化检查          │
│ · 人工校对 │ · 一致性  │ · 适配建议          │
│ · 术语保护 │ · 别名映射 │ · 敏感词检测        │
│ · 质量评估 │ · 多语言  │ · 本地化模板        │
└──────────┴──────────┴────────────────────┘
```

### 数据结构

```typescript
interface I18nProject {
  id: string
  sourceLanguage: string          // 源语言 'zh-CN'
  targetLanguages: string[]       // 目标语言 ['en-US', 'ja-JP', 'ko-KR']
  glossary: I18nGlossary
  translations: I18nTranslation[]
  culturalRules: CulturalRule[]
  qualityMetrics: I18nQualityMetrics
}

interface I18nGlossary {
  entries: GlossaryEntry[]
  consistencyScore: number        // 术语一致性0-100
  conflictCount: number
}

interface GlossaryEntry {
  term: string                    // 源术语
  translations: Record<string, string>  // 各语言翻译
  category: string                // 分类
  definition: string
  doNotTranslate: boolean         // 不翻译标记
  context: string                 // 使用上下文
  approvedBy: string
  approvedAt: string
}

interface I18nTranslation {
  sourceText: string
  sourceLanguage: string
  translatedText: string
  targetLanguage: string
  translationMethod: 'machine' | 'hybrid' | 'human'
  qualityScore: number
  reviewedBy?: string
  reviewedAt?: string
  status: 'draft' | 'reviewed' | 'approved' | 'rejected'
}
```

## 二、翻译引擎

### 3种翻译模式

| 模式 | 说明 | 质量 | 速度 | 成本 |
|------|------|------|------|------|
| 机器翻译 | LLM自动翻译 | 70-85% | 快 | 低 |
| 混合翻译 | 机器+术语表+人工校对 | 85-95% | 中 | 中 |
| 人工翻译 | 专业译员+审校 | 95-99% | 慢 | 高 |

### 术语保护机制

```typescript
interface TermProtectionRule {
  pattern: string                 // 匹配模式
  protectionLevel: 'keep' | 'transliterate' | 'explain'
  reason: string
  examples: string[]
}

// 示例保护规则
const TERM_PROTECTION_RULES = [
  { pattern: 'GaussDB', protectionLevel: 'keep', reason: '产品名不翻译' },
  { pattern: 'CodeArts', protectionLevel: 'keep', reason: '产品名不翻译' },
  { pattern: 'RESTful', protectionLevel: 'keep', reason: '技术术语保留' },
  { pattern: 'CoT', protectionLevel: 'explain', reason: '首次出现附英文全称' },
  { pattern: 'RAG', protectionLevel: 'explain', reason: '首次出现附英文全称' },
]
```

### 一致性检查

| 检查类型 | 说明 | 示例 |
|---------|------|------|
| 同义异译 | 同一术语多种翻译 | "提示词"/"Prompt"/"提示" |
| 异义同译 | 不同术语相同翻译 | "Agent"→代理 vs "Proxy"→代理 |
| 上下文不一致 | 同一术语不同上下文翻译不同 | "Token"(NLP) vs "Token"(认证) |
| 缩写不一致 | 缩写展开不统一 | "LLM"/"大语言模型"/"大型语言模型" |
| 大小写不一致 | 同一术语大小写不统一 | "RESTful"/"Restful"/"restful" |

## 三、文化适配

### 文化检查5维度

| 维度 | 说明 | 示例 |
|------|------|------|
| 日期格式 | 不同地区日期格式不同 | 2026-07-12 / 07/12/2026 / 12.07.2026 |
| 数字格式 | 千分位+小数点差异 | 1,000.00 / 1.000,00 / 1 000,00 |
| 示例选择 | 避免文化敏感示例 | 人名/地名/货币 |
| 比喻习惯 | 不同文化不同比喻 | "如鱼得水"/"like a duck to water" |
| 礼仪规范 | 敬语/称呼差异 | 中文敬语/日语敬语体系 |

### 敏感词检测

```typescript
interface SensitiveTermDetection {
  term: string
  category: 'political' | 'religious' | 'cultural' | 'legal' | 'brand'
  severity: 'low' | 'medium' | 'high'
  affectedLanguages: string[]
  suggestion: string
}
```

## 四、验收项

- [x] 国际化工具3层架构
- [x] 3种翻译模式+术语保护机制
- [x] 5种一致性检查类型
- [x] 文化适配5维度+敏感词检测
