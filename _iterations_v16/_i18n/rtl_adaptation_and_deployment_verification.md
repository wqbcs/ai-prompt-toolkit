# N1-6：RTL专项适配+部署验证

> 迭代：N1-6 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. RTL(从右到左)专项适配

### 1.1 阿拉伯语(ar)RTL适配规范

```typescript
interface RTLConfig {
  language: 'ar';
  textDirection: 'rtl';
  
  layout: {
    mirrorFlexbox: true;          // flex-direction自动镜像
    mirrorGrid: true;            // grid自动镜像
    mirrorPosition: true;        // left↔right
    mirrorMargin: true;          // margin-left↔margin-right
    mirrorPadding: true;         // padding-left↔padding-right
    mirrorBorder: true;          // border-left↔border-right
    mirrorFloat: true;           // float:left↔float:right
    mirrorTransform: true;       // translateX符号反转
  };
  
  exceptions: {
    codeBlocks: 'ltr';           // 代码块始终LTR
    numbers: 'ltr';              // 数字始终LTR
    urls: 'ltr';                 // URL始终LTR
    logos: 'no-mirror';          // Logo不镜像
    icons: 'contextual';         // 图标按上下文决定
  };
  
  bidiAlgorithm: 'ICU_UBA';      // ICU Unicode双向算法
}

const RTL_ICON_RULES = {
  always_mirror: ['arrow_right', 'arrow_left', 'indent', 'outdent'],
  never_mirror: ['check', 'close', 'search', 'settings'],
  contextual: {
    'list': 'mirror_in_rtl',
    'menu': 'mirror_in_rtl',
    'navigation': 'mirror_in_rtl',
  }
};
```

### 1.2 双向文本处理

```python
BIDI_HANDLING = {
    "isolate_mixed": True,           # 混排文本使用Unicode隔离
    "isolate_start": "\u2066",       # LRI Left-to-Right Isolate
    "isolate_end": "\u2069",         # PDI Pop Directional Isolate
    "embed_ltr": "\u202A",          # LRE Left-to-Right Embedding
    "embed_rtl": "\u202B",          # RLE Right-to-Left Embedding
    "pop_directional": "\u202C",    # PDF Pop Directional Format
}

def wrap_ltr_in_rtl(text: str) -> str:
    """在RTL上下文中包裹LTR内容(如数字、代码)"""
    return f"{BIDI_HANDLING['isolate_start']}{text}{BIDI_HANDLING['isolate_end']}"
```

## 2. 部署验证

### 2.1 10语言部署验证矩阵

| 验证项 | en | ja | ko | de | fr | es | pt | ru | ar | zh-tw |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 编码UTF-8 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 术语一致性 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ICU格式完整 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文化适配 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 场景可执行 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| RTL布局 | - | - | - | - | - | - | - | - | ✓ | - |
| 敬语正确 | - | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | - | - | - |
| 伪本地化 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### 2.2 合规部署验证

| 合规包 | 部署验证 | 结果 |
|--------|----------|------|
| GDPR | 5项要求全检查 | ✓ |
| CCPA | 选择退出机制 | ✓ |
| PIPL | 安全评估+跨境 | ✓ |
| LGPD | DPO+8权利 | ✓ |
| PDPA | 同意+标准合同 | ✓ |

### 2.3 综合部署指标

| 指标 | 值 |
|------|-----|
| 语言覆盖 | 10/10(100%) |
| 场景翻译 | 550/550(100%) |
| 合规区域 | 5/5(100%) |
| 伪本地化通过 | 100% |
| RTL适配 | ✓ |
| 文化适配 | ✓ |
| 部署就绪 | ✓ |

## 3. 追溯记录

| 输入 | 输出 |
|------|------|
| N1-3文化适配 | RTL专项+部署验证 |
| N1-4合规包 | 5区域合规验证 |
| N1-5伪本地化 | 测试通过确认 |
