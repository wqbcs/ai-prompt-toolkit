"""Rich进度条工具 — lint/scan/evaluate进度反馈

参考: promptfoo进度显示, rich.progress官方API
- ETA预估 + 速率显示 + 已完成/总数
- SIGINT优雅中断支持
- 可选禁用(--no-progress)
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Generator, Sequence

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

_console = Console(stderr=True)


def create_progress(disable: bool = False) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=_console,
        disable=disable,
    )


@contextmanager
def progress_bar(
    description: str = "处理中",
    total: int = 0,
    disable: bool = False,
) -> Generator[Progress, None, None]:
    progress = create_progress(disable=disable)
    task_id = progress.add_task(description, total=total)
    try:
        with progress:
            yield progress
    except KeyboardInterrupt:
        progress.console.print(f"\n[yellow]中断: {progress.tasks[task_id].completed}/{progress.tasks[task_id].total} 已完成[/yellow]")
        raise


def progress_iter(
    items: Sequence[Any],
    description: str = "处理中",
    disable: bool = False,
) -> Generator[tuple[int, Any], None, None]:
    progress = create_progress(disable=disable)
    task_id = progress.add_task(description, total=len(items))
    try:
        with progress:
            for i, item in enumerate(items):
                yield i, item
                progress.update(task_id, advance=1)
    except KeyboardInterrupt:
        progress.console.print(f"\n[yellow]中断: {i+1}/{len(items)} 已完成[/yellow]")
        raise
