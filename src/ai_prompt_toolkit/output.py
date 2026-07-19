"""统一输出格式（rich集成）"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

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
        console=console,
    )


def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)


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
            console.print(Panel(
                f"[bold green]✓ {self.command}完成 — 无问题发现[/bold green]",
                subtitle=f"{self.total_files} 文件 | {self.elapsed_ms/1000:.1f}s",
            ))
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

        console.print(Panel(
            f"{status}\n\n发现: [bold]{self.total_findings}[/bold] 问题 ({sev_text}){extra_lines}",
            title=f"[bold]{self.command}[/bold] 摘要",
            subtitle=f"{self.total_files} 文件 | {self.elapsed_ms/1000:.1f}s",
        ))
