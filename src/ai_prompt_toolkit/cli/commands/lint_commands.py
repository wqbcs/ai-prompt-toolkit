"""CLI命令 — Lint相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import main, _detect_template_type, _generate_sarif


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
def lint(target: str, config: str | None, fmt: str, fix: bool, interactive: bool,
         output: str | None, gate: bool, multimodal: bool) -> None:
    """Prompt Linter：静态检查提示词质量"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.cli_helpers import empty_state_tip

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("lint"))
        sys.exit(0)

    linter = PromptLinter()
    all_results = []
    total_findings = 0
    total_score = 0.0

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
        from rich.console import Console
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

    if fmt == "cli":
        for result in all_results:
            if result.findings:
                for f in result.findings:
                    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
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

    sys.exit(determine_exit_code(has_findings=total_findings > 0, error_severity="high" if has_errors else None))


@main.command()
@click.option("--target", "-t", required=True, help="扫描目标(文件或目录)")
@click.option("--provider", help="模板提供者配置文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--incremental", is_flag=True, help="增量扫描模式")
def scan(target: str, provider: str | None, fmt: str, output: str | None,
         incremental: bool) -> None:
    """安全扫描：检测Prompt注入、敏感信息泄露等安全风险"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code
    from ai_prompt_toolkit.cli_helpers import empty_state_tip
    from ai_prompt_toolkit.security import scan_template, DictTemplateProvider

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
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                marker = {"critical": "🔴", "high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                click.echo(f"  {marker} [{result.template_id}] {f.rule_id}: {f.description}")

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
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report
    from ai_prompt_toolkit.linter.token_analyzer import estimate_tokens, analyze_prompt_tokens, compare_models

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
