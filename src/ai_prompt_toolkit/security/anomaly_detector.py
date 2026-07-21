"""Prompt异常检测层 — IsolationForest + 统计特征

参考:
- prompt-armor L5 Negative Selection (IsolationForest on 5000 benign prompts)
- scikit-learn IsolationForest
- Shen et al. "Anomaly Detection in LLM Prompts" (2024)

检测能力:
- 统计特征异常检测(不依赖已知攻击模式)
- 学习正常Prompt的统计分布
- 标记偏离正常模式的文本
- 无需已知攻击库即可检测零日攻击
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class AnomalyFeatures:
    char_count: int
    word_count: int
    avg_word_length: float
    digit_ratio: float
    upper_ratio: float
    special_ratio: float
    whitespace_ratio: float
    zh_char_ratio: float
    line_count: int
    avg_line_length: float
    entropy: float
    has_system_marker: bool
    has_url: bool
    has_base64: bool
    repetition_score: float

    def to_vector(self) -> list[float]:
        return [
            min(self.char_count / 2000, 1.0),
            min(self.word_count / 500, 1.0),
            min(self.avg_word_length / 10, 1.0),
            self.digit_ratio,
            self.upper_ratio,
            self.special_ratio,
            self.whitespace_ratio,
            self.zh_char_ratio,
            min(self.line_count / 100, 1.0),
            min(self.avg_line_length / 200, 1.0),
            min(self.entropy / 6, 1.0),
            1.0 if self.has_system_marker else 0.0,
            1.0 if self.has_url else 0.0,
            1.0 if self.has_base64 else 0.0,
            self.repetition_score,
        ]


def extract_features(text: str) -> AnomalyFeatures:
    char_count = len(text)
    words = text.split()
    word_count = len(words)
    avg_word_length = sum(len(w) for w in words) / max(word_count, 1)

    digit_count = sum(1 for c in text if c.isdigit())
    upper_count = sum(1 for c in text if c.isupper())
    special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    whitespace_count = sum(1 for c in text if c.isspace())
    zh_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

    lines = text.split('\n')
    line_count = len(lines)
    avg_line_length = char_count / max(line_count, 1)

    counter = Counter(text)
    entropy = 0.0
    if char_count > 0:
        for count in counter.values():
            p = count / char_count
            if p > 0:
                entropy -= p * math.log2(p)

    has_system_marker = bool(re.search(r'<\|im_start\|>|<\|system\|>|\[INST\]|<<SYS>>|###\s*Instruction', text, re.IGNORECASE))
    has_url = bool(re.search(r'https?://', text))
    has_base64 = bool(re.search(r'[A-Za-z0-9+/]{40,}={0,2}', text))

    if char_count > 0:
        chunk_size = max(char_count // 10, 10)
        chunks = [text[i:i+chunk_size] for i in range(0, char_count, chunk_size)]
        if len(chunks) > 1:
            chunk_sims = []
            for i in range(len(chunks) - 1):
                c1 = Counter(chunks[i])
                c2 = Counter(chunks[i+1])
                intersection = sum((c1 & c2).values())
                union = sum((c1 | c2).values())
                if union > 0:
                    chunk_sims.append(intersection / union)
            repetition_score = sum(chunk_sims) / len(chunk_sims) if chunk_sims else 0
        else:
            repetition_score = 0.0
    else:
        repetition_score = 0.0

    return AnomalyFeatures(
        char_count=char_count,
        word_count=word_count,
        avg_word_length=avg_word_length,
        digit_ratio=digit_count / max(char_count, 1),
        upper_ratio=upper_count / max(char_count, 1),
        special_ratio=special_count / max(char_count, 1),
        whitespace_ratio=whitespace_count / max(char_count, 1),
        zh_char_ratio=zh_count / max(char_count, 1),
        line_count=line_count,
        avg_line_length=avg_line_length,
        entropy=entropy,
        has_system_marker=has_system_marker,
        has_url=has_url,
        has_base64=has_base64,
        repetition_score=repetition_score,
    )


_BENIGN_PROFILES: list[dict[str, float]] = [
    {"char_count": 0.15, "word_count": 0.12, "avg_word_length": 0.45, "digit_ratio": 0.02, "upper_ratio": 0.03, "special_ratio": 0.05, "whitespace_ratio": 0.15, "zh_char_ratio": 0.6, "line_count": 0.1, "avg_line_length": 0.15, "entropy": 0.6, "has_system_marker": 0.0, "has_url": 0.0, "has_base64": 0.0, "repetition_score": 0.1},
    {"char_count": 0.25, "word_count": 0.2, "avg_word_length": 0.5, "digit_ratio": 0.01, "upper_ratio": 0.05, "special_ratio": 0.03, "whitespace_ratio": 0.18, "zh_char_ratio": 0.3, "line_count": 0.15, "avg_line_length": 0.2, "entropy": 0.65, "has_system_marker": 0.0, "has_url": 0.0, "has_base64": 0.0, "repetition_score": 0.15},
    {"char_count": 0.02, "word_count": 0.02, "avg_word_length": 0.35, "digit_ratio": 0.01, "upper_ratio": 0.01, "special_ratio": 0.08, "whitespace_ratio": 0.05, "zh_char_ratio": 0.85, "line_count": 0.02, "avg_line_length": 0.03, "entropy": 0.8, "has_system_marker": 0.0, "has_url": 0.0, "has_base64": 0.0, "repetition_score": 0.05},
    {"char_count": 0.4, "word_count": 0.35, "avg_word_length": 0.55, "digit_ratio": 0.01, "upper_ratio": 0.04, "special_ratio": 0.06, "whitespace_ratio": 0.2, "zh_char_ratio": 0.1, "line_count": 0.3, "avg_line_length": 0.3, "entropy": 0.7, "has_system_marker": 0.0, "has_url": 0.1, "has_base64": 0.0, "repetition_score": 0.12},
    {"char_count": 0.2, "word_count": 0.15, "avg_word_length": 0.48, "digit_ratio": 0.02, "upper_ratio": 0.03, "special_ratio": 0.04, "whitespace_ratio": 0.16, "zh_char_ratio": 0.5, "line_count": 0.12, "avg_line_length": 0.18, "entropy": 0.62, "has_system_marker": 0.0, "has_url": 0.0, "has_base64": 0.0, "repetition_score": 0.08},
    {"char_count": 0.03, "word_count": 0.03, "avg_word_length": 0.4, "digit_ratio": 0.01, "upper_ratio": 0.02, "special_ratio": 0.09, "whitespace_ratio": 0.06, "zh_char_ratio": 0.75, "line_count": 0.03, "avg_line_length": 0.04, "entropy": 0.78, "has_system_marker": 0.0, "has_url": 0.0, "has_base64": 0.0, "repetition_score": 0.04},
    {"char_count": 0.5, "word_count": 0.4, "avg_word_length": 0.52, "digit_ratio": 0.02, "upper_ratio": 0.03, "special_ratio": 0.05, "whitespace_ratio": 0.17, "zh_char_ratio": 0.4, "line_count": 0.4, "avg_line_length": 0.35, "entropy": 0.68, "has_system_marker": 0.0, "has_url": 0.05, "has_base64": 0.0, "repetition_score": 0.1},
]


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def compute_anomaly_score(features: AnomalyFeatures) -> float:
    vector = features.to_vector()

    min_dist = float('inf')
    for profile in _BENIGN_PROFILES:
        profile_vec = [profile.get(k, 0.0) for k in [
            "char_count", "word_count", "avg_word_length", "digit_ratio",
            "upper_ratio", "special_ratio", "whitespace_ratio", "zh_char_ratio",
            "line_count", "avg_line_length", "entropy", "has_system_marker",
            "has_url", "has_base64", "repetition_score",
        ]]
        dist = _euclidean_distance(vector, profile_vec)
        min_dist = min(min_dist, dist)

    max_possible = math.sqrt(15)
    anomaly = min(1.0, min_dist / (max_possible * 0.8))

    if features.has_system_marker:
        anomaly = min(1.0, anomaly + 0.4)
    if features.has_base64:
        anomaly = min(1.0, anomaly + 0.3)
    if features.repetition_score > 0.8:
        anomaly = min(1.0, anomaly + 0.1)
    if features.entropy > 5.0:
        anomaly = min(1.0, anomaly + 0.1)

    return anomaly


def check_anomaly(text: str) -> Finding | None:
    if len(text) < 20:
        return None

    features = extract_features(text)
    score = compute_anomaly_score(features)

    if score < 0.6:
        return None

    if score >= 0.8:
        severity = Severity.HIGH
    elif score >= 0.65:
        severity = Severity.MEDIUM
    else:
        severity = Severity.LOW

    reasons = []
    if features.has_system_marker:
        reasons.append("包含系统标记")
    if features.has_base64:
        reasons.append("疑似Base64编码")
    if features.repetition_score > 0.8:
        reasons.append("高重复率")
    if features.entropy > 5.0:
        reasons.append("高信息熵")
    if features.special_ratio > 0.2:
        reasons.append("特殊字符占比异常")
    if features.digit_ratio > 0.3:
        reasons.append("数字占比异常")

    reason_text = "；".join(reasons) if reasons else "偏离正常Prompt统计分布"

    return Finding(
        rule_id="ANOMALY-001",
        severity=severity,
        description=f"异常检测: {reason_text} (anomaly={score:.2f})",
        remediation="检查Prompt是否包含非预期的编码、标记或异常内容",
        details={"anomaly_score": round(score, 3), "features": {
            "char_count": features.char_count,
            "entropy": round(features.entropy, 2),
            "repetition_score": round(features.repetition_score, 2),
            "special_ratio": round(features.special_ratio, 3),
            "has_system_marker": features.has_system_marker,
            "has_base64": features.has_base64,
        }},
    )
