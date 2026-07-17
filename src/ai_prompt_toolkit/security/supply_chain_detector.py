"""供应链攻击检测器——检测Prompt中引用的外部资源是否存在风险。

参考: agent-security-scanner-mcp (包幻觉检测4.3M+包)、whitney (AI依赖SBOM)
覆盖: 外部URL风险、包引用幻觉、依赖注入、不可信资源加载
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class SupplyChainMatch:
    match_type: str
    value: str
    line_number: int
    risk_level: str
    description: str


_SUSPICIOUS_URL_PATTERNS = [
    re.compile(r'https?://(?:bit\.ly|tinyurl|t\.co|ow\.ly|is\.gd|shorturl|clk\.ink|shorte\.st)/\S+', re.IGNORECASE),
    re.compile(r'https?://(?:pastebin|gist\.github|hastebin|dpaste|ghostbin|justpaste)\.com/\S+', re.IGNORECASE),
    re.compile(r'https?://\S+\.(?:xyz|top|click|download|stream|ga|cf|ml|tk|pw|cc|ws)/?\S*', re.IGNORECASE),
    re.compile(r'https?://\S+@\S+\.\S+', re.IGNORECASE),
    re.compile(r'javascript:\s*\S+', re.IGNORECASE),
    re.compile(r'data:\s*text/html\s*;\s*base64\s*,\S+', re.IGNORECASE),
]

_EXTERNAL_LOAD_PATTERNS = [
    re.compile(r'(?:import|include|require|load|fetch|from|source)\s+.*(?:https?://|ftp://|file://)', re.IGNORECASE),
    re.compile(r'(?:pip\s+install|npm\s+install|go\s+get|cargo\s+add)\s+\S+', re.IGNORECASE),
    re.compile(r'(?:curl|wget|fetch|download)\s+.*(?:https?://|ftp://)', re.IGNORECASE),
    re.compile(r'(?:exec|execute|run|eval|system)\s*\(.*(?:fetch|request|get|load|import)', re.IGNORECASE),
]

_PACKAGE_HALLUCINATION_PATTERNS = [
    re.compile(r'(?:pip\s+install|pip3\s+install|python\s+-m\s+pip\s+install)\s+([a-zA-Z0-9_-]+)', re.IGNORECASE),
    re.compile(r'(?:npm\s+install|yarn\s+add|pnpm\s+add)\s+(@?[a-zA-Z0-9/-]+)', re.IGNORECASE),
    re.compile(r'(?:go\s+get|go\s+install)\s+([a-zA-Z0-9/._-]+)', re.IGNORECASE),
    re.compile(r'(?:cargo\s+add)\s+([a-zA-Z0-9_-]+)', re.IGNORECASE),
]

_KNOWN_TYPO_SQUAT_PATTERNS = [
    (re.compile(r'nump[yi]', re.IGNORECASE), "可能是numpy的拼写错误（typosquatting）"),
    (re.compile(r'reqests', re.IGNORECASE), "可能是requests的拼写错误（typosquatting）"),
    (re.compile(r'djnago', re.IGNORECASE), "可能是django的拼写错误（typosquatting）"),
    (re.compile(r'flas[kc]', re.IGNORECASE), "可能是flask的拼写错误（typosquatting）"),
    (re.compile(r'tensrflow', re.IGNORECASE), "可能是tensorflow的拼写错误（typosquatting）"),
    (re.compile(r'pyton', re.IGNORECASE), "可能是python的拼写错误（typosquatting）"),
    (re.compile(r'pandsa', re.IGNORECASE), "可能是pandas的拼写错误（typosquatting）"),
]

_PROMPT_INJECTION_VIA_RESOURCE = [
    re.compile(r'(?:从|访问|读取|加载|fetch|load|read|access)\s*(?:以下|下面的|这个|the\s+following|this)?\s*(?:URL|链接|网址|网页|网站|website|link)', re.IGNORECASE),
    re.compile(r'(?:执行|运行|eval|execute|run)\s*(?:上面|以下|下面的|the\s+following|above|below)\s*(?:代码|脚本|命令|code|script|command)', re.IGNORECASE),
]


class SupplyChainDetector:
    def detect(self, text: str) -> list[SupplyChainMatch]:
        matches: list[SupplyChainMatch] = []
        lines = text.splitlines()

        for line_num, line in enumerate(lines, 1):
            for pattern in _SUSPICIOUS_URL_PATTERNS:
                if pattern.search(line):
                    matches.append(SupplyChainMatch(
                        match_type="suspicious_url",
                        value=pattern.search(line).group(0)[:80],
                        line_number=line_num,
                        risk_level="high",
                        description="可疑URL（短链接/粘贴站/可疑域名）",
                    ))
                    break

            for pattern in _EXTERNAL_LOAD_PATTERNS:
                if pattern.search(line):
                    matches.append(SupplyChainMatch(
                        match_type="external_load",
                        value=line.strip()[:80],
                        line_number=line_num,
                        risk_level="high",
                        description="外部资源加载（可能引入不可信内容）",
                    ))
                    break

            for pattern, desc in _KNOWN_TYPO_SQUAT_PATTERNS:
                if pattern.search(line):
                    matches.append(SupplyChainMatch(
                        match_type="typosquat",
                        value=pattern.search(line).group(0),
                        line_number=line_num,
                        risk_level="medium",
                        description=desc,
                    ))

            for pattern in _PROMPT_INJECTION_VIA_RESOURCE:
                if pattern.search(line):
                    matches.append(SupplyChainMatch(
                        match_type="resource_injection",
                        value=line.strip()[:80],
                        line_number=line_num,
                        risk_level="critical",
                        description="通过外部资源注入指令的风险",
                    ))
                    break

        return matches

    def check(self, text: str) -> Finding | None:
        matches = self.detect(text)
        if not matches:
            return None

        type_counts: dict[str, int] = {}
        for m in matches:
            type_counts[m.match_type] = type_counts.get(m.match_type, 0) + 1

        max_risk = max(m.risk_level for m in matches)
        severity_map = {"critical": Severity.CRITICAL, "high": Severity.HIGH, "medium": Severity.MEDIUM, "low": Severity.LOW}
        severity = severity_map.get(max_risk, Severity.MEDIUM)

        details_list = [f"{t}: {c}处" for t, c in sorted(type_counts.items())]

        return Finding(
            rule_id="SC001",
            severity=severity,
            description=f"检测到供应链安全风险 ({', '.join(details_list)})",
            location="",
            remediation="验证外部资源来源可信度、检查包名拼写、避免加载不可信URL内容",
            details={
                "total_matches": len(matches),
                "type_counts": type_counts,
                "top_risks": [
                    {"type": m.match_type, "value": m.value, "risk": m.risk_level, "line": m.line_number}
                    for m in sorted(matches, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.risk_level, 4))[:5]
                ],
            },
        )
