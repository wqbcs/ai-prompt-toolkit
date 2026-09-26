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

_TMPL_INJECT_CTX = re.compile(
    r"(?:模板|template|变量|variable|渲染|render|插值|interpolat|Mustache|Jinja|Handlebars|\{\{|\}\}|format|格式化|替换|substitut|拼接|concat)",
    re.IGNORECASE,
)

_TMPL_INJECT_DECL = re.compile(
    r"(?:转义|escap|沙箱|sandbox|隔离|isolat|禁止.*渲染|no.*render|原始.*渲染|raw.*render|注入.*防护|injection.*protect|模板.*安全|template.*safe|净化|sanitiz|过滤.*变量|filter.*variable)",
    re.IGNORECASE,
)

_CACHE_POISON_CTX = re.compile(
    r"(?:缓存|cache|存储|stor|Redis|Memcached|CDN|命中|hit|过期|TTL|失效|invalidat|预热|warm.?up)", re.IGNORECASE
)

_CACHE_POISON_DECL = re.compile(
    r"(?:缓存.*投毒|cache.*poison|签名|sign|hash|内容.*验证|content.*validat|键.*验证|key.*validat|TTL|过期|过期.*策略|expir|一致性|consistency|防篡改|tamper.*proof)",
    re.IGNORECASE,
)

# R168校准: 需对抗性/劫持语义 — 裸"系统/角色/指令/禁止"过宽(任何带角色的Prompt都误触发CRITICAL)
_JAILBREAK_CTX = re.compile(
    r"(?:越狱|jailbreak|DAN|绕过|bypass|忽略.{0,6}(?:指令|instruction)|ignore.{0,6}instruction|覆盖.{0,6}(?:指令|规则|instruction)|override|假装|pretend|扮演|impersonat|角色扮演|身份切换|不设限|无限制|unrestricted)",
    re.IGNORECASE,
)

_JAILBREAK_DECL = re.compile(
    r"(?:越狱.*防护|jailbreak.*protect|固化|anchor|锚定|锁定|lock|不可.*覆盖|cannot.*override|不可.*修改|immutable|拒绝.*策略|deny.*policy|禁止.*列表|deny.*list|角色.*固定|role.*fix|身份.*不可变|identity.*immutable)",
    re.IGNORECASE,
)

_EXTRACT_CTX = re.compile(
    r"(?:系统|system|指令|instruct|:规则|:rule|Prompt|提示词|提取|extract|泄露|leak|输出|output|响应|response|显示|show|打印|print|重复|repeat|复述|restate)",
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


def check_p161(text: str) -> Finding | None:
    rule = _RULE_MAP["P161"]
    if not _TMPL_INJECT_CTX.search(text):
        return None
    if _TMPL_INJECT_DECL.search(text):
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
    if not _JAILBREAK_CTX.search(text):
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
    if _SIDE_CHANNEL_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
