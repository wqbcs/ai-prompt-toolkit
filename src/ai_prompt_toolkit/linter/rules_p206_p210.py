"""P206-P210 RAG/知识库安全Lint规则

RAG(Retrieval-Augmented Generation)安全最佳实践(参考garak RAG probes + DeepEval metrics):
- P206: 检索注入风险(外部数据源注入恶意内容到检索结果)
- P207: 幻觉检测缺失(未配置事实性检查/来源验证)
- P208: 来源溯源缺失(未标注检索来源, 无法追溯信息出处)
- P209: 上下文窗口溢出(检索结果超上下文窗口导致截断丢失)
- P210: 嵌入偏移风险(嵌入模型更新导致检索结果偏移)

覆盖OWASP LLM08(Vulnerable Plugins), LLM09(Misinformation)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P206_P210 = [
    LintRule(
        "P206",
        "检索注入风险",
        "rag_security",
        Severity.HIGH,
        "RAG检索结果未做输入净化, 外部数据源可能注入恶意内容",
        "检索净化: sanitize_retrieval=true, 添加内容审核+PII检测+长度限制, 如 retrieval: {sanitize: true, max_length: 4096}",
        description_en="RAG retrieval results lack input sanitization, external data may inject malicious content",
        remediation_en="Retrieval sanitization: sanitize_retrieval=true, add content audit+PII detection+length limit",
        family="rag_injection",
        owasp_refs=["LLM08"],
    ),
    LintRule(
        "P207",
        "幻觉检测缺失",
        "rag_security",
        Severity.HIGH,
        "RAG未配置事实性检查/来源验证, 模型可能生成无根据内容",
        "配置幻觉检测: faithfulness_check=true, 添加source_verification+claim_extraction, 如 rag: {faithfulness: true}",
        description_en="RAG lacks factuality check/source verification, model may generate unfounded content",
        remediation_en="Configure hallucination detection: faithfulness_check=true, add source_verification+claim_extraction",
        family="rag_hallucination",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P208",
        "来源溯源缺失",
        "rag_security",
        Severity.MEDIUM,
        "检索结果未标注来源, 无法追溯信息出处, 降低可信度",
        "添加来源标注: source_citation=true, 如 retrieval: {cite_sources: true, format: 'source[1]: url'}",
        description_en="Retrieval results lack source citation, cannot trace information origin, reduces trustworthiness",
        remediation_en="Add source citation: source_citation=true, e.g. retrieval: {cite_sources: true, format: 'source[1]: url'}",
        family="rag_citation",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P209",
        "上下文窗口溢出",
        "rag_security",
        Severity.HIGH,
        "检索结果可能超过上下文窗口, 导致截断丢失关键信息",
        "限制检索量: max_chunks=5, max_total_tokens=4096, 添加截断检测+优先级排序, 如 retrieval: {max_chunks: 5, max_tokens: 4096}",
        description_en="Retrieval results may exceed context window, causing truncation and loss of key information",
        remediation_en="Limit retrieval: max_chunks=5, max_total_tokens=4096, add truncation detection+priority ranking",
        family="rag_context_window",
        owasp_refs=["LLM08"],
    ),
    LintRule(
        "P210",
        "嵌入偏移风险",
        "rag_security",
        Severity.MEDIUM,
        "嵌入模型版本未固定, 模型更新可能导致检索结果偏移/降质",
        "固定嵌入版本: embedding_model=text-embedding-3-small@v1, 添加版本校验+相似度监控, 如 embedding: {model: 'ada-002', version_lock: true}",
        description_en="Embedding model version not pinned, updates may cause retrieval drift/quality degradation",
        remediation_en="Pin embedding version: embedding_model=text-embedding-3-small@v1, add version check+similarity monitoring",
        family="rag_embedding_drift",
        owasp_refs=["LLM08"],
    ),
]

for r in _RULES_P206_P210:
    _RULE_MAP[r.rule_id] = r

_RETRIEVAL_PATTERN = re.compile(
    r"(?:检索|retrieval|retrieve|RAG|rag|搜索|search|知识库|knowledge|向量|vector|embedding)", re.IGNORECASE
)
_SANITIZE_PATTERN = re.compile(r"(?:sanitize|净化|审核|filter|clean|content.check|moderation)", re.IGNORECASE)
_FAITHFULNESS_PATTERN = re.compile(r"(?:faithfulness|事实性|factual|source.verification|来源验证|claim)", re.IGNORECASE)
_CITATION_PATTERN = re.compile(r"(?:cite|引用|来源|source|attribution|溯源|出处)", re.IGNORECASE)
_MAX_TOKENS_PATTERN_RAG = re.compile(r"(?:max_chunks|max.tokens|max_total|context.limit|窗口限制)", re.IGNORECASE)
_VERSION_LOCK_PATTERN = re.compile(r"(?:version.lock|版本固定|pin|model.version|@v\d)", re.IGNORECASE)


def check_p206(text: str) -> list[Finding]:
    findings = []
    if _RETRIEVAL_PATTERN.search(text) and not _SANITIZE_PATTERN.search(text):
        findings.append(Finding("P206", Severity.HIGH, "RAG检索结果未做输入净化", "1", "1"))
    return findings


def check_p207(text: str) -> list[Finding]:
    findings = []
    if _RETRIEVAL_PATTERN.search(text) and not _FAITHFULNESS_PATTERN.search(text):
        findings.append(Finding("P207", Severity.HIGH, "RAG未配置幻觉检测", "1", "1"))
    return findings


def check_p208(text: str) -> list[Finding]:
    findings = []
    if _RETRIEVAL_PATTERN.search(text) and not _CITATION_PATTERN.search(text):
        findings.append(Finding("P208", Severity.MEDIUM, "检索结果未标注来源", "1", "1"))
    return findings


def check_p209(text: str) -> list[Finding]:
    findings = []
    if _RETRIEVAL_PATTERN.search(text) and not _MAX_TOKENS_PATTERN_RAG.search(text):
        findings.append(Finding("P209", Severity.HIGH, "检索结果可能超过上下文窗口", "1", "1"))
    return findings


def check_p210(text: str) -> list[Finding]:
    findings = []
    has_embedding = re.search(r"(?:embedding|嵌入|向量模型|vector.model)", text, re.IGNORECASE)
    if has_embedding and not _VERSION_LOCK_PATTERN.search(text):
        findings.append(Finding("P210", Severity.MEDIUM, "嵌入模型版本未固定", "1", "1"))
    return findings
