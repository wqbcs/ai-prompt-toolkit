"""CLI编排辅助模块 — 路径校验/配置加载/报告写入/退出码判定"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml

from ai_prompt_toolkit.errors import ConfigError, ValidationError


def resolve_path(path_str: str, must_exist: bool = True) -> Path:
    p = Path(path_str).resolve()
    if must_exist and not p.exists():
        raise ValidationError(f"路径不存在 — {p}", field="path")
    return p


def load_context(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        raise ConfigError(f"上下文文件不存在 — {p}")
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON格式错误 — {p}:{e.lineno}:{e.colno} {e.msg}") from e
    return data if isinstance(data, dict) else {"_root": data}


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        raise ConfigError(f"配置文件不存在 — {p}")
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML格式错误 — {p}: {e}") from e
    return data if isinstance(data, dict) else {}


def discover_templates(target: str | Path) -> list[Path]:
    p = Path(target) if not isinstance(target, Path) else target
    if p.is_file():
        return [p] if p.suffix in (".md", ".prompt") or p.name.endswith(".prompt.md") else []
    if p.is_dir():
        results: list[Path] = []
        for pattern in ("*.md", "*.prompt", "*.prompt.md"):
            results.extend(p.rglob(pattern))
        return sorted(set(results))
    raise ValidationError(f"目标不存在 — {p}", field="target")


def auto_discover_targets(target: str | None = None) -> list[Path]:
    if target:
        return discover_templates(target)
    cwd = Path.cwd()
    results: list[Path] = []
    for pattern in ("*.prompt.md", "*.prompt", "*.md"):
        results.extend(cwd.glob(pattern))
    if not results:
        for d in ("prompts", "templates", "_scenarios"):
            dp = cwd / d
            if dp.is_dir():
                for pattern in ("*.md", "*.prompt", "*.prompt.md"):
                    results.extend(dp.rglob(pattern))
    return sorted(set(results))[:50]


def write_report(data: dict[str, Any], path: str | Path, fmt: str = "json") -> None:
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif fmt == "html":
        html = _generate_html_report(data)
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
    elif fmt == "markdown":
        md = _generate_markdown_report(data)
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)


def _generate_html_report(data: dict[str, Any]) -> str:
    from ai_prompt_toolkit.report.html_reporter import generate_html_report
    return generate_html_report(data)


def _generate_markdown_report(data: dict[str, Any]) -> str:
    from ai_prompt_toolkit.report.markdown_reporter import generate_markdown_report
    return generate_markdown_report(data)


def determine_exit_code(
    has_errors: bool = False,
    has_findings: bool = False,
    error_severity: str | None = None,
) -> int:
    if has_errors:
        return 3
    if has_findings:
        if error_severity in ("high", "critical"):
            return 2
        if error_severity == "medium":
            return 1
        return 0
    return 0


EXIT_CODE_MEANINGS = {
    0: "PASS — 通过，无问题",
    1: "WARN — 警告，存在中等风险",
    2: "FAIL — 失败，存在高危/严重风险",
    3: "ERROR — 执行错误",
}


def format_findings_table(findings: Sequence[dict[str, Any]]) -> str:
    if not findings:
        return "无发现项"
    from ai_prompt_toolkit.output import findings_list
    findings_list(findings)
    return ""


_EMPTY_STATE_TIPS: dict[str, str] = {
    "lint": """
 ┌──────────────────────────────────────┐
 │  ✨ Lint结果为空 — 你的Prompt很干净！  │
 │                                      │
 │  3步快速开始:                         │
 │  1. prompt-cli init -t general       │
 │  2. prompt-cli lint -t ./prompts     │
 │  3. prompt-cli lint --gate -t ./prompts │
 └──────────────────────────────────────┘""",
    "scan": """
 ┌──────────────────────────────────────┐
 │  🛡️ 安全扫描为空 — 无安全风险！       │
 │                                      │
 │  建议: 定期运行 scan 以保持安全       │
 │  prompt-cli scan -t ./prompts        │
 └──────────────────────────────────────┘""",
    "evaluate": """
 ┌──────────────────────────────────────┐
 │  📊 评估结果为空                      │
 │                                      │
 │  请确保目标包含有效Prompt:            │
 │  prompt-cli evaluate -t ./prompts    │
 │  prompt-cli evaluate -t . --quick    │
 └──────────────────────────────────────┘""",
    "version": "暂无版本记录。使用 'prompt-cli version create -s <file>' 创建第一个版本。",
    "market": "模板市场暂无模板。使用 'prompt-cli market publish' 发布你的第一个模板。",
    "ab-test": """
 ┌──────────────────────────────────────┐
 │  🧪 暂无A/B测试结果                   │
 │                                      │
 │  快速开始:                            │
 │  prompt-cli ab-test -c config.yaml   │
 └──────────────────────────────────────┘""",
    "redteam": """
 ┌──────────────────────────────────────┐
 │  🎯 红队探测暂无结果                   │
 │                                      │
 │  快速开始:                            │
 │  prompt-cli redteam -t ./prompt.md   │
 │  prompt-cli redteam --owasp LLM01    │
 └──────────────────────────────────────┘""",
    "default": "暂无结果。试试 'prompt-cli wizard' 开始使用工具链。",
}


def empty_state_tip(command: str) -> str:
    return _EMPTY_STATE_TIPS.get(command, _EMPTY_STATE_TIPS["default"])


def friendly_progress_label(stage: str, current: int, total: int, elapsed_ms: float = 0) -> str:
    labels = {
        "lint": "Lint检查",
        "scan": "安全扫描",
        "evaluate": "质量评估",
        "compile": "条件编译",
        "redteam": "红队探测",
        "ab-test": "A/B测试",
        "default": "处理中",
    }
    label = labels.get(stage, labels["default"])
    pct = int(current / max(total, 1) * 100)
    elapsed_str = f" ({elapsed_ms/1000:.1f}s)" if elapsed_ms > 0 else ""
    eta_str = ""
    if elapsed_ms > 0 and current > 0:
        remaining = (elapsed_ms / current) * (total - current)
        if remaining > 1000:
            eta_str = f" ~{remaining/1000:.0f}s剩余"
    return f"{label}: {current}/{total} ({pct}%){elapsed_str}{eta_str}"


_SEVERITY_STYLING = {
    "critical": ("🔴", "CRITICAL"),
    "high": ("✗", "HIGH"),
    "medium": ("⚠", "MEDIUM"),
    "low": ("ℹ", "LOW"),
    "info": ("💡", "INFO"),
}

_SEVERITY_RICH_STYLE = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim",
    "info": "blue",
}

_SCORE_EMOJI = {
    (90, 101): "🌟",
    (80, 90): "✅",
    (70, 80): "⚠️",
    (60, 70): "🔶",
    (0, 60): "❌",
}


def friendly_severity(severity: str) -> tuple[str, str]:
    key = severity.lower() if isinstance(severity, str) else str(severity).lower()
    return _SEVERITY_STYLING.get(key, ("•", key.upper()))


def friendly_score(score: float) -> str:
    for (lo, hi), emoji in _SCORE_EMOJI.items():
        if lo <= score < hi:
            return f"{emoji} {score:.1f}/100"
    return f"{score:.1f}/100"


def friendly_finding_line(template_id: str, rule_id: str, severity: str, description: str, is_multimodal: bool = False) -> str:
    marker, label = friendly_severity(severity)
    prefix = "[MM] " if is_multimodal else ""
    return f"  {marker} [{template_id}] {prefix}{rule_id} ({label}): {description}"


def friendly_lint_summary(total_files: int, avg_score: float, total_findings: int, fixed: int = 0) -> str:
    lines = [
        f"\n{'='*50}",
        f"  Lint完成 | 文件: {total_files} | 评分: {friendly_score(avg_score)} | 问题: {total_findings}",
    ]
    if fixed:
        lines.append(f"  🔧 自动修复: {fixed} 处")
    if avg_score >= 90:
        lines.append(f"  🎉 优秀！Prompt质量超过90分")
    elif avg_score >= 80:
        lines.append(f"  👍 良好！小优化可达90+")
    elif avg_score >= 70:
        lines.append(f"  💡 建议关注标记问题，提升Prompt质量")
    else:
        lines.append(f"  ⚡ 建议优先修复HIGH/CRITICAL问题")
    lines.append(f"{'='*50}")
    return "\n".join(lines)


def friendly_fix_suggestion(rule_id: str, description: str) -> str:
    _QUICK_FIXES = {
        "P001": "💡 在Prompt开头添加明确的# 角色定义",
        "P003": "💡 添加'约束'章节，使用'必须/不得'等确定性表述",
        "P009": "💡 添加'审计追踪'章节，记录关键决策点",
        "P010": "💡 添加'错误处理'章节，覆盖空输入/异常/歧义场景",
        "P018": "💡 添加Few-shot示例，展示期望的输入/输出格式",
        "P020": "💡 添加'输出质量标准'，明确评分维度和合格线",
        "P025": "💡 添加输出长度约束，如'控制在500字以内'",
        "P051": "🔒 移除硬编码凭据，使用{{API_KEY}}占位符",
        "P054": "📱 替换Android API为@ohos等效接口",
    }
    return _QUICK_FIXES.get(rule_id, f"💡 修复 {rule_id}: {description}")


def print_rich_findings(results: list, console: Any = None) -> None:
    try:
        from rich.console import Console as _Console
        from rich.text import Text as _Text
        from rich.panel import Panel as _Panel
    except ImportError:
        for result in results:
            for f in result.findings:
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                click.echo(friendly_finding_line(result.template_id, f.rule_id, sev, f.description))
        return

    if console is None:
        console = _Console()

    for result in results:
        if not result.findings:
            console.print(f"  [green]✓[/green] {result.template_id}: [green]No issues[/green]")
            continue
        for f in result.findings:
            sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
            sev_key = sev.lower()
            style = _SEVERITY_RICH_STYLE.get(sev_key, "white")
            marker, label = friendly_severity(sev)
            is_mm = f.rule_id.startswith("MM-")
            prefix = "[MM] " if is_mm else ""
            text = _Text()
            text.append(f"  {marker} ")
            text.append(f"[{result.template_id}] ", style="cyan")
            text.append(f"{prefix}{f.rule_id} ", style="bold")
            text.append(f"({label}) ", style=style)
            text.append(f.description[:120])
            console.print(text)
            if sev in ("high", "critical"):
                suggestion = friendly_fix_suggestion(f.rule_id, f.description)
                console.print(f"    [dim]{suggestion}[/dim]")


def print_rich_lint_summary(total_files: int, avg_score: float, total_findings: int, fixed: int = 0, console: Any = None) -> None:
    try:
        from rich.console import Console as _Console
        from rich.panel import Panel as _Panel
        from rich.text import Text as _Text
    except ImportError:
        click.echo(friendly_lint_summary(total_files, avg_score, total_findings, fixed))
        return

    if console is None:
        console = _Console()

    if avg_score >= 90:
        score_color = "green"
        verdict = "🎉 优秀！"
    elif avg_score >= 80:
        score_color = "cyan"
        verdict = "👍 良好！"
    elif avg_score >= 70:
        score_color = "yellow"
        verdict = "💡 建议优化"
    else:
        score_color = "red"
        verdict = "⚡ 需修复HIGH/CRITICAL"

    lines = [
        f"文件: [bold]{total_files}[/bold]  |  评分: [{score_color}]{avg_score:.1f}/100[/{score_color}]  |  问题: [bold]{total_findings}[/bold]",
    ]
    if fixed:
        lines.append(f"🔧 自动修复: [bold green]{fixed}[/bold green] 处")
    lines.append(verdict)

    console.print(_Panel("\n".join(lines), title="Lint完成", border_style=score_color))


def print_rich_evaluate_summary(reports: list, threshold: float = 0.0, console: Any = None) -> None:
    try:
        from rich.console import Console as _Console
        from rich.table import Table as _Table
    except ImportError:
        return

    if console is None:
        console = _Console()

    table = _Table(title="评估报告", show_lines=False)
    table.add_column("模板", style="cyan", width=30)
    table.add_column("均分", width=10)
    table.add_column("维度", width=8)
    table.add_column("状态", width=8)

    low_items = []
    for report in reports:
        scores = report.scores
        if not scores:
            continue
        avg = sum(s.score for s in scores) / len(scores)
        tid = report.template_id if hasattr(report, 'template_id') else 'unknown'
        if avg >= 8:
            status = "[green]✓[/green]"
        elif avg >= 6:
            status = "[yellow]⚠[/yellow]"
        else:
            status = "[red]✗[/red]"
        table.add_row(tid, f"{avg:.1f}/10", str(len(scores)), status)
        if threshold > 0 and avg < threshold:
            low_items.append((tid, avg))

    console.print(table)

    if low_items:
        console.print(f"\n[red]低于阈值({threshold})的模板({len(low_items)}个):[/red]")
        for tid, score in low_items[:5]:
            console.print(f"  [red]{tid}[/red]: {score:.1f}/10")
