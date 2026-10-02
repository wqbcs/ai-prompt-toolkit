"""P196-P200 LLM推理安全Lint规则

LLM推理安全最佳实践(参考DeepEval metrics + garak probes + OWASP LLM Top10):
- P196: LLM推理超时风险(未设置timeout导致无限等待)
- P197: LLM输出长度失控(未限制max_tokens导致成本暴增)
- P198: LLM温度参数不当(温度>1.5导致输出不可控)
- P199: LLM Top-p采样风险(top_p与temperature同时设置导致双重随机性)
- P200: LLM流式响应安全(流式输出未做内容审核导致实时泄露)

覆盖OWASP LLM06(Excessive Agency), LLM09(Overreliance)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P196_P200 = [
    LintRule(
        "P196",
        "LLM推理超时风险",
        "inference_security",
        Severity.HIGH,
        "LLM推理未设置timeout, 可能导致无限等待和资源耗尽",
        "设置推理超时: timeout=30s(同步)/60s(流式), 如 inference: {timeout: 30, max_retries: 3}",
        description_en="LLM inference has no timeout, may cause infinite wait and resource exhaustion",
        remediation_en="Set inference timeout: timeout=30s(sync)/60s(streaming), e.g. inference: {timeout: 30, max_retries: 3}",
        family="inference_timeout",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P197",
        "LLM输出长度失控",
        "inference2security",
        Severity.HIGH,
        "LLM推理未限制max_tokens, 输出长度失控可能致成本暴增",
        "限制输出长度: max_tokens=2048(对话)/4096(长文), 如 generation: {max_tokens: 2048}",
        description_en="LLM inference has no max_tokens limit, output length uncontrolled may cause cost explosion",
        remediation_en="Limit output length: max_tokens=2048(chat)/4096(long), e.g. generation: {max_tokens: 2048}",
        family="inference_max_tokens",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P198",
        "LLM温度参数不当",
        "inference_security",
        Severity.MEDIUM,
        "LLM温度参数>1.5, 输出过于随机不可控, 降低输出质量稳定性",
        "设置合理温度: temperature=0.0(确定性)/0.7(创造性)/1.0(平衡), 避免>1.5",
        description_en="LLM temperature>1.5, output too random and uncontrollable, reduces quality stability",
        remediation_en="Set reasonable temperature: 0.0(deterministic)/0.7(creative)/1.0(balanced), avoid>1.5",
        family="inference_temperature",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P199",
        "LLM采样参数冲突",
        "inference_security",
        Severity.MEDIUM,
        "LLM同时设置top_p和temperature, 双重随机性叠加导致输出极度不稳定",
        "选择一种采样策略: top_p=0.9+temperature=1.0(推荐) 或仅设temperature, 避免双重调节",
        description_en="LLM sets both top_p and temperature, dual randomness makes output extremely unstable",
        remediation_en="Choose one strategy: top_p=0.9+temperature=1.0(recommended) or only temperature, avoid dual tuning",
        family="inference_sampling",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P200",
        "LLM流式响应安全",
        "inference_security",
        Severity.HIGH,
        "LLM流式输出未做实时内容审核, 恶意/敏感内容可能逐token泄露给用户",
        "流式安全: 每N个token做内容审核+敏感词检测+中断机制, 如 streaming: {audit_interval: 50, abort_on_violation: true}",
        description_en="LLM streaming output lacks real-time content audit, malicious/sensitive content may leak token-by-token",
        remediation_en="Streaming safety: audit every N tokens+敏感词检测+abort mechanism, e.g. streaming: {audit_interval: 50}",
        family="inference_streaming",
        owasp_refs=["LLM06"],
    ),
]

for r in _RULES_P196_P200:
    _RULE_MAP[r.rule_id] = r

_TIMEOUT_PATTERN = re.compile(r"(?:timeout|超时|time.limit|max_retries)", re.IGNORECASE)
_INVOKE_PATTERN = re.compile(
    r"(?:推理|inference|invoke|generate|chat.completions|completion|predict|调用模型)", re.IGNORECASE
)
_MAX_TOKENS_PATTERN = re.compile(r"(?:max_tokens|max.tokens|最大长度|max_length|token.limit)", re.IGNORECASE)
# 思维链/逐步推理是Prompt行为描述, 不是推理服务配置 — 用于排除"逐步推理"类误报
_REASONING_BEHAVIOR_PATTERN = re.compile(
    r"(?:逐步推理|思维链|chain.of.thought|思考过程|推理过程|step.by.step|scratchpad)", re.IGNORECASE
)
_TEMP_PATTERN = re.compile(r"(?:temperature|温度|temp)\s*[:=]\s*([\d.]+)", re.IGNORECASE)
_TOP_P_PATTERN = re.compile(r"(?:top_p|top.p|核采样)\s*[:=]", re.IGNORECASE)
_STREAM_PATTERN = re.compile(r"(?:stream|流式|streaming)", re.IGNORECASE)
_STREAM_AUDIT_PATTERN = re.compile(r"(?:audit|审核|content.check|moderation|中断|abort)", re.IGNORECASE)


def check_p196(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _REASONING_BEHAVIOR_PATTERN.search(text):
        return findings
    has_invoke = _INVOKE_PATTERN.search(text)
    if has_invoke and not _TIMEOUT_PATTERN.search(text):
        findings.append(Finding("P196", Severity.HIGH, "LLM推理未设置timeout"))
    return findings


def check_p197(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _REASONING_BEHAVIOR_PATTERN.search(text):
        return findings
    has_invoke = _INVOKE_PATTERN.search(text)
    if has_invoke and not _MAX_TOKENS_PATTERN.search(text):
        findings.append(Finding("P197", Severity.HIGH, "LLM推理未限制max_tokens"))
    return findings


def check_p198(text: str) -> list[Finding]:
    findings: list[Finding] = []
    match = _TEMP_PATTERN.search(text)
    if match:
        try:
            temp = float(match.group(1))
            if temp > 1.5:
                findings.append(Finding("P198", Severity.MEDIUM, f"LLM温度参数{temp}过高(>1.5)"))
        except ValueError:
            pass
    return findings


def check_p199(text: str) -> list[Finding]:
    findings: list[Finding] = []
    has_top_p = _TOP_P_PATTERN.search(text)
    has_temp = _TEMP_PATTERN.search(text)
    if has_top_p and has_temp:
        findings.append(Finding("P199", Severity.MEDIUM, "同时设置top_p和temperature导致双重随机性"))
    return findings


def check_p200(text: str) -> list[Finding]:
    findings: list[Finding] = []
    has_stream = _STREAM_PATTERN.search(text)
    if has_stream and not _STREAM_AUDIT_PATTERN.search(text):
        findings.append(Finding("P200", Severity.HIGH, "流式输出未做实时内容审核"))
    return findings
