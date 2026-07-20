"""Prompt结构分析检测器 — 指令-数据边界/操控栈/熵分析

参考:
- prompt-armor L4 Structural层 (边界检测, Cialdini操控6原则, Shannon熵)
- Rebuff.ai (结构化注入检测)
- IBM Adversarial Prompt Toolbox

检测能力:
1. 指令-数据边界模糊 — 系统指令和用户数据之间的边界被绕过
2. Cialdini操控6原则 — 权威/稀缺/喜好/互惠/一致/社会认同操控
3. Shannon熵异常 — 文本熵值异常(过高=编码攻击, 过低=重复注入)
4. 分隔符注入 — 试图用特殊分隔符突破Prompt边界
5. 格式操控 — 利用Markdown/HTML/XML标签操控输出
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class StructuralAnalysis:
    boundary_score: float
    manipulation_score: float
    entropy: float
    delimiter_injections: int
    format_manipulations: int
    risk_score: float
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_score": round(self.boundary_score, 3),
            "manipulation_score": round(self.manipulation_score, 3),
            "entropy": round(self.entropy, 4),
            "delimiter_injections": self.delimiter_injections,
            "format_manipulations": self.format_manipulations,
            "risk_score": round(self.risk_score, 3),
            "findings": self.findings[:10],
        }


_BOUNDARY_PATTERNS = [
    (re.compile(r'<\|im_start\|>', re.IGNORECASE), "ChatML标记注入 — 试图突破对话边界", 0.9),
    (re.compile(r'<\|im_end\|>', re.IGNORECASE), "ChatML结束标记注入", 0.85),
    (re.compile(r'\[INST\]', re.IGNORECASE), "Llama指令标记注入", 0.85),
    (re.compile(r'<<SYS>>', re.IGNORECASE), "Llama系统标记注入", 0.9),
    (re.compile(r'<\|system\|>', re.IGNORECASE), "系统角色标记注入", 0.9),
    (re.compile(r'<\|assistant\|>', re.IGNORECASE), "助手角色标记注入", 0.8),
    (re.compile(r'<\|user\|>', re.IGNORECASE), "用户角色标记注入", 0.8),
    (re.compile(r'###\s*Instruction\s*:', re.IGNORECASE), "Alpaca指令标记注入", 0.75),
    (re.compile(r'System\s*:', re.IGNORECASE), "系统指令前缀注入", 0.7),
    (re.compile(r'Human\s*:', re.IGNORECASE), "人类角色前缀注入", 0.6),
    (re.compile(r'Assistant\s*:', re.IGNORECASE), "助手角色前缀注入", 0.6),
]

_CIALDINI_PATTERNS = [
    (re.compile(r'(?:我是|I am|I\'m)\s*(?:管理员|开发者|admin|developer|owner|superuser)', re.IGNORECASE),
     "权威操控 — 声称具有特权身份", "authority", 0.8),
    (re.compile(r'(?:紧急|urgent|immediately|right now|asap|马上)', re.IGNORECASE),
     "稀缺操控 — 制造紧迫感绕过安全检查", "scarcity", 0.5),
    (re.compile(r'(?:我们|we|us)\s+(?:都知道|all know|agree|同意)', re.IGNORECASE),
     "社会认同操控 — 利用群体压力", "social_proof", 0.4),
    (re.compile(r'(?:你之前说过|you said before|you promised|你承诺过)', re.IGNORECASE),
     "一致性操控 — 利用之前承诺迫使一致", "consistency", 0.5),
    (re.compile(r'(?:帮帮我|help me out|please help|求求你)', re.IGNORECASE),
     "互惠操控 — 利用感恩心理", "reciprocity", 0.3),
    (re.compile(r'(?:我喜欢你|I like you|你是最好的|you are the best)', re.IGNORECASE),
     "喜好操控 — 利用好感心理", "liking", 0.2),
]

_DELIMITER_PATTERNS = [
    re.compile(r'---+\s*\n.*?\n---+', re.DOTALL),
    re.compile(r'===+\s*\n.*?\n===+', re.DOTALL),
    re.compile(r'\*\*\*+\s*\n.*?\n\*\*\*+', re.DOTALL),
]

_FORMAT_MANIPULATION_PATTERNS = [
    (re.compile(r'<script[^>]*>', re.IGNORECASE), "Script标签注入"),
    (re.compile(r'<iframe[^>]*>', re.IGNORECASE), "Iframe标签注入"),
    (re.compile(r'javascript\s*:', re.IGNORECASE), "JavaScript协议注入"),
    (re.compile(r'data\s*:\s*text/html', re.IGNORECASE), "Data URI注入"),
    (re.compile(r'on\w+\s*=\s*["\']', re.IGNORECASE), "事件处理器注入"),
]


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counter = Counter(text)
    length = len(text)
    entropy = 0.0
    for count in counter.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def _check_boundary(text: str) -> tuple[float, list[dict[str, Any]]]:
    score = 0.0
    findings: list[dict[str, Any]] = []
    for pattern, desc, weight in _BOUNDARY_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            score += weight * len(matches)
            findings.append({
                "type": "boundary",
                "description": desc,
                "count": len(matches),
                "weight": weight,
            })
    return min(1.0, score), findings


def _check_manipulation(text: str) -> tuple[float, list[dict[str, Any]]]:
    score = 0.0
    findings: list[dict[str, Any]] = []
    for pattern, desc, principle, weight in _CIALDINI_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            score += weight * min(len(matches), 3)
            findings.append({
                "type": "manipulation",
                "principle": principle,
                "description": desc,
                "count": len(matches),
                "weight": weight,
            })
    return min(1.0, score), findings


def _check_delimiters(text: str) -> tuple[int, list[dict[str, Any]]]:
    count = 0
    findings: list[dict[str, Any]] = []
    for pattern in _DELIMITER_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            count += len(matches)
            findings.append({
                "type": "delimiter_injection",
                "description": "可疑分隔符块 — 可能试图突破Prompt边界",
                "count": len(matches),
            })
    return count, findings


def _check_format_manipulation(text: str) -> tuple[int, list[dict[str, Any]]]:
    count = 0
    findings: list[dict[str, Any]] = []
    for pattern, desc in _FORMAT_MANIPULATION_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            count += len(matches)
            findings.append({
                "type": "format_manipulation",
                "description": desc,
                "count": len(matches),
            })
    return count, findings


def analyze_structure(text: str) -> StructuralAnalysis:
    boundary_score, boundary_findings = _check_boundary(text)
    manipulation_score, manipulation_findings = _check_manipulation(text)
    delimiter_count, delimiter_findings = _check_delimiters(text)
    format_count, format_findings = _check_format_manipulation(text)
    entropy = _shannon_entropy(text)

    all_findings = boundary_findings + manipulation_findings + delimiter_findings + format_findings

    entropy_risk = 0.0
    if entropy > 5.5:
        entropy_risk = 0.3
        all_findings.append({
            "type": "entropy_high",
            "description": f"Shannon熵异常偏高({entropy:.2f}) — 可能存在编码攻击",
            "value": round(entropy, 4),
        })
    elif entropy < 1.5 and len(text) > 100:
        entropy_risk = 0.2
        all_findings.append({
            "type": "entropy_low",
            "description": f"Shannon熵异常偏低({entropy:.2f}) — 可能存在重复注入",
            "value": round(entropy, 4),
        })

    risk_score = min(1.0, boundary_score * 0.4 + manipulation_score * 0.25 + entropy_risk * 0.15 + delimiter_count * 0.1 + format_count * 0.1)

    return StructuralAnalysis(
        boundary_score=boundary_score,
        manipulation_score=manipulation_score,
        entropy=entropy,
        delimiter_injections=delimiter_count,
        format_manipulations=format_count,
        risk_score=risk_score,
        findings=all_findings,
    )


def check_structural(text: str) -> Finding | None:
    analysis = analyze_structure(text)
    if analysis.risk_score < 0.3:
        return None

    if analysis.risk_score >= 0.7:
        severity = Severity.HIGH
    elif analysis.risk_score >= 0.5:
        severity = Severity.MEDIUM
    else:
        severity = Severity.LOW

    top_findings = sorted(analysis.findings, key=lambda f: f.get("weight", 0.5), reverse=True)[:3]
    desc_parts = [f.get("description", "")[:40] for f in top_findings]
    description = f"结构分析检测到风险 (risk={analysis.risk_score:.2f}): {'; '.join(desc_parts)}"

    return Finding(
        rule_id="STRUCT-001",
        severity=severity,
        description=description,
        remediation="检查指令-数据边界, 移除操控性表述, 修复分隔符注入",
        details=analysis.to_dict(),
    )
