"""Prompt Linter 主入口——加载规则、解析模板、执行检查、生成报告。"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import (
    LintRule,
    get_all_rules,
    get_rule,
    run_all_checks,
    _RULE_MAP,
    _AMBIGUOUS_WORDS,
    _SENSITIVE_PATTERNS,
)


@dataclass
class LintResult:
    template_id: str
    findings: list[Finding] = field(default_factory=list)
    rule_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    lint_time_ms: float = 0.0
    auto_fixed: bool = False
    fixed_findings: list[Finding] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0

    @property
    def has_errors(self) -> bool:
        return any(f.severity >= Severity.HIGH for f in self.findings)

    @property
    def score(self) -> float:
        if self.rule_count == 0:
            return 100.0
        return round((self.passed_count / self.rule_count) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "findings": [f.to_dict() for f in self.findings],
            "rule_count": self.rule_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "lint_time_ms": self.lint_time_ms,
            "auto_fixed": self.auto_fixed,
            "fixed_findings": [f.to_dict() for f in self.fixed_findings],
            "score": self.score,
        }


@dataclass
class FixAction:
    rule_id: str
    original: str
    replacement: str
    description: str


class PromptLinter:
    def __init__(self, *, rules: list[str] | None = None, exclude: list[str] | None = None) -> None:
        self._all_rules = get_all_rules()
        self._active_rules = self._resolve_rules(rules, exclude)
        self._rule_ids = {r.rule_id for r in self._active_rules}

    def _resolve_rules(self, include: list[str] | None, exclude: list[str] | None) -> list[LintRule]:
        rules = list(self._all_rules)
        if include:
            rules = [r for r in rules if r.rule_id in include]
        if exclude:
            exclude_set = set(exclude)
            rules = [r for r in rules if r.rule_id not in exclude_set]
        return rules

    @property
    def active_rules(self) -> list[LintRule]:
        return list(self._active_rules)

    _KNOWLEDGE_EXCLUDED_RULES = frozenset({"P001", "P002", "P018", "P019", "P020"})

    def lint(self, template_id: str, text: str, *, fix: bool = False,
            template_type: str = "prompt") -> LintResult:
        start = time.perf_counter()

        rule_ids = self._rule_ids
        if template_type == "knowledge":
            rule_ids = rule_ids - self._KNOWLEDGE_EXCLUDED_RULES

        all_findings = run_all_checks(text)
        findings = [f for f in all_findings if f.rule_id in rule_ids]

        fixed_findings: list[Finding] = []
        if fix:
            text, fixed_findings = self._apply_fixes(text, findings)
            findings = [f for f in findings if f not in fixed_findings]

        rule_count = len(rule_ids)
        failed_count = len(findings) + len(fixed_findings)
        passed_count = rule_count - len(findings)

        elapsed = (time.perf_counter() - start) * 1000

        return LintResult(
            template_id=template_id,
            findings=findings,
            rule_count=rule_count,
            passed_count=passed_count,
            failed_count=failed_count,
            lint_time_ms=round(elapsed, 2),
            auto_fixed=fix,
            fixed_findings=fixed_findings,
        )

    def lint_batch(self, items: list[tuple[str, str]], *, fix: bool = False) -> list[LintResult]:
        return [self.lint(tid, text, fix=fix) for tid, text in items]

    def _apply_fixes(self, text: str, findings: list[Finding]) -> tuple[str, list[Finding]]:
        fixed: list[Finding] = []
        current = text

        for finding in findings:
            action = self._get_fix_action(finding, current)
            if action is None:
                continue
            current = current.replace(action.original, action.replacement, 1)
            fixed.append(finding)

        return current, fixed

    def _get_fix_action(self, finding: Finding, text: str) -> FixAction | None:
        rule_id = finding.rule_id

        if rule_id == "P005":
            if len(text) < 50:
                return FixAction(
                    rule_id=rule_id,
                    original=text[:30],
                    replacement=text + "\n\n请按照以上要求进行回答。",
                    description="补充最低内容要求",
                )

        if rule_id == "P016":
            ambiguous = _AMBIGUOUS_WORDS.findall(text)
            if ambiguous:
                first = ambiguous[0]
                replacements = {
                    "可能": "需要", "大概": "具体", "也许": "务必",
                    "maybe": "must", "perhaps": "specifically",
                    "possibly": "definitely", "some": "specific",
                    "差不多": "精确", "左右": "具体",
                }
                replacement = replacements.get(first.lower(), "具体")
                return FixAction(
                    rule_id=rule_id,
                    original=first,
                    replacement=replacement,
                    description=f"替换歧义词 '{first}' → '{replacement}'",
                )

        if rule_id == "P006":
            for pattern in _SENSITIVE_PATTERNS:
                match = pattern.search(text)
                if match:
                    return FixAction(
                        rule_id=rule_id,
                        original=match.group(0),
                        replacement=match.group(0).split("=")[0] + "=***REDACTED***"
                        if "=" in match.group(0)
                        else match.group(0).split(":")[0] + ":***REDACTED***",
                        description="遮蔽敏感信息",
                    )

        return None
