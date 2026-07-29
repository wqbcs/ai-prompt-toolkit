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
@click.option("--config", "config_path", help="Lint配置YAML文件路径(新格式: severity_threshold/exclude_categories/include_categories等)")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli", "sarif"]),
              default="cli", help="输出格式")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
@click.option("--dry-run", is_flag=True, help="干运行: 预览修复内容但不实际修改文件(需配合--fix)")
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
@click.option("--ci", "ci_mode", is_flag=True, help="CI模式: 精简输出+exit code(适合pipeline)")
@click.option("--diff", "show_diff", is_flag=True, help="修复差异: 展示修复前后对比(类似git diff)")
@click.option("--profile", "profile_mode", is_flag=True, help="性能分析: 显示每条规则执行耗时")
@click.option("--owasp-report", "owasp_report", is_flag=True, help="OWASP映射覆盖率报告")
@click.option("--rules-search", "rules_search", help="规则搜索: 按关键词搜索规则(如injection/privacy/LLM01)")
@click.option("--ignore-file", "ignore_file", help="忽略文件路径(默认.promptignore)")
@click.option("--statistics", "statistics_mode", is_flag=True, help="规则命中率统计: 显示每条规则命中次数和占比")
@click.option("--baseline", "baseline_path", help="基线管理: 指定基线文件路径(save=保存, compare=对比)")
@click.option("--baseline-save", "baseline_save", is_flag=True, help="基线保存: 保存当前lint结果为基线快照")
@click.option("--suggest", "suggest_mode", is_flag=True, help="修复建议: 智能推荐修复方案(按优先级排序)")
@click.option("--json-diff", "json_diff_path", help="结构化对比: 输出JSON格式diff到指定路径(需配合--baseline)")
@click.option("--explain", "explain_mode", is_flag=True, help="交互式解释: 每个finding的详细说明+OWASP参考+修复方案")
@click.option("--export-lcov", "export_lcov_path", help="覆盖率导出: 输出lcov格式规则覆盖率到指定路径")
def lint(target: str, config_path: str | None, fmt: str, fix: bool, dry_run: bool, interactive: bool,
         output: str | None, gate: bool, multimodal: bool, color_theme: str,
         html_report: bool, changed_only: bool, cache_dir: str | None,
         tui_mode: bool, watch: bool, ci_mode: bool, show_diff: bool, profile_mode: bool, owasp_report: bool, rules_search: str | None, ignore_file: str | None, statistics_mode: bool, baseline_path: str | None, baseline_save: bool, suggest_mode: bool, json_diff_path: str | None, explain_mode: bool, export_lcov_path: str | None) -> None:
    """Prompt Linter：静态检查提示词质量"""
    from ai_prompt_toolkit.cli_helpers import determine_exit_code, discover_templates, discover_templates_with_ignore, empty_state_tip, write_report
    from ai_prompt_toolkit.linter.linter import PromptLinter

    lint_cfg = None
    if config_path:
        from ai_prompt_toolkit.linter.lint_config import load_lint_config
        lint_cfg = load_lint_config(config_path)
        if lint_cfg.include_categories or lint_cfg.exclude_categories:
            click.echo(f"配置: categories=include{lint_cfg.include_categories}/exclude{lint_cfg.exclude_categories}")
        if lint_cfg.include_rules or lint_cfg.exclude_rules:
            click.echo(f"配置: rules=include{lint_cfg.include_rules}/exclude{lint_cfg.exclude_rules}")

    templates = discover_templates_with_ignore(target, ignore_file) if ignore_file or Path(target).is_dir() else discover_templates(target)
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
                result = linter.lint(tpl_path.name, text, fix=fix or interactive or dry_run, template_type=template_type)
                if dry_run and result.auto_fixed:
                    click.echo(f"  [DRY-RUN] {tpl_path.name}: {len(result.fixed_findings)}处可修复(未实际修改)")
                    for ff in result.fixed_findings:
                        click.echo(f"    预览: {ff.rule_id}: {ff.description}")
                elif interactive and result.auto_fixed:
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
            result = linter.lint(tpl_path.name, text, fix=fix or dry_run, template_type=template_type)
            if dry_run and result.auto_fixed:
                click.echo(f"  [DRY-RUN] {tpl_path.name}: {len(result.fixed_findings)}处可修复(未实际修改)")
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

    if ci_mode:
        click.echo(f"files={len(templates)} findings={total_findings} score={avg_score:.1f}")
        if total_findings == 0:
            click.echo("PASS")
        else:
            click.echo("FAIL")
    elif tui_mode:
        from ai_prompt_toolkit.tui_browser import render_interactive_results
        render_interactive_results(all_results, avg_score, total_findings, len(templates))
    elif fmt == "cli":
        for result in all_results:
            if result.findings:
                for f in result.findings:
                    sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                    marker = {"high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                    prefix = "[MM] " if f.rule_id.startswith("MM-") else ""
                    loc = f" L{f.location}" if f.location and str(f.location) != "1" and str(f.location) != "0" else ""
                    click.echo(f"  {marker} [{result.template_id}{loc}] {prefix}{f.rule_id}: {f.description}")

    avg_score = total_score / max(len(all_results), 1)
    click.echo(f"\nLint完成 | 文件: {len(templates)} | 平均分: {avg_score:.1f}/100 | 问题: {total_findings}")

    if profile_mode:
        from ai_prompt_toolkit.linter.rules import run_all_checks_profiled
        click.echo("\n── 性能分析 (Profile) ──")
        sample_text = templates[0].read_text(encoding="utf-8") if templates else ""
        if sample_text:
            _, profile_data = run_all_checks_profiled(sample_text)
            total_ms = sum(p["elapsed_ms"] for p in profile_data)
            top10 = sorted(profile_data, key=lambda p: p["elapsed_ms"], reverse=True)[:10]
            click.echo(f"  总耗时: {total_ms:.1f}ms | 规则数: {len(profile_data)} | Top10慢规则:")
            for p in top10:
                click.echo(f"    {p['checker']}: {p['elapsed_ms']:.3f}ms (findings={p['findings']})")

    if owasp_report:
        from ai_prompt_toolkit.linter.owasp_mapping import generate_owasp_report
        click.echo(generate_owasp_report())

    if rules_search:
        from ai_prompt_toolkit.linter.rules import search_rules
        results = search_rules(rules_search)
        click.echo(f"\n── 规则搜索: '{rules_search}' ({len(results)}条结果) ──")
        for r in results:
            owasp_str = ",".join(r["owasp_refs"]) if r["owasp_refs"] else ""
            click.echo(f"  {r['rule_id']}: {r['name']} [{r['category']}] {r['severity']} {'OWASP:'+owasp_str if owasp_str else ''}")
            click.echo(f"    {r['description']}")

    if statistics_mode:
        from ai_prompt_toolkit.linter.rules import compute_rule_statistics
        all_findings_flat = []
        for r in all_results:
            all_findings_flat.extend(r.findings)
        stats = compute_rule_statistics(all_findings_flat)
        click.echo(f"\n── 规则命中率统计 ──")
        click.echo(f"  总命中: {stats['total_findings']} | 涉及规则: {stats['unique_rules']}")
        if stats["by_category"]:
            click.echo(f"  按类别: {', '.join(f'{k}={v}' for k, v in stats['by_category'].items())}")
        if stats["by_severity"]:
            click.echo(f"  按严重度: {', '.join(f'{k}={v}' for k, v in stats['by_severity'].items())}")
        click.echo(f"  {'规则ID':<8} {'命中':>5} {'占比':>8} {'名称'}")
        click.echo(f"  {'─'*8} {'─'*5} {'─'*8} {'─'*30}")
        for rs in stats["rules"]:
            click.echo(f"  {rs['rule_id']:<8} {rs['hit_count']:>5} {rs['hit_rate']:>7.1f}% {rs['name']}")

    if baseline_path:
        from ai_prompt_toolkit.linter.baseline import save_baseline, load_baseline, compare_baseline
        all_findings_for_baseline = []
        for r in all_results:
            for f in r.findings:
                all_findings_for_baseline.append({"rule_id": f.rule_id, "description": f.description, "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity)})
        if baseline_save:
            save_baseline(all_findings_for_baseline, baseline_path, template_id=target, score=avg_score)
            click.echo(f"\n基线已保存: {baseline_path} (findings={len(all_findings_for_baseline)}, score={avg_score:.1f})")
        else:
            bp = Path(baseline_path)
            if bp.exists():
                baseline = load_baseline(baseline_path)
                diff = compare_baseline(all_findings_for_baseline, baseline)
                click.echo(f"\n── 基线对比 ──")
                click.echo(f"  基线: {baseline.total_findings} (score={baseline.score:.1f}) | 当前: {diff.current_total} | Δ={diff.delta:+d}")
                if diff.new_findings:
                    click.echo(f"  新增({len(diff.new_findings)}): {', '.join(f['rule_id'] for f in diff.new_findings[:10])}")
                if diff.fixed_findings:
                    click.echo(f"  修复({len(diff.fixed_findings)}): {', '.join(f['rule_id'] for f in diff.fixed_findings[:10])}")
                if diff.regressions:
                    click.echo(f"  回归({len(diff.regressions)}): {', '.join(f'{r[\"rule_id\"]}(+{r[\"delta\"]})' for r in diff.regressions)}")
                status = "⚠️ 回归" if diff.is_regression else "✅ 改善" if diff.delta < 0 else "➡️ 不变"
                click.echo(f"  状态: {status}")
            else:
                click.echo(f"\n基线文件不存在: {baseline_path} (使用--baseline-save先保存)")

    if json_diff_path and baseline_path:
        from ai_prompt_toolkit.linter.baseline import load_baseline, compare_baseline
        from ai_prompt_toolkit.linter.structured_diff import generate_structured_diff, format_diff_json
        bp = Path(baseline_path)
        if bp.exists():
            baseline_obj = load_baseline(baseline_path)
            all_f_for_diff = []
            for r in all_results:
                for f in r.findings:
                    all_f_for_diff.append({"rule_id": f.rule_id, "description": f.description, "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity)})
            diff_obj = compare_baseline(all_f_for_diff, baseline_obj)
            structured = generate_structured_diff(diff_obj, baseline_obj, all_f_for_diff, target=target)
            Path(json_diff_path).write_text(format_diff_json(structured), encoding="utf-8")
            click.echo(f"JSON diff已输出: {json_diff_path} (verdict={structured['verdict']})")

    if suggest_mode:
        from ai_prompt_toolkit.linter.suggest import generate_suggestions
        all_findings_for_suggest = []
        for r in all_results:
            all_findings_for_suggest.extend(r.findings)
        suggestions = generate_suggestions(all_findings_for_suggest)
        click.echo(f"\n── 修复建议 ({len(suggestions)}条, 按优先级排序) ──")
        for i, s in enumerate(suggestions, 1):
            click.echo(f"  {i}. [{s.severity.upper()}] {s.rule_id}: {s.rule_name}")
            click.echo(f"     影响: {s.estimated_impact} | 命中: {s.hit_count}次")
            click.echo(f"     修复: {s.remediation}")
            if s.action_steps:
                click.echo(f"     步骤: {' → '.join(s.action_steps[:3])}")

    if explain_mode:
        from ai_prompt_toolkit.linter.explain import explain_results, format_explanation
        all_findings_for_explain = []
        for r in all_results:
            all_findings_for_explain.extend(r.findings)
        explanations = explain_results(all_findings_for_explain)
        click.echo(f"\n── 详细解释 ({len(explanations)}条) ──")
        for expl in explanations:
            click.echo(format_explanation(expl))
            click.echo()

    if export_lcov_path:
        from ai_prompt_toolkit.linter.lcov_export import generate_lcov_report, generate_coverage_summary
        all_findings_for_lcov = []
        for r in all_results:
            all_findings_for_lcov.extend(r.findings)
        lcov_data = generate_lcov_report(all_findings_for_lcov)
        Path(export_lcov_path).write_text(lcov_data, encoding="utf-8")
        summary = generate_coverage_summary(all_findings_for_lcov)
        click.echo(f"\nlcov覆盖率: {summary['hit_rules']}/{summary['total_rules']} ({summary['coverage_pct']}%) → {export_lcov_path}")

    if fix and any(r.auto_fixed for r in all_results):
        fixed = sum(len(r.fixed_findings) for r in all_results if r.auto_fixed)
        click.echo(f"自动修复: {fixed} 处")

    if show_diff and any(r.auto_fixed for r in all_results):
        import difflib
        for r in all_results:
            if r.auto_fixed and hasattr(r, "original_text") and hasattr(r, "fixed_text"):
                orig_lines = (r.original_text or "").splitlines(keepends=True)
                fixed_lines = (r.fixed_text or "").splitlines(keepends=True)
                diff_lines = difflib.unified_diff(orig_lines, fixed_lines, fromfile="original", tofile="fixed", lineterm="")
                for dl in diff_lines:
                    click.echo(dl)

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
