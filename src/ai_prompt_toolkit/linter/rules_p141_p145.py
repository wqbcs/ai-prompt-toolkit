"""Lint规则集扩展——P141-P145 Agent/Tool-Use专项规则

R70新增(Agent与工具调用安全):
- P141: Agent目标声明缺失 — 检测Agent Prompt是否声明可执行操作的边界和目标约束
- P142: 工具调用权限越界 — 检测Agent Prompt的工具调用是否声明最小权限
- P143: Agent循环调用防护缺失 — 检测Agent Prompt是否声明最大迭代次数/递归深度限制
- P144: Agent上下文窗口管理缺失 — 检测Agent Prompt是否声明上下文窗口管理策略
- P145: 多Agent协作冲突防护缺失 — 检测多Agent Prompt是否声明协作协议/冲突解决/死锁防护

参考: OWASP Agent Security Guidelines, LangChain Agent Best Practices
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_RULES_P141_P145: list[LintRule] = [
    LintRule("P141", "Agent目标声明缺失", "structure", Severity.HIGH,
             "Agent Prompt未声明可执行操作的边界和目标约束(目标范围/禁止行为/退出条件)",
             "声明Agent目标: '你的目标是..., 禁止执行...操作, 当...条件满足时停止'",
             description_en="Agent Prompt missing goal declaration and operational boundary constraints",
             remediation_en="Declare Agent goal: 'Your goal is..., prohibited actions..., stop when...condition met'", family="agent_goal"),
    LintRule("P142", "工具调用权限越界", "security", Severity.HIGH,
             "Agent Prompt的工具调用未声明最小权限(可调API/可访问资源/权限范围)",
             "声明工具权限: '仅可调用...API, 仅可访问...资源, 禁止执行删除/修改操作, 遵循最小权限原则'",
             description_en="Agent Prompt tool calls missing minimum privilege declaration",
             remediation_en="Declare tool privileges: 'Only call...API, only access...resources, prohibit delete/modify operations, follow least privilege principle'", family="tool_permission"),
    LintRule("P143", "Agent循环调用防护缺失", "security", Severity.HIGH,
             "Agent Prompt未声明最大迭代次数或递归深度限制(防止无限循环/递归调用)",
             "声明循环防护: '最大迭代次数为10次, 递归深度不超过3层, 超过限制时输出当前结果并停止'",
             description_en="Agent Prompt missing max iteration/recursive depth limit (prevents infinite loops)",
             remediation_en="Declare loop guard: 'Max 10 iterations, max 3 recursive depth, output current result and stop when limit exceeded'", family="loop_guard"),
    LintRule("P144", "Agent上下文窗口管理缺失", "performance", Severity.MEDIUM,
             "Agent Prompt未声明上下文窗口管理策略(截断/摘要/遗忘/滑动窗口)",
             "声明上下文管理: '上下文超过8K Token时采用滑动窗口策略, 保留最近5轮对话, 对历史对话进行摘要压缩'",
             description_en="Agent Prompt missing context window management strategy (truncation/summarization/sliding window)",
             remediation_en="Declare context management: 'Use sliding window when context exceeds 8K tokens, keep last 5 turns, summarize older turns'", family="context_management"),
    LintRule("P145", "多Agent协作冲突防护缺失", "security", Severity.MEDIUM,
             "多Agent Prompt未声明协作协议/冲突解决/死锁防护",
             "声明协作防护: 'Agent间通过...协议通信, 冲突时由协调者裁决, 设置超时机制防止死锁, 资源竞争时排队执行'",
             description_en="Multi-Agent Prompt missing collaboration protocol/conflict resolution/deadlock prevention",
             remediation_en="Declare collaboration: 'Agents communicate via...protocol, coordinator arbitrates conflicts, timeout prevents deadlock, queue for resource contention'", family="multi_agent_conflict"),
]

for r in _RULES_P141_P145:
    _RULE_MAP[r.rule_id] = r


_AGENT_CTX = re.compile(
    r'(?:Agent|代理|智能体|autonomous|tool.?use|工具.?调用|function.?call|ReAct|react|reasoning.*act|plan.*execute|规划.*执行|multi.?agent|多.*代理|多.*智能体|协作.*agent|agentic)',
    re.IGNORECASE
)

_GOAL_DECL = re.compile(
    r'(?:目标|goal|目的|objective|任务.*范围|task.*scope|边界|boundary|约束|constraint|禁止.*执行|prohibit|不允许|not.*allow|退出.*条件|exit.*condition|停止.*条件|stop.*condition)',
    re.IGNORECASE
)


def check_p141(text: str) -> Finding | None:
    rule = _RULE_MAP["P141"]
    if not _AGENT_CTX.search(text):
        return None
    if _GOAL_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_TOOL_PERM_DECL = re.compile(
    r'(?:权限|permission|最小.*权限|least.*privilege|仅可|only.*allow|可调.*API|callable.*API|可访问|accessib|禁止.*删除|prohibit.*delete|禁止.*修改|prohibit.*modif|工具.*范围|tool.*scope|API.*白名单|API.*whitelist)',
    re.IGNORECASE
)


def check_p142(text: str) -> Finding | None:
    rule = _RULE_MAP["P142"]
    _TOOL_CTX = re.compile(
        r'(?:工具|tool|API|调用|call|function|函数|接口|endpoint|插件|plugin|执行.*操作|execute.*operation)',
        re.IGNORECASE
    )
    if not _AGENT_CTX.search(text):
        return None
    if not _TOOL_CTX.search(text):
        return None
    if _TOOL_PERM_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_LOOP_GUARD_DECL = re.compile(
    r'(?:最大.*迭代|max.*iterat|迭代.*次数|iteration.*count|递归.*深度|recursive.*depth|循环.*限制|loop.*limit|超过.*限制|exceed.*limit|超时|timeout|重试.*次数|retry.*count|最大.*步数|max.*step|步数.*限制|step.*limit)',
    re.IGNORECASE
)


def check_p143(text: str) -> Finding | None:
    rule = _RULE_MAP["P143"]
    if not _AGENT_CTX.search(text):
        return None
    if _LOOP_GUARD_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_CONTEXT_MGMT_DECL = re.compile(
    r'(?:上下文.*管理|context.*manage|截断|truncat|摘要|summariz|压缩|compress|滑动.*窗口|sliding.*window|遗忘|forget|丢弃|discard|保留.*最近|keep.*recent|Token.*上限|token.*limit|上下文.*窗口|context.*window|历史.*压缩|history.*compress)',
    re.IGNORECASE
)


def check_p144(text: str) -> Finding | None:
    rule = _RULE_MAP["P144"]
    if not _AGENT_CTX.search(text):
        return None
    if _CONTEXT_MGMT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_MULTI_AGENT_CTX = re.compile(
    r'(?:multi.?agent|多.*代理|多.*智能体|协作.*agent|agent.*协作|多个.*agent|agent.*间|agent间|协作.*协议|collaborat.*protocol|协调|coordinat|分布式.*agent|distribut.*agent|团队|team)',
    re.IGNORECASE
)

_CONFLICT_DECL = re.compile(
    r'(?:冲突|conflict|冲突.*解决|conflict.*resolut|死锁|deadlock|协作.*协议|collaborat.*protocol|超时.*机制|timeout.*mechanism|排队|queue|资源.*竞争|resource.*content|裁决|arbitrat|优先级|priority|共识|consensus)',
    re.IGNORECASE
)


def check_p145(text: str) -> Finding | None:
    rule = _RULE_MAP["P145"]
    if not _MULTI_AGENT_CTX.search(text):
        return None
    if _CONFLICT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )
