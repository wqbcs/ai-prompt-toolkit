"""CLI命令 — Lint相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import _detect_template_type, _generate_sarif, main


@main.command()
@click.option("--target", "-t", required=True, help="Lint目标(文件或目录)")
@click.option("--config", help="Lint配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli", "sarif"]),
              default="cli", help="输出格式")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
@click.option("--interactive", "-i", is_flag=True, help="交互式修复: 逐条确认每个修复")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--gate", is_flag=True, help="启用Quality Gate(CI模式，按verdict决定退出码)")
@click.option("--multimodal", "-mm", is_flag=True, help="启用多模态Lint检查(图片引用/格式/可访问性)")
@click.option("--color-theme", type=click.Choice(["default", "monokai", "solarized", "nord", "dracula"]), default="default", help="颜色主题")
@click.option("--html", "html_report", is_flag=True, help="生成交互式HTML报告(同--format html)")
@click.option("--changed", "changed_only", is_flag=True, help="增量模式: 仅lint git变更/未提交文件")
@click.option("--cache-dir", "cache_dir", type=click.Path(), help="增量缓存目录(默认.prompt-toolkit-cache/)")
@click.option("--tui", "tui_mode", is_flag=True, help="TUI交互式浏览: Rich树形+表格展示lint结果")
@click.option("--watch", is_flag=True, help="实时监听: 文件变更时自动重新lint")
def lint(target: str, config: str | None, fmt: str, fix: bool, interactive: bool,
         output: str | None, gate: bool, multimodal: bool, color_theme: str,
         html_report: bool, changed_only: bool, cache_dir: str | None, tui_mode: bool, watch: bool) -> None:
    """Prompt Linter：静态检查提示词质量"""
    from ai_prompt_toolkit.cli_helpers import determine_exit_code, discover_templates, empty_state_tip, write_report
    from ai_prompt_toolkit.linter.linter import PromptLinter

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("lint"))
        sys.exit(0)

    if changed_only:
        import subprocess as _sp
        try:
            _r = _sp.run(["git", "diff", "--name-only", "--diff-filter=ACMR"], capture_output=True, text=True, cwd=Path(target).parent if Path(target).is_file() else target)
            _changed_files = set(_r.stdout.strip().split("\n")) if _r.stdout.strip() else set()
            _r2 = _sp.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, cwd=Path(target).parent if Path(target).is_file() else target)
            _untracked = set(_r2.stdout.strip().split("\n")) if _r2.stdout.strip() else set()
            _git_changed = _changed_files | _untracked
            _git_changed = {f for f in _git_changed if f.endswith((".md", ".txt", ".prompt", ".yaml", ".yml"))}
            if _git_changed:
                templates = [t for t in templates if t.name in _git_changed or str(t) in _git_changed]
                click.echo(f"增量模式: 检查 {len(templates)} 个变更文件(git diff)")
            else:
                click.echo("增量模式: 无变更文件, 跳过lint")
                sys.exit(0)
        except Exception:
            click.echo("增量模式: git不可用, 回退到全量检查", err=True)

    _cache_dir_path = Path(cache_dir) if cache_dir else Path(".prompt-toolkit-cache")
    _cache_dir_path.mkdir(exist_ok=True)

    linter = PromptLinter()
    if html_report:
        fmt = "html"
    if color_theme != "default":
        import os
        os.environ["PROMPT_TOOLKIT_THEME"] = color_theme
    all_results = []
    total_findings = 0
    total_score = 0.0

    try:
        from rich.console import Console
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
        _has_rich = True
        console = Console()
    except ImportError:
        _has_rich = False

    if _has_rich:
        from ai_prompt_toolkit.cli_helpers import friendly_progress_label
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TaskProgressColumn(), console=console) as progress:
            task = progress.add_task("Lint检查中...", total=len(templates))
            for i, tpl_path in enumerate(templates, 1):
                text = tpl_path.read_text(encoding="utf-8")
                template_type = _detect_template_type(text)
                result = linter.lint(tpl_path.name, text, fix=fix or interactive, template_type=template_type)
                if interactive and result.fixes_applied:
                    for fix_info in result.fixes_applied:
                        click.echo(f"  修复: {fix_info}")
                        if not click.confirm("  应用此修复?", default=True):
                            pass
                all_results.append(result)
                total_findings += result.failed_count
                total_score += result.score
                progress.update(task, description=friendly_progress_label("lint", i, len(templates)))
                progress.advance(task)
    else:
        for tpl_path in templates:
            text = tpl_path.read_text(encoding="utf-8")
            template_type = _detect_template_type(text)
            result = linter.lint(tpl_path.name, text, fix=fix, template_type=template_type)
            all_results.append(result)
            total_findings += result.failed_count
            total_score += result.score

    mm_findings_total: list = []
    if multimodal:
        from ai_prompt_toolkit.linter.multimodal import check_multimodal_prompt
        for i, tpl_path in enumerate(templates):
            text = tpl_path.read_text(encoding="utf-8")
            mm_findings = check_multimodal_prompt(text)
            if mm_findings:
                mm_findings_total.extend(mm_findings)
                all_results[i].findings.extend(mm_findings)
                total_findings += len(mm_findings)

    if tui_mode:
        from ai_prompt_toolkit.tui_browser import render_interactive_results
        render_interactive_results(all_results, avg_score, total_findings, len(templates))
    elif fmt == "cli":
        for result in all_results:
            if result.findings:
                for f in result.findings:
                    sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                    marker = {"high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                    prefix = "[MM] " if f.rule_id.startswith("MM-") else ""
                    click.echo(f"  {marker} [{result.template_id}] {prefix}{f.rule_id}: {f.description}")

    avg_score = total_score / max(len(all_results), 1)
    click.echo(f"\nLint完成 | 文件: {len(templates)} | 平均分: {avg_score:.1f}/100 | 问题: {total_findings}")

    if fix and any(r.auto_fixed for r in all_results):
        fixed = sum(len(r.fixed_findings) for r in all_results if r.auto_fixed)
        click.echo(f"自动修复: {fixed} 处")

    if output:
        report_data = {
            "_report_type": "lint",
            "lint_target": target,
            "total_files": len(templates),
            "average_score": round(avg_score, 1),
            "total_findings": total_findings,
            "results": [r.to_dict() for r in all_results],
        }
        write_report(report_data, output, fmt=fmt)
        click.echo(f"报告: {output}")

    has_errors = any(r.has_errors for r in all_results)

    if gate:
        from ai_prompt_toolkit.linter.quality_gate import QualityGate, Verdict
        qg = QualityGate()
        all_findings_flat = []
        for r in all_results:
            all_findings_flat.extend(r.findings)
        gate_result = qg.evaluate(all_findings_flat, score=avg_score)
        verdict_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        click.echo(f"Quality Gate: {verdict_emoji.get(gate_result.verdict.value, '')} {gate_result.verdict.value.upper()} | {gate_result.summary}")
        if output:
            report_data["quality_gate"] = gate_result.to_dict()
        if gate_result.verdict == Verdict.FAIL:
            sys.exit(2)
        elif gate_result.verdict == Verdict.WARN:
            sys.exit(1)
        else:
            sys.exit(0)

    if fmt == "sarif" and output:
        sarif_data = _generate_sarif(all_results, target)
        import json as _json
        Path(output).write_text(_json.dumps(sarif_data, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"SARIF报告: {output}")
    elif fmt == "html":
        from ai_prompt_toolkit.html_report import generate_html_report
        findings_list = []
        for r in all_results:
            for f in r.findings:
                findings_list.append({
                    "rule_id": f.rule_id, "severity": str(f.severity.value if hasattr(f.severity, "value") else f.severity),
                    "category": getattr(f, "category", "other"), "name": getattr(f, "name", ""),
                    "message": f.description, "remediation": getattr(f, "remediation", ""),
                })
        html_path = output or "lint-report.html"
        generate_html_report(findings_list, target, output_path=html_path)
        click.echo(f"HTML报告: {html_path}")
    else:
        if output:
            report_data = {
                "_report_type": "lint",
                "lint_target": target,
                "total_files": len(templates),
                "average_score": round(avg_score, 1),
                "total_findings": total_findings,
                "results": [r.to_dict() for r in all_results],
            }
            write_report(report_data, output, fmt=fmt)
            click.echo(f"报告: {output}")

    if watch:
        from ai_prompt_toolkit.linter.linter import PromptLinter as _PL
        import time as _time
        click.echo(f"lint --watch: 监听 {target} (Ctrl+C退出)...")
        _watch_linter = _PL()
        _last_mtimes: dict[str, float] = {}
        while True:
            try:
                _current_templates = discover_templates(target)
                _changed = False
                for _tp in _current_templates:
                    _mt = _tp.stat().st_mtime
                    if _last_mtimes.get(str(_tp)) != _mt:
                        _last_mtimes[str(_tp)] = _mt
                        _changed = True
                if _changed:
                    click.echo(f"\n--- [{_time.strftime('%H:%M:%S')}] 文件变更, 重新lint ---")
                    for _tp in _current_templates:
                        _text = _tp.read_text(encoding="utf-8")
                        _res = _watch_linter.lint(_tp.name, _text, fix=False, template_type=_detect_template_type(_text))
                        if _res.findings:
                            for _f in _res.findings:
                                _sv = _f.severity.value if hasattr(_f.severity, "value") else str(_f.severity)
                                _mk = {"high": "✗", "medium": "⚠", "low": "ℹ"}.get(_sv, "•")
                                click.echo(f"  {_mk} [{_tp.name}] {_f.rule_id}: {_f.description}")
                        else:
                            click.echo(f"  ✓ [{_tp.name}] 通过")
                _time.sleep(1.0)
            except KeyboardInterrupt:
                click.echo("\nlint --watch: 已停止")
                break
        sys.exit(0)

    sys.exit(determine_exit_code(has_findings=total_findings > 0, error_severity="high" if has_errors else None))


@main.command()
@click.option("--target", "-t", required=True, help="扫描目标(文件或目录)")
@click.option("--provider", help="模板提供者配置文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--incremental", is_flag=True, help="增量扫描模式")
@click.option("--explain", is_flag=True, help="交互式解释: 每个安全发现的详细说明+修复建议")
def scan(target: str, provider: str | None, fmt: str, output: str | None,
         incremental: bool, explain: bool) -> None:
    """安全扫描：检测Prompt注入、敏感信息泄露等安全风险"""
    from ai_prompt_toolkit.cli_helpers import determine_exit_code, discover_templates, empty_state_tip, write_report
    from ai_prompt_toolkit.security import DictTemplateProvider, scan_template

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("scan"))
        sys.exit(0)

    prov = DictTemplateProvider({})
    if provider:
        import yaml as _yaml

        from ai_prompt_toolkit.security.inheritance_auditor import DictTemplateProvider as DTP
        prov_data = _yaml.safe_load(Path(provider).read_text(encoding="utf-8"))
        prov = DTP(prov_data or {})

    all_results = []
    total_findings = 0

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        result = scan_template(tpl_path.name, text, prov, incremental=incremental)
        all_results.append(result)
        total_findings += len(result.findings)

        if fmt == "cli" and result.findings:
            for f in result.findings:
                sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                marker = {"critical": "🔴", "high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                click.echo(f"  {marker} [{result.template_id}] {f.rule_id}: {f.description}")
                if explain:
                    click.echo(f"      规则: {f.rule_id} | 严重度: {sev}")
                    click.echo(f"      描述: {f.description}")
                    if hasattr(f, "remediation") and f.remediation:
                        click.echo(f"      修复: {f.remediation}")

    click.echo(f"\n扫描完成 | 文件: {len(templates)} | 安全发现: {total_findings}")

    if output:
        report_data = {
            "_report_type": "security_scan",
            "scan_target": target,
            "total_files": len(templates),
            "total_findings": total_findings,
            "results": [r.to_dict() for r in all_results],
        }
        write_report(report_data, output, fmt=fmt)
        click.echo(f"报告: {output}")

    has_critical = any(
        any(f.severity.value in ("critical", "high") for f in r.findings)
        for r in all_results
    )
    sys.exit(determine_exit_code(has_findings=total_findings > 0, error_severity="high" if has_critical else None))


@main.command(name="token")
@click.option("--target", "-t", required=True, help="分析目标(文件或目录)")
@click.option("--model", "-m", default="default", help="目标模型(如gpt-4o/deepseek/qwen/pangu)")
@click.option("--compare", is_flag=True, help="多模型成本对比")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
def token_cmd(target: str, model: str, compare: bool, fmt: str, output: str | None) -> None:
    """Token分析：估算Token消耗、成本和优化建议"""
    from ai_prompt_toolkit.cli_helpers import discover_templates
    from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens, compare_models

    templates = discover_templates(target)
    if not templates:
        click.echo("未找到模板文件")
        sys.exit(0)

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")

        if compare:
            comp = compare_models(text)
            click.echo(f"\n📊 [{tpl_path.name}] 多模型Token对比 (文本长度: {len(text)} chars)")
            click.echo(f"  {'模型':<16} {'Token数':>8} {'输入成本($)':>12} {'输出成本($)':>12}")
            click.echo(f"  {'─'*16} {'─'*8} {'─'*12} {'─'*12}")
            for est in comp.estimates:
                click.echo(f"  {est.model:<16} {est.estimated_tokens:>8} {est.estimated_input_cost_usd:>12.6f} {est.estimated_output_cost_usd:>12.6f}")
            click.echo(f"\n  💰 最便宜: {comp.cheapest_model} | 🎯 最少Token: {comp.most_efficient_model}")
        else:
            result = analyze_prompt_tokens(text, model)
            est = result.estimate
            click.echo(f"\n📊 [{tpl_path.name}] Token分析")
            click.echo(f"  模型: {est.model} | 字符数: {est.char_count} | Token数: {est.estimated_tokens}")
            click.echo(f"  输入成本: ${est.estimated_input_cost_usd:.6f}/1K | 输出成本: ${est.estimated_output_cost_usd:.6f}/1K")
            if result.savings_tokens > 0:
                click.echo(f"  💡 可优化: {result.savings_tokens} tokens ({result.savings_percent:.1f}%)")
            for s in result.suggestions[:3]:
                click.echo(f"    - [{s.priority}] {s.description}")
            if output:
                import json as _json
                Path(output).write_text(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
