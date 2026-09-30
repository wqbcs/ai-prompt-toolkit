"""Lint规则集扩展——P151-P155 Prompt安全编码规范

R73新增(Prompt安全编码实践):
- P151: Prompt输入边界校验缺失
- P152: Prompt输出编码转义缺失
- P153: Prompt速率限制缺失
- P154: Prompt审计日志缺失
- P155: Prompt降级策略缺失

参考: OWASP LLM Top 10 LLM05/LLM06, promptfoo安全断言
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P151_P155: list[LintRule] = [
    LintRule(
        "P151",
        "Prompt输入边界校验缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明输入边界校验(长度/格式/范围/类型校验)",
        "声明输入校验: 输入长度<=2000字符, 仅允许中英文和数字, 禁止SQL/HTML特殊字符",
        description_en="Prompt missing input boundary validation declaration",
        remediation_en="Declare input validation: Input length<=2000 chars, only CJK/alphanum allowed",
        family="input_validation",
    ),
    LintRule(
        "P152",
        "Prompt输出编码转义缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明输出编码转义(防止XSS/注入二次攻击)",
        "声明输出转义: 输出内容经过HTML实体编码, 禁止直接渲染原始HTML/JS",
        description_en="Prompt missing output encoding/escaping declaration",
        remediation_en="Declare output escaping: Output HTML entity encoded, no raw HTML/JS rendering",
        family="output_escaping",
    ),
    LintRule(
        "P153",
        "Prompt速率限制缺失",
        "performance",
        Severity.MEDIUM,
        "Prompt未声明调用频率/速率限制(防止资源耗尽)",
        "声明速率限制: 每用户每分钟最多10次调用, 单次Token上限8192",
        description_en="Prompt missing rate limiting declaration",
        remediation_en="Declare rate limit: Max 10 calls/min per user, 8192 tokens per request",
        family="rate_limiting",
    ),
    LintRule(
        "P154",
        "Prompt审计日志缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明关键操作审计追踪(调用记录/结果日志/异常告警)",
        "声明审计日志: 记录每次调用的输入摘要/输出摘要/耗时/异常, 保留90天",
        description_en="Prompt missing audit logging declaration",
        remediation_en="Declare audit logging: Log input/output per call, retain 90 days",
        family="audit_logging",
    ),
    LintRule(
        "P155",
        "Prompt降级策略缺失",
        "structure",
        Severity.MEDIUM,
        "Prompt未声明异常降级策略(超时降级/模型切换/缓存回退)",
        "声明降级策略: 超时5秒返回缓存结果, 主模型不可用时切换备用模型",
        description_en="Prompt missing degradation/fallback strategy declaration",
        remediation_en="Declare fallback: Timeout 5s returns cache, switch to backup model on failure",
        family="fallback_strategy",
    ),
]

for r in _RULES_P151_P155:
    _RULE_MAP[r.rule_id] = r

_API_CTX = re.compile(
    r"(?:API|api|接口|endpoint|服务|service|调用|call|请求|request|响应|response|Agent|代理|智能体)", re.IGNORECASE
)

_INPUT_VAL = re.compile(
    r"(?:输入.*校验|input.*validat|边界.*检查|boundary.*check|长度.*限制|length.*limit|格式.*验证|format.*validat|类型.*检查|type.*check|白名单|whitelist|黑名单|blacklist|正则|regex|净化|sanitiz|过滤|filter)",
    re.IGNORECASE,
)

_OUTPUT_ESC = re.compile(
    r"(?:输出.*转义|output.*escap|编码|encod|HTML.*实体|HTML.*entity|XSS.*防护|XSS.*prevent|净化|sanitiz|禁止.*渲染|no.*render|安全.*输出|safe.*output)",
    re.IGNORECASE,
)

_RATE_LIM = re.compile(
    r"(?:速率|rate|频率|frequency|限流|throttl|QPS|每.*分钟|per.*min|并发|concurrent|限|limit|上限|cap|Token.*上限|token.*limit)",
    re.IGNORECASE,
)

_AUDIT = re.compile(
    r"(?:审计|audit|日志|log|追踪|trac|记录|record|监控|monitor|告警|alert|保留.*天|retain.*day)", re.IGNORECASE
)

_FALLBACK = re.compile(
    r"(?:降级|degrad|回退|fallback|备用|backup|缓存.*回退|cache.*fallback|超时.*处理|timeout.*handle|模型.*切换|model.*switch|重试|retry)",
    re.IGNORECASE,
)


# R211校准: 输入校验/输出转义/速率限制/审计/降级五条"缺失声明"规则仅在
# 生产服务面才有运维语义 — 原_API_CTX泛词(服务/调用/请求/call/request)
# 命中几乎所有prompt(角色名"XX服务"即触发), R210扩样暴露48/56误报。
# 沿用R207 P181先例(版本声明仅对生产prompt强制): 需显式生产语境
# (生产/production/部署/上线/发布), 本地草稿/文档类prompt不强制。
# 否定语境排除("不直接修改生产集群"=安全约束声明, 非生产部署)。
_PROD_CTX = re.compile(
    r"(?:生产(?!库|集群)|production|部署(?!失败)|deploy(?!\s+fail)|上线|正式环境|(?<![A-Za-z0-9_/.-])prod(?![A-Za-z0-9_-])|发布(?!说明|notes|检查单|日期|前))",
    re.IGNORECASE,
)
_PROD_NEGATION = re.compile(r"(?:不|禁止|避免|勿|无需|no|without|avoid)\s*\S{0,4}$", re.IGNORECASE)


def _has_prod_ctx(text: str) -> bool:
    for m in _PROD_CTX.finditer(text):
        if _PROD_NEGATION.search(text[max(0, m.start() - 8) : m.start()]):
            continue
        return True
    return False


def check_p151(text: str) -> Finding | None:
    rule = _RULE_MAP["P151"]
    if not _API_CTX.search(text):
        return None
    if not _has_prod_ctx(text):
        return None
    if _INPUT_VAL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p152(text: str) -> Finding | None:
    rule = _RULE_MAP["P152"]
    if not _API_CTX.search(text):
        return None
    if not _has_prod_ctx(text):
        return None
    if _OUTPUT_ESC.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p153(text: str) -> Finding | None:
    rule = _RULE_MAP["P153"]
    if not _API_CTX.search(text):
        return None
    if not _has_prod_ctx(text):
        return None
    if _RATE_LIM.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p154(text: str) -> Finding | None:
    rule = _RULE_MAP["P154"]
    if not _API_CTX.search(text):
        return None
    if not _has_prod_ctx(text):
        return None
    if _AUDIT.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p155(text: str) -> Finding | None:
    rule = _RULE_MAP["P155"]
    if not _API_CTX.search(text):
        return None
    if not _has_prod_ctx(text):
        return None
    if _FALLBACK.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
