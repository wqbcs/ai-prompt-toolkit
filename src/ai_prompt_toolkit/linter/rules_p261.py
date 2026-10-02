"""P261 不可见字符交错/BiDi反转注入面 — ATR-2026-00276 信源落地 (R217, B5新规则模板×3)

触发(3 个子pattern, 全部信源 FP 验证后实证值, 非自调):
 1. 零宽交错: {U+200B, U+200C, U+2060} 中 3+ 出现, 相邻间隔≤20 个非零宽字符
    (信源 3+ 交错阈值: 单字符触发=65K 语料 15 误报, 其 #323 收紧;
    ZWJ U+200D/BOM U+FEFF 排除 — emoji 连字/UTF-8 BOM 大规模误报,
    信源 FP 验证后明确移除)
 2. BiDi override/isolate 控制字符: {U+202C, U+202D, U+202E, U+2066-2069}
    单字符即报 — Trojan Source 显示反转信号(单个 U+202E 即可反转整段显示
    文本, 3+ 交错阈值不适用); 信源 TN 实证: 纯阿拉伯/希伯来 RTL 文字
    字符(固有方向性)不触发, 仅不可见 override 控制字符触发
 3. 转义形态: 字面文本 \\u200b/\\u202c-\\u202e/\\u2060-\\u2069
    (JSON/YAML 转义承载的注入载荷对模型同样有效 — 信源转义检测项)
Severity: HIGH — 不可见字符=刻意隐藏(检测规避/Trojan Source 显示欺骗)

与 P260 子1(5+连续 zw)辖区切分: P260 保持 5+ 连续(连续堆叠面); P261 覆盖
3+ 交错(含 1-2 字符间隔, 及 3-4 连续 — R215-review HIGH"1-4 zw 嵌入双漏"面
的 3+ 部分由此覆盖); 5+ 连续两规则交叉命中(双报为常态 — P258 的"跳过不交叉"
是关键词查表双逻辑防冲突, 不迁移到 pattern 双检测, 不为此加 skip 代码)。
IGNORECASE: 子3 转义形态大小写不敏感(\\u200B 大写常见, P260 子4 大写同形
异码召回缺口同型教训)。
已知残留缺口(信源 evasion_tests 明示 known gap, 登记不扩): 组合变音符
U+0301/软连字 U+00AD 亦属不可见格式字符但不在信源字符集(FP 验证未覆盖该类,
真实案例驱动重评); U+200E/U+200F 方向标记不在字符集(信源未含, 不预支)。
OWASP: LLM01 Prompt Injection (garak 编码探针族 tag owasp:llm01 印证)
ATLAS: AML.T0015 Evade AI Model（同映射表 P021/P177/P260 行, 2026-10-01 联网复核）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P261 = [
    LintRule(
        "P261",
        "不可见字符交错/BiDi反转注入面",
        "security",
        Severity.HIGH,
        "Prompt含零宽字符(U+200B/200C/2060)3+交错或BiDi override/isolate控制字符"
        "(U+202C-2E/U+2066-69, 含\\u转义形态) — 不可见隐藏=检测规避或Trojan Source显示反转",
        "移除不可见控制字符及其转义形态; 合法RTL文字(阿/希/波斯文字字符)不受影响, 仅不可见override控制字符被报",
        description_en=(
            "Prompt contains 3+ interleaved zero-width chars (U+200B/200C/2060) or BiDi "
            "override/isolate control chars (U+202C-2E/U+2066-69, incl. \\u-escaped forms) — "
            "invisible concealment = detection evasion or Trojan Source display reversal"
        ),
        remediation_en=(
            "Remove the invisible control characters and their escaped forms; legitimate "
            "RTL script text (Arabic/Hebrew/Persian) is not affected — only invisible "
            "override controls are reported"
        ),
        family="encoding_evasion",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P261:
    _RULE_MAP[r.rule_id] = r

# 零宽族(ATR-2026-00276 FP 验证后字符集: ZWJ U+200D/BOM U+FEFF 因大规模误报移除)
_ZW_SET = "\u200b\u200c\u2060"
# BiDi override/isolate 控制字符(Trojan Source 显示反转 — 单字符即攻击)
_BIDI_SET = "\u202c\u202d\u202e\u2066\u2067\u2068\u2069"

# 子1: 零宽 3+ 交错, 间隔≤20 非零宽字符(信源原pattern, 含换行排除)
_SUB_ZW_INTERLEAVED = re.compile(rf"(?:[{_ZW_SET}][^{_ZW_SET}\n]{{0,20}}){{3,}}")
# 子2: BiDi 控制字符单字符即报(信源原pattern)
_SUB_BIDI_CONTROL = re.compile(rf"[{_BIDI_SET}]")
# 子3: 转义形态(字面 \u200b 文本; IGNORECASE 覆盖大写 \u200B — P260子4 同型教训)
_SUB_ESCAPED = re.compile(r"(?:\\u200[bc]|\\u202[cde]|\\u206[0-9])", re.IGNORECASE)

_SUB_PATTERNS = (
    ("zero_width_interleaved", _SUB_ZW_INTERLEAVED),
    ("bidi_control", _SUB_BIDI_CONTROL),
    ("escaped_form", _SUB_ESCAPED),
)


def check_p261(text: str) -> Finding | None:
    rule = _RULE_MAP["P261"]
    for name, pattern in _SUB_PATTERNS:
        m = pattern.search(text)
        if m:
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                remediation=rule.remediation,
                details={"sub_pattern": name, "match": m.group(0)[:40]},
            )
    return None
