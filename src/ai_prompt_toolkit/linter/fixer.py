"""Fixer — Prompt自动修复器，独立模块

仅修复auto_fixable=True的规则
输出修复diff
非--fix模式禁止修改任何文件
"""
from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from typing import Any

from ai_prompt_toolkit.linter.rules import (
    _AMBIGUOUS_WORDS,
    _SENSITIVE_PATTERNS,
)
from ai_prompt_toolkit.types import Finding

logger = logging.getLogger(__name__)

AUTO_FIXABLE_RULES = {"P005", "P006", "P016", "P003", "P010", "P025", "P053"}

AMBIGUOUS_REPLACEMENTS: dict[str, str] = {
    "可能": "需要",
    "大概": "具体",
    "也许": "务必",
    "maybe": "must",
    "perhaps": "specifically",
    "possibly": "definitely",
    "some": "specific",
    "差不多": "精确",
    "左右": "具体",
}


@dataclass
class FixResult:
    rule_id: str
    original_text: str
    fixed_text: str
    description: str

    @property
    def diff(self) -> str:
        original_lines = self.original_text.splitlines(keepends=True)
        fixed_lines = self.fixed_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            original_lines, fixed_lines,
            fromfile="original", tofile="fixed",
            lineterm="",
        )
        return "".join(diff)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "original_length": len(self.original_text),
            "fixed_length": len(self.fixed_text),
        }


class Fixer:
    def fix(self, text: str, findings: list[Finding], dry_run: bool = False) -> tuple[str, list[FixResult]]:
        current = text
        results: list[FixResult] = []
        for finding in findings:
            if finding.rule_id not in AUTO_FIXABLE_RULES:
                continue
            before = current
            current = self._apply_fix(finding, current)
            if current != before:
                results.append(FixResult(
                    rule_id=finding.rule_id,
                    original_text=before,
                    fixed_text=current,
                    description=f"修复规则 {finding.rule_id}",
                ))
        if dry_run:
            logger.info("dry-run模式: 不实际修改文件，共 %d 处可修复", len(results))
            return text, results
        return current, results

    def _apply_fix(self, finding: Finding, text: str) -> str:
        rule_id = finding.rule_id
        if rule_id == "P005":
            if len(text) < 50:
                return text + "\n\n请按照以上要求进行回答。"
        elif rule_id == "P006":
            for pattern in _SENSITIVE_PATTERNS:
                match = pattern.search(text)
                if match:
                    original = match.group(0)
                    if "=" in original:
                        redacted = original.split("=")[0] + "=***REDACTED***"
                    elif ":" in original:
                        redacted = original.split(":")[0] + ":***REDACTED***"
                    else:
                        redacted = "***REDACTED***"
                    return text.replace(original, redacted, 1)
        elif rule_id == "P016":
            ambiguous = _AMBIGUOUS_WORDS.findall(text)
            for word in ambiguous:
                replacement = AMBIGUOUS_REPLACEMENTS.get(word.lower())
                if replacement:
                    return text.replace(word, replacement, 1)
        return text
