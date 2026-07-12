"""注入检测器——基于预编译正则的 Prompt 注入模式匹配。"""

from __future__ import annotations

import re
import time
from typing import Any

from prompt_toolkit.types import Finding, Severity
from prompt_toolkit.security.types import InjectionRule


_BUILTIN_RULES: list[InjectionRule] = [
    InjectionRule(
        rule_id="INJ-001",
        name="指令覆盖",
        pattern=r"ignore\s+.*previous\s+.*instruction",
        severity=Severity.HIGH,
        description="检测到指令覆盖模式：尝试让模型忽略之前的指令",
        remediation="移除或重写指令覆盖语句，确保Prompt遵循预期流程",
    ),
    InjectionRule(
        rule_id="INJ-002",
        name="角色劫持",
        pattern=r"you\s+are\s+now\s+.*(?:admin|root|system)",
        severity=Severity.HIGH,
        description="检测到角色劫持模式：尝试将模型角色切换为高权限身份",
        remediation="移除角色切换语句，或使用明确的角色边界约束",
    ),
    InjectionRule(
        rule_id="INJ-003",
        name="数据外泄",
        pattern=r"(?:output|print|send)\s+.*(?:secret|key|token)",
        severity=Severity.HIGH,
        description="检测到数据外泄模式：尝试让模型输出敏感信息",
        remediation="移除敏感信息输出指令，添加输出过滤约束",
    ),
    InjectionRule(
        rule_id="INJ-004",
        name="越权操作",
        pattern=r"(?:execute|run|eval|exec)\s+.*command",
        severity=Severity.MEDIUM,
        description="检测到越权操作模式：尝试执行系统命令",
        remediation="移除命令执行语句，限制模型操作范围",
    ),
    InjectionRule(
        rule_id="INJ-005",
        name="模板逃逸",
        pattern=r"\{\{[^#/].*?\}\}.*\{\{[^#/]",
        severity=Severity.MEDIUM,
        description="检测到模板逃逸模式：连续的模板插值可能被利用逃逸沙箱",
        remediation="审查模板插值使用，确保不可被用户输入注入",
    ),
]


class InjectionDetector:
    def __init__(self, rules: list[InjectionRule] | None = None, *, extra_rules: list[InjectionRule] | None = None) -> None:
        self._rules = list(rules or _BUILTIN_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)
        self._compiled: list[tuple[InjectionRule, re.Pattern[str]]] = []
        self._compile_rules()

    def _compile_rules(self) -> None:
        self._compiled = [
            (rule, re.compile(rule.pattern, re.IGNORECASE | re.DOTALL))
            for rule in self._rules
        ]

    @property
    def rules(self) -> list[InjectionRule]:
        return list(self._rules)

    def add_rule(self, rule: InjectionRule) -> None:
        self._rules.append(rule)
        compiled = re.compile(rule.pattern, re.IGNORECASE | re.DOTALL)
        self._compiled.append((rule, compiled))

    def remove_rule(self, rule_id: str) -> bool:
        new_rules = [r for r in self._rules if r.rule_id != rule_id]
        if len(new_rules) == len(self._rules):
            return False
        self._rules = new_rules
        self._compile_rules()
        return True

    def detect(self, text: str, *, template_id: str = "") -> list[Finding]:
        start = time.perf_counter()
        findings: list[Finding] = []
        lines = text.splitlines()

        for rule, pattern in self._compiled:
            for line_idx, line in enumerate(lines):
                match = pattern.search(line)
                if match:
                    findings.append(
                        Finding(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            description=rule.description,
                            location=f"line {line_idx + 1}",
                            remediation=rule.remediation,
                            details={
                                "matched_text": match.group(0),
                                "template_id": template_id,
                                "line_number": line_idx + 1,
                                "rule_name": rule.name,
                            },
                        )
                    )

            full_match = pattern.search(text)
            if full_match:
                already_found = any(
                    f.rule_id == rule.rule_id and f.details.get("matched_text") == full_match.group(0)
                    for f in findings
                )
                if not already_found:
                    findings.append(
                        Finding(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            description=rule.description,
                            location="full_text",
                            remediation=rule.remediation,
                            details={
                                "matched_text": full_match.group(0),
                                "template_id": template_id,
                                "rule_name": rule.name,
                            },
                        )
                    )

        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > 10:
            findings.append(
                Finding(
                    rule_id="INJ-PERF",
                    severity=Severity.INFO,
                    description=f"注入检测耗时 {elapsed:.1f}ms，超出10ms阈值",
                    location="",
                    remediation="优化规则或减少模板长度",
                    details={"scan_time_ms": elapsed},
                )
            )

        return findings
