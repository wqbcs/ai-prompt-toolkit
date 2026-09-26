"""PII(个人隐私信息)检测器——检测Prompt中是否泄露姓名、手机号、身份证等个人敏感信息。

参考: AegisGate (PII脱敏)、llmtrace (PII扫描)、prompt-guard (安全审计)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class PIIMatch:
    pii_type: str
    value: str
    start: int
    end: int
    confidence: float

    def redacted(self) -> str:
        if len(self.value) <= 3:
            return "*" * len(self.value)
        if self.pii_type in ("email",):
            parts = self.value.split("@")
            if len(parts) == 2:
                return parts[0][:2] + "***@" + parts[1]
        if self.pii_type in ("phone", "mobile"):
            return self.value[:3] + "****" + self.value[-4:]
        if self.pii_type in ("id_card",):
            return self.value[:4] + "**********" + self.value[-4:]
        if self.pii_type in ("bank_card",):
            return self.value[:4] + "****" + self.value[-4:]
        return self.value[:2] + "*" * max(len(self.value) - 4, 2) + self.value[-2:]


_PII_PATTERNS: list[tuple[str, re.Pattern, float]] = [
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), 0.95),
    ("mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), 0.9),
    (
        "id_card",
        re.compile(r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"),
        0.95,
    ),
    ("bank_card", re.compile(r"(?<!\d)6[0-9]{15,18}(?!\d)"), 0.8),
    (
        "ip_address",
        re.compile(r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)"),
        0.7,
    ),
    ("ipv6_address", re.compile(r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"), 0.7),
    ("passport", re.compile(r"(?<![A-Z])[A-Z][A-Z0-9]\d{7}(?!\d)"), 0.7),
    ("cn_name", re.compile(r"(?:姓名|名字|称呼|name)\s*[:：]\s*[\u4e00-\u9fff]{2,4}"), 0.6),
    (
        "address",
        re.compile(r"(?:地址|住址|addr)\s*[:：]\s*[\u4e00-\u9fff]{2,}(?:省|市|区|县|路|街|号|室|栋|单元)"),
        0.6,
    ),
    ("social_media", re.compile(r"(?:微信号|WeChat|wechat|QQ号|qq)\s*[:：]\s*\S{5,}"), 0.7),
    (
        "license_plate",
        re.compile(
            r"(?<![京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z])[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-HJ-NP-Z0-9]{4}[A-HJ-NP-Z0-9挂学警港澳]"
        ),
        0.85,
    ),
    (
        "api_key",
        re.compile(r"(?:sk|pk|ak|api_key|apikey|secret_key|access_key|private_key)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
        0.8,
    ),
]


class PIIDetector:
    def __init__(self, custom_patterns: list[tuple[str, str, float]] | None = None) -> None:
        self._patterns = list(_PII_PATTERNS)
        if custom_patterns:
            for name, pattern_str, confidence in custom_patterns:
                self._patterns.append((name, re.compile(pattern_str), confidence))

    def detect(self, text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for pii_type, pattern, confidence in self._patterns:
            for m in pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        value=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        confidence=confidence,
                    )
                )
        matches.sort(key=lambda x: x.start)
        return self._deduplicate(matches)

    def _deduplicate(self, matches: list[PIIMatch]) -> list[PIIMatch]:
        if not matches:
            return []
        result: list[PIIMatch] = [matches[0]]
        for m in matches[1:]:
            if m.start >= result[-1].end:
                result.append(m)
        return result

    def check(self, text: str) -> Finding | None:
        matches = self.detect(text)
        if not matches:
            return None
        pii_summary: dict[str, int] = {}
        for m in matches:
            pii_summary[m.pii_type] = pii_summary.get(m.pii_type, 0) + 1
        details_list = [f"{t}: {c}处" for t, c in sorted(pii_summary.items())]
        redacted_samples = [m.redacted() for m in matches[:5]]
        severity = Severity.CRITICAL if any(m.pii_type in ("id_card", "bank_card") for m in matches) else Severity.HIGH
        return Finding(
            rule_id="PII001",
            severity=severity,
            description=f"检测到个人隐私信息(PII)泄露风险 ({', '.join(details_list)})",
            location="",
            remediation="对PII数据进行脱敏处理：使用占位符替代真实数据，添加数据保护声明",
            details={
                "pii_types": pii_summary,
                "total_count": len(matches),
                "redacted_samples": redacted_samples,
            },
        )

    def redact_text(self, text: str) -> str:
        matches = self.detect(text)
        if not matches:
            return text
        result = list(text)
        for m in reversed(matches):
            result[m.start : m.end] = list(m.redacted())
        return "".join(result)
