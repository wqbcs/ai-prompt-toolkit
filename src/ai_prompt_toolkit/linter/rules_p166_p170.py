"""Lint规则集扩展——P166-P170 Prompt输出安全防护

R76新增(参考llm-guard输出扫描器):
- P166: Prompt输出内容过滤声明缺失
- P167: Prompt幻觉防护声明缺失
- P168: Prompt偏见检测声明缺失
- P169: Prompt毒性内容过滤声明缺失
- P170: Prompt引用验证声明缺失

参考: llm-guard输出扫描器(NoRefusal/Bias/Toxicity/Relevance/FactualConsistency)
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP

_RULES_P166_P170: list[LintRule] = [
    LintRule("P166", "Prompt输出内容过滤声明缺失", "security", Severity.HIGH,
             "Prompt未声明输出内容过滤(禁止类型/格式验证/长度限制)",
             "声明输出过滤: 禁止输出代码/SQL/HTML, 格式验证JSON/Markdown, 长度限制<2000字符",
             description_en="Prompt missing output content filtering declaration",
             remediation_en="Declare output filtering: No code/SQL/HTML output, JSON/Markdown validation, length<2000",
             family="output_filtering"),
    LintRule("P167", "Prompt幻觉防护声明缺失", "security", Severity.HIGH,
             "Prompt未声明幻觉防护(事实核查/来源引用/不确定性标注)",
             "声明幻觉防护: 要求标注不确定信息, 引用来源URL, 禁止编造数据/日期/人名",
             description_en="Prompt missing hallucination protection declaration",
             remediation_en="Declare hallucination protection: Mark uncertainty, cite sources, no fabricated data",
             family="hallucination_protection"),
    LintRule("P168", "Prompt偏见检测声明缺失", "security", Severity.MEDIUM,
             "Prompt未声明偏见检测(公平性/代表性/中立性)",
             "声明偏见检测: 输出需公平无歧视, 覆盖多样代表性, 保持中立立场",
             description_en="Prompt missing bias detection declaration",
             remediation_en="Declare bias detection: Fair non-discriminatory, diverse representation, neutral stance",
             family="bias_detection"),
    LintRule("P169", "Prompt毒性内容过滤声明缺失", "security", Severity.HIGH,
             "Prompt未声明毒性内容过滤(仇恨言论/骚扰/自残/暴力)",
             "声明毒性过滤: 禁止仇恨言论/骚扰/自残/暴力内容, 检测并拒绝毒性输出",
             description_en="Prompt missing toxicity content filtering declaration",
             remediation_en="Declare toxicity filtering: No hate speech/harassment/self-harm/violence, detect and reject",
             family="toxicity_filtering"),
    LintRule("P170", "Prompt引用验证声明缺失", "security", Severity.MEDIUM,
             "Prompt未声明引用验证(来源可追溯/URL可达性/事实一致性)",
             "声明引用验证: 所有事实声明需附来源, URL需可达, 与参考文档事实一致",
             description_en="Prompt missing citation verification declaration",
             remediation_en="Declare citation verification: Facts need sources, URLs reachable, consistent with references",
             family="citation_verification"),
]

for r in _RULES_P166_P170:
    _RULE_MAP[r.rule_id] = r

_OUTPUT_FILTER_CTX = re.compile(
    r"(?:输出|output|响应|response|回答|answer|结果|result|生成|generat|返回|return|回复|reply|格式|format|JSON|Markdown|文本|text)",
    re.IGNORECASE
)

_OUTPUT_FILTER_DECL = re.compile(
    r"(?:输出.*过滤|output.*filter|禁止.*代码|no.*code|格式.*验证|format.*validat|长度.*限制|length.*limit|内容.*过滤|content.*filter|类型.*限制|type.*restrict|输出.*验证|output.*validat)",
    re.IGNORECASE
)

_HALLUCINATION_CTX = re.compile(
    r"(?:知识|knowledge|事实|fact|数据|data|信息|info|回答|answer|生成|generat|解释|explain|描述|describ|引用|cite|来源|source|参考|reference)",
    re.IGNORECASE
)

_HALLUCINATION_DECL = re.compile(
    r"(?:幻觉|hallucin|事实.*核查|fact.*check|不确定|uncertain|来源.*引用|source.*cite|禁止.*编造|no.*fabricat|标注.*不确定|mark.*uncertain|幻觉.*防护|hallucinat.*protect)",
    re.IGNORECASE
)

_BIAS_CTX = re.compile(
    r"(?:判断|judge|评价|evaluat|推荐|recommend|选择|select|比较|compar|分类|classif|排序|rank|决策|decis|分析|analyz)",
    re.IGNORECASE
)

_BIAS_DECL = re.compile(
    r"(?:偏见|bias|公平|fair|歧视|discriminat|中立|neutral|代表性|representat|多样|diverse|无偏|unbiased|偏见.*检测|bias.*detect)",
    re.IGNORECASE
)

_TOXICITY_CTX = re.compile(
    r"(?:用户|user|对话|chat|交流|communicat|社交|social|评论|comment|反馈|feedback|互动|interact|社区|community)",
    re.IGNORECASE
)

_TOXICITY_DECL = re.compile(
    r"(?:毒性|toxic|仇恨|hatred|骚扰|harass|自残|self.?harm|暴力|violen|冒犯|offens|毒性.*过滤|toxic.*filter|禁止.*仇恨|no.*hate|内容.*审核|content.*moderat)",
    re.IGNORECASE
)

_CITATION_CTX = re.compile(
    r"(?:研究|research|论文|paper|报告|report|文献|literature|引用|cite|参考|reference|来源|source|证据|evidence|数据|data|统计|statistic)",
    re.IGNORECASE
)

_CITATION_DECL = re.compile(
    r"(?:引用.*验证|citation.*verif|来源.*追溯|source.*trace|URL.*可达|URL.*reachab|事实.*一致|fact.*consist|参考.*验证|reference.*validat|引用.*声明|citation.*declar)",
    re.IGNORECASE
)


def check_p166(text: str) -> Finding | None:
    rule = _RULE_MAP["P166"]
    if not _OUTPUT_FILTER_CTX.search(text):
        return None
    if _OUTPUT_FILTER_DECL.search(text):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation)


def check_p167(text: str) -> Finding | None:
    rule = _RULE_MAP["P167"]
    if not _HALLUCINATION_CTX.search(text):
        return None
    if _HALLUCINATION_DECL.search(text):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation)


def check_p168(text: str) -> Finding | None:
    rule = _RULE_MAP["P168"]
    if not _BIAS_CTX.search(text):
        return None
    if _BIAS_DECL.search(text):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation)


def check_p169(text: str) -> Finding | None:
    rule = _RULE_MAP["P169"]
    if not _TOXICITY_CTX.search(text):
        return None
    if _TOXICITY_DECL.search(text):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation)


def check_p170(text: str) -> Finding | None:
    rule = _RULE_MAP["P170"]
    if not _CITATION_CTX.search(text):
        return None
    if _CITATION_DECL.search(text):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation)
