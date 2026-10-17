"""Lint规则集扩展——P161-P165 Prompt高级威胁防护

R75新增(Prompt高级威胁防护):
- P161: Prompt模板注入防护缺失
- P162: Prompt缓存投毒防护缺失
- P163: Prompt模型越狱防护缺失
- P164: Prompt指令提取防护缺失
- P165: Prompt侧信道泄露防护缺失

参考: OWASP LLM Top 10 LLM01/LLM05, garak越狱探测, promptfoo安全断言
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P161_P165: list[LintRule] = [
    LintRule(
        "P161",
        "Prompt模板注入防护缺失",
        "security",
        Severity.CRITICAL,
        "Prompt未声明模板注入防护(变量转义/沙箱渲染/指令隔离)",
        "声明模板注入防护: 用户变量{{input}}强制HTML/JS转义, 禁止原始渲染, 模板引擎沙箱模式",
        description_en="Prompt missing template injection protection declaration",
        remediation_en="Declare template injection protection: Force HTML/JS escaping on {{input}}, no raw rendering, sandbox template engine",
        family="template_injection",
    ),
    LintRule(
        "P162",
        "Prompt缓存投毒防护缺失",
        "security",
        Severity.HIGH,
        "Prompt未声明缓存投毒防护(缓存键验证/内容签名/过期策略)",
        "声明缓存投毒防护: 缓存键包含内容hash签名, TTL过期<24小时, 命中后异步验证内容一致性",
        description_en="Prompt missing cache poisoning protection declaration",
        remediation_en="Declare cache poisoning protection: Cache key includes content hash, TTL<24h, async validation on cache hit",
        family="cache_poisoning",
    ),
    LintRule(
        "P163",
        "Prompt模型越狱防护缺失",
        "security",
        Severity.CRITICAL,
        "Prompt未声明模型越狱防护(系统指令固化0/角色锚定/拒绝策略)",
        "声明越狱防护: 系统指令不可被用户覆盖, 角色锚定防止身份切换, 拒绝策略明确列出禁止行为",
        description_en="Prompt missing model jailbreak protection declaration",
        remediation_en="Declare jailbreak protection: System instructions cannot be overridden, role anchoring prevents identity switch, explicit deny list",
        family="jailbreak_protection",
    ),
    LintRule(
        "P164",
        "Prompt指令提取防护缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明指令提取防护(输出过滤/指令不可见/反提取措辞C)",
        "声明指令提取防护: 输出过滤禁止包含系统指令内容, 指令段对用户不可见, 反提取措辞防止指令泄露",
        description_en="Prompt missing instruction extraction protection declaration",
        remediation_en="Declare extraction protection: Output filter blocks system instructions, instructions invisible to user, anti-extraction phrasing",
        family="instruction_extraction",
    ),
    LintRule(
        "P165",
        "Prompt侧信道泄露防护缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明侧信道泄露防护(时间恒定/错误统一/日志脱敏)",
        "声明侧信道防护: 响应时间恒定(±50ms内), 错误消息统一格式, 日志禁止记录内部推理过程",
        description_en="Prompt missing side-channel leakage protection declaration",
        remediation_en="Declare side-channel protection: Constant response time(±50ms), unified error format, no internal reasoning in logs",
        family="side_channel",
    ),
]

for r in _RULES_P161_P165:
    _RULE_MAP[r.rule_id] = r

# R211校准: 原CTX泛词(裸变量/format/替换/拼接/格式化)与裸{{命中一切
# 模板填充类prompt(数据提取/邮件生成等{{var}}占位符场景),
# R210扩样暴露11/56误报。模板注入真实攻击面=用户变量进入渲染/插值
# 管道的组合(模板+渲染/变量), 收窄到管道语义。
_TMPL_INJECT_CTX = re.compile(
    r"(?:模板|template).{0,8}(?:渲染|render|注入|injection|引擎|engine|变量|variable)"
    r"|(?:渲染|render|插值|interpolat).{0,8}(?:变量|variable)"
    r"|(?:变量|variable).{0,8}(?:渲染|render|插值|interpolat|注入|injection)"
    r"|模板注入|template.{0,8}injection",
    re.IGNORECASE,
)

_TMPL_INJECT_DECL = re.compile(
    r"(?:转义|escap|沙箱|sandbox|隔离|isolat|禁止.*渲染|no.*render|原始.*渲染|raw.*render|注入.*防护|injection.*protect|模板.*安全|template.*safe|净化|sanitiz|过滤.*变量|filter.*variable)",
    re.IGNORECASE,
)

# R250-P2-26: stor/hit 裸子串命中 story/history/white(NotInject 27 命中全为误报) —
# stor→storage/storing + \bstore\w*(真存储语义), hit→\bhit\w*(词边界)
_CACHE_POISON_CTX = re.compile(
    r"(?:缓存|cache|存储|stor(?:age|ing)|\bstore\w*|Redis|Memcached|CDN|命中|\bhit\w*|过期|TTL|失效|invalidat|预热|warm.?up)",
    re.IGNORECASE,
)

_CACHE_POISON_DECL = re.compile(
    r"(?:缓存.*投毒|cache.*poison|签名|sign|hash|内容.*验证|content.*validat|键.*验证|key.*validat|TTL|过期|过期.*策略|expir|一致性|consistency|防篡改|tamper.*proof)",
    re.IGNORECASE,
)

# R168校准: 需对抗性/劫持语义 — 裸"系统/角色/指令/禁止"过宽(任何带角色的Prompt都误触发CRITICAL)
# R251-P2-26(C): 三分判定 — ①直接越狱词 ②DAN人格(旧裸 DAN+IGNORECASE 误中
# "danger"/"damage" 子串, 改词边界) ③roleplay 动词 AND 约束解除语言共现
# (Agent-Threat-Rule ATR-2026-00229/00234: 角色设定且显式解除约束才报; 单独
# pretend/roleplay=正当创作/游戏语境, 其 false_positives 字段明列)。
_JAILBREAK_CTX = re.compile(
    r"(?:越狱|jailbreak|绕过|bypass|忽略.{0,6}(?:指令|instruction)|ignore.{0,6}instruction|覆盖.{0,6}(?:指令|规则|instruction)|override|身份切换|不设限|无限制|unrestricted"
    # R257-T6: forget 指令重置族 — deepset 16 条真实 OOD 变体(forget everything
    # before that/above/we/I...)=经典越狱外壳; 负向断言排除 "forget ... about"
    # (GDPR 隐私复位合法请求, 见 r257_tn01_privacy_reset 探针护栏)。
    # 零碰撞实证: golden 232 / NotInject 339 / 干净 60 均 0(ODT-1 过防御约束)。
    r"|forget\s+(?:all|everything)(?!\s+about\b))",
    re.IGNORECASE,
)
_JAILBREAK_DAN = re.compile(r"\bDAN\b", re.IGNORECASE)
# R251-P2-26(C-fix): DAO 排除双序 — "DAN (Data Access Object)" 与更常见的
# "Data Access Object (DAN)"(全称+缩写) 都排除; 单序版漏掉后者, Java DAO
# 设计讨论被 DAN 人格分支误报
_DAN_DAO_EXCLUDE = re.compile(
    r"DAN\s*[(（]\s*Data\s+Access\s+Object|Data\s+Access\s+Object\s*[(（]\s*DAN",
    re.IGNORECASE,
)
_ROLEPLAY_VERB = re.compile(r"(?:假装|pretend|扮演|impersonat|角色扮演|roleplay|role[ ]?play)", re.IGNORECASE)
_CONSTRAINT_REMOVE = re.compile(
    r"(?:no\s+restrict|without\s+restrict|freed?\s+from\s+(?:all\s+)?rules?|free\s+from\s+(?:all\s+)?rules?"
    r"|unrestricted|no\s+rules|不受.{0,6}(?:规则|限制|约束)|不受限制|忽略.{0,6}(?:所有|全部).{0,6}规则"
    r"|ignore\s+(?:all\s+)?rules|无任何限制|没有.{0,4}(?:限制|约束))",
    re.IGNORECASE,
)

_JAILBREAK_DECL = re.compile(
    # R180: 防御性禁止声明("不得建议绕过/不得提供攻击方法")本身即越狱防护
    r"(?:越狱.*防护|jailbreak.*protect|固化|anchor|锚定|锁定|lock|不可.*覆盖|cannot.*override|不可.*修改|immutable|拒绝.*策略|deny.*policy|禁止.*列表|deny.*list|角色.*固定|role.*fix|身份.*不可变|identity.*immutable|不得.{0,6}(?:建议|提供|帮助|协助).{0,12}(?:绕过|攻击|越狱|漏洞))",
    re.IGNORECASE,
)

# R206校准: 移除泛词(系统/输出/响应/显示/打印/重复/系统指令/提取/指令/instruct/output/response/
# show/print/repeat/restate) — 干净prompt的"输出格式/系统提示"即误触发(100%误报率),
# 保留"泄露/越狱/复述指令/忽略指令"等攻击语义词
# R315-P2-26: 越狱|jailbreak 分支移除 — golden 该分支零 TP 支撑（唯一 TP 经
# 泄露触发）, NotInject 6 条真实 FP 全为越狱科普/手机越狱/游戏越狱良性语境;
# 越狱指令攻击面归 P163 辖区（R257 已定性, 双辖区重复计分）, P164 去重。
_EXTRACT_CTX = re.compile(
    r"(?:泄露|leak|泄露.*指令|复述.*指令|忽略.*指令|忽略.*系统提示|绕过.*指令|prompt.?injection|提示词注入|exfiltrat|dump.*instruction|extract.*instruction|extract.*prompt)",
    re.IGNORECASE,
)

_EXTRACT_DECL = re.compile(
    r"(?:提取.*防护|extraction.*protect|指令.*不可见|instruct.*invisible|输出.*过滤|output.*filter|反提取|anti.?extract|禁止.*泄露|prohibit.*leak|指令.*保护|instruct.*protect|系统.*保护|system.*protect)",
    re.IGNORECASE,
)

_SIDE_CHANNEL_CTX = re.compile(
    r"(?:时间|time|延迟|delay|响应|response|错误|error|异常|exception|日志|log|推理|reason|思考|think|过程|process|内部|internal|状态|state|侧信道|side.?channel|计时|timing)",
    re.IGNORECASE,
)

_SIDE_CHANNEL_DECL = re.compile(
    r"(?:侧信道|side.?channel|时间.*恒定|constant.*time|统一.*错误|unified.*error|错误.*统一|error.*uniform|日志.*脱敏|log.*mask|禁止.*推理|prohibit.*reason|禁止.*思考|prohibit.*think|恒定.*延迟|constant.*delay|±\d+ms|正则.*拒绝|regex.*reject)",
    re.IGNORECASE,
)

# R210: 泄露风险面语义 — 侧信道规则的真实触发面是"信息可能被推断/泄露"。
# 收紧: 裸"推断"是排障prompt常见词(基于日志推断原因), 不构成侧信道;
# 仅"时间+推断/攻击/探测"组合(时序侧信道)或明确泄露/攻击词才触发。
_SIDE_CHANNEL_LEAK = re.compile(
    r"(?:泄露|leak|暴露|expos|时间.{0,10}(?:推断|攻击|探测)|(?:推断|攻击|探测).{0,10}时间|攻击|attack|probe)",
    re.IGNORECASE,
)


def check_p161(text: str) -> Finding | None:
    rule = _RULE_MAP["P161"]
    if not _TMPL_INJECT_CTX.search(text):
        return None
    # R213-P0-1: 否定盲区 — "无转义/不沙箱"是放弃防护的声明, 剥离后不再当DECL放行
    from ai_prompt_toolkit.linter.rules import strip_negated_decl

    if _TMPL_INJECT_DECL.search(strip_negated_decl(text, _TMPL_INJECT_DECL)):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p162(text: str) -> Finding | None:
    rule = _RULE_MAP["P162"]
    if not _CACHE_POISON_CTX.search(text):
        return None
    if _CACHE_POISON_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p163(text: str) -> Finding | None:
    rule = _RULE_MAP["P163"]
    # R251-P2-26(C): 三分判定 — 直接越狱词 / DAN人格(排除DAO语境) / roleplay∧约束解除共现
    dan_hit = _JAILBREAK_DAN.search(text) and not _DAN_DAO_EXCLUDE.search(text)
    roleplay_hit = _ROLEPLAY_VERB.search(text) and _CONSTRAINT_REMOVE.search(text)
    if not (_JAILBREAK_CTX.search(text) or dan_hit or roleplay_hit):
        return None
    if _JAILBREAK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p164(text: str) -> Finding | None:
    rule = _RULE_MAP["P164"]
    if not _EXTRACT_CTX.search(text):
        return None
    if _EXTRACT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p165(text: str) -> Finding | None:
    rule = _RULE_MAP["P165"]
    if not _SIDE_CHANNEL_CTX.search(text):
        return None
    # R210: 侧信道防护仅当prompt真实涉及泄露风险面(泄露/推断/攻击语义) —
    # 原CTX含"时间/错误/日志"泛词, 任何含错误处理的prompt恒触发(R210新样本暴露12/56)
    if not _SIDE_CHANNEL_LEAK.search(text):
        return None
    if _SIDE_CHANNEL_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
