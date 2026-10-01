"""P258 伪造系统级标签声明缺失 — 特权边界操纵面 (R215-B2, B5新规则模板)

触发: prompt 文件出现系统级分隔符标记
     (全角括号【系统】/【システム】/半角[SYSTEM]/Llama <<SYS>>/
      模型token <|system|>/双花括号{{SYSTEM}})
     + 标签近邻(±80字符)无"示例/演示"类声明
Severity: HIGH — 标签会被模型当作特权边界, 是主动操纵面
     (比 P257 RAG语境缺失声明=MEDIUM 特权强度高, 故放行面更严)

匹配机制(两段式, R215-review 零宽交叉盲区根治):
1. 括号捕获: 5 种括号形态各自捕获内部文本(5 个捕获组, 组号=族号)
2. 关键词查表: 剥离 0-4 个零宽字符(模型分词器剥离 U+200B → 词内 zw 载荷
   对模型有效, 安全审查 HIGH) → 剥离外围空白 → 大小写不敏感查该族有限
   关键词集; 5+ 连续 zw 跳过(归 P260 子1 辖区, 不交叉覆盖 — 其 5+ 阈值
   是避合法 RTL 误报的实证值)
3. 词内空白不剥: CJK 空格插入（【系 统】）是已登记缺口(L3-14 重评门槛
   已触发, 观察探针 atk70/atk71), 本轮不放松
精度不变: 内部文本必须是有限集完整关键词, 【系统架构】这类章节标题不命中

开源参考(思路复用, 非代码复用):
- ATR-2026-00001 L7: 伪分隔符 [SYSTEM]/[INST]/<<SYS>>/{{SYSTEM}} → 半角括号族+Llama族词源
- ATR-2026-00002 L3: 模型专属 token (<|system|>/[INST]/[HIDDEN]/<<SYS>>) → token族词源
  token 族取舍: system/im_start/inst/hidden — hidden 为 ATR 原词(安全审查
  LOW 补齐, 此前静默排除无注释); im_start 为常见 chat-template 角色 token,
  跨族复用精度补强
- ATR-2026-00097: CJK 标签面 (【|「|『|{{).{0,3}(系统|SYSTEM|管理者|ADMIN|優先|緊急|オーバーライド)
  → 全角括号族词源(本轮只取【】全角族: 引号「『属引用语境, 误报面大, 精度优先不取)
  gate 词表逐词出处: 系统/管理者/優先/緊急/オーバーライド/SYSTEM/ADMIN = 00097 原词;
  管理员/システム = 同义变体扩展(无直接信源); SYS/INSTRUCTION = 半角/双花括号族
  跨族复用(本轮精度补强, 非 00097 原词)
- Willison 2025-08 role-based injection: 对话格式本身高危 → 放行只认显式
  "这是示例"声明, 不认格式合法性

残留误报面(登记不藏): standalone 【紧急】/【优先】/[PRIORITY]/[URGENT] 是合法中英文
prompt 常见优先级标记(分诊标题"【紧急】请立即处理..."), 本规则 HIGH 命中, 放行面
仅"示例/演示/引用"类兜底 — 58 clean + 15 模板实测 0 误报, 但该形态语料未覆盖;
真实误报案例出现时重评(候选: 优先标记族要求与"指令/命令"类更强信号共现), R216。
OWASP: LLM01 Prompt Injection (garak 探针族 owasp:llm01 tag 印证)
ATLAS: AML.T0051.000 Direct Prompt Injection（编号 2026-10-01 联网复核, docs/mitre-atlas-mapping.md）

放行面(近邻 ±80 字符内 — 刻意严于 P257 的文件级声明: 标签特权强度越高,
放行应越严格; 与 ESLint disable 注释近邻原则一致, 见方案文档 §5 对抗审查#1):
示例/演示/教学/样例/example/few-shot/引用/示范/demo/illustration
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P258 = [
    LintRule(
        "P258",
        "伪造系统级标签声明缺失",
        "security",
        Severity.HIGH,
        "Prompt含伪造系统级分隔标签(【系统】/[SYSTEM]/<|system|>/<<SYS>>), 且标签近邻无'示例/演示'声明 — 标签是特权边界操纵面",
        "删除伪系统标签; 若为few-shot示例, 在标签80字符内声明'以下是示例/供参考'",
        description_en=(
            "Prompt contains fake system-level delimiter tags (【系统】/[SYSTEM]/<|system|>/<<SYS>>) "
            "without a nearby 'example/demonstration' declaration — tags are a privilege-boundary "
            "manipulation surface"
        ),
        remediation_en=(
            "Remove the fake system tag; if it is a few-shot example, declare 'the following is an "
            "example' within 80 characters of the tag"
        ),
        family="injection_surface",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P258:
    _RULE_MAP[r.rule_id] = r

# 5 种括号形态 → 内部文本(捕获组号 = 族号)
_FAKE_TAG_BRACKET_RE = re.compile(
    r"【([^【】]{0,24})】"  # 1: 全角括号族(zh/ja)
    r"|\[([^\[\]]{0,24})\]"  # 2: 半角括号族(en, ATR-2026-00001 L7)
    r"|<\s*<\s*([^\n]{0,24}?)\s*>\s*>"  # 3: Llama族 <<SYS>> (ATR-2026-00001 L7)
    r"|<\|([^\|\n]{0,24}?)\|>"  # 4: 模型chat template token (ATR-20002 L3)
    r"|\{\{([^\n]{0,24}?)\}\}"  # 5: 双花括号族 (ATR-2026-00001 L7)
)

# 各族关键词有限集(出处见模块docstring逐词标注; casefold 后比较)
_FAMILY_KEYWORDS = (
    frozenset(  # 1: 全角括号族
        k.casefold()
        for k in (
            "系统", "管理员", "管理者", "システム", "SYSTEM", "ADMIN", "SYS",
            "INSTRUCTION", "オーバーライド", "優先", "緊急",
        )
    ),
    frozenset(  # 2: 半角括号族
        k.casefold()
        for k in (
            "SYSTEM", "INST", "INSTRUCTION", "SYS", "ADMIN", "ROOT", "OVERRIDE",
            "CONTROL", "PRIORITY", "URGENT",
        )
    ),
    frozenset(k.casefold() for k in ("SYS", "SYSTEM", "INST")),  # 3: Llama族
    frozenset(k.casefold() for k in ("system", "im_start", "inst", "hidden")),  # 4: token族
    frozenset(k.casefold() for k in ("SYSTEM", "INSTRUCTION", "OVERRIDE")),  # 5: 双花括号族
)

# 零宽/bidi 字符集(与 P260 子1 码点集一致)
_ZW_CHAR_RE = re.compile(
    r"[\u200b\u200c\u200d\ufeff\u2060\u180e\u200e\u200f"
    r"\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]"
)

_MAX_ZW_TOLERANCE = 4  # 5+ 连续 zw 归 P260 子1 辖区(其 5+ 阈值=避合法 RTL 误报的实证值)


def _tag_keyword_match(inner: str, keywords: frozenset[str]) -> bool:
    """标签内部文本匹配: 剥离 0-4 个零宽字符(词内 zw = 有效注入形态,
    安全审查 HIGH 根治) → 剥离外围空白 → 大小写不敏感查有限集。
    词内空白不剥离(CJK 空格插入面 = 已登记缺口, 见 L3-14)。"""
    zw_count = len(_ZW_CHAR_RE.findall(inner))
    if zw_count > _MAX_ZW_TOLERANCE:
        return False
    cleaned = _ZW_CHAR_RE.sub("", inner).strip()
    return cleaned.casefold() in keywords


# 放行面 — 近邻声明(示例/演示语境), 见模块docstring的严格度理由
_EXAMPLE_DECL_RE = re.compile(
    r"(?:示例|演示|教学|样例|example|few.?shot|引用|示范|demo|illustration)",
    re.IGNORECASE,
)

_NEIGHBOR_RADIUS = 80  # 字符 — 标签特权声明的生效半径(ESLint disable注释近邻原则)


def check_p258(text: str) -> Finding | None:
    rule = _RULE_MAP["P258"]
    for m in _FAKE_TAG_BRACKET_RE.finditer(text):
        inner = next(g for g in m.groups() if g is not None)
        if not _tag_keyword_match(inner, _FAMILY_KEYWORDS[m.lastindex - 1]):
            continue
        window = text[max(0, m.start() - _NEIGHBOR_RADIUS): m.end() + _NEIGHBOR_RADIUS]
        if not _EXAMPLE_DECL_RE.search(window):
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                remediation=rule.remediation,
                details={"tag": m.group(0), "position": m.start()},
            )
    return None
