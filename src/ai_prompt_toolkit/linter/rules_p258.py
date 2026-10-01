"""P258 伪造系统级标签声明缺失 — 特权边界操纵面 (R215-B2, B5新规则模板)

触发: prompt 文件出现系统级分隔符标记
     (全角括号【系统】/【システム】/半角[SYSTEM]/Llama <<SYS>>/
      模型token <|system|>/双花括号{{SYSTEM}})
     + 标签近邻(±80字符)无"示例/演示"类声明
Severity: HIGH — 标签会被模型当作特权边界, 是主动操纵面
     (比 P257 RAG语境缺失声明=MEDIUM 特权强度高, 故放行面更严)

开源参考(思路复用, 非代码复用, 词面逐词核对):
- ATR-2026-00001 L7: 伪分隔符 [SYSTEM]/[INST]/<<SYS>>/{{SYSTEM}}
- ATR-2026-00002 L3: 模型专属 token (<|system|>/[INST]/[HIDDEN]/<<SYS>>)
- ATR-2026-00097: CJK 标签面 (【|「|『|{{).{0,3}(システム|SYSTEM|管理者|ADMIN)
  — 本轮只取【】全角族(引号「『属引用语境, 误报面大, 精度优先不取)
- Willison 2025-08 role-based injection: 对话格式本身高危 → 放行只认显式
  "这是示例"声明, 不认格式合法性
OWASP: LLM01 Prompt Injection (garak 探针族 owasp:llm01 tag 印证)
ATLAS: AML.T0051.000 Direct Prompt Injection（编号 2026-10-01 联网复核, docs/mitre-atlas-mapping.md）

放行面(近邻 ±80 字符内 — 刻意严于 P257 的文件级声明: 标签特权强度越高,
放行应越严格; 与 ESLint disable 注释近邻原则一致, 见方案文档 §5 对抗审查#1):
示例/演示/教学/样例/example/few-shot/引用/示例/示范
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

# 伪系统标签 gate — 三信源并集(精确匹配, 括号内容必须是完整关键词,
# 【系统架构】这类章节标题不命中, 精度优先)
_FAKE_TAG_RE = re.compile(
    r"(?:"
    r"【\s*(?:系统|管理员|管理者|システム|SYSTEM|ADMIN|SYS|INSTRUCTION|オーバーライド|優先|緊急)\s*】"  # 全角括号族(zh/ja)
    r"|\[(?:SYSTEM|INST|INSTRUCTION|SYS|ADMIN|ROOT|OVERRIDE|CONTROL|PRIORITY|URGENT)\]"  # 半角括号族(en, ATR-00001 L7)
    r"|<\s*<\s*(?:SYS|SYSTEM|INST)\s*>\s*>"  # Llama族 <<SYS>> (ATR-00001 L7)
    r"|<\|(?:system|im_start|inst)\|>"  # 模型chat template token (ATR-00002 L3)
    r"|\{\{\s*(?:SYSTEM|INSTRUCTION|OVERRIDE)\s*\}\}"  # 双花括号族 (ATR-00001 L7)
    r")",
    re.IGNORECASE,
)

# 放行面 — 近邻声明(示例/演示语境), 见模块docstring的严格度理由
_EXAMPLE_DECL_RE = re.compile(
    r"(?:示例|演示|教学|样例|example|few.?shot|引用|示范|demo|illustration)",
    re.IGNORECASE,
)

_NEIGHBOR_RADIUS = 80  # 字符 — 标签特权声明的生效半径(ESLint disable注释近邻原则)


def check_p258(text: str) -> Finding | None:
    rule = _RULE_MAP["P258"]
    for m in _FAKE_TAG_RE.finditer(text):
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
