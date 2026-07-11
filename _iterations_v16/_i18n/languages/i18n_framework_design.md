# N1-1：多语言部署框架设计

> 迭代：N1-1 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. 10语言部署框架

### 1.1 语言目录结构

```
_i18n/languages/
├── en/           # 英语(P0)
│   ├── glossary.json
│   ├── scenarios/
│   │   ├── 01_requirements.json
│   │   ├── 02_architecture.json
│   │   └── ... (55场景)
│   └── cultural_rules.json
├── ja/           # 日语(P1)
├── ko/           # 韩语(P1)
├── de/           # 德语(P1)
├── fr/           # 法语(P1)
├── es/           # 西班牙语(P2)
├── pt/           # 葡萄牙语(P2)
├── ru/           # 俄语(P2)
├── ar/           # 阿拉伯语(P2, RTL)
└── zh-tw/        # 繁体中文(P2)
```

### 1.2 ICU消息格式规范

```typescript
interface I18nMessage {
  id: string;                    // 消息ID: "scenario.01.role_definition"
  defaultMessage: string;       // 默认消息(中文)
  description: string;          // 翻译者描述
  placeholders?: {              // ICU变量
    [key: string]: {
      type: 'string' | 'number' | 'date' | 'plural';
      description: string;
    };
  };
}

// 复数示例
const complexityMsg: I18nMessage = {
  id: "scenario.complexity_level",
  defaultMessage: "{level, plural, one {1个维度} other {#个维度}}",
  description: "维度数量显示",
  placeholders: {
    level: { type: "plural", description: "维度数量" }
  }
};
```

### 1.3 翻译工作流

```yaml
translation_workflow:
  source: zh-cn                # 源语言
  target_languages: [en, ja, ko, de, fr, es, pt, ru, ar, zh-tw]
  
  phases:
    - name: 术语提取
      action: extract_glossary
      output: glossary.json
    
    - name: 机器翻译初稿
      action: mt_translate
      engine: gpt-4-turbo
      constraints:
        - glossary_consistency: true
        - icu_format_preserve: true
        - placeholder_integrity: true
    
    - name: 人工校审
      action: human_review
      roles: [native_speaker, domain_expert]
    
    - name: 文化适配
      action: cultural_adaptation
      checks: [idiom, metaphor, formality, units]
    
    - name: 伪本地化验证
      action: pseudolocalization_test
    
    - name: 集成测试
      action: integration_test
      scenarios: 55
    
    - name: 发布
      action: publish_language_pack
```

### 1.4 术语表(Glossary)结构

```json
{
  "version": "1.0",
  "source_lang": "zh-cn",
  "terms": [
    {
      "key": "提示词",
      "translations": {
        "en": "Prompt",
        "ja": "プロンプト",
        "ko": "프롬프트",
        "de": "Prompt",
        "fr": "Prompt",
        "es": "Prompt",
        "pt": "Prompt",
        "ru": "Промпт",
        "ar": "موجه",
        "zh-tw": "提示詞"
      },
      "context": "核心概念，不翻译(en/ja/ko/de/fr/es/pt保留原文)",
      "do_not_translate": ["en", "ja", "ko", "de", "fr", "es", "pt"]
    },
    {
      "key": "场景",
      "translations": {
        "en": "Scenario",
        "ja": "シナリオ",
        "ko": "시나리오",
        "de": "Szenario",
        "fr": "Scénario",
        "es": "Escenario",
        "pt": "Cenário",
        "ru": "Сценарий",
        "ar": "سيناريو",
        "zh-tw": "場景"
      },
      "context": "使用场景定义"
    }
  ]
}
```

## 2. 追溯记录

| 输入 | 输出 |
|------|------|
| R14-N1-01调研 | 10语言框架+ICU格式+术语表+翻译工作流 |
| v15.0.0 i18n | 扩展为10语言完整部署 |
