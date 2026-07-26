"""Lint 规则集扩展——P041-P050 lintlang参考检测器 + 中文特有规则 (R23新增)。

参考项目:
- lintlang (https://github.com/hermes-labs-ai/lintlang) 的7大检测器 H1-H7
- 中文Prompt工程最佳实践
"""
from __future__ import annotations

import re
from typing import Any, Callable

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_H1_AMBIGUOUS_TOOL_PATTERNS = [
    re.compile(r"(?:调用|使用|执行|call|use|invoke|execute)\s*(?:工具|函数|API|接口|tool|function|api)\s*[:：]?\s*.{0,20}$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:可用|可用到|available)\s*(?:工具|函数|方法|tool|function|method)\s*[:：]", re.IGNORECASE),
]

_H1_VAGUE_DESC_PATTERNS = [
    re.compile(r"(?:处理|操作|执行|完成|handle|process|do|perform)\s*(?:数据|信息|内容|data|info|content)", re.IGNORECASE),
]

_H2_CONSTRAINT_SCAFFOLD_PATTERNS = [
    re.compile(r"(?:当|如果|when|if)\s*.*(?:发生|出现|遇到|occur|happen|encounter|无结果|不可用|失败|fail|unavailable|empty)", re.IGNORECASE),
    re.compile(r"(?:边界|限制|约束|条件|boundary|limit|constraint|condition)", re.IGNORECASE),
    re.compile(r"(?:否则|else|otherwise|如果不|if not)", re.IGNORECASE),
    re.compile(r"(?:当|如果|when|if)\s*.+?(?:时|的话|，)", re.IGNORECASE),
]

_H3_SCHEMA_PATTERNS = [
    re.compile(r"(?:参数|入参|parameter|arg|argument)\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:类型|type)\s*[:：]\s*(?:string|number|integer|boolean|array|object|str|int|float|bool|list|dict)", re.IGNORECASE),
    re.compile(r"(?:返回|return|响应|response)\s*[:：]", re.IGNORECASE),
]

_H3_INTENT_PATTERNS = [
    re.compile(r"(?:目的|意图|目标|purpose|intent|goal|objective)\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:用于|用来|use\s+for|used\s+to)", re.IGNORECASE),
]

_H4_CONTEXT_LEAK_PATTERNS = [
    re.compile(r"(?:上下文|context|会话|conversation|历史|history)", re.IGNORECASE),
    re.compile(r"(?:传递|发送|共享|pass|send|share|forward)", re.IGNORECASE),
]

_H4_BOUNDARY_PATTERNS = [
    re.compile(r"(?:隔离|隔离区|isolation|sandbox|沙箱|沙盒)", re.IGNORECASE),
    re.compile(r"(?:禁止|不得|不允许|forbidden|prohibited|not\s+allowed)\s*(?:传递|泄露|共享|pass|leak|share)", re.IGNORECASE),
    re.compile(r"(?:脱敏|遮蔽|匿名|mask|redact|anonymize|sanitize)", re.IGNORECASE),
]

_H5_IMPLICIT_PATTERNS = [
    re.compile(r"(?:隐含|默认|理所当然|implicitly|by\s+default|understood)", re.IGNORECASE),
    re.compile(r"(?:假设|假定|suppose|assume|presume)", re.IGNORECASE),
]

_H5_EXPLICIT_PATTERNS = [
    re.compile(r"(?:明确|显式|务必|必须|务必|explicitly|explicit|must|shall|请务必)", re.IGNORECASE),
    re.compile(r"(?:规则|规范|声明|rule|specification|declaration|statement)\s*[:：]", re.IGNORECASE),
]

_H6_TEMPLATE_VAR_PATTERNS = [
    re.compile(r"\{\{[^}]*\}\}"),
    re.compile(r"\$\{[^}]*\}"),
    re.compile(r"<%[^%]*%>"),
    re.compile(r"\{%[^%]*%\}"),
]

_H6_FORMAT_SPEC_PATTERNS = [
    re.compile(r"(?:格式|format|模板|template)\s*[:：]", re.IGNORECASE),
]

_H7_ROLE_PATTERNS = [
    re.compile(r"(?:你(?:是一?(?:个|名|位))?(?:是|作为|扮演))\s*.{1,}", re.UNICODE),
    re.compile(r"(?:role|角色|身份)\s*[:：]\s*.{2,}", re.IGNORECASE),
    re.compile(r"(?:作为|act\s+as|you\s+are)\s+.{2,}", re.IGNORECASE),
]

_H7_MULTI_ROLE_CONFLICT_PATTERNS = [
    re.compile(r"(?:同时|兼具|既是.*又是|both.*and|not\s+only.*but\s+also)", re.IGNORECASE),
]

_ZH_CN_PUNCTUATION_PATTERNS = [
    re.compile(r"[，。！？；：""''（）【】《》]"),
]

_ZH_CN_MIXED_PATTERNS = [
    re.compile(r"[\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u4e00-\u9fff]"),
]

_ZH_CN_REDUNDANT_PATTERNS = [
    re.compile(r"的了"),
    re.compile(r"的话的话"),
    re.compile(r"请请"),
]

_ZH_CN_HONORIFIC_PATTERNS = [
    re.compile(r"您您"),
]

_TOKEN_ESTIMATE_RATIO = 1.5
_TOKEN_WARNING_THRESHOLD = 4000
_TOKEN_CRITICAL_THRESHOLD = 8000

_AGENT_TOOL_DECL_PATTERNS = [
    re.compile(r"(?:工具|函数|API|接口|tool|function|api)\s*(?:列表|清单|定义|声明|list|definition|declaration)\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:可用|available)\s*(?:工具|函数|tool|function)", re.IGNORECASE),
]


_AGENT_RULES_V2: list[LintRule] = [
    LintRule("P041", "工具描述模糊性(H1)", "agent", Severity.HIGH,
             "Agent型Prompt中工具/函数描述模糊或过于简短，模型可能无法正确选择和调用",
             "为每个工具提供清晰的描述: 功能、参数、返回值、使用场景、注意事项",
             description_en="Agent Prompt has vague or overly brief tool/function descriptions, model may not select and call correctly",
             remediation_en="Provide clear descriptions for each tool: functionality, parameters, return values, use cases, caveats", family="agent_tool"),
    LintRule("P042", "缺失约束脚手架(H2)", "agent", Severity.HIGH,
             "Agent型Prompt缺少条件分支和边界约束脚手架，模型在异常情况下行为不可预测",
             "添加约束脚手架: 条件分支(if/when/otherwise)、边界条件、异常处理流程",
             description_en="Agent Prompt lacks conditional branching and boundary constraint scaffolding, model behavior unpredictable in edge cases",
             remediation_en="Add constraint scaffolding: conditional branches (if/when/otherwise), boundary conditions, exception handling flow", family="agent_scaffold"),
    LintRule("P043", "Schema-Intent不匹配(H3)", "agent", Severity.MEDIUM,
             "Agent型Prompt中工具参数Schema与功能意图描述不匹配",
             "确保参数类型/名称与工具功能意图一致，补充参数说明和意图声明",
             description_en="Agent Prompt tool parameter Schema does not match functional intent description",
             remediation_en="Ensure parameter types/names align with tool functional intent, add parameter descriptions and intent declarations", family="agent_schema"),
    LintRule("P044", "上下文边界侵蚀(H4)", "security", Severity.HIGH,
             "Agent型Prompt中上下文传递缺乏边界约束，可能导致敏感信息泄露",
             "添加上下文隔离策略: 禁止传递敏感字段、脱敏规则、沙箱隔离机制",
             description_en="Agent Prompt context passing lacks boundary constraints, may cause sensitive information leakage",
             remediation_en="Add context isolation strategy: prohibit passing sensitive fields, data masking rules, sandbox isolation mechanism", family="boundary_erosion"),
    LintRule("P045", "隐式指令失败(H5)", "quality", Severity.MEDIUM,
             "Prompt中存在隐含但未明确表达的期望，模型可能无法正确理解",
             "将隐式期望转为显式声明: 使用'必须'/'务必'代替默认假设，明确所有边界条件",
             description_en="Prompt contains implicit but unexpressed expectations, model may not understand correctly",
             remediation_en="Convert implicit expectations to explicit declarations: use 'must'/'shall' instead of default assumptions, clarify all boundary conditions", family="implicit_instruction"),
    LintRule("P046", "模板格式契约违反(H6)", "structure", Severity.MEDIUM,
             "Prompt中模板变量使用与格式规范不一致",
             "统一模板变量语法、声明格式规范、确保变量名与格式说明一致",
             description_en="Prompt template variable usage is inconsistent with format specification",
             remediation_en="Unify template variable syntax, declare format specification, ensure variable names match format description", family="template_contract"),
    LintRule("P047", "角色混淆(H7)", "quality", Severity.HIGH,
             "多角色Prompt中角色定义存在冲突或重叠，模型行为边界不清晰",
             "明确每个角色的职责边界: 使用分隔符区分角色、避免角色功能重叠、定义角色间交互协议",
             description_en="Multi-role Prompt has conflicting or overlapping role definitions, model behavior boundaries unclear",
             remediation_en="Clarify each role's responsibility boundary: use separators to distinguish roles, avoid role overlap, define inter-role interaction protocol", family="role_confusion"),
]

_ZH_CN_RULES: list[LintRule] = [
    LintRule("P048", "中文标点混用", "quality", Severity.LOW,
             "Prompt中存在中英文标点混用，可能导致模型理解偏差",
             "统一使用中文标点符号(，。！？)或英文标点，避免中英混用",
             description_en="Prompt mixes Chinese and English punctuation, may cause model comprehension deviation",
             remediation_en="Use consistent Chinese punctuation (，。！？) or English punctuation, avoid mixing", family="punctuation_norm"),
    LintRule("P049", "Token消耗预警", "performance", Severity.MEDIUM,
             "Prompt预计Token消耗超过阈值，可能导致成本失控或截断",
             "精简Prompt内容、拆分为多轮对话、使用更简洁的表达方式",
             description_en="Prompt estimated token consumption exceeds threshold, may cause cost overrun or truncation",
             remediation_en="Simplify Prompt content, split into multi-turn conversations, use more concise expressions", family="token_budget"),
    LintRule("P050", "中文冗余表述", "quality", Severity.LOW,
             "Prompt中存在中文冗余叠词或重复表述",
             "移除冗余叠词(如'的了'、'的话的话')，使用简洁精炼的表达",
             description_en="Prompt contains Chinese redundant tautological words or repetitive expressions",
             remediation_en="Remove redundant tautological words (e.g., '的了', '的话的话'), use concise and refined expressions", family="redundancy_zh"),
]

for r in _AGENT_RULES_V2 + _ZH_CN_RULES:
    _RULE_MAP[r.rule_id] = r


def check_p041(text: str) -> Finding | None:
    rule = _RULE_MAP["P041"]
    has_tool_decl = any(p.search(text) for p in _AGENT_TOOL_DECL_PATTERNS)
    if not has_tool_decl:
        has_tool_ref = bool(re.search(r"(?:工具|函数|API|tool|function|api)", text, re.IGNORECASE))
        if not has_tool_ref:
            return None
    has_vague = any(p.search(text) for p in _H1_VAGUE_DESC_PATTERNS)
    if has_vague:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=rule.description, remediation=rule.remediation)
    tool_desc_blocks = re.findall(
        r"(?:工具|函数|API|tool|function|api)\s*(?:说明|描述|description|定义|definition)\s*[:：]\s*(.{5,80})(?:\n|$)",
        text, re.IGNORECASE,
    )
    for block in tool_desc_blocks:
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", block)
        if len(words) < 4:
            return Finding(rule_id=rule.rule_id, severity=rule.severity,
                           description=rule.description, remediation=rule.remediation)
    return None


def check_p042(text: str) -> Finding | None:
    rule = _RULE_MAP["P042"]
    has_tool = bool(re.search(r"(?:工具|函数|API|tool|function|api)", text, re.IGNORECASE))
    if not has_tool:
        return None
    has_constraint_scaffold = any(p.search(text) for p in _H2_CONSTRAINT_SCAFFOLD_PATTERNS)
    if has_constraint_scaffold:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p043(text: str) -> Finding | None:
    rule = _RULE_MAP["P043"]
    has_schema = any(p.search(text) for p in _H3_SCHEMA_PATTERNS)
    if not has_schema:
        return None
    has_intent = any(p.search(text) for p in _H3_INTENT_PATTERNS)
    if has_intent:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p044(text: str) -> Finding | None:
    rule = _RULE_MAP["P044"]
    has_context = any(p.search(text) for p in _H4_CONTEXT_LEAK_PATTERNS)
    if not has_context:
        return None
    has_boundary = any(p.search(text) for p in _H4_BOUNDARY_PATTERNS)
    if has_boundary:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p045(text: str) -> Finding | None:
    rule = _RULE_MAP["P045"]
    has_implicit = any(p.search(text) for p in _H5_IMPLICIT_PATTERNS)
    if not has_implicit:
        return None
    has_explicit = any(p.search(text) for p in _H5_EXPLICIT_PATTERNS)
    if has_explicit:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p046(text: str) -> Finding | None:
    rule = _RULE_MAP["P046"]
    has_template_vars = any(p.search(text) for p in _H6_TEMPLATE_VAR_PATTERNS)
    if not has_template_vars:
        return None
    has_format_spec = any(p.search(text) for p in _H6_FORMAT_SPEC_PATTERNS)
    if has_format_spec:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p047(text: str) -> Finding | None:
    rule = _RULE_MAP["P047"]
    roles_found = _H7_ROLE_PATTERNS
    role_count = sum(1 for p in roles_found if p.search(text))
    if role_count < 2:
        has_multi_conflict = any(p.search(text) for p in _H7_MULTI_ROLE_CONFLICT_PATTERNS)
        if not has_multi_conflict:
            return None
    has_separation = bool(re.search(r"(?:---|===|###|角色[一二三四五]|Role\s*[1-5]|角色[A-E])", text, re.IGNORECASE))
    if has_separation:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p048(text: str) -> Finding | None:
    rule = _RULE_MAP["P048"]
    has_zh_punct = any(p.search(text) for p in _ZH_CN_PUNCTUATION_PATTERNS)
    if not has_zh_punct:
        return None
    en_punct_in_zh_context = re.findall(
        r"[\u4e00-\u9fff]\s*[,.:;!?]\s*[\u4e00-\u9fff]",
        text,
    )
    if not en_punct_in_zh_context:
        en_punct_after_zh = re.findall(
            r"[\u4e00-\u9fff]\s*[,.:;!?](?:\s|$)",
            text,
        )
        en_punct_before_zh = re.findall(
            r"(?:^|\s)[,.:;!?]\s*[\u4e00-\u9fff]",
            text,
        )
        if not en_punct_after_zh and not en_punct_before_zh:
            return None
        mixed_count = len(en_punct_after_zh) + len(en_punct_before_zh)
    else:
        mixed_count = len(en_punct_in_zh_context)
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=f"{rule.description} (发现 {mixed_count} 处)",
                   remediation=rule.remediation,
                   details={"mixed_punctuation_count": mixed_count})


def check_p049(text: str) -> Finding | None:
    rule = _RULE_MAP["P049"]
    zh_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    en_words = len(re.findall(r"[a-zA-Z]+", text))
    estimated_tokens = int(zh_chars * _TOKEN_ESTIMATE_RATIO + en_words * 1.3)
    if estimated_tokens < _TOKEN_WARNING_THRESHOLD:
        return None
    severity = rule.severity
    if estimated_tokens >= _TOKEN_CRITICAL_THRESHOLD:
        severity = Severity.HIGH
    return Finding(rule_id=rule.rule_id, severity=severity,
                   description=f"{rule.description} (预估 ~{estimated_tokens} tokens)",
                   remediation=rule.remediation,
                   details={"estimated_tokens": estimated_tokens,
                            "zh_chars": zh_chars, "en_words": en_words})


def check_p050(text: str) -> Finding | None:
    rule = _RULE_MAP["P050"]
    redundant_matches = []
    for pattern in _ZH_CN_REDUNDANT_PATTERNS:
        matches = pattern.findall(text)
        redundant_matches.extend(matches)
    for pattern in _ZH_CN_HONORIFIC_PATTERNS:
        matches = pattern.findall(text)
        redundant_matches.extend(matches)
    if not redundant_matches:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=f"{rule.description} (发现 {len(redundant_matches)} 处)",
                   remediation=rule.remediation,
                   details={"redundant_phrases": redundant_matches[:5]})


def run_checks_p041_p050(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for checker in [check_p041, check_p042, check_p043, check_p044,
                    check_p045, check_p046, check_p047,
                    check_p048, check_p049, check_p050]:
        result = checker(text)
        if result is not None:
            findings.append(result)
    return findings
