"""Lint规则集扩展——P096-P100 盘古Pangu大模型兼容性专项规则

R42新增(赛事贴合-华为云盘古大模型):
- P096: 盘古模型格式兼容性 — 检测Prompt是否适配盘古对话格式
- P097: 盘古Token限制风险 — 检测Prompt是否超出盘古模型Token上下文限制
- P098: 盘古工具调用规范 — 检测盘古Function Calling/Tool Use格式规范
- P099: 盘古多模态兼容性 — 检测盘古多模态(图文)输入格式兼容性
- P100: 盘古安全护栏声明 — 检测华为云ModelArts安全护栏配置声明
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P096_P100: list[LintRule] = [
    LintRule(
        "P096",
        "盘古模型格式兼容性风险",
        "quality",
        Severity.HIGH,
        "Prompt使用了非盘古兼容的对话格式(如ChatML/Llama格式)",
        "适配盘古对话格式: 使用system/user/assistant角色标签, 或使用华为云MaaS API格式",
        description_en="Prompt uses Pangu-incompatible dialog format (e.g., ChatML/Llama format)",
        remediation_en="Adapt to Pangu dialog format: use system/user/assistant role tags or Huawei Cloud MaaS API format",
        family="pangu_format",
    ),
    LintRule(
        "P097",
        "盘古Token限制风险",
        "performance",
        Severity.HIGH,
        "Prompt可能超出盘古模型上下文窗口限制(8K/32K/128K)",
        "声明Token限制: '本Prompt控制在N tokens以内, 适配盘古XXX模型上下文窗口'",
        description_en="Prompt may exceed Pangu model context window limit (8K/32K/128K)",
        remediation_en="Declare token limit: 'Keep this prompt within N tokens, compatible with Pangu XXX model context window'",
        family="pangu_token",
    ),
    LintRule(
        "P098",
        "盘古工具调用规范缺失",
        "structure",
        Severity.MEDIUM,
        "Prompt涉及工具/函数调用但未声明盘古Function Calling格式规范",
        "声明工具调用格式: '使用华为云MaaS Function Calling格式, tools参数定义'",
        description_en="Prompt involves tool/function calls but missing Pangu Function Calling format declaration",
        remediation_en="Declare tool call format: 'Use Huawei Cloud MaaS Function Calling format, tools parameter definition'",
        family="pangu_toolcall",
    ),
    LintRule(
        "P099",
        "盘古多模态兼容性风险",
        "quality",
        Severity.MEDIUM,
        "Prompt涉及多模态(图文)输入但未声明盘古多模态格式兼容性",
        "声明多模态格式: '图片输入使用base64编码/URL, 适配盘古多模态API格式'",
        description_en="Prompt involves multimodal (image-text) input but missing Pangu multimodal format compatibility",
        remediation_en="Declare multimodal format: 'Image input uses base64/URL, compatible with Pangu multimodal API format'",
        family="pangu_multimodal",
    ),
    LintRule(
        "P100",
        "盘古安全护栏声明缺失",
        "security",
        Severity.HIGH,
        "使用盘古模型的Prompt未声明华为云ModelArts安全护栏和内容审核配置",
        "声明安全护栏: '启用ModelArts内容审核, 配置敏感词过滤, 输出安全评分阈值≥0.8'",
        description_en="Prompt using Pangu model missing ModelArts safety guardrails and content moderation declaration",
        remediation_en="Declare safety guardrails: 'Enable ModelArts content moderation, configure sensitive word filtering, output safety score threshold ≥0.8'",
        family="safety_guardrail",
    ),
]

for r in _RULES_P096_P100:
    _RULE_MAP[r.rule_id] = r


_PANGU_CTX = re.compile(r"(?:盘古|Pangu|pangu|华为云.*模型|MaaS|maas|ModelArts|昇腾|Ascend)", re.IGNORECASE)

_CHATML_PATTERN = re.compile(r"<\|im_start\|>|<\|im_end\|>")

_LLAMA_PATTERN = re.compile(r"\[INST\]|\[/INST\]|<<SYS>>", re.IGNORECASE)

_ALPACA_PATTERN = re.compile(r"###\s*(?:Instruction|Response|Input|System):", re.IGNORECASE)

_CLAUDE_PATTERN = re.compile(r"^Human:|^Assistant:|\nHuman:|\nAssistant:", re.MULTILINE)

_PANGU_FORMAT_DECL = re.compile(
    r"(?:Pangu.*format|盘古.*格式|MaaS.*API|system.*role|user.*role|assistant.*role|messages.*数组)", re.IGNORECASE
)


def check_p096(text: str) -> Finding | None:
    rule = _RULE_MAP["P096"]
    if not _PANGU_CTX.search(text):
        return None
    non_pangu_formats = []
    if _CHATML_PATTERN.search(text):
        non_pangu_formats.append("ChatML")
    if _LLAMA_PATTERN.search(text):
        non_pangu_formats.append("Llama")
    if _ALPACA_PATTERN.search(text):
        non_pangu_formats.append("Alpaca")
    if _CLAUDE_PATTERN.search(text):
        non_pangu_formats.append("Claude/Alpaca")
    if not non_pangu_formats:
        return None
    if _PANGU_FORMAT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=f"{rule.description} (检测到: {', '.join(non_pangu_formats)}格式)",
        remediation=rule.remediation,
        details={"non_pangu_formats": non_pangu_formats},
    )


_TOKEN_DECL_PATTERN = re.compile(
    r"(?:\d+\s*[kK]\s*(?:token|上下文)|token.*预算|context.*\d+|窗口.*\d+|8[kK]|32[kK]|128[kK]|适配.*上下文)",
    re.IGNORECASE,
)

_LONG_PROMPT_THRESHOLD = 4000


def check_p097(text: str) -> Finding | None:
    rule = _RULE_MAP["P097"]
    if not _PANGU_CTX.search(text):
        return None
    if _TOKEN_DECL_PATTERN.search(text):
        return None
    char_count = len(text)
    estimated_tokens = char_count // 2
    if estimated_tokens > _LONG_PROMPT_THRESHOLD:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=f"{rule.description} (估算约{estimated_tokens}tokens, 字符数{char_count})",
            remediation=rule.remediation,
            details={"estimated_tokens": estimated_tokens, "char_count": char_count},
        )
    return None


_TOOL_CALL_PATTERN = re.compile(r"(?:工具|函数调用|function.?call|tool.?call|调用API|插件|plugin)", re.IGNORECASE)

_TOOL_DECL_PATTERN = re.compile(
    r"(?:Function.?Calling.*格式|Tool.?Use.*格式|tools.*参数.*定义|function.*定义.*格式|MaaS.*function.*API|盘古.*工具.*格式|函数调用.*规范|工具调用.*声明)",
    re.IGNORECASE,
)


def check_p098(text: str) -> Finding | None:
    rule = _RULE_MAP["P098"]
    if not _PANGU_CTX.search(text):
        return None
    if not _TOOL_CALL_PATTERN.search(text):
        return None
    if _TOOL_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_MULTIMODAL_PATTERN = re.compile(
    r"(?:图片|图像|照片|image|photo|picture|视觉|vision|截图|screenshot|多模态|multimodal|图文)", re.IGNORECASE
)

_MULTIMODAL_DECL_PATTERN = re.compile(
    r"(?:base64|图片.*URL|image.*url|多模态.*格式|multimodal.*format|盘古.*多模态|Pangu.*vision|vision.*model)",
    re.IGNORECASE,
)


def check_p099(text: str) -> Finding | None:
    rule = _RULE_MAP["P099"]
    if not _PANGU_CTX.search(text):
        return None
    if not _MULTIMODAL_PATTERN.search(text):
        return None
    if _MULTIMODAL_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_SAFETY_PATTERN = re.compile(
    r"(?:安全|审核|过滤|屏蔽|护栏|moderation|safety|filter|内容安全|content.?safe)", re.IGNORECASE
)

_SAFETY_DECL_PATTERN = re.compile(
    r"(?:ModelArts.*审核|ModelArts.*安全|内容审核.*配置|content.?moderation.*config|安全护栏.*配置|safety.?guardrail.*config|安全评分.*阈值|safety.?score.*threshold|敏感词.*过滤.*配置)",
    re.IGNORECASE,
)


def check_p100(text: str) -> Finding | None:
    rule = _RULE_MAP["P100"]
    if not _PANGU_CTX.search(text):
        return None
    if not _SAFETY_PATTERN.search(text):
        return None
    if _SAFETY_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def run_checks_p096_p100(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p096, check_p097, check_p098, check_p099, check_p100]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
