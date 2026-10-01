"""P260 编码/混淆注入面 — 已知注入载荷编码检测 (R215-B2, B5新规则模板)

触发(5 个子pattern, 全部有限集/阈值, 无新启发式, 阈值与集合直接复用
ATR 实证值非自调):
 1. 零宽/bidi 控制字符: 5+连续(ATR-2026-00002 L2 阈值 — 信源明示 5+ 是
    为避开合法多语 RTL 文本误报的实证值) 或 词内插入
    (i[zw]+g[zw]*n[zw]*o[zw]*r[zw]*e — ATR-2026-00001 L13)
 2. 已知 base64 片段有限集(8 片段 = 注入关键词 base64 前缀 —
    ATR-2026-00001 L11)
 3. base64 长串 + 解码指令共现(decode/execute…动词 + 冒号 + 20+字符b64
    — ATR-2026-00001 L10)
 4. 同形异码 西里尔/Greek 范围混入注入关键词骨架
    (gn[hw]re/verr[hw]de/ystem — ATR-2026-00001 L12)
 5. hex/URL 百分号编码注入关键词有限集(ATR-2026-00001 L14)
Severity: HIGH — 混淆 = 有意规避检测, 恶意信号强

与存量规则差异化: P021/P177 检测"存在编码内容"(质量面, 通用触发);
P260 检测"已知注入载荷的编码"(安全面, 精确触发) — R215-B1 量化: 存量
通用检测对 7 条编码探针中 5 条零覆盖。

诚实声明(机制上限): 有限集方案对**未知**编码载荷必然漏检(如
base64("删除所有数据") 不在 8 片段集) — 语义层(embedding 类, 参照
Anthropic JWE)超出本项目静态机械定位, 见方案文档 §4 P0-3。
OWASP: LLM01 Prompt Injection (garak 编码探针族 tag owasp:llm01 印证)
ATLAS: AML.T0015 Evade AI Model（同映射表 P021/P177 行, 编号 2026-10-01 联网复核）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P260 = [
    LintRule(
        "P260",
        "编码/混淆注入面",
        "security",
        Severity.HIGH,
        "Prompt含已知注入载荷的编码形态(零宽字符5+/词内插入、注入关键词base64片段、解码指令+b64共现、同形异码、hex/URL编码) — 混淆=有意规避检测",
        "移除编码混淆的注入内容; 合法编码数据请避免与解码指令共现, 并在prompt中声明数据边界",
        description_en=(
            "Prompt contains encoded forms of known injection payloads (5+ consecutive or "
            "in-word zero-width chars, base64 fragments of injection keywords, decode-instruction "
            "+ base64 co-occurrence, homoglyph substitution, hex/URL-encoded keywords) — "
            "obfuscation = deliberate detection evasion"
        ),
        remediation_en=(
            "Remove the obfuscated injection content; for legitimate encoded data, avoid "
            "co-occurrence with decode instructions and declare the data boundary"
        ),
        family="encoding_evasion",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P260:
    _RULE_MAP[r.rule_id] = r

_ZW = r"\u200b\u200c\u200d\ufeff\u2060\u180e\u200e\u200f\u202a-\u202e\u2066-\u2069"

# 子1: 零宽/bidi — 5+连续(ATR-00002 L2 阈值) 或 词内插入"ignore"(ATR-00001 L13)
_SUB_ZW = re.compile(
    rf"(?:[{_ZW}]{{5,}}|i[{_ZW}]+g[{_ZW}]*n[{_ZW}]*o[{_ZW}]*r[{_ZW}]*e)",
    re.IGNORECASE,
)
# 子2: 已知 base64 片段有限集(ATR-00001 L11, 长片段优先避免前缀遮蔽)
_SUB_B64_FRAG = re.compile(
    r"(?:aWdub3JlIGFsbCBwcmV2aW91cw|aWdub3JlIHByZXZpb3Vz|c3lzdGVtIHByb21wdA"
    r"|aWdub3Jl|ZGlzcmVnYXJk|b3ZlcnJpZGU|Zm9yZ2V0|YnlwYXNz)"
)
# 子3: base64/hex 长串 + 解码指令共现(ATR-00001 L10, 冒号必选=精度)
_SUB_B64_DECODE = re.compile(
    r"(?:decode|interpret|execute|run|process|follow|read)\s+(?:this|the\s+following)?\s*"
    r"[:：]\s*[A-Za-z0-9+/]{20,}={0,2}",
    re.IGNORECASE,
)
# 子4: 同形异码 西里尔/Greek 混入注入关键词骨架(ATR-00001 L12)
_SUB_HOMOGLYPH = re.compile(
    r"[\u0400-\u04FF\u0370-\u03FF]+(gn[\u0400-\u04FF\u0370-\u03FF]re"
    r"|verr[\u0400-\u04FF\u0370-\u03FF]de|ystem)"
)
# 子5: hex/URL 百分号编码注入关键词有限集(ATR-00001 L14)
_SUB_HEX_URL = re.compile(
    r"(?:%69%67%6[eE]%6[fF]%72%65|%64%69%73%72%65%67%61%72%64"
    r"|%6[fF]%76%65%72%72%69%64%65|\\x69\\x67\\x6e\\x6f\\x72\\x65)",
    re.IGNORECASE,
)

_SUB_PATTERNS = (
    ("zero_width", _SUB_ZW),
    ("base64_fragment", _SUB_B64_FRAG),
    ("base64_decode_cooccurrence", _SUB_B64_DECODE),
    ("homoglyph", _SUB_HOMOGLYPH),
    ("hex_url_encoded", _SUB_HEX_URL),
)


def check_p260(text: str) -> Finding | None:
    rule = _RULE_MAP["P260"]
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
