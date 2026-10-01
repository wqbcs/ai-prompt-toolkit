# 本地化测试框架

> 版本：v16.0.0 | 覆盖：伪本地化+11语言+RTL+合规

---

## 1. 伪本地化测试(Pseudolocalization)

### 1.1 转换规则

| 策略 | 输入 | 输出 | 检测目标 |
|------|------|------|---------|
| 括号包裹 | Hello | [Hello] | 硬编码字符串 |
| 字符扩展 | Hello | [Ĥêļļõ] | 布局溢出 |
| 长度扩展(40%) | Hello | [Ĥêļļõ 世界世界世界] | 布局适配 |
| 双向标记 | Hello | \u200FHello\u200F | RTL混排 |
| Unicode边界 | Hello | Hello􏿿 | 边界字符 |

### 1.2 伪本地化配置

```yaml
pseudolocalization:
  prefix: "["
  suffix: "]"
  expand_ratio: 1.4
  accents:
    a: à, e: è, i: ì, o: ò, u: ù
    A: À, E: È, I: Ì, O: Ò, U: Ù
  rtl_marker: "\u200F"
  max_length_ratio: 3.0
```

### 1.3 CI集成

```yaml
# .github/workflows/i18n-test.yml
i18n_pseudolocalization:
  steps:
    - extract_strings: 从代码/文档提取可翻译字符串
    - pseudolocalize: 应用伪本地化转换
    - build: 使用伪本地化字符串构建
    - test_screenshot: 截图对比检测布局问题
    - check_hardcoded: 检测硬编码字符串
    - check_concat: 检测字符串拼接(而非格式化)
```

## 2. 语言专项测试矩阵

### 2.1 基础测试(每语言必测)

| 测试ID | 测试项 | 检查点 | 优先级 |
|--------|--------|--------|--------|
| LT-01 | 字符编码 | UTF-8无BOM，所有字符正确显示 | P0 |
| LT-02 | 字体回退 | 系统字体→Web字体→回退字体链完整 | P0 |
| LT-03 | 文本渲染 | 无截断、无重叠、无乱码 | P0 |
| LT-04 | 日期格式 | 符合区域约定 | P0 |
| LT-05 | 数字格式 | 小数点/千分位正确 | P0 |
| LT-06 | 货币格式 | 符号位置+ISO代码正确 | P1 |
| LT-07 | 排序规则 | 区域感知排序(如de:ä介于a和b) | P1 |
| LT-08 | 复数形式 | 正确使用复数规则(en:1 item/2 items) | P1 |
| LT-09 | 性别/格变化 | 各格变化正确(de:4格, ru:6格) | P2 |
| LT-10 | 礼貌级别 | 正式/非正式用语正确 | P1 |

### 2.2 RTL专项测试(阿拉伯语)

| 测试ID | 测试项 | 检查点 |
|--------|--------|--------|
| RT-01 | 布局镜像 | 整体布局从右到左 |
| RT-02 | 文本对齐 | 默认右对齐 |
| RT-03 | 图标翻转 | 方向性图标翻转(箭头等) |
| RT-04 | 数字方向 | 数字仍LTR显示 |
| RT-05 | 混排处理 | 阿拉伯文+英文混排正确 |
| RT-06 | 标点位置 | 标点在正确侧 |
| RT-07 | 表格方向 | 表格列从右到左 |
| RT-08 | 导航方向 | 面包屑/进度条从右到左 |

### 2.3 CJK专项测试(中日韩)

| 测试ID | 测试项 | 检查点 | 语言 |
|--------|--------|--------|------|
| CJ-01 | 字符宽度 | 全角/半角混排正确 | zh/ja/ko |
| CJ-02 | 禁则处理 | 行首行尾禁则(kinsoku shori) | ja |
| CJ-03 | 换行规则 | CJK字符间可换行 | zh/ja/ko |
| CJ-04 | 竖排文本 | 竖排模式正确 | ja/zh-Hant |
| CJ-05 | 注音标注 | Ruby/Furigana正确 | ja |
| CJ-06 | 简繁转换 | 简繁用词差异(软件/軟體) | zh |

## 3. 合规验证测试

| 测试ID | 测试项 | 法规 | 检查点 |
|--------|--------|------|--------|
| CV-01 | 隐私声明可用 | ALL | 隐私声明已本地化且可访问 |
| CV-02 | 同意机制 | GDPR/PIPL | 明确同意+可撤回 |
| CV-03 | Cookie同意 | GDPR | Opt-in(非Opt-out) |
| CV-04 | 删除权 | GDPR/PIPL/CCPA | 数据删除API+级联删除 |
| CV-05 | 访问权 | ALL | 数据访问API+响应时间≤30天 |
| CV-06 | Opt-out | CCPA | "Do Not Sell"链接显眼 |
| CV-07 | 数据驻留 | PIPL | 中国数据境内存储验证 |
| CV-08 | 跨境传输 | GDPR/PIPL | 传输机制+安全保障 |
| CV-09 | DPO/PIPO | GDPR/PIPL/LGPD | 联系方式已公开 |
| CV-10 | 数据泄露通知 | GDPR | 72小时通知机制 |

## 4. 测试执行矩阵

| 语言 | 基础10项 | RTL 8项 | CJK 6项 | 合规 10项 | 总计 |
|------|---------|---------|---------|----------|------|
| en | 10 | - | - | 10 | 20 |
| zh-Hans | 10 | - | 6 | 10 | 26 |
| ja | 10 | - | 6 | 10 | 26 |
| ko | 10 | - | 6 | 10 | 26 |
| de | 10 | - | - | 10 | 20 |
| fr | 10 | - | - | 10 | 20 |
| es | 10 | - | - | 10 | 20 |
| pt | 10 | - | - | 10 | 20 |
| ru | 10 | - | - | 10 | 20 |
| ar | 10 | 8 | - | 10 | 28 |
| zh-Hant | 10 | - | 6 | 10 | 26 |
| **合计** | **110** | **8** | **24** | **110** | **252** |

## 5. 质量门禁

```yaml
i18n_quality_gate:
  pseudolocalization:
    hardcoded_strings: 0
    layout_overflow: 0
    string_concat: 0
  translation_coverage:
    minimum: 100%  # 所有55场景必须翻译
    terminology_consistency: 100%
  cultural_adaptation:
    color_violations: 0
    icon_violations: 0
    direction_violations: 0
  compliance:
    privacy_notice_available: true
    consent_mechanism: true
    data_rights_api: true
```
