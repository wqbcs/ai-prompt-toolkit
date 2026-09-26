"""输出安全扫描器——参考llm-guard输出扫描器架构

扫描器列表(参考llm-guard):
- NoRefusalScanner: 检测模型拒绝响应(拒绝/无法/不能回答)
- BiasScanner: 检测输出偏见(性别/种族/年龄/地域歧视)
- ToxicityScanner: 检测毒性内容(仇恨/骚扰/暴力/自残)
- RelevanceScanner: 检测输出与输入的相关性
- FactualConsistencyScanner: 检测事实一致性(日期/数据/引用虚构)
- CitationScanner: 检测引用有效性(URL可达/来源可追溯)

使用方式:
    from ai_prompt_toolkit.security.output_scanners import OutputScanEngine
    engine = OutputScanEngine()
    result = engine.scan(output_text, context=input_text)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


class OutputScannerType(Enum):
    NO_REFUSAL = "no_refusal"
    BIAS = "bias"
    TOXICITY = "toxicity"
    RELEVANCE = "relevance"
    FACTUAL_CONSISTENCY = "factual_consistency"
    CITATION = "citation"


@dataclass
class OutputScanResult:
    scanner: OutputScannerType
    passed: bool
    score: float
    findings: list[Finding] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanner": self.scanner.value,
            "passed": self.passed,
            "score": round(self.score, 4),
            "findings": [f.to_dict() for f in self.findings],
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class OutputScanReport:
    text: str
    results: list[OutputScanResult] = field(default_factory=list)
    overall_passed: bool = True
    overall_score: float = 0.0
    scan_time_ms: float = 0.0

    @property
    def all_findings(self) -> list[Finding]:
        findings = []
        for r in self.results:
            findings.extend(r.findings)
        return findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_passed": self.overall_passed,
            "overall_score": round(self.overall_score, 4),
            "results": [r.to_dict() for r in self.results],
            "scan_time_ms": round(self.scan_time_ms, 2),
            "finding_count": len(self.all_findings),
        }


_REFUSAL_PATTERNS = [
    re.compile(
        r"(?:我|I)\s*(?:无法|不能|不可以|won't|can't|cannot|unable to)\s*(?:回答|回复|respond|answer|complete|fulfill|provide)",
        re.I,
    ),
    re.compile(
        r"(?:作为|as)\s*(?:一个|an?)\s*(?:AI|人工智能|语言模型|language model|assistant),?\s*(?:我|I)\s*(?:不能|无法|won't|can't|cannot)",
        re.I,
    ),
    re.compile(
        r"(?:抱歉|sorry|apologize|道歉).{0,30}(?:无法|不能|won't|can't|cannot|unable).{0,30}(?:回答|提供|respond|provide|answer|help)",
        re.I,
    ),
    re.compile(
        r"(?:这|this|that)\s*(?:个问题|question|request|topic).{0,20}(?:超出了|beyond|outside|outside).{0,20}(?:能力|scope|capabilities|范围)",
        re.I,
    ),
    re.compile(r"(?:拒绝|refuse|decline).{0,20}(?:回答|respond|answer|provide)", re.I),
    re.compile(
        r"(?:我不|I don't|I am not).{0,20}(?:被允许|allowed|permitted|authorized|授权).{0,20}(?:回答|discuss|respond|讨论)",
        re.I,
    ),
    re.compile(
        r"(?:该|this|the)\s*(?:内容|content|话题|topic).{0,15}(?:违反|violates|against|breaks).{0,15}(?:政策|policy|规则|rules|guidelines)",
        re.I,
    ),
]

_BIAS_PATTERNS = [
    (
        re.compile(
            r"(?:男性|男人|males?|men).{0,30}(?:天生|自然|naturally|inherently|biologically).{0,30}(?:更适合|better\s*at|superior|更擅长|优于)",
            re.I,
        ),
        "性别偏见",
        Severity.MEDIUM,
    ),
    (
        re.compile(
            r"(?:女性|女人|females?|women).{0,30}(?:天生|自然|naturally|inherently|biologically).{0,30}(?:更适合|better\s*at|superior|更擅长|优于)",
            re.I,
        ),
        "性别偏见",
        Severity.MEDIUM,
    ),
    (
        re.compile(
            r"(?:[A-Z]|[\u4e00-\u9fff]{2,4}).{0,10}(?:人|people|race|种族|民族).{0,20}(?:天生|自然|naturally|inherently).{0,20}(?:聪明|smart|intelligent|愚笨|stupid|劣等|inferior)",
            re.I,
        ),
        "种族偏见",
        Severity.HIGH,
    ),
    (
        re.compile(
            r"(?:老年人|old\s*people|elderly).{0,20}(?:不能|cannot|can't|无法|unable).{0,20}(?:学习|learn|适应|adapt|理解|understand)",
            re.I,
        ),
        "年龄偏见",
        Severity.MEDIUM,
    ),
    (
        re.compile(
            r"(?:发展中国家|第三世界|developing|third.?world).{0,20}(?:都是|all|always|总是|全部).{0,20}(?:贫穷|poor|落后|backward|未开化|uncivilized)",
            re.I,
        ),
        "地域偏见",
        Severity.HIGH,
    ),
    (
        re.compile(
            r"(?:所有|all|every|每个).{0,10}(?:男|女|male|female|man|woman).{0,15}(?:都|are|is|必须|must|should).{0,15}(?:喜欢|like|prefer|擅长|good\s*at|应该|should)",
            re.I,
        ),
        "群体刻板印象",
        Severity.MEDIUM,
    ),
]

_TOXICITY_PATTERNS = [
    (
        re.compile(r"(?:杀|kill|murder|屠杀|slay).{0,15}(?:死|dead|掉|them|him|her|你|you)", re.I),
        "暴力威胁",
        Severity.HIGH,
    ),
    (re.compile(r"(?:去死|go\s*die|去死吧|drop\s*dead|该死|damn\s*you)", re.I), "死亡威胁", Severity.HIGH),
    (
        re.compile(
            r"(?:你|you|你们).{0,10}(?:是|are|is).{0,10}(?:废物|垃圾|蠢货|idiot|stupid|moron|trash|scum|loser|废物)",
            re.I,
        ),
        "骚扰辱骂",
        Severity.MEDIUM,
    ),
    (
        re.compile(r"(?:劣等|inferior|下等|subhuman|低等|lesser).{0,15}(?:种族|race|民族|people|人类|human)", re.I),
        "仇恨言论",
        Severity.CRITICAL,
    ),
    (
        re.compile(
            r"(?:自杀|suicide|kill\s*yourself|自残|self.?harm|割腕|cut\s*yourself).{0,20}(?:方法|method|how\s*to|怎么|ways|步骤)",
            re.I,
        ),
        "自残诱导",
        Severity.CRITICAL,
    ),
    (
        re.compile(
            r"(?:歧视|discriminate|排斥|exclude).{0,20}(?:因为|because|due\s*to|基于|based\s*on).{0,20}(?:种族|race|性别|gender|宗教|religion|性取向|orientation)",
            re.I,
        ),
        "歧视言论",
        Severity.HIGH,
    ),
]

_DATE_PATTERN = re.compile(r"(\d{4})\s*[/\-.年]\s*(\d{1,2})\s*[/\-.月]\s*(\d{1,2})\s*日?")
_STAT_PATTERN = re.compile(
    r"(?:约|大约|approximately|around|roughly|~)\s*(\d+(?:\.\d+)?)(?:%|percent|亿|万|百万|million|billion|trillion)"
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
_FABRICATION_SIGNALS = [
    re.compile(
        r"(?:据|according\s*to).{0,15}(?:研究|study|research|调查|survey|报告|report).{0,10}(?:表明|显示|shows?|indicates?|finds?|证明|proves)",
        re.I,
    ),
    re.compile(r"(?:统计|statistics|数据|data).{0,15}(?:显示|shows?|表明|indicates?|说明|demonstrates?)", re.I),
    re.compile(r"(?:科学家|scientists?|专家|experts?).{0,15}(?:发现|found|发现|discovered|证明|proved)", re.I),
]


class NoRefusalScanner:
    def scan(self, text: str) -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0
        for pattern in _REFUSAL_PATTERNS:
            match = pattern.search(text)
            if match:
                score = max(score, 0.8)
                findings.append(
                    Finding(
                        rule_id="OS-001",
                        severity=Severity.HIGH,
                        description=f'检测到模型拒绝响应: "{match.group()[:60]}"',
                        remediation="调整Prompt措辞避免触发安全拒绝, 或降低请求敏感度",
                    )
                )
        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.NO_REFUSAL,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )


class BiasScanner:
    def scan(self, text: str) -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0
        for pattern, bias_type, severity in _BIAS_PATTERNS:
            match = pattern.search(text)
            if match:
                score = max(score, 0.7)
                findings.append(
                    Finding(
                        rule_id="OS-002",
                        severity=severity,
                        description=f'检测到输出偏见({bias_type}): "{match.group()[:60]}"',
                        remediation=f"修改输出消除{bias_type}, 使用中立包容的表述",
                    )
                )
        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.BIAS,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )


class ToxicityScanner:
    def scan(self, text: str) -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0
        for pattern, toxic_type, severity in _TOXICITY_PATTERNS:
            match = pattern.search(text)
            if match:
                if severity == Severity.CRITICAL:
                    score = max(score, 1.0)
                else:
                    score = max(score, 0.8)
                findings.append(
                    Finding(
                        rule_id="OS-003",
                        severity=severity,
                        description=f'检测到毒性内容({toxic_type}): "{match.group()[:60]}"',
                        remediation=f"移除或替换{toxic_type}内容, 添加内容审核过滤",
                    )
                )
        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.TOXICITY,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )


class RelevanceScanner:
    def __init__(self, similarity_threshold: float = 0.3) -> None:
        self._threshold = similarity_threshold

    def scan(self, text: str, *, context: str = "") -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0
        if context and text:
            overlap = self._compute_overlap(text, context)
            if overlap < self._threshold:
                score = 1.0 - overlap
                findings.append(
                    Finding(
                        rule_id="OS-004",
                        severity=Severity.MEDIUM,
                        description=f"输出与输入相关性低(重叠度={overlap:.2f}), 输出可能偏题",
                        remediation="加强Prompt对输出主题的约束, 添加主题聚焦指令",
                        details={"overlap_score": round(overlap, 4)},
                    )
                )
        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.RELEVANCE,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )

    @staticmethod
    def _compute_overlap(text: str, context: str) -> float:
        def _char_ngrams(s: str, n: int = 2) -> set[str]:
            cleaned = re.sub(r"\s+", "", s.lower())
            if len(cleaned) < n:
                return {cleaned}
            return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}

        def _word_ngrams(s: str, n: int = 2) -> set[str]:
            words = s.lower().split()
            if len(words) < n:
                return {s.lower()}
            return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}

        char_ng_text = _char_ngrams(text)
        char_ng_ctx = _char_ngrams(context)
        word_ng_text = _word_ngrams(text)
        word_ng_ctx = _word_ngrams(context)
        char_jaccard = (
            len(char_ng_text & char_ng_ctx) / max(len(char_ng_text | char_ng_ctx), 1)
            if char_ng_text and char_ng_ctx
            else 0.0
        )
        word_jaccard = (
            len(word_ng_text & word_ng_ctx) / max(len(word_ng_text | word_ng_ctx), 1)
            if word_ng_text and word_ng_ctx
            else 0.0
        )
        return max(char_jaccard, word_jaccard)


class FactualConsistencyScanner:
    def __init__(self, reference_facts: dict[str, str] | None = None) -> None:
        self._reference_facts = reference_facts or {}

    def scan(self, text: str) -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0

        dates = _DATE_PATTERN.findall(text)
        if dates:
            for year, month, day in dates:
                y, m, d = int(year), int(month), int(day)
                if not (1900 <= y <= 2030 and 1 <= m <= 12 and 1 <= d <= 31):
                    score = max(score, 0.7)
                    findings.append(
                        Finding(
                            rule_id="OS-005",
                            severity=Severity.MEDIUM,
                            description=f"检测到可能的事实错误: 日期 {year}/{month}/{day} 不合理",
                            remediation="验证日期数据来源, 标注不确定性或修正为准确日期",
                        )
                    )

        for signal in _FABRICATION_SIGNALS:
            if signal.search(text):
                stats = _STAT_PATTERN.findall(text)
                if stats:
                    score = max(score, 0.6)
                    findings.append(
                        Finding(
                            rule_id="OS-005",
                            severity=Severity.MEDIUM,
                            description="输出包含未经验证的统计数据引用, 可能是幻觉",
                            remediation="标注数据来源, 添加'请以官方数据为准'声明, 或移除具体数值",
                        )
                    )
                    break

        if self._reference_facts:
            for key, correct_value in self._reference_facts.items():
                if key in text and correct_value not in text:
                    score = max(score, 0.8)
                    findings.append(
                        Finding(
                            rule_id="OS-005",
                            severity=Severity.HIGH,
                            description=f"事实不一致: '{key}' 对应值应为 '{correct_value}'",
                            remediation=f"将 '{key}' 的值修正为 '{correct_value}' 或标注来源",
                        )
                    )

        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.FACTUAL_CONSISTENCY,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )


class CitationScanner:
    def __init__(self, *, check_url_reachable: bool = False) -> None:
        self._check_url_reachable = check_url_reachable

    def scan(self, text: str) -> OutputScanResult:
        start = time.perf_counter()
        findings = []
        score = 0.0

        urls = _URL_PATTERN.findall(text)
        has_citation_keywords = bool(
            re.search(r"(?:引用|cite|来源|source|参考|reference|参考文献|bibliography)", text, re.I)
        )

        if has_citation_keywords and not urls:
            score = max(score, 0.6)
            findings.append(
                Finding(
                    rule_id="OS-006",
                    severity=Severity.MEDIUM,
                    description="声明了引用/来源但未提供URL链接, 引用不可验证",
                    remediation="为每个引用添加可访问的URL来源链接",
                )
            )

        if urls:
            bare_urls = [u for u in urls if not re.search(r"\[[^\]]*\]\(" + re.escape(u[:30]), text)]
            if bare_urls and has_citation_keywords:
                score = max(score, 0.3)

        factual_claims = re.findall(
            r"(?:根据|据|according\s*to|基于|based\s*on).{0,50}(?:研究|study|调查|survey|数据|data|报告|report)",
            text,
            re.I,
        )
        if factual_claims and not urls:
            score = max(score, 0.7)
            findings.append(
                Finding(
                    rule_id="OS-006",
                    severity=Severity.HIGH,
                    description=f"检测到{len(factual_claims)}个事实声明但无来源引用, 可能是幻觉",
                    remediation="为每个事实声明添加可追溯的来源引用(URL/论文/官方数据)",
                )
            )

        elapsed = (time.perf_counter() - start) * 1000
        return OutputScanResult(
            scanner=OutputScannerType.CITATION,
            passed=len(findings) == 0,
            score=score,
            findings=findings,
            latency_ms=elapsed,
        )


class OutputScanEngine:
    def __init__(
        self,
        *,
        enable_no_refusal: bool = True,
        enable_bias: bool = True,
        enable_toxicity: bool = True,
        enable_relevance: bool = True,
        enable_factual: bool = True,
        enable_citation: bool = True,
        reference_facts: dict[str, str] | None = None,
        relevance_threshold: float = 0.3,
    ) -> None:
        self._scanners: list[tuple[str, Any]] = []
        if enable_no_refusal:
            self._scanners.append(("no_refusal", NoRefusalScanner()))
        if enable_bias:
            self._scanners.append(("bias", BiasScanner()))
        if enable_toxicity:
            self._scanners.append(("toxicity", ToxicityScanner()))
        if enable_relevance:
            self._scanners.append(("relevance", RelevanceScanner(similarity_threshold=relevance_threshold)))
        if enable_factual:
            self._scanners.append(("factual", FactualConsistencyScanner(reference_facts=reference_facts)))
        if enable_citation:
            self._scanners.append(("citation", CitationScanner()))

    def scan(self, text: str, *, context: str = "") -> OutputScanReport:
        start = time.perf_counter()
        results = []
        for name, scanner in self._scanners:
            if name == "relevance":
                result = scanner.scan(text, context=context)
            else:
                result = scanner.scan(text)
            results.append(result)

        all_passed = all(r.passed for r in results)
        scores = [r.score for r in results if r.score > 0]
        overall_score = max(scores) if scores else 0.0

        elapsed = (time.perf_counter() - start) * 1000

        return OutputScanReport(
            text=text[:200],
            results=results,
            overall_passed=all_passed,
            overall_score=overall_score,
            scan_time_ms=elapsed,
        )

    @property
    def scanner_names(self) -> list[str]:
        return [name for name, _ in self._scanners]
