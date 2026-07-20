"""Lint规则集扩展——P051-P055 安全合规+可维护性+鸿蒙适配

参考: promptfoo assertion规则 + OWASP LLM Top10 + 鸿蒙开发规范
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_RULES_P051_P055: list[LintRule] = [
    LintRule("P051", "硬编码凭据检测", "security", Severity.HIGH,
             "Prompt中存在硬编码的密码/API密钥/Token",
             "使用环境变量替代硬编码凭据，如{{API_KEY}}占位符"),
    LintRule("P052", "缺少输出格式约束", "quality", Severity.MEDIUM,
             "长Prompt未指定输出格式要求",
             "明确指定输出格式(JSON/Markdown/列表等)"),
    LintRule("P053", "模糊指令检测", "quality", Severity.LOW,
             "Prompt中存在模糊表述(等等/之类的/可能/适当等)",
             "使用确定性表述，明确列举所有项和具体数值"),
    LintRule("P054", "鸿蒙兼容性检查", "toolchain", Severity.MEDIUM,
             "Prompt中包含Android专用API/组件",
             "替换为鸿蒙等效接口(@ohos/Ability/ArkTS)"),
    LintRule("P055", "版本标记缺失", "toolchain", Severity.LOW,
             "Prompt缺少版本标记/Front Matter",
             "添加Front Matter version字段或版本注释"),
]

for r in _RULES_P051_P055:
    _RULE_MAP[r.rule_id] = r


_CRED_PATTERNS = [
    (re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*\S{6,}', re.IGNORECASE), "硬编码密码"),
    (re.compile(r'(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*[A-Za-z0-9_\-]{20,}', re.IGNORECASE), "硬编码API密钥"),
    (re.compile(r'(?:token|auth[_-]?token|bearer)\s*[:=]\s*[A-Za-z0-9_\-\.]{20,}', re.IGNORECASE), "硬编码Token"),
]

_AMBIGUOUS_ZH = [
    (re.compile(r'等等'), "模糊结尾'等等' — 请明确列举所有项"),
    (re.compile(r'之类的'), "模糊表述'之类的' — 请明确指定范围"),
    (re.compile(r'可能|大概|也许|应该|尽量'), "模糊词汇 — 请使用确定性表述"),
    (re.compile(r'适当|合理|一定|相关'), "模糊量词 — 请提供具体数值或标准"),
]

_HARMONYOS_ANDROID = [
    (re.compile(r'android\.(?:os|content|widget|app|intent)'), "Android专用API — 鸿蒙需替换为@ohos等效接口"),
    (re.compile(r'java\.(?:lang|util|io)'), "Java包引用 — 鸿蒙ArkTS/ETS需替换"),
    (re.compile(r'\bActivity\b|\bFragment\b|\bService\b|\bBroadcastReceiver\b'), "Android四大组件 — 鸿蒙需替换为Ability"),
]


def check_p051(text: str) -> Finding | None:
    rule = _RULE_MAP["P051"]
    matches = []
    for pattern, desc in _CRED_PATTERNS:
        for m in pattern.finditer(text):
            matches.append(desc)
    if not matches:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(matches)} 处: {', '.join(matches[:3])})",
        remediation=rule.remediation,
        details={"count": len(matches), "types": matches[:5]},
    )


def check_p052(text: str) -> Finding | None:
    rule = _RULE_MAP["P052"]
    has_output_hint = bool(re.search(
        r'(?:输出|回答|返回|格式|format|output|JSON|XML|markdown|列表)', text, re.IGNORECASE))
    if len(text) > 200 and not has_output_hint:
        return Finding(
            rule_id=rule.rule_id, severity=rule.severity,
            description=rule.description, remediation=rule.remediation,
        )
    return None


def check_p053(text: str) -> Finding | None:
    rule = _RULE_MAP["P053"]
    found = []
    for pattern, desc in _AMBIGUOUS_ZH:
        for m in pattern.finditer(text):
            found.append({"word": m.group(), "hint": desc, "line": text[:m.start()].count("\n") + 1})
    if not found:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(found)} 处模糊表述)",
        remediation=rule.remediation,
        details={"ambiguous": found[:5]},
    )


def check_p054(text: str) -> Finding | None:
    rule = _RULE_MAP["P054"]
    found = []
    for pattern, desc in _HARMONYOS_ANDROID:
        for m in pattern.finditer(text):
            found.append({"match": m.group(), "hint": desc, "line": text[:m.start()].count("\n") + 1})
    if not found:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (发现 {len(found)} 处Android专用引用)",
        remediation=rule.remediation,
        details={"android_refs": found[:5]},
    )


def check_p055(text: str) -> Finding | None:
    rule = _RULE_MAP["P055"]
    if text.startswith("---"):
        try:
            import yaml
            end = text.find("---", 3)
            if end != -1:
                fm = yaml.safe_load(text[3:end].strip())
                if isinstance(fm, dict) and "version" not in fm and "v" not in fm:
                    return Finding(
                        rule_id=rule.rule_id, severity=rule.severity,
                        description="Front Matter缺少version字段 — 建议添加版本号便于追踪变更",
                        remediation=rule.remediation,
                    )
        except Exception:
            pass
    elif len(text) > 100:
        return Finding(
            rule_id=rule.rule_id, severity=rule.severity,
            description="长Prompt缺少版本标记 — 建议添加Front Matter或版本注释",
            remediation=rule.remediation,
        )
    return None


def run_checks_p051_p055(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p051, check_p052, check_p053, check_p054, check_p055]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
