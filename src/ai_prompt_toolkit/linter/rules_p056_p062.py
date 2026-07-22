"""Lint规则集扩展——P056-P062 Prompt版式规范+输出稳定性+多语言冲突+Agent工具规范+RAG规范

参考: promptfoo质量规则 + OWASP LLM Top10 2025 + RAG最佳实践
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_RULES_P056_P062: list[LintRule] = [
    LintRule("P056", "Markdown层级过深", "quality", Severity.LOW,
             "Prompt中Markdown标题层级超过4级，影响可读性",
             "精简标题层级至4级以内，使用列表替代深层嵌套", family="markdown_depth"),
    LintRule("P057", "输出非确定性风险", "quality", Severity.MEDIUM,
             "Prompt中存在导致非确定性输出的措辞但未设定约束",
             "对'随机/任意/自由'等措辞添加seed或范围约束", family="output_determinism"),
    LintRule("P058", "多语言指令冲突", "quality", Severity.MEDIUM,
             "同一Prompt中混用中英文指令但未明确指定输出语言",
             "在约束中明确指定输出语言，避免混用导致输出不稳定", family="multilang_conflict"),
    LintRule("P059", "Agent工具描述不完整", "quality", Severity.HIGH,
             "Agent型Prompt中工具定义缺少必要的参数说明或返回值描述",
             "每个工具定义必须包含name/description/parameters/returns", family="agent_tool"),
    LintRule("P060", "RAG引用格式不规范", "quality", Severity.MEDIUM,
             "RAG型Prompt中未定义检索结果的引用格式",
             "定义统一的引用格式，如[文档编号, 段落位置]", family="rag_citation"),
    LintRule("P061", "空行规范", "quality", Severity.LOW,
             "Prompt中存在3个及以上连续空行",
             "精简连续空行至最多1个，保持版面整洁", family="whitespace_norm"),
    LintRule("P062", "条件编译语法错误", "quality", Severity.HIGH,
             "条件编译指令存在未闭合或嵌套错误",
             "检查{{#if}}/{{/if}}配对和嵌套层级", family="conditional_syntax"),
]

for r in _RULES_P056_P062:
    _RULE_MAP[r.rule_id] = r


_HEADING_PATTERN = re.compile(r'^(#{1,6})\s', re.MULTILINE)

_NONDETERMINISTIC_WORDS = re.compile(
    r'(?:随机|任意|自由发挥|创造性|灵活|random|arbitrary|creative|freely)',
    re.IGNORECASE,
)
_SEED_CONSTRAINT = re.compile(
    r'(?:seed|固定|确定性|温度|temperature|top_p|top_k)',
    re.IGNORECASE,
)

_ZH_INSTRUCTION = re.compile(r'(?:必须|需要|应该|请|不要|禁止|不得|限制)')
_EN_INSTRUCTION = re.compile(r'(?:must|should|need|please|do not|never|avoid|forbidden)', re.IGNORECASE)
_LANG_SPEC = re.compile(r'(?:输出语言|回复语言|使用中文|使用英文|output\s+in|respond\s+in|language)', re.IGNORECASE)

_TOOL_DEF_PATTERN = re.compile(r'(?:tool|函数|function|方法|method)\s*[:：]\s*(.{5,80}?)(?=\n|$)', re.IGNORECASE)
_TOOL_HAS_PARAMS = re.compile(r'(?:参数|parameter|input|inputSchema|参数说明)', re.IGNORECASE)
_TOOL_HAS_RETURNS = re.compile(r'(?:返回|return|输出|output|返回值)', re.IGNORECASE)

_RAG_PATTERN = re.compile(r'(?:检索|RAG|retrieval|搜索|search|知识库|knowledge)', re.IGNORECASE)
_CITE_FORMAT = re.compile(r'(?:引用|来源|参考|citation|reference|\[文档|\[Doc)', re.IGNORECASE)

_CONSECUTIVE_BLANKS = re.compile(r'\n{4,}')

_IF_OPEN = re.compile(r'\{\{#if\b')
_IF_CLOSE = re.compile(r'\{\{/if\}\}')


def check_p056(text: str) -> Finding | None:
    rule = _RULE_MAP["P056"]
    matches = _HEADING_PATTERN.findall(text)
    deep = [m for m in matches if len(m) > 4]
    if not deep:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(deep)} 处超过4级标题)",
        remediation=rule.remediation,
        details={"deep_headings": len(deep)},
    )


def check_p057(text: str) -> Finding | None:
    rule = _RULE_MAP["P057"]
    nondet_matches = _NONDETERMINISTIC_WORDS.findall(text)
    if not nondet_matches:
        return None
    has_constraint = bool(_SEED_CONSTRAINT.search(text))
    if has_constraint:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(nondet_matches)} 处非确定性措辞)",
        remediation=rule.remediation,
        details={"nondet_words": nondet_matches[:5]},
    )


def check_p058(text: str) -> Finding | None:
    rule = _RULE_MAP["P058"]
    has_zh = bool(_ZH_INSTRUCTION.search(text))
    has_en = bool(_EN_INSTRUCTION.search(text))
    if not (has_zh and has_en):
        return None
    has_lang_spec = bool(_LANG_SPEC.search(text))
    if has_lang_spec:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p059(text: str) -> Finding | None:
    rule = _RULE_MAP["P059"]
    tool_defs = _TOOL_DEF_PATTERN.findall(text)
    if not tool_defs:
        return None
    has_params = bool(_TOOL_HAS_PARAMS.search(text))
    has_returns = bool(_TOOL_HAS_RETURNS.search(text))
    if has_params and has_returns:
        return None
    missing = []
    if not has_params:
        missing.append("参数说明")
    if not has_returns:
        missing.append("返回值描述")
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (缺少: {', '.join(missing)})",
        remediation=rule.remediation,
        details={"tool_count": len(tool_defs), "missing": missing},
    )


def check_p060(text: str) -> Finding | None:
    rule = _RULE_MAP["P060"]
    is_rag = bool(_RAG_PATTERN.search(text))
    if not is_rag:
        return None
    has_cite = bool(_CITE_FORMAT.search(text))
    if has_cite:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p061(text: str) -> Finding | None:
    rule = _RULE_MAP["P061"]
    matches = _CONSECUTIVE_BLANKS.findall(text)
    if not matches:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(matches)} 处)",
        remediation=rule.remediation,
        details={"count": len(matches)},
    )


def check_p062(text: str) -> Finding | None:
    rule = _RULE_MAP["P062"]
    opens = _IF_OPEN.findall(text)
    closes = len(_IF_CLOSE.findall(text))
    if len(opens) == 0 and closes == 0:
        return None
    if len(opens) == closes:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} ({{#if}}: {len(opens)}, {{/if}}: {closes})",
        remediation=rule.remediation,
        details={"if_opens": len(opens), "if_closes": closes},
    )


def run_checks_p056_p062(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p056, check_p057, check_p058, check_p059, check_p060, check_p061, check_p062]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
