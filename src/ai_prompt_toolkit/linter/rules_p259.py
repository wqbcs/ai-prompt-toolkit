"""P259 人格切换与前约束作废 — 越狱复合面 (R215-B2, B5新规则模板)

触发: 身份重赋值(你现在是…新的…助手 / You are now a new assistant /
     あなたは今から…新しい…アシスタント)
     AND 前约束作废(之前…约束…作废 / previous constraints are void /
     以前の制約はすべて無効) 共现
Severity: HIGH — 越狱复合信号

为什么必须复合面(单面不检): "你是X助手"是 prompt 编写最高频合法句
("You are a helpful assistant" 变体) — 单独检测是误报陷阱, 违反 0.92%
误报基线纪律; "作废/void"单独出现于合规的"规则更新"声明。复合共现才
是越狱信号。

开源参考(思路复用, 非代码复用):
- ATR-2026-00097: CJK persona (你现在是…新的…助手 / あなたは今から…新しい…アシスタント)
- ATR-2026-00001 L2a: persona switching (you are now / transform into)
R215-B1 数据裁决(方案文档 §7): 复合面 3/3 探针命中(zh/ja/en), 58 clean +
15 内置模板 0 误报 → 落地; 宽面("你是X"单独)被否决
OWASP: LLM01 Prompt Injection
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P259 = [
    LintRule(
        "P259",
        "人格切换与前约束作废",
        "security",
        Severity.HIGH,
        "Prompt含'身份重赋值'与'前约束作废'共现(越狱复合面) — 单独'你是X'是合法高频句不检, 复合共现才是信号",
        "移除身份重赋值+约束作废的共现表述; 规则更新场景请分句表述(新角色定义与旧规则废止分开声明)",
        description_en=(
            "Prompt contains co-occurring identity reassignment ('you are now a new assistant') "
            "and prior-constraint voiding ('previous constraints are void') — a jailbreak "
            "compound surface (single 'you are X' is a legitimate high-frequency sentence, not flagged)"
        ),
        remediation_en=(
            "Remove the co-occurring identity reassignment + constraint voiding; for legitimate "
            "rule updates, declare the new role and the old-rule retirement in separate sentences"
        ),
        family="jailbreak_surface",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P259:
    _RULE_MAP[r.rule_id] = r

# 身份重赋值面(zh/en/ja — ATR-2026-00097 + ATR-2026-00001 L2a 词面)
_IDENTITY_ZH = re.compile(
    r"(?:你现在是|你現在是|你已经是|你已經是|你变成|你變成|你成为了|你成為了|你是)"
    r".{0,10}(?:全新的|新的|另一个|另一個|不同的)?\s*(?:助手|助理|AI|机器人|機器人|客服|模型|系统|系統)"
)
_IDENTITY_EN = re.compile(
    r"(?:you\s+are\s+now|you\s+have\s+become|now\s+you\s+are|you\s+will\s+be)"
    r"\s+(?:a\s+|an\s+|the\s+)?(?:brand\s+new|new|different|another|fresh)?\s*"
    r"(?:assistant|AI|agent|model|bot)",
    re.IGNORECASE,
)
_IDENTITY_JA = re.compile(
    r"(?:あなたは今から|これからあなたは|今からあなたは|あなたはもう)"
    r".{0,15}(?:別の|新しい|違う).{0,10}(?:アシスタント|助手|AI|ボット|モデル|システム)"
)

# 前约束作废面(zh/en/ja — 支持"之前所有的约束和限制规则"连词/的/重复名词形态)
_VOIDING_ZH = re.compile(
    r"(?:之前|以前|上述|以上|原有|先前)(?:所有|全部|这些|那些|一切)?\s*的?\s*"
    r"(?:约束|限制|规则|指令|规定)(?:[和与、]?(?:约束|限制|规则|指令|规定))*"
    r"\s*(?:全部|都|被|已|整体)?\s*(?:作废|无效|废除|取消|解除|失效|废弃)"
)
_VOIDING_EN = re.compile(
    r"(?:all\s+)?(?:previous|prior|earlier|above)\s+"
    r"(?:constraints?|limits?|rules?|instructions?|guidelines?)"
    r"(?:\s*(?:,|and|or)\s*(?:constraints?|limits?|rules?|instructions?|guidelines?))*"
    r"\s+are\s+(?:void|invalid|nullified|cancelled|canceled|removed|no\s+longer\s+in\s+effect)",
    re.IGNORECASE,
)
_VOIDING_JA = re.compile(
    r"(?:以前|過去|上記)(?:の)?(?:ペルソナ|制約|ルール|指示|規約|条件)(?:と|が|は)"
    r".{0,10}(?:すべて|全て|全部)?(?:無効|失効|解除|取消|廃止)(?:になる|です|します|する)"
)


def check_p259(text: str) -> Finding | None:
    rule = _RULE_MAP["P259"]
    id_m = (
        _IDENTITY_ZH.search(text)
        or _IDENTITY_EN.search(text)
        or _IDENTITY_JA.search(text)
    )
    void_m = (
        _VOIDING_ZH.search(text)
        or _VOIDING_EN.search(text)
        or _VOIDING_JA.search(text)
    )
    if id_m and void_m:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            remediation=rule.remediation,
            details={
                "identity": id_m.group(0)[:40],
                "voiding": void_m.group(0)[:40],
            },
        )
    return None
