"""Prompt Diff引擎 — 参考difflib+diff-match-patch

核心特性:
- PromptDiff: 结构化Prompt差异对比
- 结构化解析: 将Prompt分解为system/instruction/examples/constraints/output_format等段
- 段级Diff: 每段独立diff，精确到行级变化
- 语义相似度: 基于编辑距离的轻量相似度计算
- DiffReport: 人类可读+机器可读的差异报告
- 合并策略: 基于结构感知的冲突解决

参考:
- python difflib (LCS diff)
- google/diff-match-patch (patch应用)
- thefuzz (模糊匹配相似度)
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_PROMPT_SECTIONS = [
    ("role", ["角色", "你是一个", "You are a", "Act as", "作为"]),
    ("instruction", ["指令", "任务", "请", "要求", "Instruction", "Task"]),
    ("examples", ["示例", "例子", "Example", "Few-shot", "示例：", "Examples:"]),
    ("constraints", ["约束", "限制", "不得", "禁止", "Constraint", "Limitation"]),
    ("output_format", ["输出格式", "格式", "Output format", "返回"]),
    ("security", ["安全", "防护", "Security", "注入"]),
    ("error_handling", ["错误处理", "异常", "Error handling", "如果无法"]),
]


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    lines = text.split("\n")
    current_section = "header"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        matched = False
        for section_name, keywords in _PROMPT_SECTIONS:
            if any(kw in stripped for kw in keywords):
                if stripped.startswith(("#", "**")) or any(c in stripped[:5] for c in "#*_-"):
                    if current_lines:
                        sections[current_section] = "\n".join(current_lines)
                    current_section = section_name
                    current_lines = [line]
                    matched = True
                    break

        if not matched:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    return sections


@dataclass
class DiffLine:
    tag: str = ""
    content: str = ""
    line_old: int = 0
    line_new: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "content": self.content,
            "line_old": self.line_old,
            "line_new": self.line_new,
        }


@dataclass
class SectionDiff:
    section_name: str = ""
    similarity: float = 1.0
    added_lines: int = 0
    removed_lines: int = 0
    changed_lines: int = 0
    lines: list[DiffLine] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section_name,
            "similarity": round(self.similarity, 3),
            "added": self.added_lines,
            "removed": self.removed_lines,
            "changed": self.changed_lines,
            "lines": [l.to_dict() for l in self.lines[:50]],
        }


@dataclass
class DiffReport:
    old_text: str = ""
    new_text: str = ""
    overall_similarity: float = 1.0
    section_diffs: list[SectionDiff] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0
    total_changed: int = 0
    sections_added: list[str] = field(default_factory=list)
    sections_removed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_similarity": round(self.overall_similarity, 3),
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "total_changed": self.total_changed,
            "sections_added": self.sections_added,
            "sections_removed": self.sections_removed,
            "section_diffs": [s.to_dict() for s in self.section_diffs],
        }

    def to_unified_diff(self, context_lines: int = 3) -> str:
        old_lines = self.old_text.splitlines(keepends=True)
        new_lines = self.new_text.splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile="old",
                tofile="new",
                n=context_lines,
            )
        )

    def summary(self) -> str:
        parts = [f"相似度: {self.overall_similarity:.1%}"]
        if self.total_added:
            parts.append(f"+{self.total_added}行")
        if self.total_removed:
            parts.append(f"-{self.total_removed}行")
        if self.total_changed:
            parts.append(f"~{self.total_changed}行")
        if self.sections_added:
            parts.append(f"新增段: {', '.join(self.sections_added)}")
        if self.sections_removed:
            parts.append(f"删除段: {', '.join(self.sections_removed)}")
        return " | ".join(parts)


def _compute_similarity(text_a: str, text_b: str) -> float:
    if not text_a and not text_b:
        return 1.0
    if not text_a or not text_b:
        return 0.0
    return difflib.SequenceMatcher(None, text_a, text_b).ratio()


def _diff_section(old_text: str, new_text: str, section_name: str) -> SectionDiff:
    similarity = _compute_similarity(old_text, new_text)

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    diff_lines: list[DiffLine] = []
    added = 0
    removed = 0
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k, line in enumerate(old_lines[i1:i2]):
                diff_lines.append(DiffLine(tag=" ", content=line, line_old=i1 + k + 1, line_new=j1 + k + 1))
        elif tag == "replace":
            changed += max(i2 - i1, j2 - j1)
            for k, line in enumerate(old_lines[i1:i2]):
                diff_lines.append(DiffLine(tag="-", content=line, line_old=i1 + k + 1))
            for k, line in enumerate(new_lines[j1:j2]):
                diff_lines.append(DiffLine(tag="+", content=line, line_new=j1 + k + 1))
        elif tag == "delete":
            removed += i2 - i1
            for k, line in enumerate(old_lines[i1:i2]):
                diff_lines.append(DiffLine(tag="-", content=line, line_old=i1 + k + 1))
        elif tag == "insert":
            added += j2 - j1
            for k, line in enumerate(new_lines[j1:j2]):
                diff_lines.append(DiffLine(tag="+", content=line, line_new=j1 + k + 1))

    return SectionDiff(
        section_name=section_name,
        similarity=similarity,
        added_lines=added,
        removed_lines=removed,
        changed_lines=changed,
        lines=diff_lines,
    )


def prompt_diff(old_text: str, new_text: str) -> DiffReport:
    old_sections = _parse_sections(old_text)
    new_sections = _parse_sections(new_text)

    report = DiffReport(old_text=old_text, new_text=new_text)

    all_sections = set(old_sections.keys()) | set(new_sections.keys())
    total_sim = 0.0
    section_count = 0

    for section_name in sorted(all_sections):
        old_content = old_sections.get(section_name, "")
        new_content = new_sections.get(section_name, "")

        if section_name not in old_sections:
            report.sections_added.append(section_name)
            sec_diff = SectionDiff(
                section_name=section_name,
                similarity=0.0,
                added_lines=len(new_content.splitlines()),
                lines=[
                    DiffLine(tag="+", content=line, line_new=i + 1) for i, line in enumerate(new_content.splitlines())
                ],
            )
        elif section_name not in new_sections:
            report.sections_removed.append(section_name)
            sec_diff = SectionDiff(
                section_name=section_name,
                similarity=0.0,
                removed_lines=len(old_content.splitlines()),
                lines=[
                    DiffLine(tag="-", content=line, line_old=i + 1) for i, line in enumerate(old_content.splitlines())
                ],
            )
        else:
            sec_diff = _diff_section(old_content, new_content, section_name)

        report.section_diffs.append(sec_diff)
        report.total_added += sec_diff.added_lines
        report.total_removed += sec_diff.removed_lines
        report.total_changed += sec_diff.changed_lines

        total_sim += sec_diff.similarity
        section_count += 1

    report.overall_similarity = total_sim / max(section_count, 1)
    return report


def prompt_merge(
    base_text: str,
    ours_text: str,
    theirs_text: str,
    *,
    strategy: str = "prefer_newer",
) -> str:
    ours_sections = _parse_sections(ours_text)
    theirs_sections = _parse_sections(theirs_text)
    all_sections = set(ours_sections.keys()) | set(theirs_sections.keys())

    merged_sections: dict[str, str] = {}

    for section_name in all_sections:
        ours_content = ours_sections.get(section_name, "")
        theirs_content = theirs_sections.get(section_name, "")

        if not ours_content:
            merged_sections[section_name] = theirs_content
        elif not theirs_content or ours_content == theirs_content:
            merged_sections[section_name] = ours_content
        else:
            if strategy == "prefer_newer":
                merged_sections[section_name] = theirs_content
            elif strategy == "prefer_longer":
                merged_sections[section_name] = (
                    theirs_content if len(theirs_content) > len(ours_content) else ours_content
                )
            elif strategy == "union":
                ours_lines = set(ours_content.splitlines())
                theirs_lines = theirs_content.splitlines()
                merged_lines = list(ours_content.splitlines())
                for line in theirs_lines:
                    if line not in ours_lines:
                        merged_lines.append(line)
                merged_sections[section_name] = "\n".join(merged_lines)
            else:
                merged_sections[section_name] = theirs_content

    section_order = [
        "role",
        "instruction",
        "examples",
        "constraints",
        "output_format",
        "security",
        "error_handling",
        "header",
    ]

    result_parts: list[str] = []
    for s in section_order:
        if s in merged_sections:
            result_parts.append(merged_sections.pop(s))
    for s in sorted(merged_sections.keys()):
        result_parts.append(merged_sections[s])

    return "\n\n".join(p for p in result_parts if p.strip())


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class SemanticChange:
    change_type: str
    section: str
    description: str
    impact: str = "low"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_type": self.change_type,
            "section": self.section,
            "description": self.description,
            "impact": self.impact,
            "detail": self.detail,
        }


@dataclass
class SemanticDiffReport:
    old_hash: str
    new_hash: str
    changes: list[SemanticChange] = field(default_factory=list)
    sections_added: list[str] = field(default_factory=list)
    sections_removed: list[str] = field(default_factory=list)
    sections_modified: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "changes": [c.to_dict() for c in self.changes],
            "sections_added": self.sections_added,
            "sections_removed": self.sections_removed,
            "sections_modified": self.sections_modified,
            "summary": self.summary,
        }


def semantic_diff(old_text: str, new_text: str) -> SemanticDiffReport:
    old_sections = _parse_sections(old_text)
    new_sections = _parse_sections(new_text)
    changes: list[SemanticChange] = []
    sections_added = []
    sections_removed = []
    sections_modified = []

    for section in new_sections:
        if section not in old_sections:
            sections_added.append(section)
            changes.append(
                SemanticChange(
                    change_type="section_added",
                    section=section,
                    description=f"新增'{section}'段",
                    impact="medium",
                    detail=new_sections[section][:100],
                )
            )

    for section in old_sections:
        if section not in new_sections:
            sections_removed.append(section)
            changes.append(
                SemanticChange(
                    change_type="section_removed",
                    section=section,
                    description=f"删除'{section}'段",
                    impact="high",
                    detail=old_sections[section][:100],
                )
            )

    for section in old_sections:
        if section in new_sections:
            old_content = old_sections[section]
            new_content = new_sections[section]
            if old_content != new_content:
                sections_modified.append(section)
                similarity = _compute_similarity(old_content, new_content)
                old_lines = set(old_content.strip().split("\n"))
                new_lines = set(new_content.strip().split("\n"))
                added_lines = new_lines - old_lines
                removed_lines = old_lines - new_lines

                if section == "role":
                    impact = "high"
                    desc = f"角色定义变更(相似度{similarity:.0%})"
                elif section == "security":
                    impact = "critical"
                    desc = f"安全策略变更(相似度{similarity:.0%})"
                elif section == "constraints":
                    impact = "high"
                    desc = f"约束条件变更(相似度{similarity:.0%})"
                elif section == "examples":
                    impact = "medium"
                    desc = f"示例变更(相似度{similarity:.0%})"
                else:
                    impact = "low"
                    desc = f"{section}段变更(相似度{similarity:.0%})"

                detail_parts = []
                if added_lines:
                    detail_parts.append(f"新增{len(added_lines)}行")
                if removed_lines:
                    detail_parts.append(f"删除{len(removed_lines)}行")

                changes.append(
                    SemanticChange(
                        change_type="section_modified",
                        section=section,
                        description=desc,
                        impact=impact,
                        detail=", ".join(detail_parts),
                    )
                )

    high_count = sum(1 for c in changes if c.impact in ("high", "critical"))
    crit_count = sum(1 for c in changes if c.impact == "critical")

    if crit_count > 0:
        summary = f"严重变更{crit_count}项(安全策略), 需立即审核"
    elif high_count > 0:
        summary = f"重要变更{high_count}项(角色/约束), 建议审核"
    elif changes:
        summary = f"轻微变更{len(changes)}项, 可自动合并"
    else:
        summary = "无变更"

    return SemanticDiffReport(
        old_hash=prompt_hash(old_text),
        new_hash=prompt_hash(new_text),
        changes=changes,
        sections_added=sections_added,
        sections_removed=sections_removed,
        sections_modified=sections_modified,
        summary=summary,
    )


class RollbackRisk(str):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


@dataclass
class RollbackCheckResult:
    is_safe: bool
    risk_level: str
    security_section_removed: bool
    constraints_section_removed: bool
    security_lines_removed: list[str] = field(default_factory=list)
    constraint_lines_removed: list[str] = field(default_factory=list)
    security_score_delta: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_level": self.risk_level,
            "security_section_removed": self.security_section_removed,
            "constraints_section_removed": self.constraints_section_removed,
            "security_lines_removed": self.security_lines_removed,
            "constraint_lines_removed": self.constraint_lines_removed,
            "security_score_delta": self.security_score_delta,
            "recommendations": self.recommendations,
        }


_SECURITY_KW = re.compile(
    r"(?:禁止|不允许|不得|do not|must not|never|forbidden|"
    r"验证|校验|validate|verify|authenticate|"
    r"过滤|filter|sanitize|escape|encode|"
    r"加密|encrypt|decrypt|hash|"
    r"角色|role|权限|permission|auth|"
    r"注入|inject|XSS|CSRF|SQL)",
    re.IGNORECASE,
)
_CONSTRAINT_KW = re.compile(
    r"(?:约束|constraint|限制|limit|边界|boundary|"
    r"不得|禁止|must not|shall not|"
    r"范围|range|上限|upper|下限|lower)",
    re.IGNORECASE,
)


def rollback_safety_check(old_text: str, new_text: str) -> RollbackCheckResult:
    old_sections = _parse_sections(old_text)
    new_sections = _parse_sections(new_text)

    security_section_removed = "security" in old_sections and "security" not in new_sections
    constraints_section_removed = "constraints" in old_sections and "constraints" not in new_sections

    old_lines = set(old_text.splitlines())
    new_lines = set(new_text.splitlines())
    removed_lines = old_lines - new_lines

    security_lines_removed = [l for l in removed_lines if _SECURITY_KW.search(l)]
    constraint_lines_removed = [l for l in removed_lines if _CONSTRAINT_KW.search(l)]

    old_sec_score = sum(1 for l in old_text.splitlines() if _SECURITY_KW.search(l))
    new_sec_score = sum(1 for l in new_text.splitlines() if _SECURITY_KW.search(l))
    score_delta = float(new_sec_score - old_sec_score)

    risk = RollbackRisk.SAFE
    recommendations: list[str] = []

    if security_section_removed:
        risk = RollbackRisk.DANGEROUS
        recommendations.append("CRITICAL: 安全段(security)被完全删除, 回滚将丢失所有安全防护")
    if constraints_section_removed:
        risk = RollbackRisk.DANGEROUS if risk != RollbackRisk.DANGEROUS else risk
        recommendations.append("CRITICAL: 约束段(constraints)被完全删除, 回滚将丢失所有约束条件")
    if security_lines_removed:
        if risk == RollbackRisk.SAFE:
            risk = RollbackRisk.DANGEROUS
        recommendations.append(f"删除了{len(security_lines_removed)}行安全声明, 建议逐条审核")
    if constraint_lines_removed:
        if risk == RollbackRisk.SAFE:
            risk = RollbackRisk.WARNING
        recommendations.append(f"删除了{len(constraint_lines_removed)}行约束声明, 建议确认是否必要")
    if score_delta < -2:
        if risk == RollbackRisk.SAFE:
            risk = RollbackRisk.WARNING
        recommendations.append(f"安全评分下降{abs(score_delta):.0f}分, 回滚可能引入安全降级")

    if not recommendations:
        recommendations.append("回滚安全: 无安全降级风险")

    return RollbackCheckResult(
        is_safe=(risk != RollbackRisk.DANGEROUS),
        risk_level=risk,
        security_section_removed=security_section_removed,
        constraints_section_removed=constraints_section_removed,
        security_lines_removed=security_lines_removed,
        constraint_lines_removed=constraint_lines_removed,
        security_score_delta=score_delta,
        recommendations=recommendations,
    )
