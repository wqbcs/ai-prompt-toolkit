"""CLI命令 — 安全相关命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import click

from ai_prompt_toolkit.cli_core import main


@main.command(name="canary")
@click.option("--prompt", "-p", help="注入Canary Token的Prompt文件路径")
@click.option("--check", "-c", help="检测泄露的LLM输出文件路径")
@click.option("--count", type=int, default=3, help="生成Canary Token数量(默认3)")
@click.option("--output", "-o", help="输出路径")
def canary_cmd(prompt: str | None, check: str | None, count: int, output: str | None) -> None:
    """Canary Token泄露防护：注入追踪标记/检测系统Prompt泄露"""
    import re

    from ai_prompt_toolkit.security.unicode_guard import (
        check_unicode_threats,
        clean_unicode,
        inject_canary_tokens,
    )

    if check:
        check_path = Path(check)
        if check_path.exists():
            output_text = check_path.read_text(encoding="utf-8")
        else:
            output_text = check

        uni_findings = check_unicode_threats(output_text)
        if uni_findings:
            click.echo("Unicode威胁检测:")
            for f in uni_findings:
                marker = "✗" if f.severity.value in ("critical", "high") else "⚠"
                click.echo(f"  {marker} [{f.rule_id}] {f.description}")

        cleaned, clean_result = clean_unicode(output_text)
        if clean_result.was_modified:
            click.echo(f"\nUnicode清洗: {clean_result.original_length}→{clean_result.cleaned_length}字符")
            click.echo(f"  不可见字符: {sum(clean_result.invisible_chars_found.values())}个")
            click.echo(f"  RTL覆盖: {sum(clean_result.rtl_overrides_found.values())}个")
            click.echo(f"  同形字: {len(clean_result.homoglyphs_found)}个")
            click.echo(f"  风险等级: {clean_result.risk_level}")

        canary_matches = re.findall(r"::CANARY_[A-Z0-9]+::", output_text)
        if canary_matches:
            click.echo(f"\n⚠ 检测到{len(canary_matches)}个Canary Token泄露!")
            click.echo(f"  泄露标记: {', '.join(canary_matches)}")
            click.echo("  → 系统Prompt可能已被LLM输出泄露")
        else:
            click.echo("\n✓ 未检测到Canary Token泄露")

        if output and clean_result.was_modified:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(cleaned, encoding="utf-8")
            click.echo(f"清洗后内容: {output}")

    elif prompt:
        prompt_path = Path(prompt)
        if prompt_path.exists():
            prompt_text = prompt_path.read_text(encoding="utf-8")
        else:
            prompt_text = prompt

        injected, tokens = inject_canary_tokens(prompt_text, count)
        click.echo(f"已注入{len(tokens)}个Canary Token:")
        for t in tokens:
            click.echo(f"  {t.token_string}")

        if output:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(injected, encoding="utf-8")
            click.echo(f"注入后文件: {output}")
        else:
            click.echo("\n--- 注入后内容 ---")
            click.echo(injected[:500] + ("..." if len(injected) > 500 else ""))

        click.echo("\n检测方法: 将LLM输出通过 'prompt-cli canary -c <output_file>' 检查泄露")
    else:
        click.echo("错误: 请指定 --prompt(注入) 或 --check(检测)", err=True)
        sys.exit(2)


@main.command(name="score")
@click.option("--target", "-t", required=True, help="目标Prompt文件")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
def score_cmd(target: str, fmt: str) -> None:
    """一键安全评分(0-100分)"""
    import json as _json

    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.output import console

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"文件不存在: {target}", err=True)
        sys.exit(3)

    text = target_path.read_text(encoding="utf-8")

    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.prompt_scorecard import Decision, compute_scorecard
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES

    linter = PromptLinter()
    lint_result = linter.lint(target_path.name, text)
    lint_findings = lint_result.findings if hasattr(lint_result, "findings") else []

    detector = InjectionDetector(extra_rules=ZH_INJECTION_RULES)
    sec_findings = detector.detect(text)

    pii = PIIDetector()
    pii_finding = pii.check(text)
    if pii_finding:
        sec_findings.append(pii_finding)

    struct_finding = check_structural(text)
    if struct_finding:
        sec_findings.append(struct_finding)

    all_findings = list(lint_findings) + sec_findings
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, "score") else None)

    if fmt == "json":
        click.echo(_json.dumps(scorecard.to_dict(), ensure_ascii=False, indent=2))
    else:
        grade_colors = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bold red"}
        gc = grade_colors.get(scorecard.grade.value, "white")
        console.print(
            f"\n[bold]安全评分卡: [{gc}]{scorecard.overall_score}/100 ({scorecard.grade.value})[/{gc}][/bold]"
        )
        console.print(f"  决策: [bold]{scorecard.decision.value.upper()}[/bold] | {scorecard.summary}")
        console.print(
            f"  发现: {scorecard.total_findings} (严重:{scorecard.critical_count} 高危:{scorecard.high_count} 中危:{scorecard.medium_count} 低危:{scorecard.low_count})"
        )
        console.print("\n  [bold]维度评分:[/bold]")
        for dim in scorecard.dimensions:
            bar_len = 20
            filled = int(dim.ratio * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            console.print(f"  {dim.name:10s} [{bar}] {dim.earned}/{dim.max_points}")

    if scorecard.decision == Decision.BLOCK:
        sys.exit(2)
    elif scorecard.decision == Decision.WARN:
        sys.exit(1)


@main.command(name="engine")
@click.option("--target", "-t", required=True, help="目标Prompt文件")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
@click.option("--session", "-s", default="", help="会话ID(启用炎症级联)")
@click.option("--no-inflammation", is_flag=True, help="禁用炎症级联")
def engine_cmd(target: str, fmt: str, session: str, no_inflammation: bool) -> None:
    """多层融合注入检测引擎(5层+元分类器融合)"""
    import json as _json

    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.output import console
    from ai_prompt_toolkit.security.engine import FusionEngine
    from ai_prompt_toolkit.security.prompt_scorecard import Decision

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"文件不存在: {target}", err=True)
        sys.exit(3)

    text = target_path.read_text(encoding="utf-8")
    engine = FusionEngine(enable_inflammation=not no_inflammation)
    result = engine.analyze(text, session_id=session)

    if fmt == "json":
        click.echo(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        decision_colors = {"allow": "green", "warn": "yellow", "block": "bold red"}
        dc = decision_colors.get(result.decision.value, "white")
        console.print("\n[bold]融合引擎分析结果:[/bold]")
        console.print(
            f"  风险分数: {result.risk_score:.4f} | 校准分数: {result.calibrated_score:.4f} | 置信度: {result.confidence:.4f}"
        )
        console.print(f"  决策: [{dc}]{result.decision.value.upper()}[/{dc}]")
        console.print(f"  耗时: {result.scan_time_ms:.2f}ms")

        console.print("\n  [bold]各层结果:[/bold]")
        for lr in result.layer_results:
            status = "[green]✓[/green]" if lr.score < 0.1 else "[red]✗[/red]"
            console.print(f"  {status} {lr.layer:20s} score={lr.score:.4f}  latency={lr.latency_ms:.2f}ms")
            if lr.evidence:
                for ev in lr.evidence[:2]:
                    console.print(f"      {ev[:70]}")

        if result.findings:
            console.print(f"\n  [bold yellow]发现 {len(result.findings)} 个问题:[/bold yellow]")
            for f in result.findings[:10]:
                console.print(f"  [{f.rule_id}] {f.description[:80]}")

    if result.decision == Decision.BLOCK:
        sys.exit(2)
    elif result.decision == Decision.WARN:
        sys.exit(1)


@main.command(name="badge")
@click.option("--target", "-t", required=True, help="目标Prompt文件")
@click.option("--output", "-o", required=True, help="输出SVG文件路径")
@click.option("--compact", is_flag=True, help="紧凑模式(仅评分+等级)")
@click.option(
    "--theme", type=click.Choice(["light", "dark", "huawei"]), default="light", help="主题(light/dark/huawei)"
)
def badge_cmd(target: str, output: str, compact: bool, theme: str) -> None:
    """生成安全评分徽章SVG"""
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.output import success
    from ai_prompt_toolkit.security.badge import Theme, generate_scorecard_badge_file
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"文件不存在: {target}", err=True)
        sys.exit(3)

    text = target_path.read_text(encoding="utf-8")

    linter = PromptLinter()
    lint_result = linter.lint(target_path.name, text)
    lint_findings = lint_result.findings if hasattr(lint_result, "findings") else []

    detector = InjectionDetector(extra_rules=ZH_INJECTION_RULES)
    sec_findings = detector.detect(text)

    pii = PIIDetector()
    pii_finding = pii.check(text)
    if pii_finding:
        sec_findings.append(pii_finding)

    struct_finding = check_structural(text)
    if struct_finding:
        sec_findings.append(struct_finding)

    all_findings = list(lint_findings) + sec_findings
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, "score") else None)

    # R199: click.Choice返回str, 收窄为Theme字面量
    generate_scorecard_badge_file(scorecard, output, compact=compact, theme=cast("Theme", theme))
    success(f"评分徽章已生成到 {output} (评分: {scorecard.overall_score}/100 {scorecard.grade.value})")
