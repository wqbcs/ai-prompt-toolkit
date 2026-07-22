"""Lint规则集扩展——P081-P085 模板变量/Trace/Doctor/输出校验/模型兼容

R38新增:
- P081: 模板变量完整性 — 检测{{var}}变量是否已声明
- P082: Trace兼容性 — 检测是否支持OTLP Trace输出
- P083: Doctor健康检查集成 — 建议运行prompt-doctor诊断
- P084: 输出格式校验 — 检测JSON/Markdown等输出格式规范
- P085: 模型兼容性 — 检测模型特定语法兼容性
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_RULES_P081_P085: list[LintRule] = [
    LintRule("P081", "模板变量完整性缺失", "quality", Severity.MEDIUM,
             "使用{{var}}模板变量的Prompt缺少变量默认值声明",
             "为每个变量添加默认值: {{var|default('fallback')}}", family="template_var"),
    LintRule("P082", "Trace可观测性缺失", "quality", Severity.LOW,
             "复杂Prompt(>500字符)缺少Trace可观测性声明",
             "添加'## Trace: enabled'或使用trace()上下文管理器", family="observability"),
    LintRule("P083", "Doctor健康检查建议", "quality", Severity.LOW,
             "Prompt缺少Doctor诊断检查，建议运行prompt-doctor",
             "运行 'promptkit prompt-doctor -t <file>' 获取健康报告", family="health_check"),
    LintRule("P084", "输出格式规范缺失", "quality", Severity.MEDIUM,
             "Prompt声明了JSON/Markdown输出但缺少格式约束",
             "添加输出格式示例和Schema约束, 如'返回JSON: {\"key\": \"value\"}'", family="output_schema"),
    LintRule("P085", "模型兼容性风险", "quality", Severity.MEDIUM,
             "Prompt使用了特定模型语法但未声明目标模型",
             "声明目标模型: '适用于GPT-4/Claude-3/盘古'或使用条件编译", family="model_compat"),
]

for r in _RULES_P081_P085:
    _RULE_MAP[r.rule_id] = r


_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*default\(['\"]([^'\"]*)['\"]\))?\s*\}\}")


def check_p081(text: str) -> Finding | None:
    rule = _RULE_MAP["P081"]
    vars_without_default = []
    for match in _VAR_PATTERN.finditer(text):
        name = match.group(1)
        default = match.group(2)
        if not default:
            vars_without_default.append(name)
    if not vars_without_default:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (变量: {', '.join(vars_without_default[:5])})",
        remediation=rule.remediation,
        details={"vars_without_default": vars_without_default[:5]},
    )


def check_p082(text: str) -> Finding | None:
    rule = _RULE_MAP["P082"]
    if len(text) <= 500:
        return None
    has_trace = any(kw in text for kw in ["trace", "Trace", "tracing", "observability", "可观测"])
    if has_trace:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (当前{len(text)}字符)",
        remediation=rule.remediation,
        details={"char_count": len(text)},
    )


def check_p083(text: str) -> Finding | None:
    rule = _RULE_MAP["P083"]
    if len(text) <= 200:
        return None
    has_doctor = any(kw in text for kw in ["doctor", "Doctor", "健康检查", "health check"])
    if has_doctor:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_JSON_OUTPUT_PATTERN = re.compile(r'JSON|json|JsonObject|返回JSON|输出JSON')
_MD_OUTPUT_PATTERN = re.compile(r'Markdown|markdown|\.md|输出Markdown')
_FORMAT_CONSTRAINT_PATTERN = re.compile(r'Schema|schema|格式如下|示例:|Example:')


def check_p084(text: str) -> Finding | None:
    rule = _RULE_MAP["P084"]
    has_json_output = bool(_JSON_OUTPUT_PATTERN.search(text))
    has_md_output = bool(_MD_OUTPUT_PATTERN.search(text))
    has_format_constraint = bool(_FORMAT_CONSTRAINT_PATTERN.search(text))
    if not (has_json_output or has_md_output):
        return None
    if has_format_constraint:
        return None
    fmt = "JSON" if has_json_output else "Markdown"
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (声明{fmt}输出但无格式约束)",
        remediation=rule.remediation,
        details={"format": fmt},
    )


_CHATML_PATTERN = re.compile(r'system.*message|system_prompt|<\|im_start\|>')
_LLAMA_PATTERN = re.compile(r'\[INST\]|\[/INST\]|<s>|</s>')
_ALPACA_PATTERN = re.compile(r'Human:|Assistant:|###')
_MODEL_DECL_PATTERN = re.compile(r'GPT-4|Claude|DeepSeek|Qwen|盘古|Llama|模型', re.IGNORECASE)


def check_p085(text: str) -> Finding | None:
    rule = _RULE_MAP["P085"]
    model_specific = []
    if _CHATML_PATTERN.search(text):
        model_specific.append("ChatML")
    if _LLAMA_PATTERN.search(text):
        model_specific.append("Llama")
    if _ALPACA_PATTERN.search(text):
        model_specific.append("Claude/Alpaca")
    if not model_specific:
        return None
    has_model_decl = bool(_MODEL_DECL_PATTERN.search(text))
    if has_model_decl:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (检测到{', '.join(model_specific)}语法)",
        remediation=rule.remediation,
        details={"model_syntax": model_specific},
    )


def run_checks_p081_p085(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p081, check_p082, check_p083, check_p084, check_p085]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
