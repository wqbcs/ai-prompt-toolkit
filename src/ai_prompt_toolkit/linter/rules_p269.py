"""P269 Unicode tag 块 ASCII smuggling 注入面 — 不可见 tag 块隐蔽载荷 (R312, B5新规则模板)

信源(全部联网核实, 独立真实案例 ≥4):
 - Cisco AI Security (Adam Swanda, 2024-03): Riley Goodside 2024-01-11 披露 tag 块
   隐蔽载荷; 发布 YARA 规则(F3 A0 [0-2] ??, 阈值>10 次出现)
 - AWS Security Blog (2025-09-30): Unicode character smuggling 专文; Bedrock
   Guardrails denied topics 即按 U+E0000–E007F 全块拒止; 含 UTF-16 代理对
   单遍清洗可绕过(孤儿代理重组)的实证
 - Trend Micro (2025-01): 真实 ASR 数据(Claude 3.5 Sonnet 87.5%→0%, 拦截后);
   载荷=可见问题+tag 编码指令长序列
 - CSA Research Note 2026 (wunderwuzzi 2026-02-11 生产利用): Claude Code/
   GitHub Copilot/Codex Skills/Gemini CLI 执行技能文件中 tag 块隐蔽 shell 指令;
   明示"标准工具链不覆盖 agent 技能文件/MCP 工具清单/配置仓库面"
 - arXiv 2607.05744 (MCP 工具元数据投毒): 8 技术中仅 TAG 块(T7)同时击穿
   字符串 sanitizer 与人工审批视图; 25 条良性工具描述 0 误报(baseline TN)

触发(2 个子pattern, 阈值对信源/合法用途实证, 非自调):
 1. tag 块字符总数 8+: U+E0000–E007F 全块(含边界标记 E0000/E0001/E007F)。
    阈值依据: 合法旗帜 emoji 区划代码最长 5 字符+cancel 标记=6 个 tag 字符
    (如 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England GBENG); 真实 payload=有意义指令 ≥10 字符→≥10 tag;
    Cisco 发布阈值 >10; 8+ 处于"合法上限 6"与"最小 payload ~10"之间。
 2. 转义形态 2+: 字面 \\U000E00xx(8位 Python 形态)或 \\uDB40\\uDC[0-7]xx
    (UTF-16 代理对正确编码域 — 低代理 DC00–DC7F 才对应 E0000–E007F;
    AWS 样例中 DD20–DD7F 实属他区, 不采用其宽口径)。1+ 提及在 Unicode 科普
    文本中合法, 2+ 已是攻击签名(真实转义 payload 为长序列)。
 3. 真字符+转义混排联合 8+: 子1/子2 独立阈值对混排编码有联合盲区
    (7 真字符+1 转义=总量 8, 两子阈值各差 1 皆不触发) — R319 深审发现并
    修复; 混排是单遍清洗规避的自然伪装面(AWS 实证: 单遍清洗重组孤儿代理)。
Severity: HIGH — 不可见隐蔽=刻意规避人工审查(2026 生产利用已实证)

与零宽族辖区切分(码点域互斥, 零交叉): P260=已知注入载荷编码(base64/hex/
同形字/零宽5+连续); P261=零宽 3+ 交错+BiDi override 控制; P269=tag 块
(Plane 14) — 三族码点域不相交, 无需 skip 逻辑(同 P260/P261 关系)。
已知残留缺口(登记不预支): <8 tag 的短 payload(如 "go"=2 tag)漏检 — 同 P261
3+ 阈值同型, 真实 TP 驱动重评; 代理对拆散跨边界(\\uDB40 与 \\uDCxx 之间插
文字)漏检; 变体选择符 U+FE00–FE0F 不覆盖(emoji 呈现选择符在 emoji 文本中
大规模合法, FP 验证未覆盖该类 — 同 P261 ZWJ/BOM 排除同型纪律)。
OWASP: LLM01 Prompt Injection (indirect, encoding-concealed 子类)
ATLAS: AML.T0015 Evade AI Model（同映射表 P021/P177/P260/P261 行）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P269 = [
    LintRule(
        "P269",
        "Unicode tag块ASCII smuggling注入面",
        "security",
        Severity.HIGH,
        "Prompt含8+ Unicode tag块字符(U+E0000–E007F)或2+ tag块转义形态"
        "(\\U000E00xx / \\uDB40\\uDCxx代理对)或真字符+转义形态合计8+ — "
        "tag块ASCII smuggling=不可见隐藏载荷(LLM分词器解码为明文); 合法旗帜"
        "emoji(≤6个tag字符)不报",
        "移除tag块字符及其转义形态(剥离U+E0000–E007F); 合法旗帜emoji(≤6个tag字符)不受影响",
        description_en=(
            "Prompt contains 8+ Unicode tag-block chars (U+E0000–E007F) or 2+ "
            "escaped tag-block forms (\\U000E00xx / \\uDB40\\uDCxx surrogate "
            "pairs), or a combined total of 8 real+escaped chars — "
            "tag-block ASCII smuggling: invisible payload decoded as "
            "plaintext by LLM tokenizers; legitimate flag emoji (≤6 tag chars) "
            "are not reported"
        ),
        remediation_en=(
            "Remove tag-block characters and their escaped forms (strip "
            "U+E0000–E007F); legitimate flag emoji (≤6 tag chars) are not "
            "affected"
        ),
        family="encoding_evasion",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P269:
    _RULE_MAP[r.rule_id] = r

# tag 块全块(Plane 14: TAG NULL – TAG DELETE)
_TAG_BLOCK_RE = re.compile(r"[\U000E0000-\U000E007F]")
# 转义形态: \\U000E00xx(8位) 或 \\uDB40\\uDC[0-7]xx(代理对, 低代理 DC00–DC7F)
_TAG_ESCAPED_RE = re.compile(
    r"(?:\\uDB40\\uDC[0-7][0-9A-Fa-f]|\\U000E00[0-7][0-9A-Fa-f])",
    re.IGNORECASE,
)
_TAG_MIN_COUNT = 8  # 合法旗帜上限 6 / 最小真实 payload ~10 (信源阈值面, 见模块 docstring)
_TAG_ESCAPED_MIN = 2  # 1+ 提及=Unicode 科普合法, 2+ = 攻击签名


def _decode_tag_preview(cps: list[int], limit: int = 40) -> str:
    """tag 码点→原 ASCII 预览(非可打印位→空格, 同 Cisco skill-scanner 参考实现)"""
    out: list[str] = []
    for cp in cps:
        v = cp - 0xE0000
        out.append(chr(v) if 0x20 <= v <= 0x7E else " ")
    return "".join(out)[:limit]


def check_p269(text: str) -> Finding | None:
    rule = _RULE_MAP["P269"]

    # 子1: tag 块字符总数 8+ (一次线性扫描, O(n), 确定性)
    tag_cps: list[int] = []
    first: re.Match[str] | None = None
    for m in _TAG_BLOCK_RE.finditer(text):
        cp = ord(m.group(0))
        tag_cps.append(cp)
        if first is None:
            first = m
    # 不变量: tag_cps 非空 ⟺ first 非 None (同一 finditer 循环产出两者)
    if len(tag_cps) >= _TAG_MIN_COUNT and first is not None:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            location=loc_from_match(text, first),
            remediation=rule.remediation,
            details={
                "sub_pattern": "tag_block_count",
                "count": len(tag_cps),
                "decoded_preview": _decode_tag_preview(tag_cps),
            },
        )

    # 子2: 转义形态 2+ (字面文本中的 JSON/YAML/Python 转义承载)
    escaped = list(_TAG_ESCAPED_RE.finditer(text))
    if len(escaped) >= _TAG_ESCAPED_MIN:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            location=loc_from_match(text, escaped[0]),
            remediation=rule.remediation,
            details={
                "sub_pattern": "tag_block_escaped",
                "count": len(escaped),
                "decoded_preview": "",
            },
        )

    # 子3: 真字符+转义混排联合阈值(R319 深审 MEDIUM-1: 7 真+1 转义=总量 8
    # 攻击签名 — 子1/子2 独立阈值对混排编码有联合盲区)。走到此分支必是
    # raw<8 且 escaped<2(子1/子2 已先行返回), 即混排形态专属触发面。
    total = len(tag_cps) + len(escaped)
    if total >= _TAG_MIN_COUNT and first is not None and escaped:
        anchor = first if first.start() <= escaped[0].start() else escaped[0]
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            location=loc_from_match(text, anchor),
            remediation=rule.remediation,
            details={
                "sub_pattern": "tag_block_mixed",
                "count": total,
                "decoded_preview": _decode_tag_preview(tag_cps),
            },
        )
    return None
