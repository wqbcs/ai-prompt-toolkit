"""Prompt消毒器 — 参考PromptSage + Rebuff多层防御

核心特性:
- Base64/Hex/Unicode编码检测与解码
- 模板注入标记清理({{}}/${}/<%%>)
- 敏感信息脱敏(API Key/密码/AK-SK)
- 指令注入关键词检测与中和
- 零LLM依赖，纯规则引擎
"""
from __future__ import annotations

import base64
import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SanitizeResult:
    original_text: str = ""
    sanitized_text: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    risk_level: str = "low"

    @property
    def is_safe(self) -> bool:
        return self.risk_level in ("low", "medium")

    @property
    def action_count(self) -> int:
        return len(self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "is_safe": self.is_safe,
            "action_count": self.action_count,
            "actions": self.actions,
            "original_length": len(self.original_text),
            "sanitized_length": len(self.sanitized_text),
        }


_BASE64_PATTERN = re.compile(
    r'[A-Za-z0-9+/]{20,}={0,2}'
)

_HEX_PATTERN = re.compile(
    r'(?:\\x[0-9a-fA-F]{2}){4,}'
)

_UNICODE_ESCAPE = re.compile(
    r'(?:\\u[0-9a-fA-F]{4}){3,}'
)

_TEMPLATE_INJECTION = re.compile(
    r'\{\{.*?(?:__class__|__import__|__subclasses__|__globals__|__builtins__|eval|exec|compile|open|os\.|sys\.|subprocess).*?\}\}',
    re.DOTALL | re.IGNORECASE
)

_DOLLAR_INJECTION = re.compile(
    r'\$\{.*?(?:Runtime|Process|exec|eval|import|require).*?\}',
    re.DOTALL | re.IGNORECASE
)

_SENSITIVE_PATTERNS = [
    re.compile(r'(?:api[_-]?key|apikey)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:secret|token)\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:AK|SK)\s*[:=]\s*[A-Za-z0-9]{16,}', re.IGNORECASE),
]

_INJECTION_KEYWORDS = re.compile(
    r'(?:ignore\s+(?:previous|above|all)\s+instructions?|'
    r'disregard\s+(?:previous|above|all)\s+instructions?|'
    r'forget\s+(?:previous|above|all)\s+instructions?|'
    r'you\s+are\s+now\s+(?:DAN|jailbreak|unlocked|unfiltered)|'
    r'system\s*:\s*override|'
    r'new\s+instructions?\s*:|'
    r'stop\s+being\s+(?:an?\s+)?AI)',
    re.IGNORECASE
)

_ENCODING_BOM = re.compile(r'^\ufeff|^\ufffe')


class PromptSanitizer:
    def sanitize(self, text: str, *, level: str = "standard") -> SanitizeResult:
        result = SanitizeResult(original_text=text, sanitized_text=text)
        if level == "none":
            return result
        current = text
        current = self._remove_bom(current, result)
        current = self._decode_base64(current, result)
        current = self._decode_hex(current, result)
        current = self._decode_unicode_escapes(current, result)
        current = self._clean_template_injection(current, result)
        current = self._clean_dollar_injection(current, result)
        current = self._redact_sensitive(current, result)
        if level in ("standard", "strict"):
            current = self._neutralize_injection_keywords(current, result)
        if level == "strict":
            current = self._normalize_unicode(current, result)
            current = self._remove_invisible_chars(current, result)
        result.sanitized_text = current
        if result.action_count == 0:
            result.risk_level = "low"
        elif result.action_count <= 2:
            result.risk_level = "medium"
        elif result.action_count <= 5:
            result.risk_level = "high"
        else:
            result.risk_level = "critical"
        return result

    def _remove_bom(self, text: str, result: SanitizeResult) -> str:
        match = _ENCODING_BOM.match(text)
        if match:
            result.actions.append({"action": "remove_bom", "detail": "移除BOM标记"})
            return text[match.end():]
        return text

    def _decode_base64(self, text: str, result: SanitizeResult) -> str:
        matches = _BASE64_PATTERN.findall(text)
        for match in matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
                if decoded and any(c.isalpha() for c in decoded):
                    result.actions.append({
                        "action": "decode_base64",
                        "detail": f"检测到Base64编码: {match[:20]}... → {decoded[:30]}",
                        "risk": "high",
                    })
                    text = text.replace(match, f"[BASE64_DECODED:{decoded[:50]}]")
            except Exception:
                pass
        return text

    def _decode_hex(self, text: str, result: SanitizeResult) -> str:
        matches = _HEX_PATTERN.findall(text)
        for match in matches:
            try:
                decoded = bytes.fromhex(match.replace("\\x", "")).decode("utf-8", errors="ignore")
                if decoded:
                    result.actions.append({
                        "action": "decode_hex",
                        "detail": f"检测到Hex编码 → {decoded[:30]}",
                        "risk": "medium",
                    })
                    text = text.replace(match, f"[HEX_DECODED:{decoded[:50]}]")
            except Exception:
                pass
        return text

    def _decode_unicode_escapes(self, text: str, result: SanitizeResult) -> str:
        matches = _UNICODE_ESCAPE.findall(text)
        for match in matches:
            try:
                decoded = match.encode("utf-8").decode("unicode_escape")
                result.actions.append({
                    "action": "decode_unicode_escape",
                    "detail": f"检测到Unicode转义 → {decoded[:30]}",
                    "risk": "medium",
                })
                text = text.replace(match, f"[UNICODE_DECODED:{decoded[:50]}]")
            except Exception:
                pass
        return text

    def _clean_template_injection(self, text: str, result: SanitizeResult) -> str:
        matches = _TEMPLATE_INJECTION.findall(text)
        if matches:
            result.actions.append({
                "action": "clean_template_injection",
                "detail": f"检测到模板注入({len(matches)}处): 危险标识已中和",
                "risk": "critical",
            })
            text = _TEMPLATE_INJECTION.sub("[INJECTION_REMOVED]", text)
        return text

    def _clean_dollar_injection(self, text: str, result: SanitizeResult) -> str:
        matches = _DOLLAR_INJECTION.findall(text)
        if matches:
            result.actions.append({
                "action": "clean_dollar_injection",
                "detail": f"检测到${{}}注入({len(matches)}处): 危险标识已中和",
                "risk": "critical",
            })
            text = _DOLLAR_INJECTION.sub("[INJECTION_REMOVED]", text)
        return text

    def _redact_sensitive(self, text: str, result: SanitizeResult) -> str:
        for pattern in _SENSITIVE_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                result.actions.append({
                    "action": "redact_sensitive",
                    "detail": f"敏感信息已脱敏: {match[:15]}***",
                    "risk": "high",
                })
                if "=" in match:
                    key = match.split("=")[0] + "="
                    text = text.replace(match, key + "***REDACTED***", 1)
                elif ":" in match:
                    key = match.split(":")[0] + ":"
                    text = text.replace(match, key + "***REDACTED***", 1)
        return text

    def _neutralize_injection_keywords(self, text: str, result: SanitizeResult) -> str:
        matches = _INJECTION_KEYWORDS.findall(text)
        if matches:
            result.actions.append({
                "action": "neutralize_injection",
                "detail": f"检测到注入关键词({len(matches)}处): 已中和",
                "risk": "high",
            })
            text = _INJECTION_KEYWORDS.sub("[INJECTION_NEUTRALIZED]", text)
        return text

    def _normalize_unicode(self, text: str, result: SanitizeResult) -> str:
        import unicodedata
        normalized = unicodedata.normalize("NFKC", text)
        if normalized != text:
            result.actions.append({
                "action": "normalize_unicode",
                "detail": "Unicode已归一化(NFKC)",
                "risk": "low",
            })
        return normalized

    def _remove_invisible_chars(self, text: str, result: SanitizeResult) -> str:
        invisible = re.compile(r'[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufffe]')
        matches = invisible.findall(text)
        if matches:
            result.actions.append({
                "action": "remove_invisible",
                "detail": f"移除不可见字符({len(matches)}处)",
                "risk": "medium",
            })
            text = invisible.sub("", text)
        return text


def sanitize_prompt(text: str, *, level: str = "standard") -> SanitizeResult:
    return PromptSanitizer().sanitize(text, level=level)
