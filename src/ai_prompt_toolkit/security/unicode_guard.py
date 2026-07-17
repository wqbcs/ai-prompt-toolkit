"""Unicode清洗规范化 + Canary Token泄露防护

参考:
- prompt-armor (https://github.com/prompt-armor/prompt-armor): 5层防御, 91.7% F1, ~27ms
- prismor (https://github.com/PrismorSec/prismor): Agent运行时防火墙
- OWASP LLM Top 10 2025: LLM07 System Prompt Leakage

核心能力:
1. Unicode规范化: NFC + 零宽字符剥离 + 同形字检测
2. Canary Token: 在系统Prompt中注入可追踪标记，检测输出泄露
3. 不可见字符检测: 检测U+200B-ZWSP/U+200C-ZWNJ/U+200D-ZWJ/U+FEFF-BOM等
4. 同形字攻击检测: 检测Unicode混淆字符(如西里尔字母冒充拉丁字母)
5. RTL覆盖检测: 检测U+202E右到左覆盖攻击
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


_INVISIBLE_CHARS = {
    "\u200b": "ZWSP(零宽空格)",
    "\u200c": "ZWNJ(零宽非连接符)",
    "\u200d": "ZWJ(零宽连接符)",
    "\u2060": "WJ(字连接符)",
    "\ufeff": "BOM(字节序标记)",
    "\u00ad": "SHY(软连字符)",
    "\u180e": "MONGOLIAN_VOWEL_SEPARATOR",
    "\u2061": "FUNCTION_APPLICATION",
    "\u2062": "INVISIBLE_TIMES",
    "\u2063": "INVISIBLE_SEPARATOR",
    "\u2064": "INVISIBLE_PLUS",
}

_RTL_OVERRIDE_CHARS = {
    "\u202e": "RLO(右到左覆盖)",
    "\u202d": "LRO(左到右覆盖)",
    "\u202a": "RLE(右到左嵌入)",
    "\u202b": "LRE(左到右嵌入)",
    "\u202c": "PDF(弹出方向格式)",
}

_HOMOGLYPH_GROUPS = [
    {"a", "\u0430"},
    {"c", "\u0441"},
    {"e", "\u0435"},
    {"o", "\u043e"},
    {"p", "\u0440"},
    {"x", "\u0445"},
    {"y", "\u0443"},
    {"A", "\u0410"},
    {"B", "\u0412"},
    {"C", "\u0421"},
    {"E", "\u0415"},
    {"H", "\u041d"},
    {"K", "\u041a"},
    {"M", "\u041c"},
    {"O", "\u041e"},
    {"P", "\u0420"},
    {"T", "\u0422"},
    {"X", "\u0425"},
]

_CANARY_PREFIX = "::CANARY_"
_CANARY_SUFFIX = "::"
_CANARY_PATTERN = re.compile(r"::CANARY_[A-Z0-9]+::")


@dataclass
class UnicodeCleanResult:
    original_length: int
    cleaned_length: int
    invisible_chars_found: dict[str, int] = field(default_factory=dict)
    rtl_overrides_found: dict[str, int] = field(default_factory=dict)
    homoglyphs_found: list[dict[str, Any]] = field(default_factory=list)
    was_modified: bool = False
    risk_level: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_length": self.original_length,
            "cleaned_length": self.cleaned_length,
            "invisible_chars_found": self.invisible_chars_found,
            "rtl_overrides_found": self.rtl_overrides_found,
            "homoglyphs_found": self.homoglyphs_found,
            "was_modified": self.was_modified,
            "risk_level": self.risk_level,
        }


def clean_unicode(text: str) -> tuple[str, UnicodeCleanResult]:
    result = UnicodeCleanResult(original_length=len(text), cleaned_length=0)

    cleaned = unicodedata.normalize("NFC", text)

    invisible_found: dict[str, int] = {}
    for char, name in _INVISIBLE_CHARS.items():
        count = cleaned.count(char)
        if count > 0:
            invisible_found[name] = count
            cleaned = cleaned.replace(char, "")
    result.invisible_chars_found = invisible_found

    rtl_found: dict[str, int] = {}
    for char, name in _RTL_OVERRIDE_CHARS.items():
        count = cleaned.count(char)
        if count > 0:
            rtl_found[name] = count
            cleaned = cleaned.replace(char, "")
    result.rtl_overrides_found = rtl_found

    homoglyphs = detect_homoglyphs(cleaned)
    result.homoglyphs_found = homoglyphs

    result.cleaned_length = len(cleaned)
    result.was_modified = len(cleaned) != len(text) or unicodedata.normalize("NFC", text) != text

    issues = len(invisible_found) + len(rtl_found) + len(homoglyphs)
    if len(rtl_found) > 0:
        result.risk_level = "critical"
    elif issues >= 3:
        result.risk_level = "high"
    elif issues >= 1:
        result.risk_level = "medium"
    else:
        result.risk_level = "none"

    return cleaned, result


def detect_homoglyphs(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_positions: set[int] = set()

    for group in _HOMOGLYPH_GROUPS:
        latin_char = None
        cyrillic_char = None
        for ch in group:
            if ord(ch) < 128:
                latin_char = ch
            else:
                cyrillic_char = ch

        if not cyrillic_char:
            continue

        for i, ch in enumerate(text):
            if i in seen_positions:
                continue
            if ch == cyrillic_char:
                context_start = max(0, i - 10)
                context_end = min(len(text), i + 10)
                context = text[context_start:context_end]
                findings.append({
                    "position": i,
                    "character": ch,
                    "unicode": f"U+{ord(ch):04X}",
                    "looks_like": latin_char or "?",
                    "context": context,
                })
                seen_positions.add(i)

    return findings


def check_unicode_threats(text: str) -> list[Finding]:
    findings: list[Finding] = []

    _, clean_result = clean_unicode(text)

    for name, count in clean_result.invisible_chars_found.items():
        findings.append(Finding(
            rule_id="UNI-001",
            severity=Severity.HIGH,
            description=f"不可见字符检测: {name} ×{count}",
        ))

    for name, count in clean_result.rtl_overrides_found.items():
        findings.append(Finding(
            rule_id="UNI-002",
            severity=Severity.CRITICAL,
            description=f"RTL覆盖攻击: {name} ×{count}",
        ))

    for hg in clean_result.homoglyphs_found:
        findings.append(Finding(
            rule_id="UNI-003",
            severity=Severity.MEDIUM,
            description=f"同形字混淆: U+{hg['unicode']}({hg['looks_like']}) 位置{hg['position']}",
        ))

    return findings


@dataclass
class CanaryToken:
    token_id: str
    token_string: str
    inserted_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "token_string": self.token_string,
            "inserted_at": self.inserted_at,
        }


def generate_canary_tokens(count: int = 3) -> list[CanaryToken]:
    tokens: list[CanaryToken] = []
    for _ in range(count):
        token_id = secrets.token_hex(4).upper()
        token_string = f"{_CANARY_PREFIX}{token_id}{_CANARY_SUFFIX}"
        tokens.append(CanaryToken(token_id=token_id, token_string=token_string))
    return tokens


def inject_canary_tokens(prompt: str, count: int = 3) -> tuple[str, list[CanaryToken]]:
    tokens = generate_canary_tokens(count)
    lines = prompt.split("\n")
    if lines:
        insert_positions = [0, len(lines) // 2, len(lines) - 1]
        for i, token in enumerate(tokens[:min(count, 3)]):
            pos = insert_positions[i % len(insert_positions)]
            lines.insert(pos + i, token.token_string)
    return "\n".join(lines), tokens


def check_canary_leakage(output: str, tokens: list[CanaryToken]) -> list[Finding]:
    findings: list[Finding] = []
    leaked_tokens: list[str] = []

    for token in tokens:
        if token.token_string in output:
            leaked_tokens.append(token.token_string)

    all_canary_matches = _CANARY_PATTERN.findall(output)

    if leaked_tokens:
        findings.append(Finding(
            rule_id="CANARY-001",
            severity=Severity.CRITICAL,
            description=f"系统Prompt泄露! 检测到{len(leaked_tokens)}个Canary Token在输出中出现: {', '.join(leaked_tokens)}",
        ))
    elif all_canary_matches:
        findings.append(Finding(
            rule_id="CANARY-002",
            severity=Severity.HIGH,
            description=f"疑似Prompt泄露! 检测到{len(all_canary_matches)}个未知Canary格式标记",
        ))

    return findings


def scan_unicode_and_canary(text: str) -> list[Finding]:
    findings = check_unicode_threats(text)
    canary_matches = _CANARY_PATTERN.findall(text)
    if canary_matches:
        findings.append(Finding(
            rule_id="CANARY-003",
            severity=Severity.MEDIUM,
            description=f"文本中包含{len(canary_matches)}个Canary Token标记(可能为已注入的泄露追踪标记)",
        ))
    return findings
