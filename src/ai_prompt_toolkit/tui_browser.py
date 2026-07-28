"""TUI浏览器 — Rich交互式Lint结果浏览

基于Rich Tree+Table实现轻量交互式浏览:
- 树形展示: 文件 > 规则类别 > 具体发现
- 颜色编码: CRITICAL红色/HIGH橙色/MEDIUM黄色/LOW蓝色
- 代码片段: 展示问题代码上下文
- 统计摘要: 分类统计+评分
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


_SEVERITY_STYLES = {
    "critical": ("bold red", "CRITICAL"),
    "high": ("bold yellow", "HIGH"),
    "medium": ("yellow", "MEDIUM"),
    "low": ("cyan", "LOW"),
    "info": ("dim cyan", "INFO"),
}


def _sev_text(severity: str) -> Text:
    style, label = _SEVERITY_STYLES.get(severity, ("", severity.upper()))
    return Text(f" {label} ", style=style)


def render_interactive_results(
    results: list[Any],
    avg_score: float,
    total_findings: int,
    total_files: int,
) -> None:
    console = Console()

    tree = Tree("[bold blue]Lint Results", guide_style="dim blue")

    by_file: dict[str, list[Any]] = {}
    for r in results:
        by_file.setdefault(r.template_id, []).extend(r.findings)

    for filename, findings in by_file.items():
        if not findings:
            continue
        file_node = tree.add(f"[bold]{filename}[/] ({len(findings)} findings)")

        by_category: dict[str, list[Any]] = {}
        for f in findings:
            cat = getattr(f, "category", "other") or "other"
            by_category.setdefault(cat, []).append(f)

        for cat, cat_findings in by_category.items():
            cat_node = file_node.add(f"[dim]{cat}[/] ({len(cat_findings)})")
            for f in cat_findings:
                sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                style, _ = _SEVERITY_STYLES.get(sev, ("", ""))
                cat_node.add(Text.assemble(
                    _sev_text(sev),
                    Text(f" {f.rule_id}: {f.description}"),
                ))

    table = Table(title="Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    table.add_row("Files", str(total_files))
    table.add_row("Avg Score", f"{avg_score:.1f}/100")
    table.add_row("Total Findings", str(total_findings))

    sev_counts: dict[str, int] = {}
    for r in results:
        for f in r.findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
    for sev in ("critical", "high", "medium", "low"):
        if sev in sev_counts:
            style, label = _SEVERITY_STYLES.get(sev, ("", sev))
            table.add_row(label, f"[{style}]{sev_counts[sev]}[/{style}]")

    grade = _score_to_grade(avg_score)
    grade_style = {"S": "bold green", "A": "green", "B": "yellow", "C": "yellow", "D": "red", "F": "bold red"}.get(grade, "")
    table.add_row("Grade", f"[{grade_style}]{grade}[/{grade_style}]")

    group = Group(tree, table)
    console.print(Panel(group, title="[bold blue]ai-prompt-toolkit lint --tui[/]", border_style="blue"))


def _score_to_grade(score: float) -> str:
    if score >= 95:
        return "S"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
