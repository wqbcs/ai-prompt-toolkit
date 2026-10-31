"""Prompt注入预检层(Defender模式)

参考: StackOneHQ/defender — 快速预检, <10ms延迟
核心思路: 在用户输入发送给LLM之前, 通过多层快速检测拦截已知注入模式

5层防御:
1. 模式黑名单: 已知注入关键词/短语快速匹配
2. 指令提取检测: 检测用户输入中试图覆盖系统指令的模式
3. 角色切换检测: 检测"DAN"/"越狱"/"忽略之前"等角色切换
4. 编码绕过检测: 检测Base64/URL编码/HTML实体等编码绕过
5. 上下文边界检测: 检测试图突破Prompt边界的外部内容标记

设计原则:
- 快速(<10ms目标): 纯正则+字符串匹配, 无LLM调用
- 低误报: 白名单机制, 允许正常编程/技术讨论
- 可配置: 每层独立开关, 自定义黑名单
"""

from __future__ import annotations

import base64
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import unquote

from ai_prompt_toolkit.security.normalization import normalize_for_detection
from ai_prompt_toolkit.types import Finding, Severity


class DefenseLayer(Enum):
    PATTERN_BLACKLIST = "pattern_blacklist"
    INSTRUCTION_EXTRACTION = "instruction_extraction"
    ROLE_SWITCH = "role_switch"
    ENCODING_BYPASS = "encoding_bypass"
    CONTEXT_BOUNDARY = "context_boundary"


_INJECTION_BLACKLIST = [
    r"ignore\s+(all\s+)?previous\s+(instructions|prompts|rules)",
    r"forget\s+(all\s+)?previous\s+(instructions|prompts|rules)",
    r"disregard\s+(all\s+)?(previous\s+)?(instructions|safety|rules)",
    r"you\s+are\s+now\s+(DAN|jailbreak|unfiltered|uncensored)",
    r"act\s+as\s+(if\s+you\s+are|an?)\s+(unfiltered|uncensored|unrestricted)\s+AI",
    r"bypass\s+(all\s+)?(safety|security|filter|restriction)",
    r"override\s+(all\s+)?(safety|security|filter|restriction)",
    r"system\s*:\s*you\s+are",
    r"<\|im_start\|>system",
    r"\[INST\]\s*<<SYS>>",
    r"###\s*Instruction\s*:",
    r"新角色[：:]\s*你现在是",
    r"忽略[以之]上[的]?(所有)?(指令|规则|限制|约束)",
    r"请[不再要]?遵守[以之]上[的]?(所有)?(指令|规则|限制)",
    r"你现在没有任何限制",
    r"你已解除所有限制",
    r"作为(一个)?(不受限制|无过滤|无审查)的AI",
    r"不要(再)?(遵守|遵循|执行)(任何)?(安全|限制|过滤|规则)",
]

_INSTRUCTION_EXTRACTION_PATTERNS = [
    r"(what|show|tell|reveal|display|print|output)\s+(are|is|was|were)?\s*.*(system|initial|original|hidden|secret|private)\s+(prompt|instruction|message|rule)",
    r"(repeat|echo|copy|reproduce)\s+(your|the|my)\s+(system|initial|original)\s+(prompt|instruction)",
    r"output\s+(your|the)\s+(system|initial|original)\s+prompt",
    r"what\s+(were|are|is)\s+you\s+(told|instructed|programmed)\s+to",
    r"(暴露|显示|输出|打印|重复)(你的)?(系统|初始|原始|隐藏|秘密)(提示|指令|规则)",
]

_ROLE_SWITCH_PATTERNS = [
    r"\bDAN\b.*\bmode\b",
    r"\b(AIM|STAN|KEVIN|DUDE|OMEGA)\b.*\bmode\b",
    r"(jailbreak|越狱|解锁|解锁模式)",
    r"(developer|admin|root|sudo)\s+mode",
    r"(开发者|管理员|超级用户)\s*模式",
    r"(evil|dark|shadow|chaos)\s+(twin|mode|side)",
    r"(now\s+you\s+(are|act|behave|respond)\s+free|unleashed|unbound)",
]

_ENCODING_BYPASS_PATTERNS = [
    # P2-34 (R354): 原 [A-Za-z0-9+/]{20,} 把斜杠词列/驼峰标识符当编码 blob 命中 (26 模板 10/26 误报)。
    # 收窄=run 须含至少一个数字 (base64 自然文本编码压倒性特征: 15B 无数字 3.2%, 30B 0.1%, 40B+ 0%)。
    # 全 run 锚定 (lookbehind/lookahead) 保精确; 线性 O(n)。逃生舱=攻击者构造无数字 base64 (预检层, 纵深防御, 留痕)。
    r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]{20,})(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]+={0,2}(?![A-Za-z0-9+/])",
    r"%[0-9A-Fa-f]{2}(%[0-9A-Fa-f]{2}){5,}",
    r"&#x?[0-9A-Fa-f]{2,4};",
    r"\\u[0-9A-Fa-f]{4}",
    r"\\x[0-9A-Fa-f]{2}",
]

_CONTEXT_BOUNDARY_PATTERNS = [
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    r"###\s*(Human|Assistant|System)\s*:",
    r"<system>",
    r"</system>",
]

_TECHNICAL_WHITELIST = [
    r"```[\s\S]*?```",
    r"`[^`]+`",
    r"def\s+\w+\s*\(",
    r"function\s+\w+\s*\(",
    r"class\s+\w+",
    r"import\s+\w+",
    r"from\s+\w+\s+import",
]


@dataclass
class DefenseResult:
    is_safe: bool = True
    risk_score: float = 0.0
    triggered_layers: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    scan_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_score": round(self.risk_score, 3),
            "triggered_layers": self.triggered_layers,
            "findings": [f.to_dict() for f in self.findings],
            "scan_time_ms": round(self.scan_time_ms, 2),
        }


def _is_whitelisted(text: str) -> bool:
    for pattern in _TECHNICAL_WHITELIST:
        if re.search(pattern, text, re.DOTALL):
            code_blocks = re.findall(pattern, text, re.DOTALL)
            if sum(len(b) for b in code_blocks) > len(text) * 0.5:
                return True
    return False


def _check_layer(text: str, patterns: list[str], layer: DefenseLayer, severity: Severity, prefix: str) -> list[Finding]:
    findings: list[Finding] = []
    for i, pattern in enumerate(patterns, 1):
        try:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                rule_id = f"DEF-{layer.value[:3].upper()}-{i:03d}"
                sample = str(matches[0])[:80]
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=severity,
                        description=f"{prefix}: 匹配'{sample}'",
                    )
                )
        except re.error:
            pass
    return findings


class PromptDefender:
    def __init__(
        self,
        *,
        enable_pattern_blacklist: bool = True,
        enable_instruction_extraction: bool = True,
        enable_role_switch: bool = True,
        enable_encoding_bypass: bool = True,
        enable_context_boundary: bool = True,
        custom_blacklist: list[str] | None = None,
        risk_threshold: float = 0.5,
    ) -> None:
        self._layers = {
            DefenseLayer.PATTERN_BLACKLIST: (
                enable_pattern_blacklist,
                _INJECTION_BLACKLIST,
                Severity.HIGH,
                "注入黑名单",
            ),
            DefenseLayer.INSTRUCTION_EXTRACTION: (
                enable_instruction_extraction,
                _INSTRUCTION_EXTRACTION_PATTERNS,
                Severity.HIGH,
                "指令提取",
            ),
            DefenseLayer.ROLE_SWITCH: (enable_role_switch, _ROLE_SWITCH_PATTERNS, Severity.HIGH, "角色切换"),
            DefenseLayer.ENCODING_BYPASS: (
                enable_encoding_bypass,
                _ENCODING_BYPASS_PATTERNS,
                Severity.MEDIUM,
                "编码绕过",
            ),
            DefenseLayer.CONTEXT_BOUNDARY: (
                enable_context_boundary,
                _CONTEXT_BOUNDARY_PATTERNS,
                Severity.HIGH,
                "上下文边界",
            ),
        }
        self._custom_blacklist = custom_blacklist or []
        self._risk_threshold = risk_threshold

    def defend(self, text: str) -> DefenseResult:
        start = time.perf_counter()
        all_findings: list[Finding] = []
        triggered: list[str] = []

        if _is_whitelisted(text):
            elapsed = (time.perf_counter() - start) * 1000
            return DefenseResult(is_safe=True, risk_score=0.0, scan_time_ms=elapsed)

        # T1-2 (R356): 检测输入归一化（NFKC + 零宽剥离）——全角/零宽插入攻击面
        # 归一后走既有层（P3-38 取证：2 独立归一化面原静默）。行计数不变 → 行号天然正确。
        normalized = normalize_for_detection(text)
        if normalized != text:
            text = normalized

        for layer, (enabled, patterns, severity, prefix) in self._layers.items():
            if not enabled:
                continue
            findings = _check_layer(text, patterns, layer, severity, prefix)
            if findings:
                all_findings.extend(findings)
                triggered.append(layer.value)

        if self._custom_blacklist:
            custom_findings = _check_layer(
                text, self._custom_blacklist, DefenseLayer.PATTERN_BLACKLIST, Severity.HIGH, "自定义黑名单"
            )
            all_findings.extend(custom_findings)
            if custom_findings and DefenseLayer.PATTERN_BLACKLIST.value not in triggered:
                triggered.append(DefenseLayer.PATTERN_BLACKLIST.value)

        self._check_decoded_content(text, all_findings, triggered)

        risk_score = 0.0
        for f in all_findings:
            if f.severity == Severity.CRITICAL:
                risk_score += 0.8
            elif f.severity == Severity.HIGH:
                risk_score += 0.6
            elif f.severity == Severity.MEDIUM:
                risk_score += 0.4
            else:
                risk_score += 0.2
        risk_score = min(risk_score, 1.0)
        is_safe = risk_score < self._risk_threshold

        elapsed = (time.perf_counter() - start) * 1000
        return DefenseResult(
            is_safe=is_safe,
            risk_score=risk_score,
            triggered_layers=triggered,
            findings=all_findings,
            scan_time_ms=elapsed,
        )

    def _check_decoded_content(self, text: str, findings: list[Finding], triggered: list[str]) -> None:
        decoded_texts: list[str] = []

        try:
            b64_matches = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text)
            for match in b64_matches[:3]:
                try:
                    decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
                    if any(kw in decoded.lower() for kw in ["ignore", "system", "jailbreak", "越狱", "忽略"]):
                        decoded_texts.append(decoded)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if "%" in text:
                decoded_url = unquote(text)
                if decoded_url != text:
                    decoded_texts.append(decoded_url)
        except Exception:
            pass

        for decoded in decoded_texts:
            for pattern in _INJECTION_BLACKLIST[:5]:
                if re.search(pattern, decoded, re.IGNORECASE):
                    findings.append(
                        Finding(
                            rule_id="DEF-ENC-DECODED",
                            severity=Severity.HIGH,
                            description=f"编码内容中检测到注入: 匹配'{pattern[:40]}'",
                        )
                    )
                    if DefenseLayer.ENCODING_BYPASS.value not in triggered:
                        triggered.append(DefenseLayer.ENCODING_BYPASS.value)
                    break
