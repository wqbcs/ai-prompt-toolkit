"""统一输出格式（rich集成）

增强特性:
- Rich Progress: 带时间估计的进度条
- Rich Table: 彩色评估矩阵/版本列表
- Rich Tree: 版本历史/Flow DAG树形展示
- Rich Panel: 评估摘要/GEPA结果面板
- Rich Live: 实时分数刷新
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

if TYPE_CHECKING:
    from collections.abc import Sequence

console = Console()

_SEVERITY_STYLES: dict[str, tuple[str, str]] = {
    "critical": ("blink bold red", "✗✗"),
    "high": ("bold red", "✗"),
    "medium": ("bold yellow", "⚠"),
    "low": ("bold green", "ℹ"),
    "info": ("dim", "·"),
}


def success(message: str) -> None:
    console.print(f"[bold green]✓[/bold green] {message}")


def warning(message: str) -> None:
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def error(message: str) -> None:
    console.print(f"[bold red]✗[/bold red] {message}")


def info(message: str) -> None:
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def finding(severity: str, rule_id: str, description: str, remediation: str = "") -> None:
    style, marker = _SEVERITY_STYLES.get(severity, ("", "•"))
    text = Text()
    text.append(f"  {marker} ", style=style)
    text.append(f"[{rule_id}] ", style="dim")
    text.append(description)
    if remediation:
        text.append(f"\n    → {remediation}", style="dim italic")
    console.print(text)


def findings_list(findings_data: Sequence[dict[str, Any]]) -> None:
    if not findings_data:
        success("无发现项")
        return
    for f in findings_data:
        sev = f.get("severity", "info")
        rid = f.get("rule_id", "")
        desc = f.get("description", "")
        rem = f.get("remediation", "")
        finding(sev, rid, desc, rem)


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def print_table(
    title: str, columns: list[str], rows: list[list[str]], *, highlight: bool = True, border_style: str = "blue"
) -> None:
    table = Table(title=title, show_lines=False, border_style=border_style, highlight=highlight)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def print_eval_matrix(
    title: str, prompt_names: list[str], evaluator_names: list[str], cells: list[dict[str, Any]]
) -> None:
    table = Table(title=title, show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("模板", style="bold cyan", min_width=20)
    for ev in evaluator_names:
        table.add_column(ev, justify="center", min_width=12)

    for prompt in prompt_names:
        row = [prompt]
        for ev in evaluator_names:
            cell_data = next(
                (c for c in cells if c.get("prompt_name") == prompt and c.get("evaluator_name") == ev), None
            )
            if cell_data:
                score = cell_data.get("score", 0)
                max_score = cell_data.get("max_score", 10)
                passed = cell_data.get("passed", False)
                ratio = score / max_score if max_score > 0 else 0
                if passed and ratio >= 0.9:
                    style = "bold green"
                elif passed and ratio >= 0.7:
                    style = "green"
                elif passed:
                    style = "yellow"
                else:
                    style = "bold red"
                badge = "PASS" if passed else "FAIL"
                row.append(
                    f"[{style}]{score:.1f}/{max_score}[/{style}] [{'green' if passed else 'red'}]{badge}[/{'green' if passed else 'red'}]"
                )
            else:
                row.append("[dim]-[/dim]")
        table.add_row(*row)
    console.print(table)


def print_version_tree(versions: list[dict[str, Any]]) -> None:
    if not versions:
        console.print("[dim]无版本记录[/dim]")
        return
    tree = Tree("[bold cyan]版本历史[/bold cyan]")
    for v in versions:
        vid = v.get("version_id", "?")[:8]
        name = v.get("prompt_name", "")
        score = v.get("score", 0)
        source = v.get("source", "")
        created = v.get("created_at", "")
        score_style = "green" if score >= 90 else "yellow" if score >= 70 else "red"
        branch = tree.add(f"[bold]{name}[/bold] [dim]#{vid}[/dim]")
        branch.add(f"[{score_style}]分数: {score:.1f}[/{score_style}]")
        if source:
            branch.add(f"[dim]来源: {source}[/dim]")
        if created:
            branch.add(f"[dim]时间: {created}[/dim]")
    console.print(tree)


def print_flow_dag(flow_data: dict[str, Any]) -> None:
    name = flow_data.get("name", "Flow DAG")
    tree = Tree(f"[bold cyan]{name}[/bold cyan]")
    nodes = flow_data.get("nodes", {})
    edges = flow_data.get("edges", [])

    entry_targets = {e.get("target") for e in edges}
    entry_nodes = [n for n in nodes if n not in entry_targets]

    for entry in entry_nodes:
        node = nodes.get(entry, {})
        ntype = node.get("node_type", "prompt")
        branch = tree.add(f"[bold green]▸ {entry}[/bold green] [dim]({ntype})[/dim]")
        _add_flow_children(branch, entry, edges, nodes)

    console.print(tree)


def _add_flow_children(branch: Any, parent: str, edges: list[dict], nodes: dict) -> None:
    for edge in edges:
        if edge.get("source") == parent:
            target = edge.get("target", "")
            node = nodes.get(target, {})
            ntype = node.get("node_type", "prompt")
            cond = edge.get("condition", "")
            label = f"[cyan]▸ {target}[/cyan] [dim]({ntype})[/dim]"
            if cond:
                label += f" [yellow]if {cond}[/yellow]"
            child = branch.add(label)
            _add_flow_children(child, target, edges, nodes)


def print_gepa_result(result_data: dict[str, Any]) -> None:
    best = result_data.get("best_score", 0)
    initial = result_data.get("initial_score", 0)
    improvement = result_data.get("improvement", 0)
    candidates = result_data.get("candidates_explored", 0)
    generations = result_data.get("generations", 0)
    frontier = result_data.get("frontier_size", 0)

    score_style = "bold green" if improvement > 0 else "yellow" if improvement == 0 else "red"

    console.print(
        Panel(
            f"[{score_style}]初始分数: {initial:.4f} → 最优分数: {best:.4f}[/{score_style}]\n\n"
            f"提升: [{'green' if improvement > 0 else 'yellow'}]{improvement:+.4f}[/{'green' if improvement > 0 else 'yellow'}] | "
            f"候选: {candidates} | 代数: {generations} | Pareto前沿: {frontier}",
            title="[bold]GEPA反射式进化结果[/bold]",
            border_style="cyan",
        )
    )


def print_contest_result(result_data: dict[str, Any]) -> None:
    score = result_data.get("contest_score", 0)
    level = result_data.get("readiness_level", "unknown")
    pangu = result_data.get("pangu_integration", False)
    harmony = result_data.get("harmonyos_integration", False)

    level_styles = {
        "excellent": "bold green",
        "good": "green",
        "moderate": "yellow",
        "basic": "red",
        "insufficient": "bold red",
    }
    style = level_styles.get(level, "white")

    console.print(
        Panel(
            f"[{style}]赛事贴合度: {score:.1f}/10 ({level})[/{style}]\n\n"
            f"盘古集成: {'[green]✓[/green]' if pangu else '[red]✗[/red]'} | "
            f"鸿蒙集成: {'[green]✓[/green]' if harmony else '[red]✗[/red]'}",
            title="[bold]华为云赛事贴合评估[/bold]",
            border_style="cyan",
        )
    )


@dataclass
class ScanSummary:
    command: str = ""
    total_files: int = 0
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    elapsed_ms: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.critical == 0 and self.high == 0

    def render(self) -> None:
        if self.total_findings == 0:
            console.print(
                Panel(
                    f"[bold green]✓ {self.command}完成 — 无问题发现[/bold green]",
                    subtitle=f"{self.total_files} 文件 | {self.elapsed_ms / 1000:.1f}s",
                )
            )
            return

        severity_parts = []
        if self.critical:
            severity_parts.append(f"[blink bold red]{self.critical} critical[/blink bold red]")
        if self.high:
            severity_parts.append(f"[bold red]{self.high} high[/bold red]")
        if self.medium:
            severity_parts.append(f"[bold yellow]{self.medium} medium[/bold yellow]")
        if self.low:
            severity_parts.append(f"[green]{self.low} low[/green]")
        if self.info:
            severity_parts.append(f"[dim]{self.info} info[/dim]")

        status = "[bold red]✗ FAIL[/bold red]" if not self.passed else "[bold yellow]⚠ PASS WITH WARNINGS[/bold yellow]"
        sev_text = " | ".join(severity_parts)

        extra_lines = ""
        for k, v in self.extras.items():
            extra_lines += f"\n  {k}: {v}"

        console.print(
            Panel(
                f"{status}\n\n发现: [bold]{self.total_findings}[/bold] 问题 ({sev_text}){extra_lines}",
                title=f"[bold]{self.command}[/bold] 摘要",
                subtitle=f"{self.total_files} 文件 | {self.elapsed_ms / 1000:.1f}s",
            )
        )
