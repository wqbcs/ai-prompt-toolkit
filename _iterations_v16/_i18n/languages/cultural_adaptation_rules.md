# N1-3：文化适配与本地化规则

> 迭代：N1-3 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. 文化适配规则体系

### 1.1 10语言文化适配矩阵

| 适配维度 | en | ja | ko | de | fr | es | pt | ru | ar | zh-tw |
|----------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 敬语体系 | 无 | 3级 | 6级 | Sie/du | vous/tu | usted/tú | você/tu | вы/ты | 无 | 无 |
| 日期格式 | MM/DD | YYYY/MM/DD | YYYY.MM.DD | DD.MM.YYYY | DD/MM/YYYY | DD/MM/YYYY | DD/MM/YYYY | DD.MM.YYYY | DD/MM/YYYY | YYYY/MM/DD |
| 数字格式 | 1,000.00 | 1,000.00 | 1,000.00 | 1.000,00 | 1 000,00 | 1.000,00 | 1.000,00 | 1 000,00 | 1,000.00 | 1,000.00 |
| 文本方向 | LTR | LTR | LTR | LTR | LTR | LTR | LTR | LTR | RTL | LTR |
| 编码优先 | ASCII | Shift-JIS/UTF-8 | EUC-KR/UTF-8 | UTF-8 | UTF-8 | UTF-8 | UTF-8 | UTF-8 | UTF-8 | Big5/UTF-8 |
| 示例风格 | 直接 | 含蓄 | 含蓄 | 直接 | 直接 | 热情 | 热情 | 直接 | 正式 | 含蓄 |

### 1.2 敬语体系适配

```typescript
interface FormalityRules {
  language: string;
  levels: FormalityLevel[];
  defaultLevel: string;
}

const japaneseFormality: FormalityRules = {
  language: "ja",
  levels: [
    { level: "desu-masu", description: "丁寧語-标准礼貌", use: "默认场景描述" },
    { level: "kenjougo", description: "謙譲語-自谦", use: "描述用户操作" },
    { level: "sonkeigo", description: "尊敬語-尊敬", use: "描述系统/权威" },
  ],
  defaultLevel: "desu-masu"
};

const koreanFormality: FormalityRules = {
  language: "ko",
  levels: [
    { level: "hapshio-che", description: "합쇼체-最高敬语", use: "正式文档" },
    { level: "haeyo-che", description: "해요체-标准敬语", use: "默认场景" },
    { level: "hao-che", description: "하오체-文语敬语", use: "技术文档" },
    { level: "hage-che", description: "하게체-半语", use: "代码注释" },
    { level: "hae-che", description: "해체-平语", use: "内部调试" },
    { level: "haera-che", description: "해라체-文语平语", use: "日志输出" },
  ],
  defaultLevel: "haeyo-che"
};
```

### 1.3 隐喻与文化引用适配

| 中文原隐喻 | 文化域 | en适配 | ja适配 | ko适配 | ar适配 |
|-----------|--------|--------|--------|--------|--------|
| 守门人 | 体系 | Gatekeeper | 門番 | 수문장 | الحارس |
| 闭环 | 物理 | Closed Loop | フィードバックループ | 피드백 루프 | حلقة مغلقة |
| 沙箱 | 安全 | Sandbox | サンドボックス | 샌드박스 | صندوق الرمل |
| 路线图 | 旅行 | Roadmap | ロードマップ | 로드맵 | خارطة الطريق |
| 生态 | 自然 | Ecosystem | エコシステム | 에코시스템 | النظام البيئي |
| 零信任 | 安全 | Zero Trust | ゼロトラスト | 제로 트러스트 | الثقة المعدومة |

### 1.4 RTL语言(ar)专项适配

```typescript
interface RTLAdaptation {
  direction: 'rtl';
  mirrorElements: string[];       // 需镜像的UI元素
  bidiMarkers: boolean;           // 双向文本标记
  numberDirection: 'ltr';         // 数字始终LTR
  codeBlocksDirection: 'ltr';     // 代码块始终LTR
  punctuationSwap: {              // 标点交换
    '(': ')',
    ')': '(',
    '[': ']',
    ']': '[',
    '{': '}',
    '}': '{',
    '<': '>',
    '>': '<',
  };
}
```

## 2. 本地化质量标准

| 检查项 | 标准 | 工具 |
|--------|------|------|
| 字符完整性 | UTF-8无遗漏 | ICU4C |
| 格式化保留 | ICU占位符完整 | 自定义检查 |
| 长度偏差 | ≤30%膨胀 | 伪本地化 |
| 敬语正确性 | 符合目标文化 | 人工审查 |
| 隐喻适配 | 无文化冒犯 | 文化审查 |
| RTL布局 | 无溢出/截断 | BiDi测试 |

## 3. 追溯记录

| 输入 | 输出 |
|------|------|
| N1-2翻译矩阵 | 10语言文化适配规则 |
| R14-N1-01调研 | 敬语+隐喻+RTL策略 |
