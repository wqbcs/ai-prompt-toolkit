"""P191-P195 AI Agent安全Lint规则

AI Agent安全最佳实践(参考garak Agent probes + OWASP LLM Agent Top10):
- P191: Agent权限边界未声明(Agent可执行操作需显式约束)
- P192: Agent工具调用约束缺失(工具调用需参数验证+频率限制)
- P193: Agent思维链泄露风险(CoT推理过程可能暴露给用户)
- P194: 多Agent协调安全缺失(多Agent通信需加密+认证)
- P195: Agent记忆隔离不足(长期记忆需隔离+脱敏)

覆盖OWASP LLM06(Excessive Agency), LLM02(Sensitive Info), LLM09(Overreliance)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P191_P195 = [
    LintRule(
        "P191",
        "Agent权限边界未声明",
        "agent_security",
        Severity.HIGH,
        "AI Agent缺少权限边界声明, 可能执行超出预期的操作",
        "声明Agent权限边界: 允许的操作列表+禁止的操作列表, 如 permissions: [read, search], denied: [write, delete, exec]",
        description_en="AI Agent lacks permission boundary, may execute unexpected operations",
        remediation_en="Declare Agent permissions: allowed+denied operations, e.g. permissions: [read, search], denied: [write, delete, exec]",
        family="agent_permission",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P192",
        "Agent工具调用约束缺失",
        "agent_security",
        Severity.HIGH,
        "AI Agent工具调用缺少约束(参数验证/频率限制/超时), 可能被滥用",
        "声明工具调用约束: 参数类型验证+调用频率限制(如10次/分钟)+超时(如30s), 如 tool_constraints: {max_calls: 10, timeout: 30}",
        description_en="AI Agent tool calls lack constraints (validation/rate-limit/timeout), may be abused",
        remediation_en="Declare tool constraints: param validation+rate limit+timeout, e.g. tool_constraints: {max_calls: 10, timeout: 30}",
        family="agent_tool_constraint",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P193",
        "Agent思维链泄露风险",
        "agent_security",
        Severity.MEDIUM,
        "Agent思维链(CoT)推理过程可能泄露给用户, 暴露内部逻辑和敏感信息",
        "隔离思维链: CoT推理对用户不可见, 仅返回最终结果, 如 cot_visibility: internal_only",
        description_en="Agent CoT reasoning may leak to user, exposing internal logic and sensitive info",
        remediation_en="Isolate CoT: reasoning invisible to user, return only final result, e.g. cot_visibility: internal_only",
        family="agent_cot_isolation",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P194",
        "多Agent协调安全缺失",
        "agent_security",
        Severity.HIGH,
        "多Agent协调通信缺少安全机制(加密/认证/消息验证), 可能被中间人攻击",
        "声明协调安全: Agent间通信加密(TLS)+身份认证+消息签名, 如 coordination: {encrypt: TLS, auth: token, sign: hmac}",
        description_en="Multi-Agent coordination lacks security (encryption/auth/verification), vulnerable to MITM",
        remediation_en="Declare coordination security: TLS encryption+token auth+message signing, e.g. coordination: {encrypt: TLS, auth: token}",
        family="agent_coordination",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P195",
        "Agent记忆隔离不足",
        "agent_security",
        Severity.MEDIUM,
        "Agent长期记忆未隔离脱敏, 可能跨用户泄露或累积敏感信息",
        "声明记忆隔离: 用户记忆沙箱隔离+PII自动脱敏+TTL过期策略, 如 memory: {sandbox: per_user, pii_mask: true, ttl: 7d}",
        description_en="Agent long-term memory not isolated, may leak cross-user or accumulate sensitive info",
        remediation_en="Declare memory isolation: per-user sandbox+PII masking+TTL expiry, e.g. memory: {sandbox: per_user, pii_mask: true, ttl: 7d}",
        family="agent_memory_isolation",
        owasp_refs=["LLM02"],
    ),
]

for r in _RULES_P191_P195:
    _RULE_MAP[r.rule_id] = r

_AGENT_PATTERN = re.compile(r"(?:Agent|agent|智能体|自主体|autonomous|agentic)", re.IGNORECASE)
_PERMISSION_PATTERN = re.compile(r"(?:权限|permission|允许|allowed|denied|禁止|capabilities|scope)", re.IGNORECASE)
_TOOL_PATTERN = re.compile(r"(?:工具|tool|function_call|调用|invoke|API_call)", re.IGNORECASE)
_TOOL_CONSTRAINT_PATTERN = re.compile(r"(?:约束|constraint|频率|rate.limit|超时|timeout|max_calls|限制)", re.IGNORECASE)
_COT_PATTERN = re.compile(r"(?:思维链|CoT|chain.of.thought|推理过程|reasoning|think.step|scratchpad)", re.IGNORECASE)
_COT_ISOLATED_PATTERN = re.compile(r"(?:内部|internal|不可见|hidden|隔离|isolate|不暴露|不显示)", re.IGNORECASE)
# 注: 不含裸"消息/message" — 该词常出现在"错误消息"等单Agent语境, 会造成误报
_MULTI_AGENT_PATTERN = re.compile(
    r"(?:多Agent|multi.agent|协调|coordination|通信|communicate|分布式|distributed)", re.IGNORECASE
)
_COORD_SECURE_PATTERN = re.compile(r"(?:加密|encrypt|TLS|认证|auth|token|签名|sign|hmac|安全通道)", re.IGNORECASE)
_MEMORY_PATTERN = re.compile(r"(?:记忆|memory|长期记忆|long.term|历史|history|上下文存储|context.store)", re.IGNORECASE)
_MEMORY_ISOLATED_PATTERN = re.compile(r"(?:隔离|sandbox|脱敏|mask|PII|TTL|过期|expire|per_user|沙箱)", re.IGNORECASE)


def check_p191(text: str) -> list[Finding]:
    findings = []
    has_agent = _AGENT_PATTERN.search(text)
    if has_agent and not _PERMISSION_PATTERN.search(text):
        findings.append(Finding("P191", Severity.HIGH, "AI Agent缺少权限边界声明", 1, 1))
    return findings


def check_p192(text: str) -> list[Finding]:
    findings = []
    has_tool = _TOOL_PATTERN.search(text) and _AGENT_PATTERN.search(text)
    if has_tool and not _TOOL_CONSTRAINT_PATTERN.search(text):
        findings.append(Finding("P192", Severity.HIGH, "Agent工具调用缺少约束", 1, 1))
    return findings


def check_p193(text: str) -> list[Finding]:
    findings = []
    has_cot = _COT_PATTERN.search(text)
    if has_cot and not _COT_ISOLATED_PATTERN.search(text):
        findings.append(Finding("P193", Severity.MEDIUM, "Agent思维链可能泄露给用户", 1, 1))
    return findings


def check_p194(text: str) -> list[Finding]:
    findings = []
    has_multi = _MULTI_AGENT_PATTERN.search(text)
    if has_multi and not _COORD_SECURE_PATTERN.search(text):
        findings.append(Finding("P194", Severity.HIGH, "多Agent协调缺少安全机制", 1, 1))
    return findings


def check_p195(text: str) -> list[Finding]:
    findings = []
    has_memory = _MEMORY_PATTERN.search(text)
    if has_memory and not _MEMORY_ISOLATED_PATTERN.search(text):
        findings.append(Finding("P195", Severity.MEDIUM, "Agent记忆未隔离脱敏", 1, 1))
    return findings
