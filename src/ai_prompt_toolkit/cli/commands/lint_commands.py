"""CLI命令 — Lint相关命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from ai_prompt_toolkit.cli_core import _detect_template_type, _generate_sarif, main

if TYPE_CHECKING:
    from ai_prompt_toolkit.linter.linter import LintResult


@main.command(name="audit-waivers")
@click.option("--target", "-t", required=True, help="审计目标(文件或目录)")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
@click.option(
    "--fail-on",
    type=click.Choice(["expired", "no_owner", "unknown_rule"]),
    default=None,
    help="CI 门禁: 存在该状态 waiver 即 FAIL(exit 1)",
)
def audit_waivers_cmd(target: str, fmt: str, fail_on: str | None) -> None:
    """R225-P2-09: waiver 审计 — 列全仓豁免声明, 无 owner/过期/未注册规则告警

    声明语法约定(adoption.md): promptlint:ignore P107 @owner 2026-12-31
    状态: ok(有owner+未过期) / no_owner / expired / unknown_rule(未注册ID或通配符)
    """
    import json as _json
    from datetime import date

    from ai_prompt_toolkit.cli_helpers import discover_templates
    from ai_prompt_toolkit.linter.waivers import parse_waiver_declarations

    files = discover_templates(target)
    if not files:
        click.echo(f"未找到可审计文件: {target}")
        sys.exit(0)

    today = date.today().isoformat()
    all_decls: list[dict[str, str]] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        for d in parse_waiver_declarations(text, today=today):
            d["file"] = str(f)
            all_decls.append(d)

    counts = {"ok": 0, "no_owner": 0, "expired": 0, "unknown_rule": 0}
    for d in all_decls:
        counts[d["status"]] = counts.get(d["status"], 0) + 1

    if fmt == "json":
        click.echo(
            _json.dumps(
                {
                    "total_files": len(files),
                    "total_declarations": len(all_decls),
                    "counts": counts,
                    "today": today,
                    "declarations": all_decls,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if fail_on and counts.get(fail_on, 0) > 0:
            sys.exit(1)
        sys.exit(0)
    else:
        click.echo(f"waiver 审计: {len(files)} 文件, {len(all_decls)} 条声明 (基准日 {today})")
        click.echo(
            f"  ok={counts['ok']}  no_owner={counts['no_owner']}  "
            f"expired={counts['expired']}  unknown_rule={counts['unknown_rule']}"
        )
        for d in all_decls:
            mark = {"ok": "✓", "no_owner": "⚠", "expired": "✗", "unknown_rule": "✗"}[d["status"]]
            extra = []
            if d["owner"]:
                extra.append(f"@{d['owner']}")
            if d["expiry"]:
                extra.append(f"至{d['expiry']}")
            if d["unknown_ids"]:
                extra.append(f"未知规则[{d['unknown_ids']}]")
            suffix = f" ({', '.join(extra)})" if extra else ""
            click.echo(f"  {mark} [{d['status']}] {d['file']} 规则[{d['rule_ids'] or '-'}]{suffix}")

    if fail_on and counts.get(fail_on, 0) > 0:
        click.echo(f"Waiver审计门禁: ❌ FAIL | {fail_on} 状态 {counts[fail_on]} 条")
        sys.exit(1)
    if all_decls and any(d["status"] != "ok" for d in all_decls):
        click.echo("提示: 存在非 ok 状态 waiver — 补 owner(@name) 与到期日(YYYY-MM-DD), 过期者移除或重批")
    elif not all_decls:
        click.echo("✓ 无 waiver 声明")
    sys.exit(0)


@main.command()
@click.option("-t", "-s", "--target", help="Lint目标(文件或目录) — --stdio 模式无需(协议内传text); -t 与 -s 同义")
@click.option(
    "--config",
    "config_path",
    help="Lint配置YAML文件路径(新格式: severity_threshold/exclude_categories/include_categories等)",
)
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli", "sarif"]), default="cli", help="输出格式")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
@click.option("--dry-run", is_flag=True, help="干运行: 预览修复内容但不实际修改文件(需配合--fix)")
@click.option("--interactive", "-i", is_flag=True, help="交互式修复: 逐条确认每个修复")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--gate", is_flag=True, help="启用Quality Gate(CI模式，按verdict决定退出码)")
@click.option(
    "--fail-on",
    "fail_on",
    type=click.Choice(["critical", "high", "medium"]),
    default=None,
    help="显式CI门禁: 指定级别及以上findings>0时退出码2(比--gate更直接的级别门禁)",
)
@click.option(
    "--fail-on-waiver",
    "fail_on_waiver",
    is_flag=True,
    help="豁免审计门禁(R213): 任何文件的waiver实际生效(压制≥1条finding)即退出码2 — 严格CI禁新增豁免",
)
@click.option("--multimodal", "-mm", is_flag=True, help="启用多模态Lint检查(图片引用/格式/可访问性)")
@click.option(
    "--color-theme",
    type=click.Choice(["default", "monokai", "solarized", "nord", "dracula"]),
    default="default",
    help="颜色主题",
)
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
@click.option(
    "--incremental",
    "incremental",
    is_flag=True,
    help="增量门禁(R224): 与--baseline+--gate/--fail-on合用时, 门禁只计NEW findings(基线内已知的PRE-EXISTING放行) — 老仓库接入不被存量打回",
)
@click.option("--suggest", "suggest_mode", is_flag=True, help="修复建议: 智能推荐修复方案(按优先级排序)")
@click.option("--json-diff", "json_diff_path", help="结构化对比: 输出JSON格式diff到指定路径(需配合--baseline)")
@click.option("--explain", "explain_mode", is_flag=True, help="交互式解释: 每个finding的详细说明+OWASP参考+修复方案")
@click.option("--export-lcov", "export_lcov_path", help="覆盖率导出: 输出lcov格式规则覆盖率到指定路径")
@click.option("--resume", is_flag=True, help="恢复模式: 从上次SIGINT中断处继续(参考pytest --lf)")
@click.option("--parallel", "parallel", default=0, type=int, help="并行lint线程数(0=串行; 多文件目录建议4)")
@click.option(
    "--trace-json",
    "trace_json_path",
    help="Trace导出: 将本次执行的OTel trace写入指定路径(JSON/OTLP兼容, 供Langfuse/Jaeger消费)",
)
@click.option("--rules", "rules_filter", help="规则过滤: 仅运行指定规则(逗号分隔, 支持前缀: P161或P16=P16x族)")
@click.option("--ignore-rules", "ignore_rules_filter", help="规则过滤: 忽略指定规则(逗号分隔, 支持前缀)")
@click.option(
    "--stdio",
    "stdio_mode",
    is_flag=True,
    help="P1-05a: 常驻 stdio 协议 server(行JSON请求/响应, 编辑器bridge用) — 忽略其他选项, 见 docs/stdio-protocol.md",
)
@click.option(
    "--inline",
    "inline_mode",
    is_flag=True,
    help="P1-15/15b: 从 Python/TS 源码静态抽取内嵌 prompt(字符串字面量)再 lint — 裁决层复用规则引擎, 纯 stdlib",
)
@click.option(
    "--target-model",
    "target_model",
    default=None,
    help="P1-16: 声明部署目标模型(如 claude/gpt-4o/qwen) — prompt 绑定到其他厂商品牌时 P262 升级为 HIGH",
)
def lint(
    target: str,
    config_path: str | None,
    fmt: str,
    fix: bool,
    dry_run: bool,
    interactive: bool,
    output: str | None,
    gate: bool,
    fail_on: str | None,
    multimodal: bool,
    color_theme: str,
    html_report: bool,
    changed_only: bool,
    cache_dir: str | None,
    tui_mode: bool,
    watch: bool,
    ci_mode: bool,
    show_diff: bool,
    profile_mode: bool,
    owasp_report: bool,
    rules_search: str | None,
    ignore_file: str | None,
    statistics_mode: bool,
    baseline_path: str | None,
    baseline_save: bool,
    incremental: bool,
    suggest_mode: bool,
    json_diff_path: str | None,
    explain_mode: bool,
    export_lcov_path: str | None,
    trace_json_path: str | None = None,
    resume: bool = False,
    parallel: int = 0,
    fail_on_waiver: bool = False,
    rules_filter: str | None = None,
    ignore_rules_filter: str | None = None,
    stdio_mode: bool = False,
    inline_mode: bool = False,
    target_model: str | None = None,
) -> None:
    """Prompt Linter：静态检查提示词质量"""
    if stdio_mode:
        from ai_prompt_toolkit.cli.stdio_server import run_stdio_server

        run_stdio_server()
        return
    if not target:
        click.echo("错误: 需要 --target/-t (或 --stdio 模式)", err=True)
        sys.exit(2)
    # 管道 stdin 面（05 §5 回归护栏）：`echo "text" | prompt-cli lint -t -`
    # 把 `-` 落临时文件再走统一发现路径 — 与 --inline 目录发现正交(inline 不接 stdin)
    if target == "-":
        import os as _os
        import tempfile as _tempfile

        _stdin_text = sys.stdin.read()
        _stdin_fd, _stdin_name = _tempfile.mkstemp(suffix=".prompt", prefix="promptcli-stdin-")
        with _os.fdopen(_stdin_fd, "w", encoding="utf-8") as _stdin_file:
            _stdin_file.write(_stdin_text)
        target = _stdin_name
        _stdin_tmp_path = Path(_stdin_name)  # 函数退出前清理

        def _cleanup_stdin_tmp() -> None:
            _stdin_tmp_path.unlink(missing_ok=True)

        import atexit as _atexit

        _atexit.register(_cleanup_stdin_tmp)
    from ai_prompt_toolkit.cli_helpers import (
        determine_exit_code,
        discover_templates,
        discover_templates_with_ignore,
        empty_state_tip,
        load_promptignore,
        write_report,
    )
    from ai_prompt_toolkit.linter.linter import PromptLinter

    lint_cfg = None
    if config_path:
        from ai_prompt_toolkit.linter.lint_config import load_lint_config

        lint_cfg = load_lint_config(config_path)
        if lint_cfg.include_categories or lint_cfg.exclude_categories:
            click.echo(f"配置: categories=include{lint_cfg.include_categories}/exclude{lint_cfg.exclude_categories}")
        if lint_cfg.include_rules or lint_cfg.exclude_rules:
            click.echo(f"配置: rules=include{lint_cfg.include_rules}/exclude{lint_cfg.exclude_rules}")
    elif not config_path:
        for candidate in [".lint-rc.yml", ".lint-rc.yaml", ".prompt-toolkit.yml", ".prompt-toolkit.yaml"]:
            if Path(candidate).exists():
                from ai_prompt_toolkit.linter.lint_config import load_lint_config

                lint_cfg = load_lint_config(candidate)
                click.echo(f"自动发现配置: {candidate}")
                break

    templates: list
    if inline_mode:
        from ai_prompt_toolkit.linter.inline_prompt import collect_inline_prompts

        ignore_pats = load_promptignore(Path(target)) if Path(target).is_dir() else []
        inline_templates = collect_inline_prompts(target, ignore_pats)
        if not inline_templates:
            click.echo(
                "P1-15 内嵌抽取: 未在目标 Python 源码中发现内嵌 prompt 字符串"
                "（信号=SDK调用实参/prompt键字典/prompt命名变量赋值; 均要求纯字符串字面量）"
            )
            sys.exit(0)
        click.echo(f"P1-15 内嵌抽取: 发现 {len(inline_templates)} 个内嵌 prompt（来源 .py/.ts/.tsx 源码）")
        for it in inline_templates:
            click.echo(f"  · {it.source}:{it.line} [{it.origin}] {len(it.text)}字符")
        templates = list(inline_templates)
    else:
        templates = (
            discover_templates_with_ignore(target, ignore_file)
            if ignore_file or Path(target).is_dir()
            else discover_templates(target)
        )
    if not templates:
        click.echo(empty_state_tip("lint"))
        sys.exit(0)

    # R177: 恢复R71的--resume功能(模块化重构时曾随inline死代码丢失)
    _completed_before: list[str] = []
    if resume:
        from ai_prompt_toolkit.resume_state import load_progress

        saved = load_progress("lint")
        if saved:
            _completed_before = saved.get("completed_files", [])
            templates = [t for t in templates if str(t) not in set(_completed_before)]
            click.echo(f"恢复进度: 已完成 {len(_completed_before)} 个文件, 剩余 {len(templates)} 个")
        else:
            click.echo("无已保存的进度, 从头开始")
    if resume and not templates:
        from ai_prompt_toolkit.resume_state import clear_progress

        try:
            clear_progress("lint")
        except Exception:
            pass
        click.echo("全部文件已完成, 无待处理项")

    if changed_only:
        import subprocess as _sp

        try:
            _r = _sp.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR"],
                capture_output=True,
                text=True,
                cwd=Path(target).parent if Path(target).is_file() else target,
            )
            _changed_files = set(_r.stdout.strip().split("\n")) if _r.stdout.strip() else set()
            _r2 = _sp.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                cwd=Path(target).parent if Path(target).is_file() else target,
            )
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

    # R213-P1-7: CLI直接规则过滤(前缀支持; 与YAML配置include_rules/exclude_rules取交集叠加)
    from ai_prompt_toolkit.cli_helpers import expand_rule_ids

    cli_rules = expand_rule_ids(rules_filter) if rules_filter else None
    cli_ignore = expand_rule_ids(ignore_rules_filter) if ignore_rules_filter else None
    if cli_rules:
        shown = ",".join(cli_rules[:5]) + ("..." if len(cli_rules) > 5 else "")
        click.echo(f"规则过滤: 仅运行 {len(cli_rules)} 条规则 ({shown})")
    if cli_ignore:
        click.echo(f"规则过滤: 忽略 {len(cli_ignore)} 条规则")
    linter = PromptLinter(rules=cli_rules, exclude=cli_ignore)
    from ai_prompt_toolkit.linter.otel_tracer import get_tracer

    tracer = get_tracer()  # 默认Noop零开销; PROMPT_TOOLKIT_TRACING=memory启用
    if html_report:
        fmt = "html"
    if color_theme != "default":
        import os

        os.environ["PROMPT_TOOLKIT_THEME"] = color_theme
    # R196: 显式标注消除dict[str, object].findings误报(all_results实为LintResult列表)
    all_results: list[LintResult] = []
    total_findings = 0
    total_score = 0.0

    try:
        from rich.console import Console
        from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

        _has_rich = True
        console = Console()
    except ImportError:
        _has_rich = False

    # R187: --parallel并行预计算(实测线程池4对50文件1.87x); 交互/修复/干跑强制串行
    # R200: 值类型LintResult — 原object过严致else分支标注报错
    parallel_results: dict[str, LintResult] | None = None
    if parallel > 0 and not interactive and not dry_run and not fix and not watch and len(templates) > 1:
        from concurrent.futures import ThreadPoolExecutor

        def _lint_one(tpl: Path):
            _t = tpl.read_text(encoding="utf-8")
            return linter.lint(
                tpl.name,
                _t,
                template_type=_detect_template_type(_t),
                lint_config=lint_cfg,
                target_model=target_model,
            )

        with ThreadPoolExecutor(max_workers=parallel) as _ex:
            parallel_results = dict(zip([str(t) for t in templates], _ex.map(_lint_one, templates)))

    if _has_rich:
        from ai_prompt_toolkit.cli_helpers import friendly_progress_label

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Lint检查中...", total=len(templates))
            for i, tpl_path in enumerate(templates, 1):
                text = tpl_path.read_text(encoding="utf-8")
                template_type = _detect_template_type(text)
                # R199: 改名防与else分支result重定义
                lint_res = linter.lint(
                    tpl_path.name,
                    text,
                    fix=fix or interactive or dry_run,
                    template_type=template_type,
                    lint_config=lint_cfg,
                    target_model=target_model,
                )
                if dry_run and lint_res.auto_fixed:
                    click.echo(f"  [DRY-RUN] {tpl_path.name}: {len(lint_res.fixed_findings)}处可修复(未实际修改)")
                    for ff in lint_res.fixed_findings:
                        click.echo(f"    预览: {ff.rule_id}: {ff.description}")
                elif interactive and lint_res.auto_fixed:
                    # R200: LintResult真实字段为fixed_findings(无fixes_applied)
                    for fix_f in lint_res.fixed_findings:
                        click.echo(f"  修复: {fix_f.rule_id}: {fix_f.description}")
                        if not click.confirm("  应用此修复?", default=True):
                            pass
                tracer.trace_lint(tpl_path.name, len(lint_res.findings), float(lint_res.score), lint_res.lint_time_ms)
                all_results.append(lint_res)
                total_findings += lint_res.failed_count
                total_score += lint_res.score
                progress.update(task, description=friendly_progress_label("lint", i, len(templates)))
                progress.advance(task)
    else:
        for tpl_path in templates:
            text = tpl_path.read_text(encoding="utf-8")
            template_type = _detect_template_type(text)
            _pre = parallel_results.get(str(tpl_path)) if parallel_results else None
            # R197: 并行分支_pre类型与lint()返回一致(LintResult), 三元后统一
            result: LintResult = (
                _pre
                if _pre is not None
                else linter.lint(
                    tpl_path.name,
                    text,
                    fix=fix or dry_run,
                    template_type=template_type,
                    lint_config=lint_cfg,
                    target_model=target_model,
                )
            )
            if dry_run and result.auto_fixed:
                click.echo(f"  [DRY-RUN] {tpl_path.name}: {len(result.fixed_findings)}处可修复(未实际修改)")
            tracer.trace_lint(tpl_path.name, len(result.findings), float(result.score), result.lint_time_ms)
            all_results.append(result)
            total_findings += result.failed_count
            total_score += result.score

    if resume:
        from ai_prompt_toolkit.resume_state import clear_progress, save_progress

        save_progress("lint", [], _completed_before + [str(t) for t in templates], [])
        try:
            clear_progress("lint")
        except Exception:
            pass

    if trace_json_path:
        _write_trace_json(tracer, Path(trace_json_path))
        click.echo(f"Trace: {trace_json_path}")

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

    # avg_score须在ci_mode/tui_mode引用前计算(修复: 原先在引用之后赋值, --ci模式必NameError)
    avg_score = total_score / max(len(all_results), 1)
    # R184: 并行采样扣分制质量分(score v2 RFC方案C)
    avg_quality = sum(r.quality_score for r in all_results) / max(len(all_results), 1)

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
        from ai_prompt_toolkit.types import parse_location

        for result in all_results:
            if result.findings:
                for f in result.findings:
                    sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                    marker = {"high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                    prefix = "[MM] " if f.rule_id.startswith("MM-") else ""
                    # R218: 统一走 location 契约（"" = 文件级 → 不显示行号）
                    line1, col1 = parse_location(str(f.location or ""))
                    if line1 is not None:
                        loc = f" L{line1}" + (f":C{col1}" if col1 else "")
                    else:
                        loc = ""
                    click.echo(f"  {marker} [{result.template_id}{loc}] {prefix}{f.rule_id}: {f.description}")

        # R233-P2-01: deprecation 迁移提示 — stderr 面(协议/机器通道 stdout 神圣,
        # --json/--stdio/ci_mode 一律不出现此提示); deprecate 不改裁决, 只加信号
        if not ci_mode:
            from ai_prompt_toolkit.linter.rules import get_rule

            # R233: 循环变量避用 r — 本函数后文 r 绑定 dict(规则搜索/回归),
            # 复用 r 会改变 mypy 首次类型推断致 6 处既有误报(R196 同族问题)
            _deprecated_seen: set[str] = set()
            for lint_res in all_results:
                for f in lint_res.findings:
                    _rule = get_rule(f.rule_id)
                    if _rule and _rule.status == "deprecated" and f.rule_id not in _deprecated_seen:
                        _deprecated_seen.add(f.rule_id)
                        click.echo(
                            f"⚠ [{f.rule_id}] 已弃用(v{_rule.deprecated_since} 起, 计划 v{_rule.removal_version} 摘除)"
                            f" — 裁决不变, 请按 {f.rule_id} 修复建议迁移",
                            err=True,
                        )

    click.echo(
        f"\nLint完成 | 文件: {len(templates)} | 平均分: {avg_score:.1f}/100 | 问题: {total_findings} | 质量分: {avg_quality:.1f}"
    )

    # R212-8: lint时成本预估(INFO级, 不产生finding不进门禁) — 成本是用户第一直觉
    # 指标。复用 token_analyzer×pricing(零新依赖), 按原始prompt文本估token×
    # 默认模型定价, 投影1k/1M调用两档; 定价数据缺失时优雅降级(仅显示token数)。
    if not ci_mode and not tui_mode and fmt != "json" and templates:
        from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens
        from ai_prompt_toolkit.pricing import get_catalog

        _n_tok = 0
        _sum_call = 0.0
        _count = 0
        for _tpl in templates:
            try:
                _t = _tpl.read_text(encoding="utf-8")
            except OSError:
                continue
            _est = analyze_prompt_tokens(_t, "default").estimate
            _n_tok += _est.estimated_tokens
            _sum_call += _est.estimated_input_cost_usd + _est.estimated_output_cost_usd
            _count += 1
        if _count > 0:
            # 单文件: 该prompt单次成本; 多文件: 取均值(代表性单次调用成本)
            _avg_tok = _n_tok // _count
            _per_call = _sum_call / _count
            _model_price = get_catalog().get_or_default("default")
            if _model_price.input_cost_per_token > 0 or _model_price.output_cost_per_token > 0:
                click.echo(
                    f"成本预估 | ~{_avg_tok} tokens | "
                    f"~${_per_call:.4f}/call | ~${_per_call * 1000:,.2f}/1k次 | ~${_per_call * 1_000_000:,.0f}/1M次"
                )
            else:
                click.echo(f"成本预估 | ~{_avg_tok} tokens (定价数据缺失, 未计价)")

    # D3: 无高危发现时的下一步引导(CI模式已有PASS输出, 不重复; medium/info仍列出)
    has_blocking = any(
        getattr(f.severity, "value", str(f.severity)) in ("high", "critical") for r in all_results for f in r.findings
    )
    if not has_blocking and not ci_mode:
        from ai_prompt_toolkit.cli_helpers import clean_result_next_steps

        click.echo(clean_result_next_steps(avg_score, len(templates)))

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
            click.echo(
                f"  {r['rule_id']}: {r['name']} [{r['category']}] {r['severity']} {'OWASP:' + owasp_str if owasp_str else ''}"
            )
            click.echo(f"    {r['description']}")

    if statistics_mode:
        from typing import Any as _Any

        from ai_prompt_toolkit.linter.rules import compute_rule_statistics

        all_findings_flat = []
        # R196: 循环变量改名避免与上方search_rules的dict循环变量r同名(mypy沿用首次推断)
        for lint_res in all_results:
            all_findings_flat.extend(lint_res.findings)
        stats: dict[str, _Any] = compute_rule_statistics(all_findings_flat)
        click.echo("\n── 规则命中率统计 ──")
        click.echo(f"  总命中: {stats['total_findings']} | 涉及规则: {stats['unique_rules']}")
        if stats["by_category"]:
            click.echo(f"  按类别: {', '.join(f'{k}={v}' for k, v in stats['by_category'].items())}")
        if stats["by_severity"]:
            click.echo(f"  按严重度: {', '.join(f'{k}={v}' for k, v in stats['by_severity'].items())}")
        click.echo(f"  {'规则ID':<8} {'命中':>5} {'占比':>8} {'名称'}")
        click.echo(f"  {'─' * 8} {'─' * 5} {'─' * 8} {'─' * 30}")
        for rs in stats["rules"]:
            click.echo(f"  {rs['rule_id']:<8} {rs['hit_count']:>5} {rs['hit_rate']:>7.1f}% {rs['name']}")

    if baseline_save and not baseline_path:
        baseline_path = ".baseline.json"  # R186: 单独--baseline-save用默认路径(修复静默无效)
    if baseline_path:
        from ai_prompt_toolkit.linter.baseline import compare_baseline, load_baseline, save_baseline

        all_findings_for_baseline = []
        for lint_res in all_results:
            for f in lint_res.findings:
                all_findings_for_baseline.append(
                    {
                        "rule_id": f.rule_id,
                        "description": f.description,
                        "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                    }
                )
        if baseline_save:
            save_baseline(all_findings_for_baseline, baseline_path, template_id=target, score=avg_score)
            click.echo(
                f"\n基线已保存: {baseline_path} (findings={len(all_findings_for_baseline)}, score={avg_score:.1f})"
            )
        else:
            bp = Path(baseline_path)
            if bp.exists():
                baseline = load_baseline(baseline_path)
                diff = compare_baseline(all_findings_for_baseline, baseline)
                click.echo("\n── 基线对比 ──")
                click.echo(
                    f"  基线: {baseline.total_findings} (score={baseline.score:.1f}) | 当前: {diff.current_total} | Δ={diff.delta:+d}"
                )
                if diff.new_findings:
                    click.echo(
                        f"  新增({len(diff.new_findings)}): {', '.join(f['rule_id'] for f in diff.new_findings[:10])}"
                    )
                if diff.fixed_findings:
                    click.echo(
                        f"  修复({len(diff.fixed_findings)}): {', '.join(f['rule_id'] for f in diff.fixed_findings[:10])}"
                    )
                if diff.regressions:
                    reg_parts = []
                    for r in diff.regressions:
                        reg_parts.append(f"{r['rule_id']}(+{r['delta']})")
                    click.echo(f"  回归({len(diff.regressions)}): {', '.join(reg_parts)}")
                status = "⚠️ 回归" if diff.is_regression else "✅ 改善" if diff.delta < 0 else "➡️ 不变"
                click.echo(f"  状态: {status}")
            else:
                click.echo(f"\n基线文件不存在: {baseline_path} (使用--baseline-save先保存)")

    if json_diff_path and baseline_path:
        from ai_prompt_toolkit.linter.baseline import compare_baseline, load_baseline
        from ai_prompt_toolkit.linter.structured_diff import format_diff_json, generate_structured_diff

        bp = Path(baseline_path)
        if bp.exists():
            baseline_obj = load_baseline(baseline_path)
            all_f_for_diff = []
            # R196: 循环变量改名 — 避免与上方dict循环变量r同名被mypy沿用推断
            for lint_res in all_results:
                for f in lint_res.findings:
                    all_f_for_diff.append(
                        {
                            "rule_id": f.rule_id,
                            "description": f.description,
                            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                        }
                    )
            diff_obj = compare_baseline(all_f_for_diff, baseline_obj)
            structured = generate_structured_diff(diff_obj, baseline_obj, all_f_for_diff, target=target)
            Path(json_diff_path).write_text(format_diff_json(structured), encoding="utf-8")
            click.echo(f"JSON diff已输出: {json_diff_path} (verdict={structured['verdict']})")

    if suggest_mode:
        from ai_prompt_toolkit.linter.suggest import generate_suggestions

        all_findings_for_suggest = []
        for lint_res in all_results:
            all_findings_for_suggest.extend(lint_res.findings)
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
        for lint_res in all_results:
            all_findings_for_explain.extend(lint_res.findings)
        explanations = explain_results(all_findings_for_explain)
        click.echo(f"\n── 详细解释 ({len(explanations)}条) ──")
        for expl in explanations:
            click.echo(format_explanation(expl))
            click.echo()

    if export_lcov_path:
        from ai_prompt_toolkit.linter.lcov_export import generate_coverage_summary, generate_lcov_report

        all_findings_for_lcov = []
        for lint_res in all_results:
            all_findings_for_lcov.extend(lint_res.findings)
        lcov_data = generate_lcov_report(all_findings_for_lcov)
        Path(export_lcov_path).write_text(lcov_data, encoding="utf-8")
        summary = generate_coverage_summary(all_findings_for_lcov)
        click.echo(
            f"\nlcov覆盖率: {summary['hit_rules']}/{summary['total_rules']} ({summary['coverage_pct']}%) → {export_lcov_path}"
        )

    if fix and any(r.auto_fixed for r in all_results):
        fixed = sum(len(r.fixed_findings) for r in all_results if r.auto_fixed)
        click.echo(f"自动修复: {fixed} 处")

    if show_diff and any(r.auto_fixed for r in all_results):
        import difflib

        for lint_res in all_results:
            if lint_res.auto_fixed and hasattr(lint_res, "original_text") and hasattr(lint_res, "fixed_text"):
                orig_lines = (lint_res.original_text or "").splitlines(keepends=True)
                fixed_lines = (lint_res.fixed_text or "").splitlines(keepends=True)
                diff_lines = difflib.unified_diff(
                    orig_lines, fixed_lines, fromfile="original", tofile="fixed", lineterm=""
                )
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

    if fail_on_waiver:
        # R213-P0-2: waiver审计门禁 — 任何豁免实际生效即FAIL(严格CI禁新增豁免)
        total_waived = sum(r.waived_finding_count for r in all_results)
        waived_files = [r.template_id for r in all_results if r.waived_finding_count > 0]
        if total_waived:
            shown = ", ".join(waived_files[:10]) + ("…" if len(waived_files) > 10 else "")
            click.echo(
                f"Waiver门禁: ❌ FAIL | {len(waived_files)}个文件豁免生效, 共压制{total_waived}条finding: {shown}"
            )
            sys.exit(2)
        click.echo("Waiver门禁: ✅ PASS | 0个豁免生效")

    # R224-P1-2: 增量门禁 — --incremental 与 --baseline 合用时, 把 --gate/--fail-on
    # 的判定面过滤为仅 NEW findings(不在基线快照内), 存量PRE-EXISTING放行,
    # 解决老仓库接入被500条存量打回的采用死结。复用compare_baseline, 无新模块。
    _incremental_new_keys: set[str] | None = None
    if incremental:
        if not baseline_path:
            click.echo("错误: --incremental 需配合 --baseline <path>(基线文件)使用", err=True)
            sys.exit(2)
        from ai_prompt_toolkit.linter.baseline import compare_baseline, load_baseline

        _bp = Path(baseline_path)
        if not _bp.exists():
            click.echo(f"错误: 基线文件不存在 {_bp} (先 --baseline-save 保存)", err=True)
            sys.exit(2)
        _base = load_baseline(baseline_path)
        _all_f: list[dict[str, str]] = []
        for lint_res in all_results:
            for f in lint_res.findings:
                _all_f.append(
                    {
                        "rule_id": f.rule_id,
                        "description": f.description,
                        "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                    }
                )
        _diff = compare_baseline(_all_f, _base)
        _incremental_new_keys = {f"{f['rule_id']}:{f['description']}" for f in _diff.new_findings}
        click.echo(
            f"── 增量门禁 ──\n"
            f"  基线: {_base.total_findings} | 当前: {_diff.current_total} | "
            f"新增: {len(_diff.new_findings)} | 已修复: {len(_diff.fixed_findings)}\n"
            f"  门禁判定面 = 仅 {len(_diff.new_findings)} 条 NEW findings (存量放行)"
        )

    if fail_on:
        # R203: 显式级别门禁 — fail-on critical/high/medium, 该级别及以上有finding即FAIL(退出码2)
        _level_rank = {"critical": 0, "high": 1, "medium": 2}
        _threshold = _level_rank[fail_on]
        _failing = 0
        for lint_res in all_results:
            for f in lint_res.findings:
                if _incremental_new_keys is not None:
                    if f"{f.rule_id}:{f.description}" not in _incremental_new_keys:
                        continue
                sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                if _level_rank.get(sev, 99) <= _threshold:
                    _failing += 1
        if _failing:
            click.echo(f"Fail-on门禁: ❌ FAIL | {fail_on}及以上 {_failing} 处 (阈值: >0)")
            sys.exit(2)
        click.echo(f"Fail-on门禁: ✅ PASS | {fail_on}及以上 0 处")

    if gate:
        from ai_prompt_toolkit.linter.quality_gate import QualityGate

        qg = QualityGate()
        all_findings_flat = []
        for lint_res in all_results:
            all_findings_flat.extend(lint_res.findings)
        if _incremental_new_keys is not None:
            all_findings_flat = [
                f for f in all_findings_flat if f"{f.rule_id}:{f.description}" in _incremental_new_keys
            ]
        gate_result = qg.evaluate(all_findings_flat, score=avg_score)
        verdict_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        click.echo(
            f"Quality Gate: {verdict_emoji.get(gate_result.verdict.value, '')} {gate_result.verdict.value.upper()} | {gate_result.summary}"
        )
        if output:
            report_data["quality_gate"] = gate_result.to_dict()
        from ai_prompt_toolkit.linter.quality_gate import verdict_to_exit_code

        sys.exit(verdict_to_exit_code(gate_result.verdict))

    if fmt == "sarif" and output:
        sarif_data = _generate_sarif(all_results, target)
        import json as _json

        Path(output).write_text(_json.dumps(sarif_data, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"SARIF报告: {output}")
    elif fmt == "html":
        from ai_prompt_toolkit.html_report import generate_html_report

        findings_list = []
        for lint_res in all_results:
            for f in lint_res.findings:
                findings_list.append(
                    {
                        "rule_id": f.rule_id,
                        "severity": str(f.severity.value if hasattr(f.severity, "value") else f.severity),
                        "category": getattr(f, "category", "other"),
                        "name": getattr(f, "name", ""),
                        "message": f.description,
                        "remediation": getattr(f, "remediation", ""),
                    }
                )
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
        import time as _time

        from ai_prompt_toolkit.linter.linter import PromptLinter

        click.echo(f"lint --watch: 监听 {target} (Ctrl+C退出)...")
        _watch_linter = PromptLinter()
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
                        _res = _watch_linter.lint(
                            _tp.name,
                            _text,
                            fix=False,
                            template_type=_detect_template_type(_text),
                            target_model=target_model,
                        )
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
@click.option("--resume", is_flag=True, help="恢复模式: 从上次SIGINT中断处继续(参考pytest --lf)")
def scan(
    target: str,
    provider: str | None,
    fmt: str,
    output: str | None,
    incremental: bool,
    explain: bool,
    resume: bool = False,
) -> None:
    """安全扫描：检测Prompt注入、敏感信息泄露等安全风险"""
    from ai_prompt_toolkit.cli_helpers import determine_exit_code, discover_templates, empty_state_tip, write_report
    from ai_prompt_toolkit.security import DictTemplateProvider, scan_template

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("scan"))
        sys.exit(0)

    # R177: 恢复R71的--resume功能
    _scan_done: list[str] = []
    if resume:
        from ai_prompt_toolkit.resume_state import load_progress

        saved = load_progress("scan")
        if saved:
            _scan_done = saved.get("completed_files", [])
            templates = [t for t in templates if str(t) not in set(_scan_done)]
            click.echo(f"恢复进度: 已完成 {len(_scan_done)} 个文件, 剩余 {len(templates)} 个")
        else:
            click.echo("无已保存的进度, 从头开始")
    if resume and not templates:
        from ai_prompt_toolkit.resume_state import clear_progress

        try:
            clear_progress("scan")
        except Exception:
            pass
        click.echo("全部文件已扫描, 无待处理项")
        sys.exit(0)

    prov = DictTemplateProvider({})
    if provider:
        import yaml as _yaml

        from ai_prompt_toolkit.security.inheritance_auditor import DictTemplateProvider

        prov_data = _yaml.safe_load(Path(provider).read_text(encoding="utf-8"))
        prov = DictTemplateProvider(prov_data or {})

    all_results = []
    total_findings = 0

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        result = scan_template(tpl_path.name, text, prov, incremental=incremental)
        all_results.append(result)
        total_findings += len(result.all_findings)
        if resume:
            from ai_prompt_toolkit.resume_state import save_progress

            _scan_done.append(str(tpl_path))
            save_progress("scan", [], _scan_done, [str(t) for t in templates[templates.index(tpl_path) + 1 :]])

        if fmt == "cli" and result.all_findings:
            for f in result.all_findings:
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

    has_critical = any(any(f.severity.value in ("critical", "high") for f in r.all_findings) for r in all_results)
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
            click.echo(f"  {'─' * 16} {'─' * 8} {'─' * 12} {'─' * 12}")
            for est in comp.estimates:
                click.echo(
                    f"  {est.model:<16} {est.estimated_tokens:>8} {est.estimated_input_cost_usd:>12.6f} {est.estimated_output_cost_usd:>12.6f}"
                )
            click.echo(f"\n  💰 最便宜: {comp.cheapest_model} | 🎯 最少Token: {comp.most_efficient_model}")
        else:
            result = analyze_prompt_tokens(text, model)
            est = result.estimate
            click.echo(f"\n📊 [{tpl_path.name}] Token分析")
            click.echo(f"  模型: {est.model} | 字符数: {est.char_count} | Token数: {est.estimated_tokens}")
            click.echo(
                f"  输入成本: ${est.estimated_input_cost_usd:.6f}/1K | 输出成本: ${est.estimated_output_cost_usd:.6f}/1K"
            )
            if result.savings_tokens > 0:
                click.echo(f"  💡 可优化: {result.savings_tokens} tokens ({result.savings_percent:.1f}%)")
            for s in result.suggestions[:3]:
                click.echo(f"    - [{s.priority}] {s.description}")
            if output:
                import json as _json

                Path(output).write_text(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_trace_json(tracer: object, path: Path) -> None:
    """U1: 将tracer的span树落盘为JSON(OTLP兼容), 供Langfuse/Jaeger/Grafana消费"""
    trace_data = tracer.to_dict()  # type: ignore[attr-defined]
    to_otlp = getattr(tracer, "to_otlp_json", None)
    if callable(to_otlp):
        trace_data["otlp"] = json.loads(to_otlp())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace_data, ensure_ascii=False, indent=2), encoding="utf-8")
