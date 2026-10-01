# N1-5：伪本地化测试框架

> 迭代：N1-5 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. 伪本地化测试框架

### 1.1 伪本地化规则

```python
class Pseudolocalizer:
    CHAR_MAP = {
        'a': 'à', 'b': 'ƀ', 'c': 'ç', 'd': 'đ', 'e': 'é',
        'f': 'ƒ', 'g': 'ĝ', 'h': 'ĥ', 'i': 'î', 'j': 'ĵ',
        'k': 'ķ', 'l': 'ļ', 'm': 'ɱ', 'n': 'ñ', 'o': 'ó',
        'p': 'ƥ', 'q': 'ɋ', 'r': 'ř', 's': 'ş', 't': 'ţ',
        'u': 'û', 'v': 'ʋ', 'w': 'ŵ', 'x': 'ẋ', 'y': 'ý',
        'z': 'ẑ',
        'A': 'À', 'B': 'Ɓ', 'C': 'Ç', 'D': 'Đ', 'E': 'É',
        'F': 'Ƒ', 'G': 'Ĝ', 'H': 'Ĥ', 'I': 'Î', 'J': 'Ĵ',
        'K': 'Ķ', 'L': 'Ļ', 'M': 'Ɱ', 'N': 'Ñ', 'O': 'Ó',
        'P': 'Ƥ', 'Q': 'Ɋ', 'R': 'Ř', 'S': 'Ş', 'T': 'Ţ',
        'U': 'Û', 'V': 'Ʋ', 'W': 'Ŵ', 'X': 'Ẋ', 'Y': 'Ý',
        'Z': 'Ẑ',
    }
    
    def pseudolocalize(self, text: str, mode: str = 'full') -> str:
        if mode == 'full':
            return self._full_pseudo(text)
        elif mode == 'ascii':
            return self._ascii_pseudo(text)
        elif mode == 'bidi':
            return self._bidi_pseudo(text)
    
    def _full_pseudo(self, text: str) -> str:
        result = "["
        for char in text:
            if char in self.CHAR_MAP:
                result += self.CHAR_MAP[char]
            else:
                result += char
        result += "]"
        return self._expand(result, ratio=1.3)
    
    def _bidi_pseudo(self, text: str) -> str:
        return "\u200F\u202B" + text + "\u202C\u200E"
```

### 1.2 测试检测矩阵

| 缺陷类型 | 检测方法 | 严重度 | 伪本地化模式 |
|----------|----------|--------|-------------|
| 硬编码字符串 | 伪本地化后文本不变 | CRITICAL | full |
| 字符串拼接 | 方括号不配对 | CRITICAL | full |
| 占位符损坏 | ICU变量被替换 | CRITICAL | full |
| 布局溢出 | 文本加长30%后UI溢出 | HIGH | full |
| 编码缺陷 | 变音标记显示为?或□ | HIGH | full |
| RTL混排 | 双向文本方向错误 | HIGH | bidi |
| 数字格式化 | 数字分隔符错误 | MEDIUM | ascii |
| 日期格式化 | 日期顺序错误 | MEDIUM | ascii |
| 复数规则 | 复数形式不匹配 | MEDIUM | full |
| 排序错误 | 变音标记排序异常 | LOW | ascii |

### 1.3 自动化测试流水线

```yaml
pseudolocalization_test_pipeline:
  stages:
    - name: 伪本地化生成
      action: generate_pseudo_locale
      modes: [full, ascii, bidi]
      output: pseudo_locale_pack/
    
    - name: 硬编码检测
      action: detect_hardcoded_strings
      scan_paths: [src/, prompts/]
      exclude: [test/, vendor/]
      threshold: 0  # 零容忍
    
    - name: 字符串完整性
      action: check_string_integrity
      checks:
        - bracket_matching: true
        - placeholder_preservation: true
        - icu_format_preservation: true
    
    - name: 布局溢出检测
      action: detect_layout_overflow
      method: visual_regression_test
      expand_ratio: 1.3
      tolerance_px: 5
    
    - name: 编码验证
      action: verify_encoding
      expected: UTF-8
      check_bom: false
    
    - name: RTL验证
      action: verify_rtl_layout
      languages: [ar]
      checks: [direction, mirror, bidi_reorder]
    
    - name: 报告生成
      action: generate_report
      format: [json, html]
      fail_on: [CRITICAL, HIGH]
```

### 1.4 预期测试结果

```json
{
  "test_id": "pseudo-l10n-v16",
  "total_strings": 550,
  "results": {
    "hardcoded_detected": 0,
    "integrity_passed": 550,
    "overflow_detected": 0,
    "encoding_passed": 550,
    "rtl_passed": 55,
    "overall_pass_rate": "100%"
  },
  "defects": []
}
```

## 2. 追溯记录

| 输入 | 输出 |
|------|------|
| R14-N1-01伪本地化 | 完整测试框架+自动化流水线 |
| N1-2翻译矩阵 | 550个字符串验证 |
