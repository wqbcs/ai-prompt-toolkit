"""prompt-cli统一入口"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import click

from ai_prompt_toolkit import __version__


def _detect_template_type(text: str) -> str:
    if not text.startswith("---"):
        return "prompt"
    import yaml as _yaml
    end = text.find("---", 3)
    if end == -1:
        return "prompt"
    try:
        data = _yaml.safe_load(text[3:end].strip())
        if isinstance(data, dict) and data.get("template_type"):
            return data["template_type"]
    except _yaml.YAMLError:
        pass
    return "prompt"


def _generate_sarif(results: list, target: str) -> dict:
    import json as _json
    from ai_prompt_toolkit.linter.rules import get_rule
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "ai-prompt-toolkit",
                    "version": __version__,
                    "informationUri": "https://github.com/ai-prompt-toolkit",
                    "rules": [],
                }
            },
            "results": [],
        }]
    }
    rules_seen = set()
    for result in results:
        for f in result.findings:
            if f.rule_id not in rules_seen:
                rules_seen.add(f.rule_id)
                rule_def = get_rule(f.rule_id)
                rule_entry = {
                    "id": f.rule_id,
                    "shortDescription": {"text": f.description},
                    "properties": {"severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity)},
                }
                if rule_def:
                    rule_entry["helpUri"] = f"https://ai-prompt-toolkit.dev/rules/{f.rule_id}"
                    if rule_def.remediation:
                        rule_entry["fullDescription"] = {"text": f"{rule_def.description}\n\nFix: {rule_def.remediation}"}
                    if rule_def.owasp_refs:
                        rule_entry["properties"]["owaspRefs"] = rule_def.owasp_refs
                    rule_entry["properties"]["category"] = rule_def.category
                    rule_entry["properties"]["precision"] = "high" if rule_def.category == "security" else "medium"
                sarif["runs"][0]["tool"]["driver"]["rules"].append(rule_entry)
            sev_map = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
            sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
            sarif["runs"][0]["results"].append({
                "ruleId": f.rule_id,
                "level": sev_map.get(sev, "warning"),
                "message": {"text": f.description},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": result.template_id}}}],
            })
    return sarif


@click.group()
@click.version_option(version=__version__, prog_name="prompt-cli", message="%(prog)s %(version)s\n\n组件统计: 150条Lint规则 | 90评估维度 | 59 MCP工具 | 23+ Probes | 11+ Detectors | 25 Providers")
def main() -> None:
    """AI提示词体系工具链"""
    from ai_prompt_toolkit.easter_eggs import is_first_run, show_welcome
    if is_first_run():
        show_welcome()


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """生成Shell自动补全脚本(bash/zsh/fish)

    使用方式:
      apt completion bash > ~/.apt-completion.bash && echo 'source ~/.apt-completion.bash' >> ~/.bashrc
      apt completion zsh > ~/.zsh/completion/_apt && echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc
      apt completion fish > ~/.config/fish/completions/apt.fish
    """
    from click.shell_completion import get_completion_class
    prog_name = "apt"
    complete_var = f"_APT_COMPLETE={shell}_source"
    comp_class = get_completion_class(shell)
    if comp_class is None:
        click.echo(f"不支持 {shell} 补全", err=True)
        raise SystemExit(1)
    comp = comp_class(main, {}, prog_name, complete_var)
    script = comp.source()
    click.echo(script)
@main.result_callback()
def _handle_result(result: Any, **kwargs: Any) -> None:
    pass


def _install_exception_handler() -> None:
    import functools
    import signal

    original_invoke = main.invoke

    _graceful_exit_active = False

    def _sigint_handler(signum: int, frame: Any) -> None:
        nonlocal _graceful_exit_active
        if _graceful_exit_active:
            import sys
            sys.exit(130)
        _graceful_exit_active = True
        try:
            from ai_prompt_toolkit.resume_state import save_progress
            import inspect
            _local = frame.f_locals if frame else {}
            _cf = _local.get("_completed_files", [])
            _af = _local.get("_all_file_names", [])
            _cmd = _local.get("resume_cmd_hint", "lint")
            if _cf and _af:
                pending = [f for f in _af if f not in set(_cf)]
                save_progress(_cmd, [], _cf, pending)
                click.echo(f"\n\n⏹ 操作已取消。进度已保存({_cmd}: {len(_cf)}/{len(_af)})，使用 --resume 恢复。", err=True)
            else:
                click.echo("\n\n⏹ 操作已取消。进度已保存，可重新运行继续。", err=True)
        except Exception:
            click.echo("\n\n⏹ 操作已取消。进度已保存，可重新运行继续。", err=True)
        import sys
        sys.exit(130)

    try:
        signal.signal(signal.SIGINT, _sigint_handler)
    except (OSError, ValueError):
        pass

    def _wrapped_invoke(ctx: click.Context) -> None:
        from ai_prompt_toolkit.errors import ToolkitError, format_error_for_cli, toolkit_exit_code
        try:
            original_invoke(ctx)
        except ToolkitError as e:
            click.echo(f"错误: {format_error_for_cli(e)}", err=True)
            ctx.exit(toolkit_exit_code(e))
        except click.exceptions.Exit:
            raise
        except click.exceptions.Abort:
            click.echo("\n操作已取消", err=True)
            ctx.exit(130)

    main.invoke = _wrapped_invoke  # type: ignore[method-assign]

_install_exception_handler()


@main.command()
@click.option("--source", "-s", required=True, help="源模板文件路径")
@click.option("--context", "-c", help="编译上下文JSON文件路径")
@click.option("--config", help="编译配置YAML文件路径")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--report", help="编译报告输出路径(JSON)")
def compile(source: str, context: str | None, config: str | None,
            output: str | None, report: str | None) -> None:
    """条件编译：按模型/语言/行业条件编译提示词模板"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_context, write_report, determine_exit_code
    from ai_prompt_toolkit.compiler import compile_template, CompileContext

    src_path = resolve_path(source)
    template_text = src_path.read_text(encoding="utf-8")
    ctx_data = load_context(context) if context else {}

    try:
        model = ctx_data.get("model", "")
        language = ctx_data.get("language", "")
        industry = ctx_data.get("industry", "")
        flags = {k: v for k, v in ctx_data.items() if k not in ("model", "language", "industry") and isinstance(v, bool)}
        ctx = CompileContext(model=model, language=language, industry=industry, flags=flags)
        result = compile_template(template_text, ctx)
    except Exception as e:
        from ai_prompt_toolkit.errors import CompilerError
        if isinstance(e, CompilerError):
            raise
        raise CompilerError(str(e)) from e

    if output:
        Path(output).write_text(result.compiled_text, encoding="utf-8")
        click.echo(f"已输出: {output}")

    click.echo(f"编译完成 | 激活分支: {len(result.report.activated_branches)} "
               f"| 忽略分支: {len(result.report.ignored_branches)} "
               f"| 警告: {len(result.report.warnings)}")

    if report:
        write_report(result.report.to_dict(), report, fmt="json")
        click.echo(f"报告: {report}")

    sys.exit(determine_exit_code(has_errors=False, has_findings=len(result.report.warnings) > 0))


@main.command(name="ab-test")
@click.option("--config", "-c", required=True, help="A/B测试配置YAML文件路径")
@click.option("--models", "-m", help="模型列表(逗号分隔)")
@click.option("--dataset", "-d", help="测试数据集路径")
@click.option("--output", "-o", help="输出报告路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def ab_test(config: str, models: str | None, dataset: str | None,
            output: str | None, fmt: str) -> None:
    """A/B测试：多模型并行对比提示词效果"""
    import asyncio
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_config, write_report, empty_state_tip
    from ai_prompt_toolkit.ab_test.types import ABTestConfig, ModelConfig, ProviderType, TestDataset
    from ai_prompt_toolkit.ab_test.engine import ParallelEngine
    from ai_prompt_toolkit.ab_test.statistics import StatisticalAnalyzer
    from ai_prompt_toolkit.ab_test.recommender import Recommender

    cfg = load_config(config)
    model_list = models.split(",") if models else cfg.get("models", [])

    parsed_models = []
    for m in model_list:
        parts = m.strip().split(":")
        if len(parts) == 2:
            provider_str, model_name = parts
            try:
                provider = ProviderType(provider_str)
            except ValueError:
                click.echo(f"警告: 未知Provider '{provider_str}'，使用openai", err=True)
                provider = ProviderType.OPENAI
        else:
            provider = ProviderType.OPENAI
            model_name = m.strip()
        parsed_models.append(ModelConfig(provider=provider, model_name=model_name))

    if not parsed_models:
        click.echo(empty_state_tip("ab-test"))
        sys.exit(2)

    items = [{"input": "测试输入"}]
    if dataset:
        import json as _json
        ds_path = resolve_path(dataset)
        with open(ds_path, encoding="utf-8") as f:
            data = _json.load(f)
            items = data if isinstance(data, list) else data.get("items", [{"input": str(data)}])

    ds = TestDataset(dataset_id="cli-ds", name="CLI数据集", items=items)
    templates = cfg.get("prompt_templates", ["请根据以下内容生成回复：{input}"])

    ab_config = ABTestConfig(
        test_id=f"cli-ab-{int(time.time())}",
        models=parsed_models,
        datasets=[ds],
        prompt_templates=templates,
    )

    engine = ParallelEngine(ab_config)

    click.echo(f"A/B测试 | 模型: {', '.join(m.provider.value + ':' + m.model_name for m in parsed_models)}")
    click.echo(f"数据集: {len(items)}条 | 模板: {len(templates)}个")

    results = asyncio.run(engine.run())

    summary = engine.get_summary()

    if fmt == "json":
        report_data = {"summary": summary, "results": [r.model_result.to_dict() for r in results]}
        if output:
            write_report(report_data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(report_data, ensure_ascii=False, indent=2))
    else:
        for name, stats in summary.items():
            click.echo(f"\n  {name}:")
            click.echo(f"    成功: {stats['success']}/{stats['total']}")
            click.echo(f"    平均延迟: {stats['avg_latency_ms']:.1f}ms")
            click.echo(f"    总费用: ${stats['total_cost']:.4f}")
            click.echo(f"    平均Token: {stats['avg_token_count']:.0f}")

    from ai_prompt_toolkit.ab_test.provider import get_cost_tracker
    cost_tracker = get_cost_tracker()
    if cost_tracker.spent > 0:
        click.echo(f"\n总费用: ${cost_tracker.spent:.4f} (剩余: ${cost_tracker.remaining:.2f})")


@main.command()
@click.option("--target", "-t", required=True, help="评估目标(文件或目录)")
@click.option("--dimensions", "-d", help="指定维度(逗号分隔，如D1,D5,D10)")
@click.option("--categories", help="指定类别(逗号分隔，如structure,security)")
@click.option("--threshold", type=float, default=0.0, help="质量阈值(0-10，低于此值退出码1)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli", "table", "yaml"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
@click.option("--quick", is_flag=True, help="快速模式: 仅评估TOP10核心维度(D01-D10)")
@click.option("--save", "save_history", is_flag=True, help="保存评估结果到历史(SQLite)")
@click.option("--preset", type=click.Choice(["default", "security-heavy", "quality-balanced", "performance-first", "harmonyos-strict", "redteam-ready", "cost-efficient"]), default="default", help="权重预设(行业场景)")
def evaluate(target: str, dimensions: str | None, categories: str | None,
             threshold: float, fmt: str, output: str | None, quick: bool,
             save_history: bool, preset: str) -> None:
    """130维度质量评估：全面评估Prompt质量(支持行业权重预设)"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report, empty_state_tip
    from ai_prompt_toolkit.evaluator import evaluate_template, get_weight_preset

    weight_preset_obj = get_weight_preset(preset)
    _wo = weight_preset_obj._overrides if (weight_preset_obj and preset != "default") else None
    if _wo:
        click.echo(f"权重预设: {weight_preset_obj.display_name} ({weight_preset_obj.description})")

    target_path = resolve_path(target)
    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None
    if quick and dim_list is None:
        dim_list = [f"D{i:02d}" for i in range(1, 11)]
    cat_list = [c.strip() for c in categories.split(",")] if categories else None

    if target_path.is_dir():
        files = sorted(f for f in target_path.rglob("*.md") if len(f.relative_to(target_path).parts) <= 10)
    else:
        files = [target_path]

    if not files:
        click.echo(empty_state_tip("evaluate"))
        sys.exit(2)

    reports = []

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
        from rich.console import Console as _EvConsole
        _has_rich_ev = True
        _ev_console = _EvConsole()
    except ImportError:
        _has_rich_ev = False

    if _has_rich_ev:
        from ai_prompt_toolkit.cli_helpers import friendly_progress_label
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), MofNCompleteColumn(), TimeElapsedColumn(), TimeRemainingColumn(), console=console) as progress:
            task = progress.add_task("质量评估中...", total=len(files))
            for i, f in enumerate(files, 1):
                text = f.read_text(encoding="utf-8")
                report = evaluate_template(
                    str(f), text, dimensions=dim_list, categories=cat_list, weight_overrides=_wo
                )
                reports.append(report)
                progress.update(task, description=friendly_progress_label("evaluate", i, len(files)))
                progress.advance(task)
    else:
        for f in files:
            text = f.read_text(encoding="utf-8")
            report = evaluate_template(
                str(f), text, dimensions=dim_list, categories=cat_list, weight_overrides=_wo
            )
            reports.append(report)

    if fmt == "json":
        import json as _json
        data = {"reports": [r.to_dict() for r in reports]}
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"报告已保存: {output}")

    elif fmt == "table":
        try:
            from rich.console import Console as _TConsole
            from rich.table import Table as _Table
            _tc = _TConsole()
            for report in reports:
                t = _Table(title=f"评估: {report.template_id}")
                t.add_column("维度", style="cyan")
                t.add_column("名称")
                t.add_column("类别")
                t.add_column("分数", justify="right")
                t.add_column("权重", justify="right")
                for s in report.scores[:30]:
                    t.add_row(s.dimension_id, s.name, s.category, f"{s.score:.1f}", f"{s.weight:.1f}")
                _tc.print(t)
        except ImportError:
            click.echo("Table format requires 'rich' package")

    elif fmt == "yaml":
        try:
            import yaml as _yaml
            data = [r.to_dict() for r in reports]
            click.echo(_yaml.dump(data, allow_unicode=True, default_flow_style=False))
        except ImportError:
            import json as _json
            data = [r.to_dict() for r in reports]
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if _has_rich_ev:
            from ai_prompt_toolkit.cli_helpers import print_rich_evaluate_summary
            print_rich_evaluate_summary(reports, threshold=threshold, console=_ev_console)
            total_score_val = 0.0
            total_count = 0
            for report in reports:
                scores = report.scores
                if not scores:
                    continue
                avg = sum(s.score for s in scores) / len(scores) if scores else 0
                total_score_val += avg
                total_count += 1
            if total_count > 0:
                _ev_console.print(f"\n总均分: [bold]{total_score_val / total_count:.1f}/10[/bold]")
        else:
            total_score = 0.0
            total_count = 0
            low_items = []
            for report in reports:
                scores = report.scores
                if not scores:
                    continue
                avg = sum(s.score for s in scores) / len(scores) if scores else 0
                total_score += avg
                total_count += 1
                tid = report.template_id if hasattr(report, 'template_id') else 'unknown'
                click.echo(f"  {tid}: 均分 {avg:.1f}/10 ({len(scores)}维度)")
                if threshold > 0 and avg < threshold:
                    low_items.append((tid, avg))

            if total_count > 0:
                click.echo(f"\n总均分: {total_score / total_count:.1f}/10")

            if low_items:
                click.echo(f"\n低于阈值({threshold})的模板({len(low_items)}个):")
                for tid, score in low_items[:5]:
                    click.echo(f"  {tid}: {score:.1f}/10")

    exit_code = 0
    if threshold > 0:
        for report in reports:
            scores = report.scores
            avg = sum(s.score for s in scores) / len(scores) if scores else 0
            if avg < threshold:
                exit_code = 1
                break

    if save_history:
        from ai_prompt_toolkit.eval_store import EvalStore
        store = EvalStore()
        for report in reports:
            snapshot = store.save(report)
            click.echo(f"  已保存: #{snapshot.snapshot_id} ({report.template_id})")
            alerts = store.get_alerts(template_id=report.template_id, limit=5)
            if alerts:
                for a in alerts:
                    click.echo(f"  ⚠ 回归告警: {a.dimension_name} {a.previous_score:.1f}→{a.current_score:.1f} ({a.change_percent:.0f}%)")
        store.close()

    sys.exit(exit_code)


@main.command()
@click.option("--target", "-t", required=True, help="扫描目标(文件或目录)")
@click.option("--config", help="安全扫描配置YAML文件路径")
@click.option("--incremental", is_flag=True, help="增量扫描模式")
@click.option("--depth", type=click.Choice(["quick", "standard", "deep"]),
              default="standard", help="扫描深度: quick=仅注入, standard=5层检测, deep=5层+Probe+评分卡")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli", "sarif", "jsonl"]),
              default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--resume", is_flag=True, help="从上次中断处恢复进度")
@click.option("--semantic-cache", "semantic_cache", is_flag=True, help="启用语义缓存(避免重复scan相似prompt)")
def scan(target: str, config: str | None, incremental: bool, depth: str,
         fmt: str, output: str | None, resume: bool, semantic_cache: bool) -> None:
    """安全扫描：5层融合检测(注入/PII/供应链/结构/消毒)+可选Probe+评分卡"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code, empty_state_tip, friendly_progress_label
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.prompt_sanitizer import PromptSanitizer
    from ai_prompt_toolkit.types import Finding, Severity

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("scan"))
        sys.exit(0)

    _completed_files: list[str] = []
    _all_file_names = [str(t) for t in templates]
    resume_cmd_hint = "scan"
    if resume:
        from ai_prompt_toolkit.resume_state import load_progress, clear_progress
        saved = load_progress("scan")
        if saved:
            _completed_files = saved.get("completed_files", [])
            click.echo(f"恢复进度: 已完成 {len(_completed_files)}/{len(templates)} 个文件")
            templates = [t for t in templates if str(t) not in set(_completed_files)]
        else:
            click.echo("无已保存的进度，从头开始")
            _completed_files = []

    injection_detector = InjectionDetector()
    pii_detector = PIIDetector()
    supply_chain_detector = SupplyChainDetector()
    sanitizer = PromptSanitizer()
    all_findings = []
    detector_stats = {"injection": 0, "pii": 0, "supply_chain": 0, "structural": 0, "sanitizer": 0, "probe": 0}
    total = len(templates)

    _sem_cache = None
    if semantic_cache:
        from ai_prompt_toolkit.semantic_cache import SemanticCache
        _sem_cache = SemanticCache(threshold=0.85, max_size=500, ttl_seconds=86400.0)

    _SCAN_LAYERS = {
        "quick": ["injection"],
        "standard": ["injection", "pii", "supply_chain", "structural", "sanitizer"],
        "deep": ["injection", "pii", "supply_chain", "structural", "sanitizer", "probe"],
    }
    active_layers = _SCAN_LAYERS[depth]

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
        from rich.console import Console as _Console
        _has_rich = True
    except ImportError:
        _has_rich = False

    def _scan_single(text: str) -> list[dict]:
        findings_data = []
        if "injection" in active_layers:
            for f in injection_detector.detect(text):
                findings_data.append(f.to_dict())
                detector_stats["injection"] += 1
        if "pii" in active_layers:
            pii_finding = pii_detector.check(text)
            if pii_finding:
                findings_data.append(pii_finding.to_dict())
                detector_stats["pii"] += 1
        if "supply_chain" in active_layers:
            sc_finding = supply_chain_detector.check(text)
            if sc_finding:
                findings_data.append(sc_finding.to_dict())
                detector_stats["supply_chain"] += 1
        if "structural" in active_layers:
            struct_finding = check_structural(text)
            if struct_finding:
                findings_data.append(struct_finding.to_dict())
                detector_stats["structural"] += 1
        if "sanitizer" in active_layers:
            san_result = sanitizer.sanitize_prompt(text)
            if san_result.findings:
                for sf in san_result.findings:
                    findings_data.append(sf.to_dict())
                    detector_stats["sanitizer"] += 1
        if "probe" in active_layers:
            try:
                from ai_prompt_toolkit.probe_framework import ProbeRunner
                runner = ProbeRunner()
                report = runner.run(text, probes="auto")
                for pr in report.results:
                    for det_result in pr.detection_results:
                        if det_result.detected:
                            findings_data.append({
                                "rule_id": f"PROBE-{pr.probe_name}",
                                "severity": "high" if det_result.confidence > 0.7 else "medium",
                                "description": f"[{pr.probe_name}] {det_result.detector_name}: {det_result.reason}",
                            })
                            detector_stats["probe"] += 1
            except Exception:
                pass
        return findings_data

    if _has_rich:
        _console = _Console()
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), MofNCompleteColumn(), TimeElapsedColumn(), TimeRemainingColumn(), console=console) as progress:
            task = progress.add_task(f"安全扫描[{depth}]...", total=total)
            for i, tpl_path in enumerate(templates, 1):
                text = tpl_path.read_text(encoding="utf-8")
                findings_data = _scan_single(text)
                all_findings.extend(findings_data)
                _completed_files.append(str(tpl_path))
                if resume:
                    from ai_prompt_toolkit.resume_state import save_progress
                    pending = [f for f in _all_file_names if f not in set(_completed_files)]
                    save_progress("scan", [], _completed_files, pending)
                progress.update(task, description=friendly_progress_label("scan", i, total))
                progress.advance(task)
    else:
        for i, tpl_path in enumerate(templates, 1):
            text = tpl_path.read_text(encoding="utf-8")
            findings_data = _scan_single(text)
            all_findings.extend(findings_data)
            _completed_files.append(str(tpl_path))
            if resume:
                from ai_prompt_toolkit.resume_state import save_progress
                pending = [f for f in _all_file_names if f not in set(_completed_files)]
                save_progress("scan", [], _completed_files, pending)
            if fmt == "cli" and findings_data:
                for f in findings_data:
                    sev = f.get("severity", "info")
                    marker = {"high": "✗", "critical": "✗✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                    click.echo(f"  {marker} [{tpl_path.name}] {f.get('rule_id', '')}: {f.get('description', '')}")

    high_count = sum(1 for f in all_findings if f.get("severity") in ("high", "critical"))
    medium_count = sum(1 for f in all_findings if f.get("severity") == "medium")
    low_count = sum(1 for f in all_findings if f.get("severity") == "low")
    critical_count = sum(1 for f in all_findings if f.get("severity") == "critical")

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        console = Console()
        risk_label = "CRITICAL" if critical_count > 0 else "HIGH" if high_count > 0 else "MEDIUM" if medium_count > 0 else "LOW" if low_count > 0 else "SAFE"
        risk_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "cyan", "LOW": "green", "SAFE": "green"}[risk_label]
        top5 = sorted(all_findings, key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.get("severity", "low"), 3))[:5]
        summary_lines = [f"[bold]风险等级: [{risk_color}]{risk_label}[/{risk_color}][/bold]",
                         f"扫描深度: {depth} | 层数: {len(active_layers)} | 文件: {total} | 发现: {len(all_findings)}",
                         f"CRITICAL: {critical_count} | HIGH: {high_count - critical_count} | MEDIUM: {medium_count} | LOW: {low_count}"]

        layer_table = Table(title="检测层统计", show_header=True, header_style="bold")
        layer_table.add_column("检测层", style="cyan")
        layer_table.add_column("发现数", justify="right")
        layer_names = {"injection": "注入检测", "pii": "PII隐私", "supply_chain": "供应链", "structural": "结构分析", "sanitizer": "Prompt消毒", "probe": "Probe探测"}
        for layer_key in active_layers:
            layer_table.add_row(layer_names.get(layer_key, layer_key), str(detector_stats.get(layer_key, 0)))
        summary_lines_str = "\n".join(summary_lines)
        console.print(Panel(summary_lines_str, title=f"安全扫描摘要 [{depth}]", border_style=risk_color))
        console.print(layer_table)

        if top5:
            console.print("\n[bold]TOP5风险:[/bold]")
            for idx, f in enumerate(top5, 1):
                console.print(f"  {idx}. [{f.get('rule_id', '?')}] {f.get('description', '')[:70]}")

        if depth == "deep":
            try:
                from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
                findings_objs = [Finding(rule_id=f.get("rule_id", ""), severity=Severity(f.get("severity", "info")),
                                         description=f.get("description", "")) for f in all_findings]
                scorecard = compute_scorecard(findings_objs)
                score_lines = [f"[bold]安全评分: {scorecard.overall_score}/100 ({scorecard.grade.value})[/bold]",
                               f"决策: {scorecard.decision.value}"]
                for dim in scorecard.dimensions:
                    bar_filled = int(dim.ratio * 20)
                    bar = "█" * bar_filled + "░" * (20 - bar_filled)
                    score_lines.append(f"  {dim.name}: {dim.earned}/{dim.max_points} [{bar}]")
                console.print(Panel("\n".join(score_lines), title="安全评分卡", border_style="green" if scorecard.overall_score >= 75 else "yellow" if scorecard.overall_score >= 50 else "red"))
            except Exception:
                pass

        from ai_prompt_toolkit.security.finding_enhancer import enhance_findings
        findings_objs = [Finding(rule_id=f.get("rule_id", ""), severity=Severity(f.get("severity", "info")),
                                 description=f.get("description", "")) for f in all_findings[:10]]
        enhanced = enhance_findings(findings_objs)
        if enhanced:
            console.print("\n[bold]详细解释(TOP10):[/bold]")
            for ef in enhanced:
                console.print(f"  [bold][{ef.finding.rule_id}][/bold] {ef.plain_explanation}")
                if ef.risk_reason:
                    console.print(f"    [dim]风险: {ef.risk_reason}[/dim]")
    except ImportError:
        click.echo(f"\n=== 安全扫描摘要 [{depth}] ===")
        click.echo(f"风险等级: {'CRITICAL' if critical_count > 0 else 'HIGH' if high_count > 0 else 'MEDIUM' if medium_count > 0 else 'LOW' if low_count > 0 else 'SAFE'}")
        click.echo(f"层数: {len(active_layers)} | 文件: {total} | 发现: {len(all_findings)} (CRITICAL:{critical_count} HIGH:{high_count - critical_count} MEDIUM:{medium_count} LOW:{low_count})")
        for layer_key in active_layers:
            layer_names = {"injection": "注入检测", "pii": "PII隐私", "supply_chain": "供应链", "structural": "结构分析", "sanitizer": "Prompt消毒", "probe": "Probe探测"}
            click.echo(f"  {layer_names.get(layer_key, layer_key)}: {detector_stats.get(layer_key, 0)}")

    if output and all_findings:
        report_data: dict[str, Any] = {
            "scan_target": target,
            "scan_depth": depth,
            "active_layers": active_layers,
            "detector_stats": detector_stats,
            "total_files": total,
            "findings": all_findings,
            "risk_level": "critical" if high_count > 0 and any(f.get("severity") == "critical" for f in all_findings)
                         else "high" if high_count > 0
                         else "medium" if medium_count > 0
                         else "low" if low_count > 0 else "none",
        }
        if depth == "deep":
            try:
                from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
                findings_objs = [Finding(rule_id=f.get("rule_id", ""), severity=Severity(f.get("severity", "info")),
                                         description=f.get("description", "")) for f in all_findings]
                scorecard = compute_scorecard(findings_objs)
                report_data["scorecard"] = scorecard.to_dict()
            except Exception:
                pass
        if fmt == "sarif" and output:
            from ai_prompt_toolkit.report.sarif_reporter import write_sarif_report
            findings_objs = [Finding(rule_id=f.get("rule_id", ""), severity=Severity(f.get("severity", "info")),
                                     description=f.get("description", "")) for f in all_findings]
            write_sarif_report(findings_objs, output, source_file=target)
            click.echo(f"SARIF报告: {output}")
        elif fmt == "jsonl" and output:
            from ai_prompt_toolkit.report.sarif_reporter import write_jsonl_report
            findings_objs = [Finding(rule_id=f.get("rule_id", ""), severity=Severity(f.get("severity", "info")),
                                     description=f.get("description", "")) for f in all_findings]
            write_jsonl_report(findings_objs, output, source_file=target)
            click.echo(f"JSONL报告: {output}")
        else:
            write_report(report_data, output, fmt=fmt)
            if output:
                click.echo(f"报告: {output}")

    sys.exit(determine_exit_code(has_findings=len(all_findings) > 0,
                                  error_severity="high" if high_count > 0 else None))


@main.command()
@click.option("--target", "-t", required=True, help="Lint目标(文件或目录)")
@click.option("--config", help="Lint配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli", "sarif", "table", "yaml", "csv"]),
              default="cli", help="输出格式(json/html/cli/sarif/table/yaml/csv)")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
@click.option("--interactive", "-i", is_flag=True, help="交互式修复: 逐条确认每个修复")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--gate", is_flag=True, help="启用Quality Gate(CI模式，按verdict决定退出码)")
@click.option("--multimodal", "-mm", is_flag=True, help="启用多模态Lint检查(图片引用/格式/可访问性)")
@click.option("--fail-on", "fail_on", type=click.Choice(["none", "low", "medium", "high", "critical"]),
              default="none", help="CI失败阈值: 发现该级别及以上问题时退出码非0")
@click.option("--baseline", type=click.Path(exists=True), help="基线JSON文件路径(仅报告新增问题)")
@click.option("--inline-suppress", "inline_suppress", is_flag=True, help="识别并跳过行内抑制的规则(prompt-lint-disable)")
@click.option("--resume", is_flag=True, help="从上次中断处恢复进度")
@click.option("--watch", is_flag=True, help="监视文件变化，自动重新执行lint")
@click.option("--semantic-cache", "semantic_cache", is_flag=True, help="启用语义缓存(避免重复lint相似prompt)")
@click.option("--json-schema", "json_schema", is_flag=True, help="输出Lint规则集JSON Schema定义")
@click.option("--explain", "explain", is_flag=True, help="交互式修复建议: 对每个问题输出详细解释和修复方案")
@click.option("--parallel", "-j", "parallel", type=int, default=1, help="并行lint线程数(默认1, 设为0=CPU核数)")
@click.option("--quiet", "-q", "quiet", is_flag=True, help="精简模式: 仅输出PASS/FAIL和分数(CI友好)")
def lint(target: str, config: str | None, fmt: str, fix: bool, interactive: bool, output: str | None, gate: bool, multimodal: bool, fail_on: str, baseline: str | None, inline_suppress: bool, resume: bool, watch: bool, semantic_cache: bool, json_schema: bool, explain: bool, parallel: int, quiet: bool) -> None:
    """Prompt Linter：静态检查提示词质量"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code
    from ai_prompt_toolkit.linter.linter import PromptLinter

    if json_schema:
        from ai_prompt_toolkit.linter.rules import get_all_rules
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        import json as _json
        rules = get_all_rules()
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ai-prompt-toolkit Lint Rule Set",
            "type": "object",
            "properties": {
                "rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rule_id": {"type": "string", "pattern": "^P\\d{3}$"},
                            "name": {"type": "string"},
                            "category": {"type": "string"},
                            "severity": {"type": "string"},
                            "description": {"type": "string"},
                            "remediation": {"type": "string"},
                            "auto_fixable": {"type": "boolean"},
                            "owasp_refs": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["rule_id", "name", "category", "severity"],
                    },
                },
            },
        }
        rules_data = []
        for r in rules:
            entry = r.to_dict()
            entry["auto_fixable"] = r.rule_id in AUTO_FIXABLE_RULES
            rules_data.append(entry)
        output_data = {"schema": schema, "rules": rules_data, "total_count": len(rules_data)}
        click.echo(_json.dumps(output_data, ensure_ascii=False, indent=2))
        sys.exit(0)

    from ai_prompt_toolkit.cli_helpers import empty_state_tip

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("lint"))
        sys.exit(0)

    _completed_files: list[str] = []
    _all_file_names = [str(t) for t in templates]
    resume_cmd_hint = "lint"
    if resume:
        from ai_prompt_toolkit.resume_state import load_progress, load_results, clear_progress
        saved = load_progress("lint")
        if saved:
            _completed_files = saved.get("completed_files", [])
            click.echo(f"恢复进度: 已完成 {len(_completed_files)}/{len(templates)} 个文件")
            templates = [t for t in templates if str(t) not in set(_completed_files)]
        else:
            click.echo("无已保存的进度，从头开始")
            _completed_files = []

    linter = PromptLinter()
    all_results = []
    total_findings = 0
    total_score = 0.0

    if parallel == 0:
        import os
        parallel = os.cpu_count() or 4
    _use_parallel = parallel > 1 and len(templates) > 1

    _sem_cache = None
    if semantic_cache:
        from ai_prompt_toolkit.semantic_cache import SemanticCache
        _sem_cache = SemanticCache(threshold=0.85, max_size=1000, ttl_seconds=86400.0)

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
        from rich.console import Console
        _has_rich = True
        console = Console()
    except ImportError:
        _has_rich = False

    if _has_rich:
        from ai_prompt_toolkit.cli_helpers import friendly_progress_label
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), MofNCompleteColumn(), TimeElapsedColumn(), TimeRemainingColumn(), console=console) as progress:
            task = progress.add_task("Lint检查中...", total=len(templates))
            for i, tpl_path in enumerate(templates, 1):
                text = tpl_path.read_text(encoding="utf-8")
                template_type = _detect_template_type(text)
                _cache_hit = False
                if _sem_cache:
                    _cached = _sem_cache.lookup(text)
                    if _cached is not None:
                        from ai_prompt_toolkit.linter.linter import LintResult
                        result = LintResult(template_id=tpl_path.name, findings=[], score=_cached.get("score", 0), passed=True, fixes_applied=[])
                        _cache_hit = True
                if not _cache_hit:
                    result = linter.lint(tpl_path.name, text, fix=fix or interactive, template_type=template_type)
                    if _sem_cache:
                        _sem_cache.store(text, {"score": result.score, "findings_count": result.failed_count})
                if interactive and result.fixes_applied:
                    for fix_info in result.fixes_applied:
                        click.echo(f"  修复: {fix_info}")
                        if not click.confirm("  应用此修复?", default=True):
                            pass
                all_results.append(result)
                total_findings += result.failed_count
                total_score += result.score
                _completed_files.append(str(tpl_path))
                if resume:
                    from ai_prompt_toolkit.resume_state import save_progress
                    pending = [f for f in _all_file_names if f not in set(_completed_files)]
                    save_progress("lint", [], _completed_files, pending)
                progress.update(task, description=friendly_progress_label("lint", i, len(templates)))
                progress.advance(task)
    else:
        for tpl_path in templates:
            text = tpl_path.read_text(encoding="utf-8")
            template_type = _detect_template_type(text)
            _cache_hit = False
            if _sem_cache:
                _cached = _sem_cache.lookup(text)
                if _cached is not None:
                    from ai_prompt_toolkit.linter.linter import LintResult
                    result = LintResult(template_id=tpl_path.name, findings=[], score=_cached.get("score", 0), passed=True, fixes_applied=[])
                    _cache_hit = True
            if not _cache_hit:
                result = linter.lint(tpl_path.name, text, fix=fix, template_type=template_type)
                if _sem_cache:
                    _sem_cache.store(text, {"score": result.score, "findings_count": result.failed_count})
            all_results.append(result)
            total_findings += result.failed_count
            total_score += result.score
            _completed_files.append(str(tpl_path))
            if resume:
                from ai_prompt_toolkit.resume_state import save_progress
                pending = [f for f in _all_file_names if f not in set(_completed_files)]
                save_progress("lint", [], _completed_files, pending)

    if _use_parallel and not _has_rich:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _lint_single(tpl_path):
            text = tpl_path.read_text(encoding="utf-8")
            template_type = _detect_template_type(text)
            result = linter.lint(tpl_path.name, text, fix=fix, template_type=template_type)
            if _sem_cache:
                _sem_cache.store(text, {"score": result.score, "findings_count": result.failed_count})
            return result, tpl_path
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(_lint_single, tpl): tpl for tpl in templates}
            for future in as_completed(futures):
                result, tpl_path = future.result()
                all_results.append(result)
                total_findings += result.failed_count
                total_score += result.score
                _completed_files.append(str(tpl_path))
        all_results.sort(key=lambda r: templates[0].name if not _completed_files else r.template_id)

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

    if inline_suppress:
        import re as _re
        _SUPPRESS_RE = _re.compile(r"prompt-lint-disable\s+(.+?)(?:\s*--\s*(.+))?$")
        for result in all_results:
            suppressed = []
            for finding in result.findings:
                if finding.details and isinstance(finding.details, dict):
                    line_num = finding.details.get("line", 0)
                else:
                    line_num = 0
            remaining = []
            text_for_suppress = ""
            for tpl_path in templates:
                if tpl_path.name == result.template_id or result.template_id.startswith(tpl_path.stem):
                    text_for_suppress = tpl_path.read_text(encoding="utf-8")
                    break
            if text_for_suppress:
                suppress_rules = set()
                for line in text_for_suppress.split("\n"):
                    m = _SUPPRESS_RE.search(line)
                    if m:
                        rules_str = m.group(1).strip()
                        for r in rules_str.split(","):
                            suppress_rules.add(r.strip())
                result.findings = [f for f in result.findings if f.rule_id not in suppress_rules]
            total_findings = sum(len(r.findings) for r in all_results)

    if baseline:
        import json as _json
        try:
            with open(baseline, "r", encoding="utf-8") as bf:
                baseline_data = _json.load(bf)
            baseline_ids = set()
            if isinstance(baseline_data, dict):
                for r in baseline_data.get("results", []):
                    for f in r.get("findings", []):
                        baseline_ids.add(f"{r.get('template_id', '')}:{f.get('rule_id', '')}")
            elif isinstance(baseline_data, list):
                for f in baseline_data:
                    baseline_ids.add(f"{f.get('template_id', '')}:{f.get('rule_id', '')}")
            for result in all_results:
                before = len(result.findings)
                result.findings = [f for f in result.findings
                                   if f"{result.template_id}:{f.rule_id}" not in baseline_ids]
                if len(result.findings) < before:
                    click.echo(f"  基线过滤: {result.template_id} 跳过{before - len(result.findings)}条已知问题")
            total_findings = sum(len(r.findings) for r in all_results)
        except (OSError, _json.JSONDecodeError) as e:
            click.echo(f"警告: 无法加载基线文件: {e}")

    if fail_on != "none":
        _SEV_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold = _SEV_ORDER.get(fail_on, 0)
        fail_findings = []
        for result in all_results:
            for f in result.findings:
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                if _SEV_ORDER.get(sev, 0) >= threshold:
                    fail_findings.append((result.template_id, f.rule_id, sev))
        if fail_findings:
            click.echo(f"\n--fail-on={fail_on}: 发现{len(fail_findings)}条 >= {fail_on} 级别问题")
            for tid, rid, sev in fail_findings[:10]:
                click.echo(f"  [{sev.upper()}] {tid}: {rid}")
            if len(fail_findings) > 10:
                click.echo(f"  ... 还有{len(fail_findings) - 10}条")
            sys.exit(2)

    if explain:
        from ai_prompt_toolkit.linter.rules import get_rule, _RULE_MAP
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        from ai_prompt_toolkit.linter.harmonyos_templates import get_template
        for result in all_results:
            if not result.findings:
                continue
            click.echo(f"\n{'='*60}")
            click.echo(f"文件: {result.template_id} ({len(result.findings)}个问题)")
            click.echo(f"{'='*60}")
            for i, f in enumerate(result.findings, 1):
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                click.echo(f"\n  [{i}] {f.rule_id} [{sev.upper()}]")
                rule = _RULE_MAP.get(f.rule_id)
                if rule:
                    click.echo(f"  名称: {rule.name}")
                    click.echo(f"  类别: {rule.category} | 家族: {rule.family or 'N/A'}")
                    if rule.description_en:
                        click.echo(f"  描述: {rule.description}")
                        click.echo(f"  Desc:  {rule.description_en}")
                    else:
                        click.echo(f"  描述: {rule.description}")
                else:
                    click.echo(f"  描述: {f.description}")
                click.echo(f"  修复: {f.remediation or (rule.remediation if rule else 'N/A')}")
                if rule and rule.remediation_en:
                    click.echo(f"  Fix:   {rule.remediation_en}")
                if f.rule_id in AUTO_FIXABLE_RULES:
                    click.echo(f"  可自动修复: 是 (使用 --fix)")
                template = get_template(f.rule_id)
                if template:
                    click.echo(f"  鸿蒙模板: 可用 (使用 harmonyos_template_generate 获取)")
                if rule and rule.owasp_refs:
                    click.echo(f"  OWASP: {', '.join(rule.owasp_refs)}")
                click.echo(f"  {'─'*50}")
        click.echo()

    if fmt == "table":
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
            for result in all_results:
                table = Table(title=f"Lint: {result.template_id}", show_lines=False)
                table.add_column("Rule", style="cyan", width=6)
                table.add_column("Severity", width=10)
                table.add_column("Description", style="white")
                for f in result.findings:
                    sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                    sev_style = "bold red" if sev in ("critical", "high") else "yellow" if sev == "medium" else "dim"
                    table.add_row(f.rule_id, f"[{sev_style}]{sev.upper()}[/{sev_style}]", f.description[:80])
                if result.findings:
                    console.print(table)
                else:
                    console.print(f"[green]✓ {result.template_id}: No issues[/green]")
        except ImportError:
            click.echo("Table format requires 'rich' package. Install with: pip install rich")
            fmt = "cli"

    if quiet:
        for result in all_results:
            status = "PASS" if result.passed else "FAIL"
            click.echo(f"{result.template_id}: {status} ({result.score:.0f})")
        if total_findings > 0:
            click.echo(f"TOTAL: FAIL | {total_findings} findings | avg={avg_score:.0f}")
        else:
            click.echo(f"TOTAL: PASS | avg={avg_score:.0f}")
    elif fmt == "cli":
        if _has_rich:
            from ai_prompt_toolkit.cli_helpers import print_rich_findings
            print_rich_findings(all_results, console=console)
        else:
            for result in all_results:
                if result.findings:
                    for f in result.findings:
                        sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                        from ai_prompt_toolkit.cli_helpers import friendly_finding_line, friendly_fix_suggestion
                        is_mm = f.rule_id.startswith("MM-")
                        click.echo(friendly_finding_line(result.template_id, f.rule_id, sev, f.description, is_mm))
                        if sev in ("high", "critical"):
                            click.echo(f"    {friendly_fix_suggestion(f.rule_id, f.description)}")

    avg_score = total_score / max(len(all_results), 1)
    from ai_prompt_toolkit.cli_helpers import friendly_lint_summary
    fixed_count = sum(len(r.fixed_findings) for r in all_results if r.auto_fixed) if fix else 0
    if _has_rich and fmt == "cli":
        from ai_prompt_toolkit.cli_helpers import print_rich_lint_summary
        print_rich_lint_summary(len(templates), avg_score, total_findings, fixed_count, console=console)
    else:
        click.echo(friendly_lint_summary(len(templates), avg_score, total_findings, fixed_count))

    if total_findings > 0 and fmt == "cli":
        from collections import Counter
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        category_counts = Counter()
        severity_counts = Counter()
        for result in all_results:
            for f in result.findings:
                rule = _RULE_MAP.get(f.rule_id)
                cat = rule.category if rule else "unknown"
                category_counts[cat] += 1
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                severity_counts[sev] += 1
        cat_summary = " | ".join(f"{k}: {v}" for k, v in sorted(category_counts.items(), key=lambda x: -x[1]))
        sev_summary = " | ".join(f"{k.upper()}: {v}" for k, v in sorted(severity_counts.items(), key=lambda x: -x[1]))
        click.echo(f"  类别统计: {cat_summary}")
        click.echo(f"  严重度:   {sev_summary}")

    if avg_score >= 100.0 and total_findings == 0:
        from ai_prompt_toolkit.easter_eggs import show_perfect_score_celebration
        celebration = show_perfect_score_celebration(avg_score)
        if celebration:
            click.echo(celebration)

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

    if _sem_cache:
        _cache_stats = _sem_cache.stats()
        click.echo(f"语义缓存: 命中{_cache_stats['hits']}次 / 未命中{_cache_stats['misses']}次 / 命中率{_cache_stats['hit_rate']:.1%}")

    if watch:
        from ai_prompt_toolkit.config import ConfigWatcher
        import time
        watcher = ConfigWatcher(poll_interval=2.0, debounce_seconds=1.0)
        target_path = Path(target)
        if target_path.is_dir():
            for p in target_path.rglob("*"):
                if p.suffix in (".txt", ".md", ".prompt", ".yaml", ".yml", ".toml"):
                    watcher.add_watch(p)
        elif target_path.is_file():
            watcher.add_watch(target_path)
        click.echo(f"👀 监视中... (Ctrl+C退出)")
        try:
            while True:
                time.sleep(2.0)
                if watcher.check_and_reload():
                    click.echo("\n📝 文件变化，重新lint...")
                    templates = discover_templates(target)
                    if templates:
                        linter = PromptLinter()
                        new_results = []
                        for tpl_path in templates:
                            text = tpl_path.read_text(encoding="utf-8")
                            result = linter.lint(tpl_path.name, text, fix=fix)
                            new_results.append(result)
                        new_findings = sum(r.failed_count for r in new_results)
                        new_score = sum(r.score for r in new_results) / len(new_results) if new_results else 0
                        click.echo(f"  文件: {len(templates)} | 发现: {new_findings} | 评分: {new_score:.1f}")
        except KeyboardInterrupt:
            click.echo("\n停止监视")
            return

    sys.exit(determine_exit_code(has_findings=total_findings > 0, error_severity="high" if has_errors else None))


@main.command()
@click.option("--source-locale", "-s", default="zh-CN", help="源语言(BCP 47)")
@click.option("--target-locale", "-t", default="en-US", help="目标语言(BCP 47)")
@click.option("--output", "-o", help="输出目录")
@click.option("--base-dir", help="i18n资源基础目录")
@click.option("--llm", is_flag=True, help="启用LLM辅助翻译(需配置Provider)")
@click.option("--provider", help="LLM Provider(provider:model_name)")
def i18n(source_locale: str, target_locale: str, output: str | None,
         base_dir: str | None, llm: bool, provider: str | None) -> None:
    """国际化：多语言翻译和质量报告"""
    from ai_prompt_toolkit.i18n.manager import I18nManager

    if llm:
        from ai_prompt_toolkit.i18n.llm_translator import LLMTranslator
        from ai_prompt_toolkit.i18n.glossary import Glossary
        from ai_prompt_toolkit.i18n.translation import TranslationEngine

        prov = None
        if provider:
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
            from ai_prompt_toolkit.ab_test.provider import create_provider
            parts = provider.split(":")
            if len(parts) == 2:
                try:
                    pt = ProviderType(parts[0])
                except ValueError:
                    pt = ProviderType.OPENAI
                model_name = parts[1]
            else:
                pt = ProviderType.OPENAI
                model_name = provider
            config = ModelConfig(provider=pt, model_name=model_name)
            prov = create_provider(config)

        translator = LLMTranslator(
            glossary=Glossary.default(),
            engine=TranslationEngine(),
            provider=prov,
        )
        click.echo(f"LLM辅助翻译: {source_locale} → {target_locale}")
        if not prov:
            click.echo("警告: 未指定Provider，仅使用术语表+缓存翻译")
        result = translator.translate_template(
            "你是一个专业的AI助手。", source_locale, target_locale
        )
        click.echo(f"翻译结果: {result['translated']}")
        click.echo(f"术语命中: {result['glossary_hit']} | 一致性: {result['consistency_ok']}")
        return

    mgr = I18nManager(base_dir=base_dir)
    click.echo(f"翻译: {source_locale} → {target_locale}")
    report = mgr.generate(source_locale, target_locale, output)
    click.echo(f"覆盖率: {report.coverage_pct:.1f}%")
    click.echo(f"质量: {report.quality_pct:.1f}%")
    click.echo(f"已翻译: {report.translated}/{report.total_keys}")
    if report.missing > 0:
        click.echo(f"缺失: {report.missing}")


@main.command()
@click.option("--action", "-a", type=click.Choice(["submit", "review", "deploy", "status"]),
              required=True, help="市场操作")
@click.option("--template", "-t", help="模板ID或文件路径")
@click.option("--config", help="市场配置YAML文件路径")
def market(action: str, template: str | None, config: str | None) -> None:
    """模板市场：提交、评审、灰度发布"""
    from ai_prompt_toolkit.cli_helpers import empty_state_tip
    from ai_prompt_toolkit.market.service import MarketService
    svc = MarketService()

    if action == "status" and template:
        status = svc.get_status(template)
        click.echo(json.dumps(status, ensure_ascii=False, indent=2))
    elif action == "submit" and template:
        from ai_prompt_toolkit.market.types import Template
        tpl = Template(id=template, name=template, version="1.0")
        try:
            svc.submit(tpl)
            click.echo(f"模板提交成功: {template}")
        except ValueError as e:
            click.echo(f"错误: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(empty_state_tip("market"))


@main.command(name="upgrade-fm")
@click.option("--target", "-t", required=True, help="目标目录或文件")
@click.option("--dry-run", is_flag=True, help="仅预览变更不写入")
@click.option("--locale", "-l", default="zh-CN", help="默认语言标签(BCP 47)")
def upgrade_fm(target: str, dry_run: bool, locale: str) -> None:
    """Front Matter升级：v2→v3(新增i18n_status/market_status/lint_score)"""
    from ai_prompt_toolkit.cli_helpers import discover_templates
    from ai_prompt_toolkit.frontmatter import upgrade_markdown_file

    templates = discover_templates(target)
    if not templates:
        click.echo("未发现.md模板文件")
        sys.exit(0)

    upgraded = 0
    errors_total = 0

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        new_text, errors = upgrade_markdown_file(text)

        if errors and errors[0].startswith("No front matter"):
            continue

        errors_total += len(errors)
        for e in errors:
            click.echo(f"  ⚠ [{tpl_path.name}] {e}")

        if dry_run:
            click.echo(f"  预览: {tpl_path.name} (i18n/market/lint_score字段已添加)")
        else:
            tpl_path.write_text(new_text, encoding="utf-8")
            click.echo(f"  升级: {tpl_path.name}")
        upgraded += 1

    click.echo(f"\nFront Matter升级完成 | 文件: {upgraded} | 验证问题: {errors_total}")
    if dry_run:
        click.echo("(dry-run模式，未写入文件)")


@main.command(name="init")
@click.option("--target", "-t", default=".", help="项目目录(默认当前目录)")
@click.option("--non-interactive", is_flag=True, help="非交互模式")
@click.option("--ci", is_flag=True, help="生成CI/CD配置(GitHub Action+Docker+pre-commit)")
@click.option("--template", type=click.Choice(["general", "harmonyos", "security", "rag", "code-review"]), default=None, help="项目模板")
def init_project(target: str, non_interactive: bool, ci: bool, template: str | None) -> None:
    """新用户引导：3步创建AI提示词项目"""
    if ci:
        _generate_ci_config(target)
        return

    if template:
        _apply_template(target, template)

    from ai_prompt_toolkit.onboarding import run_onboarding

    result = run_onboarding(target, non_interactive=non_interactive)
    steps = result["steps_completed"]
    errors = result.get("errors", [])

    if steps == 3:
        click.echo(f"\n引导完成! 创建了 {result['files_created']} 个文件，3步全部成功")
    else:
        click.echo(f"\n引导完成 {steps}/3 步")
        for e in errors:
            click.echo(f"  错误: {e}", err=True)

    sys.exit(0 if steps == 3 else 1)


_TEMPLATE_FILES: dict[str, dict[str, str]] = {
    "general": {
        "prompts/general-assistant.prompt.md": "---\ntemplate_type: prompt\nname: 通用助手\nmodel_compatibility: [gpt-4o, claude-3.5, qwen]\n---\n你是一个有帮助的AI助手。请根据用户的问题提供准确、有用的回答。",
    },
    "harmonyos": {
        "prompts/harmonyos-dev.prompt.md": "---\ntemplate_type: prompt\nname: 鸿蒙开发助手\nmodel_compatibility: [qwen, pangu]\nindustry: 华为云\n---\n你是一个专业的HarmonyOS NEXT ArkTS开发专家。请按照以下步骤执行：\n1. 分析开发需求\n2. 提供ArkTS代码\n3. 确保符合HarmonyOS NEXT 5.0+规范",
    },
    "security": {
        "prompts/security-auditor.prompt.md": "---\ntemplate_type: prompt\nname: 安全审计助手\n---\n你是一个AI安全审计专家。请检查Prompt中的安全风险：\n1. 注入攻击检测\n2. PII隐私信息泄露\n3. 供应链安全",
    },
    "rag": {
        "prompts/rag-assistant.prompt.md": "---\ntemplate_type: prompt\nname: RAG检索增强助手\n---\n你是一个基于检索增强生成的AI助手。请根据提供的上下文回答问题：\n\n上下文：{{context}}\n\n问题：{{question}}",
    },
    "code-review": {
        "prompts/code-reviewer.prompt.md": "---\ntemplate_type: prompt\nname: 代码审查助手\n---\n你是一个专业的代码审查专家。请审查以下代码，关注：\n1. 安全漏洞\n2. 性能问题\n3. 代码规范\n4. 可维护性",
    },
}


def _apply_template(target: str, template_name: str) -> None:
    templates = _TEMPLATE_FILES.get(template_name, {})
    if not templates:
        click.echo(f"未知模板: {template_name}", err=True)
        return
    project_dir = Path(target).resolve()
    created = 0
    for rel_path, content in templates.items():
        file_path = project_dir / rel_path
        if file_path.exists():
            click.echo(f"  跳过(已存在): {rel_path}")
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        click.echo(f"  创建: {rel_path}")
        created += 1
    click.echo(f"模板 '{template_name}' 应用完成 | 创建 {created} 个文件")


def _generate_ci_config(target: str) -> None:
    from pathlib import Path as _Path
    project_dir = _Path(target).resolve()

    github_dir = project_dir / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)

    lint_action = """name: Prompt Lint & Scan

on:
  push:
    paths: ['**/*.md', '_scenarios/**']
  pull_request:
    paths: ['**/*.md', '_scenarios/**']

jobs:
  prompt-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: prompt-cli lint -t ./_scenarios
      - run: prompt-cli scan -t ./_scenarios
      - run: prompt-cli evaluate -t ./_scenarios --quick
"""
    (github_dir / "prompt-lint.yml").write_text(lint_action, encoding="utf-8")
    click.echo(f"  ✓ GitHub Action: {github_dir / 'prompt-lint.yml'}")

    pre_commit = """repos:
  - repo: local
    hooks:
      - id: prompt-lint
        name: Prompt Lint
        entry: prompt-cli lint -t
        language: system
        files: '\\.md$'
      - id: prompt-scan
        name: Prompt Security Scan
        entry: prompt-cli scan -t
        language: system
        files: '\\.md$'
"""
    (project_dir / ".pre-commit-config.yaml").write_text(pre_commit, encoding="utf-8")
    click.echo(f"  ✓ pre-commit hook: {project_dir / '.pre-commit-config.yaml'}")

    dockerfile = """FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[full]"
ENTRYPOINT ["prompt-cli"]
"""
    (project_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    click.echo(f"  ✓ Dockerfile: {project_dir / 'Dockerfile'}")

    click.echo("\nCI/CD配置生成完成! 下一步:")
    click.echo("  1. git add .github/ .pre-commit-config.yaml Dockerfile")
    click.echo("  2. pre-commit install")
    click.echo("  3. docker build -t ai-prompt-toolkit .")


@main.command(name="assert")
@click.option("--response", "-r", required=True, help="待验证的响应文本文件路径")
@click.option("--config", "-c", required=True, help="断言配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def assert_cmd(response: str, config: str, fmt: str) -> None:
    """断言验证：对LLM响应执行质量断言检查"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_config, write_report
    from ai_prompt_toolkit.assertion.types import AssertType, AssertionConfig
    from ai_prompt_toolkit.assertion.engine import AssertionEngine

    resp_path = resolve_path(response)
    resp_text = resp_path.read_text(encoding="utf-8")
    cfg = load_config(config)

    assertions_cfg = cfg.get("assertions", [])
    configs = []
    for item in assertions_cfg:
        atype = AssertType(item.get("type", "contains"))
        configs.append(AssertionConfig(
            assert_type=atype,
            value=item.get("value", ""),
            threshold=item.get("threshold", 0.8),
            weight=item.get("weight", 1.0),
        ))

    if not configs:
        click.echo("错误: 未配置任何断言", err=True)
        sys.exit(2)

    engine = AssertionEngine()
    results = engine.evaluate_batch(configs, response=resp_text)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if fmt == "json":
        import json as _json
        data = {"passed": passed, "total": total, "results": [r.to_dict() for r in results]}
        click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for r in results:
            icon = "✓" if r.passed else "✗"
            click.echo(f"  {icon} [{r.assert_type.value}] {r.reason} (分数: {r.score:.2f})")
        click.echo(f"\n断言结果: {passed}/{total} 通过")

    sys.exit(0 if passed == total else 1)


@main.command()
@click.option("--host", default="127.0.0.1", help="绑定主机(默认127.0.0.1)")
@click.option("--port", "-p", default=8000, type=int, help="端口(默认8000)")
@click.option("--reload", "do_reload", is_flag=True, help="开发模式(自动重载)")
def serve(host: str, port: int, do_reload: bool) -> None:
    """启动Playground Web UI"""
    try:
        import uvicorn
    except ImportError:
        click.echo("错误: uvicorn未安装，请运行: pip install uvicorn", err=True)
        sys.exit(2)

    click.echo(f"启动 Playground: http://{host}:{port}")
    uvicorn.run("ai_prompt_toolkit.playground.server:app", host=host, port=port, reload=do_reload)


@main.command(name="redteam")
@click.option("--target", "-t", help="目标文本文件路径(离线模式)")
@click.option("--probes", "-p", help="探测类型(逗号分隔，默认全部)")
@click.option("--provider", help="Provider配置(provider:model_name，在线模式)")
@click.option("--output", "-o", help="输出报告路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli", "html"]), default="cli", help="输出格式")
@click.option("--owasp", help="按OWASP LLM Top 10分类过滤(如LLM01,LLM06)")
@click.option("--top-n", type=int, default=0, help="仅运行前N个Probe")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="最低严重性过滤")
@click.option("--compliance", type=click.Choice(["eu_ai_act", "china_algorithm", "owasp_llm_top10"]), help="合规报告框架")
@click.option("--scorecard", is_flag=True, help="红队探测后自动运行安全评分卡")
def redteam_cmd(target: str | None, probes: str | None, provider: str | None,
                output: str | None, fmt: str, owasp: str | None,
                top_n: int, severity: str | None, compliance: str | None,
                scorecard: bool) -> None:
    """红队探测：对抗性安全测试"""
    from ai_prompt_toolkit.cli_helpers import empty_state_tip
    from ai_prompt_toolkit.redteam.probe import create_probe, get_available_probes, get_probes_by_owasp
    from ai_prompt_toolkit.redteam.detector import create_detector, get_available_detectors, LeakageDetector, ComplianceDetector, RefusalDetector
    from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator

    available = get_available_probes()

    if owasp:
        owasp_refs = [ref.strip() for ref in owasp.split(",")]
        owasp_probes: list[str] = []
        for ref in owasp_refs:
            owasp_probes.extend(get_probes_by_owasp(ref))
        available = [p for p in available if p in owasp_probes]

    selected_probes = probes.split(",") if probes else available

    if top_n > 0:
        selected_probes = selected_probes[:top_n]

    _SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    probe_instances = []
    for name in selected_probes:
        try:
            probe = create_probe(name.strip())
            if severity:
                min_level = _SEVERITY_ORDER.get(severity, 3)
                probe_inputs = probe.generate_inputs()
                has_qualifying = any(
                    _SEVERITY_ORDER.get(pi.severity, 3) <= min_level
                    for pi in probe_inputs
                )
                if has_qualifying:
                    probe_instances.append(probe)
            else:
                probe_instances.append(probe)
        except ValueError as e:
            click.echo(f"警告: {e}", err=True)

    if not probe_instances:
        click.echo(empty_state_tip("redteam"))
        sys.exit(2)

    detectors = [LeakageDetector(), ComplianceDetector(), RefusalDetector()]
    orchestrator = ExplorationOrchestrator(probes=probe_instances, detectors=detectors)

    if provider:
        from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
        from ai_prompt_toolkit.ab_test.provider import create_provider
        parts = provider.split(":")
        if len(parts) == 2:
            try:
                pt = ProviderType(parts[0])
            except ValueError:
                pt = ProviderType.OPENAI
            model_name = parts[1]
        else:
            pt = ProviderType.OPENAI
            model_name = provider
        config = ModelConfig(provider=pt, model_name=model_name)
        prov = create_provider(config)
        report = orchestrator.run_with_provider(prov)
    elif target:
        from ai_prompt_toolkit.cli_helpers import resolve_path
        path = resolve_path(target)
        text = path.read_text(encoding="utf-8")
        report = orchestrator.run_offline(text)
    else:
        click.echo("错误: 请指定--target(离线)或--provider(在线)", err=True)
        sys.exit(2)

    if compliance:
        import json as _json
        compliance_data = report.generate_compliance_report(framework=compliance)
        if output:
            from ai_prompt_toolkit.cli_helpers import write_report
            write_report(compliance_data, output, fmt="json")
            click.echo(f"合规报告已保存: {output}")
        else:
            click.echo(_json.dumps(compliance_data, ensure_ascii=False, indent=2))
    elif fmt == "json":
        import json as _json
        if output:
            from ai_prompt_toolkit.cli_helpers import write_report
            write_report(report.to_dict(), output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif fmt == "html":
        framework = compliance or "owasp_llm_top10"
        html_content = report.generate_html_report(framework=framework)
        if output:
            out_path = output if output.endswith(".html") else output + ".html"
            Path(out_path).write_text(html_content, encoding="utf-8")
            click.echo(f"HTML报告已保存: {out_path}")
        else:
            click.echo(html_content)
    else:
        click.echo(report.get_summary())


@main.command(name="judge")
@click.option("--question", "-q", required=True, help="评估问题/输入")
@click.option("--response", "-r", required=True, help="待评估的回答(文本或文件路径)")
@click.option("--response-b", help="第二回答(成对比较模式)")
@click.option("--reference", help="参考答案(可选)")
@click.option("--judge-model", "-j", default="gpt-4o-mini", help="裁判模型(provider:model_name)")
@click.option("--dimensions", "-d", help="评估维度(逗号分隔: relevance,accuracy,fluency,completeness,safety,helpfulness)")
@click.option("--mode", type=click.Choice(["absolute", "pairwise"]), default="absolute", help="评估模式")
@click.option("--aggregation", type=click.Choice(["majority_vote", "weighted_average", "swap_debias"]),
              default="majority_vote", help="多裁判集成方式")
@click.option("--multi-judge", is_flag=True, help="启用多裁判模式(3个裁判)")
@click.option("--output", "-o", help="输出报告路径")
def judge_cmd(question: str, response: str, response_b: str | None, reference: str | None,
              judge_model: str, dimensions: str | None, mode: str, aggregation: str,
              multi_judge: bool, output: str | None) -> None:
    """LLM-as-Judge评估：用LLM作为裁判评估Prompt回答质量"""
    import asyncio
    from ai_prompt_toolkit.ab_test.judge import (
        create_judge, create_multi_judge, BUILTIN_DIMENSIONS,
    )

    resp_text = response
    resp_path = Path(response)
    if resp_path.exists() and resp_path.is_file():
        resp_text = resp_path.read_text(encoding="utf-8")

    resp_b_text: str | None = None
    if response_b:
        rb_path = Path(response_b)
        resp_b_text = rb_path.read_text(encoding="utf-8") if rb_path.exists() else response_b

    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None

    if multi_judge:
        parts = judge_model.split(":")
        provider = parts[0] if len(parts) == 2 else "openai"
        model = parts[1] if len(parts) == 2 else judge_model
        judge_configs = [
            {"provider": provider, "model": model},
            {"provider": provider, "model": model},
            {"provider": provider, "model": model},
        ]
        ensemble = create_multi_judge(judge_configs, dim_list, mode, aggregation)

        if mode == "pairwise" and resp_b_text:
            result = asyncio.run(ensemble.evaluate_pairwise(question, resp_text, resp_b_text))
        else:
            result = asyncio.run(ensemble.evaluate_absolute(question, resp_text, reference or ""))

        if output:
            from ai_prompt_toolkit.cli_helpers import write_report
            write_report(result.to_dict(), output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            import json as _json
            click.echo(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        judge = create_judge(judge_model, dimensions=dim_list, mode=mode)

        if mode == "pairwise" and resp_b_text:
            result = asyncio.run(judge.evaluate_pairwise(question, resp_text, resp_b_text))
            click.echo(f"Winner: {result.winner}")
            if result.reasoning:
                click.echo(f"理由: {result.reasoning[:200]}")
        else:
            results = asyncio.run(judge.evaluate_absolute(question, resp_text, reference or ""))
            for r in results:
                marker = "✓" if r.score >= 4 else "⚠" if r.score >= 3 else "✗"
                click.echo(f"  {marker} {r.dimension.name}: {r.score}/5")
                if r.reasoning:
                    click.echo(f"     {r.reasoning[:100]}")

            if results:
                overall = sum(r.score * r.dimension.weight for r in results) / max(
                    sum(r.dimension.weight for r in results), 1
                )
                click.echo(f"\n综合评分: {overall:.2f}/5")

            if output:
                from ai_prompt_toolkit.cli_helpers import write_report
                report_data = {
                    "mode": mode,
                    "question": question[:200],
                    "results": [r.to_dict() for r in results],
                    "overall_score": round(overall, 2) if results else 0,
                }
                write_report(report_data, output, fmt="json")
                click.echo(f"报告已保存: {output}")


@main.command(name="version")
@click.option("--action", "-a", type=click.Choice(["create", "list", "diff", "rollback", "show"]),
              required=True, help="版本操作")
@click.option("--template", "-t", help="模板ID")
@click.option("--source", "-s", help="源文件路径(create时读取)")
@click.option("--version", "ver", type=int, help="版本号(show/diff/rollback)")
@click.option("--version-a", type=int, help="对比版本A(diff)")
@click.option("--version-b", type=int, help="对比版本B(diff)")
@click.option("--author", help="作者")
@click.option("--message", "-m", help="变更说明")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--semantic", is_flag=True, help="使用语义差异分析(按段比较+安全策略变更检测)")
def version_cmd(action: str, template: str | None, source: str | None, ver: int | None,
                version_a: int | None, version_b: int | None, author: str | None,
                message: str | None, fmt: str, semantic: bool) -> None:
    """Prompt版本管理：版本创建/列表/diff/回滚"""
    from ai_prompt_toolkit.cli_helpers import empty_state_tip
    from ai_prompt_toolkit.version_store import VersionStore

    store = VersionStore()

    try:
        if action == "create":
            if not template:
                click.echo("错误: 请指定--template", err=True)
                sys.exit(2)
            content = ""
            if source:
                from ai_prompt_toolkit.cli_helpers import resolve_path
                content = resolve_path(source).read_text(encoding="utf-8")
            elif not click.get_text_stream("stdin").isatty():
                content = click.get_text_stream("stdin").read()
            else:
                click.echo("错误: 请指定--source或通过管道传入内容", err=True)
                sys.exit(2)

            v = store.create_version(template, content, author=author or "", message=message or "")
            click.echo(f"版本已创建: {template} v{v.version_number} ({v.content_hash})")

        elif action == "list":
            if not template:
                click.echo("错误: 请指定--template", err=True)
                sys.exit(2)
            versions = store.list_versions(template)
            if not versions:
                click.echo(empty_state_tip("version"))
                sys.exit(0)
            if fmt == "json":
                import json as _json
                click.echo(_json.dumps([v.to_dict() for v in versions], ensure_ascii=False, indent=2))
            else:
                for v in versions:
                    click.echo(f"  v{v.version_number} | {v.created_at} | {v.author or '-'} | {v.message or '-'} | {v.content_hash}")

        elif action == "show":
            if not template or not ver:
                click.echo("错误: 请指定--template和--version", err=True)
                sys.exit(2)
            v = store.get_version(template, ver)
            if not v:
                click.echo(f"版本不存在: {template} v{ver}", err=True)
                sys.exit(2)
            click.echo(v.content)

        elif action == "diff":
            if not template or not version_a or not version_b:
                click.echo("错误: 请指定--template --version-a --version-b", err=True)
                sys.exit(2)
            if semantic:
                from ai_prompt_toolkit.prompt_diff import semantic_diff
                import json as _json
                va = store.get_version(template, version_a)
                vb = store.get_version(template, version_b)
                if not va or not vb:
                    click.echo("错误: 版本不存在", err=True)
                    sys.exit(2)
                sem_result = semantic_diff(va.content, vb.content)
                click.echo(_json.dumps(sem_result.to_dict(), ensure_ascii=False, indent=2))
            else:
                result = store.diff(template, version_a, version_b)
                if fmt == "json":
                    import json as _json
                    click.echo(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
                else:
                    from ai_prompt_toolkit.output import console
                    console.print(f"[bold]Diff: {template} v{version_a} → v{version_b}[/bold]")
                    console.print(f"  [green]+{result.added_lines}[/green] [red]-{result.removed_lines}[/red] | {result.change_summary}")
                    for line in result.unified_diff:
                        if line.startswith("+") and not line.startswith("+++"):
                            console.print(f"  [green]{line}[/green]")
                        elif line.startswith("-") and not line.startswith("---"):
                            console.print(f"  [red]{line}[/red]")
                        elif line.startswith("@@"):
                            console.print(f"  [cyan]{line}[/cyan]")
                        else:
                            console.print(f"  {line}")

        elif action == "rollback":
            if not template or not ver:
                click.echo("错误: 请指定--template和--version", err=True)
                sys.exit(2)
            v = store.rollback(template, ver, author=author or "")
            click.echo(f"已回滚: {template} v{v.version_number} (回滚到v{ver})")

    finally:
        store.close()


@main.command(name="eval-history")
@click.option("--template", "-t", help="模板ID(过滤)")
@click.option("--limit", "-n", type=int, default=10, help="显示条数(默认10)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def eval_history_cmd(template: str | None, limit: int, fmt: str) -> None:
    """评估历史：查看评估结果趋势和回归告警"""
    from ai_prompt_toolkit.eval_store import EvalStore

    store = EvalStore()

    if template:
        snapshots = store.get_snapshots(template, limit=limit)
        trend = store.get_trend(template, limit=limit)
        alerts = store.get_alerts(template_id=template, limit=10)
    else:
        snapshots = []
        trend = []
        alerts = store.get_alerts(limit=10)

    if fmt == "json":
        import json as _json
        click.echo(_json.dumps({
            "snapshots": [s.to_dict() for s in snapshots],
            "trend": [t.to_dict() for t in trend],
            "alerts": [a.to_dict() for a in alerts],
        }, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        if snapshots:
            table = Table(title=f"评估历史 (模板: {template})", show_lines=True)
            table.add_column("#", style="dim", width=5)
            table.add_column("时间", width=20)
            table.add_column("总分", width=8)
            table.add_column("百分位", width=8)
            table.add_column("维度数", width=6)
            for s in snapshots:
                table.add_row(
                    str(s.snapshot_id), s.created_at,
                    f"{s.overall_score:.2f}", f"{s.percentage:.1f}%",
                    str(s.dimension_count),
                )
            console.print(table)

        if trend and len(trend) > 1:
            console.print("\n[bold]趋势线[/bold]")
            for tp in trend:
                bar_len = int(tp.percentage / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                console.print(f"  #{tp.snapshot_id} {tp.created_at} {bar} {tp.percentage:.1f}%")

        if alerts:
            console.print(f"\n[bold red]回归告警 ({len(alerts)}条)[/bold red]")
            for a in alerts:
                icon = "🔴" if a.severity == "critical" else "🟡"
                console.print(f"  {icon} {a.dimension_name}: {a.previous_score:.1f}→{a.current_score:.1f} ({a.change_percent:.0f}%)")

    store.close()


@main.command(name="eval-compare")
@click.argument("snapshot_a", type=int)
@click.argument("snapshot_b", type=int)
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def eval_compare_cmd(snapshot_a: int, snapshot_b: int, fmt: str) -> None:
    """评估对比：对比两次评估结果的维度差异"""
    from ai_prompt_toolkit.eval_store import EvalStore

    store = EvalStore()
    result = store.compare(snapshot_a, snapshot_b)
    store.close()

    if "error" in result:
        click.echo(f"错误: {result['error']}", err=True)
        sys.exit(2)

    if fmt == "json":
        import json as _json
        click.echo(_json.dumps(result, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"评估对比: #{snapshot_a} vs #{snapshot_b}", show_lines=True)
        table.add_column("维度", style="bold", width=10)
        table.add_column(f"#{snapshot_a}", width=8)
        table.add_column(f"#{snapshot_b}", width=8)
        table.add_column("差异", width=8)
        table.add_column("趋势", width=10)

        for d in result["dimension_diffs"]:
            diff = d["diff"]
            if diff > 0:
                trend_icon = "[green]↑ +{:.1f}[/green]".format(diff)
            elif diff < 0:
                trend_icon = "[red]↓ {:.1f}[/red]".format(diff)
            else:
                trend_icon = "[dim]= 0[/dim]"
            table.add_row(d["dimension_id"], str(d["score_a"]), str(d["score_b"]),
                         f"{diff:+.1f}", trend_icon)

        console.print(table)
        overall = result["overall_diff"]
        icon = "↑" if overall > 0 else "↓" if overall < 0 else "="
        console.print(f"\n总分变化: {icon} {overall:+.4f}")


@main.command(name="canary")
@click.option("--prompt", "-p", help="注入Canary Token的Prompt文件路径")
@click.option("--check", "-c", help="检测泄露的LLM输出文件路径")
@click.option("--count", type=int, default=3, help="生成Canary Token数量(默认3)")
@click.option("--output", "-o", help="输出路径")
def canary_cmd(prompt: str | None, check: str | None, count: int, output: str | None) -> None:
    """Canary Token泄露防护：注入追踪标记/检测系统Prompt泄露"""
    from ai_prompt_toolkit.security.unicode_guard import (
        generate_canary_tokens, inject_canary_tokens,
        check_canary_leakage, clean_unicode, check_unicode_threats,
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

        click.echo(f"\n检测方法: 将LLM输出通过 'prompt-cli canary -c <output_file>' 检查泄露")
    else:
        click.echo("错误: 请指定 --prompt(注入) 或 --check(检测)", err=True)
        sys.exit(2)


@main.command(name="token")
@click.option("--target", "-t", required=True, help="Prompt文件路径")
@click.option("--model", "-m", default="gpt-4o", help="目标模型(gpt-4o/claude-3/deepseek/qwen等)")
@click.option("--output", "-o", help="输出报告路径")
def token_cmd(target: str, model: str, output: str | None) -> None:
    """Token压缩分析：估算Token消耗+检测冗余+优化建议"""
    from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens, estimate_tokens

    target_path = Path(target)
    if not target_path.exists():
        click.echo(f"错误: 文件不存在 — {target}", err=True)
        sys.exit(2)

    text = target_path.read_text(encoding="utf-8")
    result = analyze_prompt_tokens(text, model)

    click.echo(f"Token分析 | 文件: {target_path.name} | 模型: {model}")
    click.echo(f"  字符数: {result.estimate.char_count}")
    click.echo(f"  估算Tokens: {result.original_tokens}")
    click.echo(f"  输入成本: ${result.estimate.estimated_input_cost_usd:.6f}/次")
    click.echo(f"  输出成本: ${result.estimate.estimated_output_cost_usd:.6f}/次")

    if result.suggestions:
        click.echo(f"\n优化建议({len(result.suggestions)}条):")
        for s in result.suggestions:
            priority_marker = "🔴" if s.priority == "high" else "🟡" if s.priority == "medium" else "🟢"
            click.echo(f"  {priority_marker} [{s.suggestion_id}] {s.description}")
            click.echo(f"     预计节省: {s.estimated_savings_tokens} tokens ({s.estimated_savings_percent:.1f}%)")

    if result.findings:
        click.echo(f"\n警告:")
        for f in result.findings:
            click.echo(f"  ⚠ [{f.rule_id}] {f.description}")

    click.echo(f"\n优化后: {result.optimized_tokens} tokens | 节省: {result.savings_tokens} ({result.savings_percent:.1f}%)")

    if output:
        from ai_prompt_toolkit.cli_helpers import write_report
        write_report(result.to_dict(), output, fmt="json")
        click.echo(f"报告: {output}")


@main.command(name="watch")
@click.option("--target", "-t", required=True, help="监视目标(文件或目录)")
@click.option("--command", "-c", type=click.Choice(["lint", "scan", "evaluate", "compliance"]),
              default="lint", help="文件变更时执行的命令")
@click.option("--interval", type=float, default=1.0, help="轮询间隔(秒)")
@click.option("--debounce", type=float, default=0.5, help="变更防抖延迟(秒)")
@click.option("--gate", is_flag=True, help="lint模式启用Quality Gate")
def watch_cmd(target: str, command: str, interval: float, debounce: float, gate: bool) -> None:
    """文件监视：检测变更时自动执行Lint/Scan/Evaluate"""
    import hashlib

    target_path = Path(target).resolve()
    if not target_path.exists():
        click.echo(f"错误: 目标不存在 — {target_path}", err=True)
        sys.exit(2)

    files_to_watch: list[Path] = []
    if target_path.is_file():
        files_to_watch = [target_path]
    else:
        files_to_watch = sorted(target_path.rglob("*.md"))

    if not files_to_watch:
        click.echo("未发现.md文件，正在监视目录...")
    else:
        click.echo(f"监视 {len(files_to_watch)} 个文件 (命令: {command}, 间隔: {interval}s)")

    file_hashes: dict[str, str] = {}
    for f in files_to_watch:
        try:
            file_hashes[str(f)] = hashlib.md5(f.read_bytes()).hexdigest()
        except OSError:
            pass

    last_triggered = 0.0

    def run_command_on_target(t: str) -> None:
        if command == "lint":
            from ai_prompt_toolkit.linter.linter import PromptLinter
            from ai_prompt_toolkit.cli_helpers import discover_templates
            templates = discover_templates(t)
            linter = PromptLinter()
            total_findings = 0
            for tpl in templates:
                text = tpl.read_text(encoding="utf-8")
                result = linter.lint(tpl.name, text)
                total_findings += result.failed_count
            click.echo(f"[lint] {len(templates)} 文件 | {total_findings} 问题")
            if gate and total_findings > 0:
                click.echo("[gate] WARN: 发现Lint问题")
        elif command == "scan":
            from ai_prompt_toolkit.security.injection_detector import InjectionDetector
            from ai_prompt_toolkit.cli_helpers import discover_templates
            templates = discover_templates(t)
            detector = InjectionDetector()
            total_findings = 0
            for tpl in templates:
                text = tpl.read_text(encoding="utf-8")
                findings = detector.detect(text)
                total_findings += len(findings)
            click.echo(f"[scan] {len(templates)} 文件 | {total_findings} 风险")
        elif command == "evaluate":
            from ai_prompt_toolkit.evaluator import evaluate_template
            from ai_prompt_toolkit.cli_helpers import resolve_path
            tp = resolve_path(t, must_exist=False)
            if tp.is_file():
                text = tp.read_text(encoding="utf-8")
                report = evaluate_template(str(tp), text)
                scores = report.scores
                avg = sum(s.score for s in scores) / len(scores) if scores else 0
                click.echo(f"[evaluate] {tp.name} | 均分: {avg:.1f}/10")
        elif command == "compliance":
            from ai_prompt_toolkit.security.huaweicloud_compliance import compute_huaweicloud_compliance
            from ai_prompt_toolkit.security.injection_detector import InjectionDetector
            from ai_prompt_toolkit.security.pii_detector import PIIDetector
            from ai_prompt_toolkit.cli_helpers import discover_templates
            templates = discover_templates(t)
            all_findings = []
            for tpl in templates:
                text = tpl.read_text(encoding="utf-8")
                all_findings.extend(InjectionDetector().detect(text))
                pii_f = PIIDetector().check(text)
                if pii_f:
                    all_findings.append(pii_f)
            comp_report = compute_huaweicloud_compliance(all_findings)
            click.echo(f"[compliance] {comp_report.overall_score}/100 ({comp_report.grade.value}) {comp_report.decision.value}")

    try:
        click.echo("按 Ctrl+C 停止监视")
        while True:
            import time as _time
            _time.sleep(interval)

            current_files: list[Path] = []
            if target_path.is_file():
                current_files = [target_path]
            else:
                current_files = sorted(target_path.rglob("*.md"))

            changed = False
            for f in current_files:
                key = str(f)
                try:
                    new_hash = hashlib.md5(f.read_bytes()).hexdigest()
                except OSError:
                    continue
                old_hash = file_hashes.get(key)
                if old_hash != new_hash:
                    file_hashes[key] = new_hash
                    changed = True

            removed = set(file_hashes.keys()) - {str(f) for f in current_files}
            for r in removed:
                del file_hashes[r]
                changed = True

            if changed:
                now = _time.time()
                if now - last_triggered < debounce:
                    continue
                last_triggered = now
                ts = _time.strftime("%H:%M:%S")
                click.echo(f"\n[{ts}] 检测到变更，执行 {command}...")
                try:
                    run_command_on_target(target)
                except Exception as e:
                    click.echo(f"[error] {e}", err=True)
    except KeyboardInterrupt:
        click.echo("\n\n⏹ 监视已停止。下次运行 'prompt-cli watch' 即可继续。")


@main.command(name="doctor")
@click.option("--provider", "-p", help="仅检查指定Provider(如openai,anthropic)")
@click.option("--json", "as_json", is_flag=True, help="JSON格式输出")
@click.option("--init", "init_config", is_flag=True, help="首次运行: 自动生成.prompt-toolkit.yml配置模板")
def doctor_cmd(provider: str | None, as_json: bool, init_config: bool) -> None:
    """健康检查：检测Provider连接状态和API Key配置"""
    if init_config:
        from pathlib import Path as _P
        config_path = _P(".prompt-toolkit.yml")
        if config_path.exists():
            click.echo(f"配置文件已存在: {config_path}")
        else:
            config_content = """# ai-prompt-toolkit 配置
lint:
  fail_on: high
  format: cli
  semantic_cache: true
  parallel: 0

scan:
  depth: full
  format: json

evaluate:
  threshold: 5.0
  format: cli

security:
  block_threshold: 0.7
  warn_threshold: 0.35

output_scan:
  enabled: true
  scanners: [no_refusal, bias, toxicity, relevance, factual_consistency, citation]

harmonyos:
  stage_model: true
  min_api: 12
  target_api: 14

weight_preset: default
"""
            config_path.write_text(config_content, encoding="utf-8")
            click.echo(f"配置模板已生成: {config_path}")
        return

    _config_path = _P(".prompt-toolkit.yml") if (_P := __import__("pathlib").Path)(".prompt-toolkit.yml").exists() else None
    if not _config_path and not as_json:
        click.echo("提示: 未找到配置文件, 使用 --init 生成 .prompt-toolkit.yml 模板\n")
    from ai_prompt_toolkit.ab_test.provider import run_health_check
    from ai_prompt_toolkit.ab_test.types import ProviderType

    targets = None
    if provider:
        try:
            pt = ProviderType(provider.lower())
            targets = [pt]
        except ValueError:
            click.echo(f"错误: 不支持的Provider '{provider}'", err=True)
            click.echo(f"可选: {', '.join(p.value for p in ProviderType)}")
            sys.exit(2)

    click.echo("正在检查Provider健康状态...")
    results = run_health_check(targets)

    if as_json:
        import json as _json
        click.echo(_json.dumps([
            {"provider": r.provider.value, "label": r.label, "status": r.status,
             "latency_ms": r.latency_ms, "error": r.error,
             "api_key_configured": r.api_key_configured, "endpoint": r.endpoint}
            for r in results
        ], ensure_ascii=False, indent=2))
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Provider 健康检查报告", show_lines=True)
    table.add_column("Provider", style="bold")
    table.add_column("状态", width=12)
    table.add_column("API Key", width=8)
    table.add_column("延迟(ms)", width=10)
    table.add_column("端点", width=40)
    table.add_column("错误", width=20)

    status_styles = {
        "healthy": "[green]✓ healthy[/green]",
        "unreachable": "[red]✗ unreachable[/red]",
        "no_api_key": "[yellow]⚠ no_api_key[/yellow]",
        "unknown": "[dim]? unknown[/dim]",
    }

    for r in results:
        status_str = status_styles.get(r.status, r.status)
        key_str = "[green]✓[/green]" if r.api_key_configured else "[red]✗[/red]"
        latency_str = f"{r.latency_ms:.0f}" if r.latency_ms > 0 else "-"
        table.add_row(r.label, status_str, key_str, latency_str, r.endpoint or "-", r.error or "-")

    console.print(table)

    healthy = sum(1 for r in results if r.status == "healthy")
    no_key = sum(1 for r in results if r.status == "no_api_key")
    unreachable = sum(1 for r in results if r.status == "unreachable")
    total = len(results)

    if healthy == total:
        panel_color = "green"
        verdict = "✅ 全部正常"
    elif unreachable > 0:
        panel_color = "red"
        verdict = "❌ 存在不可达Provider"
    elif no_key > 0:
        panel_color = "yellow"
        verdict = "⚠️ 部分Provider未配置API Key"
    else:
        panel_color = "cyan"
        verdict = "ℹ️ 部分Provider异常"

    from rich.panel import Panel
    summary_lines = [
        f"[bold]健康: {healthy}/{total}[/bold]  |  未配置: {no_key}  |  不可达: {unreachable}",
        verdict,
    ]
    top_issues = [r for r in results if r.status != "healthy"][:3]
    if top_issues:
        summary_lines.append("[bold]优先修复:[/bold]")
        for idx, r in enumerate(top_issues, 1):
            summary_lines.append(f"  {idx}. {r.label}: {r.error or r.status}")
    console.print(Panel("\n".join(summary_lines), title="诊断摘要", border_style=panel_color))

    sys.exit(0 if healthy == total else 1)


@main.command(name="wizard")
@click.option("--command", "-c", type=click.Choice(["lint", "scan", "evaluate", "ab-test", "redteam"]),
              help="直接指定命令(跳过功能选择)")
def wizard_cmd(command: str | None) -> None:
    """交互式向导：5步引导你完成Prompt工具链操作"""
    from ai_prompt_toolkit.wizard import run_wizard
    exit_code = run_wizard(command)
    sys.exit(exit_code)


@main.command(name="lsp")
@click.option("--mode", type=click.Choice(["stdio", "tcp"]), default="stdio", help="LSP传输模式")
@click.option("--host", default="127.0.0.1", help="TCP模式监听地址")
@click.option("--port", type=int, default=2087, help="TCP模式监听端口")
def lsp_cmd(mode: str, host: str, port: int) -> None:
    """LSP服务：VS Code实时Prompt Lint(debounce 300ms)"""
    try:
        from ai_prompt_toolkit.linter.lsp_server import run_lsp_stdio, run_lsp_tcp
    except ImportError:
        click.echo("错误: LSP功能需要安装pygls: pip install pygls lsprotocol", err=True)
        sys.exit(1)

    click.echo(f"启动Prompt LSP服务({mode}模式)...")
    if mode == "tcp":
        click.echo(f"监听: {host}:{port}")
        run_lsp_tcp(host, port)
    else:
        run_lsp_stdio()


@main.command(name="benchmark")
@click.option("--case", "-c", help="指定测试用例(默认全部)")
@click.option("--save", is_flag=True, help="保存结果到数据库")
@click.option("--threshold", type=float, default=20.0, help="回归告警阈值(%)")
@click.option("--json", "as_json", is_flag=True, help="JSON格式输出")
def benchmark_cmd(case: str | None, save: bool, threshold: float, as_json: bool) -> None:
    """性能基准：Lint/Scan/Evaluate执行时间基准"""
    from ai_prompt_toolkit.benchmark import run_benchmark, run_full_benchmark, BenchmarkDB

    if save:
        report = run_full_benchmark(threshold_pct=threshold)
        if as_json:
            import json as _json
            click.echo(_json.dumps(report, ensure_ascii=False, indent=2))
        else:
            click.echo("性能基准测试结果:")
            for r in report["results"]:
                click.echo(f"  {r['name']}: {r['duration_ms']:.2f}ms")
            if report["regression_alerts"]:
                click.echo("\n回归告警:")
                for a in report["regression_alerts"]:
                    click.echo(f"  [{a['case_id']}] {a['regression_pct']:.1f}% 回归 (基线: {a['baseline_ms']:.2f}ms)")
            click.echo(f"\n平均耗时: {report['summary']['avg_duration_ms']:.2f}ms | 回归数: {report['summary']['regressions']}")
    else:
        results = run_benchmark(case)
        if as_json:
            import json as _json
            click.echo(_json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
        else:
            click.echo("性能基准测试:")
            for r in results:
                click.echo(f"  {r.name}: {r.duration_ms:.2f}ms")


@main.command(name="recommend")
@click.option("--category", "-c", help="场景分类(如general,development,translation)")
@click.option("--industry", "-i", help="行业(如科技,金融,华为云)")
@click.option("--model", "-m", help="模型(如gpt-4,qwen,deepseek)")
@click.option("--top-n", type=int, default=5, help="推荐数量")
@click.option("--json", "as_json", is_flag=True, help="JSON格式输出")
def recommend_cmd(category: str | None, industry: str | None, model: str | None,
                  top_n: int, as_json: bool) -> None:
    """智能推荐：基于场景/行业/模型推荐最佳Prompt模板"""
    from ai_prompt_toolkit.template_recommender import TemplateRecommender

    recommender = TemplateRecommender()
    results = recommender.recommend(category=category, industry=industry, model=model, top_n=top_n)

    if as_json:
        import json as _json
        click.echo(_json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        click.echo(f"模板推荐(Top {len(results)}):")
        for i, r in enumerate(results, 1):
            click.echo(f"  {i}. {r.name} ({r.template_id})")
            click.echo(f"     Lint: {r.lint_score}/100 | 评分: {r.market_rating}/5 | 下载: {r.download_count}")
            click.echo(f"     相关度: {r.relevance_score:.1f} | 原因: {r.reason}")


@main.command(name="optimize")
@click.option("--source", "-s", required=True, help="源Prompt文件路径")
@click.option("--max-iterations", type=int, default=5, help="最大优化轮次")
@click.option("--min-improvement", type=float, default=1.0, help="最小改进阈值(分)")
@click.option("--output", "-o", help="输出优化后文件路径")
def optimize_cmd(source: str, max_iterations: int, min_improvement: float, output: str | None) -> None:
    """Prompt自动优化：基于Lint评估的迭代式自动优化"""
    from ai_prompt_toolkit.prompt_optimizer import optimize_prompt
    from ai_prompt_toolkit.cli_helpers import resolve_path

    path = resolve_path(source)
    text = path.read_text(encoding="utf-8")

    click.echo(f"优化Prompt: {path.name} (最大{max_iterations}轮)")
    result = optimize_prompt(text, max_iterations=max_iterations, min_improvement=min_improvement)

    click.echo(f"\n优化完成:")
    click.echo(f"  原始评分: {result.original_score:.1f}/100")
    click.echo(f"  优化评分: {result.final_score:.1f}/100")
    click.echo(f"  提升: +{result.total_improvement:.1f}分 ({result.iterations}步)")

    for step in result.steps:
        status = "✓" if step.improvement > 0 else "✗"
        click.echo(f"  {status} {step.strategy_name}: {step.score_before:.1f} → {step.score_after:.1f}")

    if output:
        from ai_prompt_toolkit.cli_helpers import resolve_path as rp
        out_path = rp(output)
        out_path.write_text(result.optimized_text, encoding="utf-8")
        click.echo(f"\n已保存: {output}")


@main.command(name="probe")
@click.option("--target", "-t", required=True, help="目标Prompt文本文件路径")
@click.option("--probes", "-p", help="指定探针(逗号分隔，默认全部)", default="")
@click.option("--detectors", "-d", help="指定检测器(逗号分隔，默认全部)", default="")
@click.option("--output", "-o", help="输出报告路径(JSON)")
@click.option("--max-payloads", type=int, default=20, help="每个探针最大payload数")
@click.option("--quick", is_flag=True, help="快速模式: 仅运行TOP5高危Probe, 30秒内返回")
def probe_cmd(target: str, probes: str, detectors: str, output: str | None, max_payloads: int, quick: bool) -> None:
    """Red Team Probe扫描: garak风格探针类别自动检测Prompt安全漏洞"""
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.probe_framework import ProbeRunner, list_probes, list_detectors as list_det

    if target == "list":
        probe_list = list_probes()
        det_list = list_det()
        click.echo("可用探针(Probe):")
        for p in probe_list:
            click.echo(f"  {p['name']:25s} [{p['severity']:8s}] {p['description']}")
        click.echo(f"\n可用检测器(Detector):")
        for d in det_list:
            click.echo(f"  {d['name']:25s} {d['description']}")
        return

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"错误: 文件不存在: {target}")
        sys.exit(1)

    text = target_path.read_text(encoding="utf-8")

    _QUICK_PROBES = ["dan", "prompt_inject", "system_prompt_leak", "encoding_bypass", "package_hallucination"]
    if quick:
        if probes:
            click.echo("[INFO] --quick 已指定, 忽略 --probes 参数, 使用TOP5高危Probe")
        probe_names = _QUICK_PROBES
    else:
        probe_names = [p.strip() for p in probes.split(",") if p.strip()] if probes else None
    detector_names = [d.strip() for d in detectors.split(",") if d.strip()] if detectors else None

    runner = ProbeRunner(probe_names=probe_names, detector_names=detector_names, max_payloads_per_probe=max_payloads)
    click.echo(f"正在运行Probe扫描({runner._probes.__len__()}探针, {len(runner._detectors)}检测器)...")

    report = runner.run(target_path.name, text)

    click.echo(f"\n{'='*60}")
    click.echo(f"Probe扫描报告: {report.template_id}")
    click.echo(f"{'='*60}")
    click.echo(f"探针数: {report.total_probes} | Payload数: {report.total_payloads} | 检出: {report.total_detections}")
    click.echo(f"风险评分: {report.risk_score:.1f}/10.0")

    if report.probe_summary:
        click.echo(f"\n探针检出统计:")
        for name, count in sorted(report.probe_summary.items(), key=lambda x: -x[1]):
            if count > 0:
                click.echo(f"  {name:25s} {count} 检出")

    if report.detector_summary:
        click.echo(f"\n检测器统计:")
        for name, count in sorted(report.detector_summary.items(), key=lambda x: -x[1]):
            click.echo(f"  {name:25s} {count} 次")

    if report.recommendations:
        click.echo(f"\n防御建议:")
        for rec in report.recommendations:
            click.echo(f"  {rec}")

    if output:
        import json as _json
        Path(output).write_text(_json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"\n报告已保存: {output}")

    if report.risk_score >= 7.0:
        sys.exit(2)
    elif report.risk_score >= 4.0:
        sys.exit(1)


if __name__ == "__main__":
    main()


@main.command()
@click.option("--target", "-t", required=True, help="监听目标(文件或目录)")
@click.option("--command", "-c", type=click.Choice(["lint", "scan", "evaluate", "compliance"]), default="lint", help="变更时执行的命令")
@click.option("--debounce", type=float, default=1.0, help="防抖延迟(秒)")
def watch(target: str, command: str, debounce: float) -> None:
    """Watch模式：文件变更自动重新检查"""
    import hashlib

    from ai_prompt_toolkit.cli_helpers import discover_templates
    from ai_prompt_toolkit.output import console, info, success

    target_path = Path(target).resolve()
    if not target_path.exists():
        click.echo(f"目标不存在: {target}", err=True)
        sys.exit(2)

    info(f"Watch模式启动 — 监听: {target} | 命令: {command} | 防抖: {debounce}s")
    info("按 Ctrl+C 退出")

    file_hashes: dict[str, str] = {}

    def _hash_files() -> dict[str, str]:
        templates = discover_templates(target)
        hashes = {}
        for p in templates:
            try:
                hashes[str(p)] = hashlib.md5(p.read_bytes()).hexdigest()
            except OSError:
                pass
        return hashes

    file_hashes = _hash_files()

    try:
        while True:
            time.sleep(debounce)
            new_hashes = _hash_files()
            changed = []
            for path_str, h in new_hashes.items():
                if file_hashes.get(path_str) != h:
                    changed.append(path_str)
            for path_str in set(file_hashes) - set(new_hashes):
                changed.append(path_str)
            if changed:
                file_hashes = new_hashes
                console.print(f"\n[bold]检测到 {len(changed)} 个文件变更[/bold]")
                from click.testing import CliRunner
                runner = CliRunner()
                cmd_args = [command, "-t", target]
                result = runner.invoke(main, cmd_args, catch_exceptions=False)
                if result.output:
                    console.print(result.output.rstrip())
    except KeyboardInterrupt:
        success("Watch模式已退出")


@main.group(name="dataset")
def dataset_group() -> None:
    """数据集管理: 创建/导入/运行测试用例集"""


@dataset_group.command(name="create")
@click.option("--name", "-n", required=True, help="数据集名称")
@click.option("--description", "-d", default="", help="数据集描述")
@click.option("--tags", "-t", default="", help="标签(逗号分隔)")
def dataset_create(name: str, description: str, tags: str) -> None:
    """创建新数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import console, success
    store = DatasetStore()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    ds = store.create_dataset(name, description=description, tags=tag_list)
    success(f"数据集已创建: {ds.dataset_id} ({name})")
    store.close()


@dataset_group.command(name="list")
@click.option("--page", default=1, help="页码")
@click.option("--page-size", default=20, help="每页数量")
def dataset_list(page: int, page_size: int) -> None:
    """列出所有数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import console
    from rich.table import Table
    store = DatasetStore()
    datasets, total = store.list_datasets(page, page_size)
    table = Table(title=f"数据集 (共{total}个)")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="white")
    table.add_column("描述")
    table.add_column("用例数", style="green")
    table.add_column("标签")
    table.add_column("更新时间")
    for ds in datasets:
        table.add_row(ds.dataset_id, ds.name, ds.description[:30], str(ds.case_count), ",".join(ds.tags[:3]), ds.updated_at[:16])
    console.print(table)
    store.close()


@dataset_group.command(name="add-case")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--input", "-i", required=True, help="输入文本")
@click.option("--expected", "-e", default="", help="期望输出")
@click.option("--tags", "-t", default="", help="标签(逗号分隔)")
def dataset_add_case(dataset: str, input: str, expected: str, tags: str) -> None:
    """添加测试用例"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success
    store = DatasetStore()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    c = store.add_case(dataset, input, expected_output=expected, tags=tag_list)
    success(f"用例已添加: {c.case_id}")
    store.close()


@dataset_group.command(name="import")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--file", "-f", required=True, help="导入文件路径(JSON/CSV)")
def dataset_import(dataset: str, file: str) -> None:
    """从JSON/CSV文件导入用例"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success
    store = DatasetStore()
    p = Path(file)
    if not p.exists():
        click.echo(f"文件不存在: {file}", err=True)
        sys.exit(2)
    content = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        import json
        items = json.loads(content)
        count = store.import_json(dataset, items)
    elif p.suffix == ".csv":
        count = store.import_csv(dataset, content)
    else:
        click.echo("仅支持.json/.csv格式", err=True)
        sys.exit(2)
    success(f"已导入{count}条用例")
    store.close()


@dataset_group.command(name="export")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--format", "-f", type=click.Choice(["json", "csv"]), default="json", help="导出格式")
@click.option("--output", "-o", help="输出文件路径")
def dataset_export(dataset: str, format: str, output: str | None) -> None:
    """导出数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success
    store = DatasetStore()
    if format == "csv":
        data = store.export_csv(dataset)
    else:
        data = store.export_json(dataset)
    if output:
        Path(output).write_text(data, encoding="utf-8")
        success(f"已导出到: {output}")
    else:
        click.echo(data)
    store.close()


@dataset_group.command(name="run")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--type", "-t", type=click.Choice(["all", "lint", "scan", "evaluate"]), default="all", help="运行类型")
def dataset_run(dataset: str, type: str) -> None:
    """对数据集批量运行lint/scan/evaluate"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import console
    from rich.table import Table
    store = DatasetStore()
    results = store.run_dataset(dataset, run_type=type)
    table = Table(title=f"数据集运行结果 ({type})")
    table.add_column("用例ID", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("Lint分数")
    table.add_column("扫描问题")
    table.add_column("评估分数")
    for r in results:
        status_style = "green" if r.status == "completed" else "red"
        table.add_row(r.case_id[:8], f"[{status_style}]{r.status}[/]", f"{r.lint_score:.1f}", str(r.scan_findings), f"{r.eval_score:.1f}")
    console.print(table)
    store.close()


@dataset_group.command(name="delete")
@click.option("--dataset", "-d", required=True, help="数据集ID")
def dataset_delete(dataset: str) -> None:
    """删除数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success
    store = DatasetStore()
    if store.delete_dataset(dataset):
        success(f"数据集已删除: {dataset}")
    else:
        click.echo(f"数据集不存在: {dataset}", err=True)
        sys.exit(2)
    store.close()


@main.group(name="plugin")
def plugin_group() -> None:
    """插件管理: 注册/列表/启用/禁用"""


@plugin_group.command(name="list")
def plugin_list() -> None:
    """列出已注册插件"""
    from ai_prompt_toolkit.plugin import PluginManager
    from ai_prompt_toolkit.output import console
    from rich.table import Table
    mgr = PluginManager.get_instance()
    plugins = mgr.list_plugins()
    if not plugins:
        click.echo("暂无已注册插件")
        return
    table = Table(title="已注册插件")
    table.add_column("名称", style="cyan")
    table.add_column("版本")
    table.add_column("状态", style="green")
    table.add_column("描述")
    for p in plugins:
        status = "启用" if p.enabled else "禁用"
        table.add_row(p.meta.name, p.meta.version, status, p.meta.description[:40])
    console.print(table)


@plugin_group.command(name="load")
@click.option("--module", "-m", help="Python模块路径")
@click.option("--file", "-f", help="插件文件路径")
def plugin_load(module: str | None, file: str | None) -> None:
    """加载插件"""
    from ai_prompt_toolkit.plugin import PluginManager
    from ai_prompt_toolkit.output import success
    mgr = PluginManager.get_instance()
    if module:
        p = mgr.load_from_module(module)
        if p:
            success(f"插件已加载: {p.meta.name}")
        else:
            click.echo(f"加载失败: {module}", err=True)
    elif file:
        p = mgr.load_from_file(file)
        if p:
            success(f"插件已加载: {p.meta.name}")
        else:
            click.echo(f"加载失败: {file}", err=True)
    else:
        click.echo("请指定--module或--file", err=True)


@plugin_group.command(name="enable")
@click.option("--name", "-n", required=True, help="插件名称")
def plugin_enable(name: str) -> None:
    """启用插件"""
    from ai_prompt_toolkit.plugin import PluginManager
    from ai_prompt_toolkit.output import success
    mgr = PluginManager.get_instance()
    p = mgr.get_plugin(name)
    if not p:
        click.echo(f"插件不存在: {name}", err=True)
        return
    p.enable()
    success(f"插件已启用: {name}")


@plugin_group.command(name="disable")
@click.option("--name", "-n", required=True, help="插件名称")
def plugin_disable(name: str) -> None:
    """禁用插件"""
    from ai_prompt_toolkit.plugin import PluginManager
    from ai_prompt_toolkit.output import success
    mgr = PluginManager.get_instance()
    p = mgr.get_plugin(name)
    if not p:
        click.echo(f"插件不存在: {name}", err=True)
        return
    p.disable()
    success(f"插件已禁用: {name}")


@main.command(name="locale")
@click.option("--set", "-s", "set_locale", help="设置语言(zh-CN/en-US)")
@click.option("--list", "-l", "list_locales", is_flag=True, help="列出支持的语言")
def locale_cmd(set_locale: str | None, list_locales: bool) -> None:
    """查看/设置界面语言"""
    from ai_prompt_toolkit.i18n.messages import t, set_locale as msg_set_locale, get_current_locale, get_supported_locales
    if list_locales:
        current = get_current_locale()
        for loc in get_supported_locales():
            marker = " (当前)" if loc == current else ""
            click.echo(f"  {loc}{marker}")
        return
    if set_locale:
        msg_set_locale(set_locale)
        click.echo(f"语言已切换为: {set_locale}")
        return
    current = get_current_locale()
    click.echo(f"当前语言: {current}")
    click.echo(f"支持的语言: {', '.join(get_supported_locales())}")


@main.command(name="feedback")
@click.option("--message", "-m", help="反馈内容(最长2000字)")
@click.option("--type", "-t", type=click.Choice(["bug", "feature", "improvement", "other"]), default="other", help="反馈类型")
@click.option("--action", type=click.Choice(["submit", "list", "stats"]), default="submit", help="操作: submit/list/stats")
def feedback_cmd(message: str | None, type: str, action: str) -> None:
    """提交/查看用户反馈"""
    import json
    from ai_prompt_toolkit.output import success, console
    feedback_dir = Path.home() / ".ai-prompt-toolkit" / "feedback"

    if action == "list":
        feedback_dir.mkdir(parents=True, exist_ok=True)
        entries = sorted(feedback_dir.glob("fb_*.json"))
        if not entries:
            console.print("[dim]暂无反馈记录[/dim]")
            return
        for entry in entries[-20:]:
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                console.print(f"  [{data.get('type', '?')}] {data.get('message', '')[:60]}  [dim]{data.get('timestamp', '')}[/dim]")
            except Exception:
                pass
        return

    if action == "stats":
        feedback_dir.mkdir(parents=True, exist_ok=True)
        entries = list(feedback_dir.glob("fb_*.json"))
        if not entries:
            console.print("[dim]暂无反馈记录[/dim]")
            return
        type_counts: dict[str, int] = {}
        for entry in entries:
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                t = data.get("type", "other")
                type_counts[t] = type_counts.get(t, 0) + 1
            except Exception:
                pass
        console.print(f"[bold cyan]反馈统计[/bold cyan]  总计: [bold]{len(entries)}[/bold]条")
        for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
            console.print(f"  {t}: {cnt}条")
        return

    if not message:
        console.print("[red]错误: submit操作需要--message参数[/red]")
        return
    if len(message) > 2000:
        console.print("[red]错误: 反馈内容不能超过2000字[/red]")
        return

    feedback_dir.mkdir(parents=True, exist_ok=True)
    import time
    entry = {
        "message": message,
        "type": type,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": __version__,
    }
    fb_file = feedback_dir / f"fb_{int(time.time())}.json"
    fb_file.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    success(f"感谢反馈! 已保存到 {fb_file}")


@main.command(name="stats")
@click.option("--target", "-t", help="目标文件或目录")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
def stats_cmd(target: str | None, fmt: str) -> None:
    """查看项目/文件的Prompt统计数据"""
    from ai_prompt_toolkit.output import console
    import json as _json

    target_path = Path(target) if target else Path(".")

    prompt_files: list[Path] = []
    if target_path.is_file():
        prompt_files = [target_path]
    elif target_path.is_dir():
        for ext in ("*.md", "*.prompt", "*.txt"):
            prompt_files.extend(target_path.rglob(ext))

    prompt_files = [f for f in prompt_files if f.stat().st_size > 0]

    total_size = sum(f.stat().st_size for f in prompt_files)
    total_chars = 0
    total_lines = 0
    lang_dist: dict[str, int] = {}

    for f in prompt_files:
        try:
            text = f.read_text(encoding="utf-8")
            total_chars += len(text)
            total_lines += text.count("\n") + 1
            zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
            if zh_chars > en_chars:
                lang_dist["中文"] = lang_dist.get("中文", 0) + 1
            elif en_chars > 0:
                lang_dist["英文"] = lang_dist.get("英文", 0) + 1
        except Exception:
            pass

    from ai_prompt_toolkit.version_store import VersionStore
    from ai_prompt_toolkit.dataset import DatasetStore

    version_count = 0
    try:
        vs = VersionStore()
        conn = vs._connect()
        row = conn.execute("SELECT COUNT(DISTINCT template_id) as cnt FROM prompt_versions").fetchone()
        version_count = row["cnt"] if row else 0
        vs.close()
    except Exception:
        pass

    dataset_count = 0
    try:
        ds = DatasetStore()
        datasets, total = ds.list_datasets()
        dataset_count = total
        ds.close()
    except Exception:
        pass

    lint_rules_count = 0
    auto_fixable_count = 0
    try:
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        lint_rules_count = len(_RULE_MAP)
        auto_fixable_count = len(AUTO_FIXABLE_RULES)
    except Exception:
        pass

    security_rules_count = 0
    try:
        from ai_prompt_toolkit.security.injection_detector import InjectionDetector
        from ai_prompt_toolkit.security.pii_detector import PIIDetector
        sec_counts = []
        try:
            sec_counts.append(len(InjectionDetector.RULES))
        except Exception:
            pass
        try:
            sec_counts.append(len(PIIDetector.PATTERNS))
        except Exception:
            pass
        security_rules_count = sum(sec_counts)
    except Exception:
        pass

    probe_count = 0
    detector_count = 0
    try:
        from ai_prompt_toolkit.probe_framework import _PROBE_REGISTRY, _DETECTOR_REGISTRY
        probe_count = len(_PROBE_REGISTRY)
        detector_count = len(_DETECTOR_REGISTRY)
    except Exception:
        pass

    eval_dims_count = 0
    try:
        from ai_prompt_toolkit.evaluator import get_all_dimensions
        eval_dims_count = len(get_all_dimensions())
    except Exception:
        pass

    mcp_tools_count = 0
    try:
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        mcp_tools_count = len(_get_tool_dispatch())
    except Exception:
        pass

    template_count = 0
    try:
        from ai_prompt_toolkit.prompt_template import list_templates
        template_count = len(list_templates())
    except Exception:
        pass

    stats_data = {
        "prompt_files": len(prompt_files),
        "total_chars": total_chars,
        "total_lines": total_lines,
        "total_size_kb": round(total_size / 1024, 1),
        "language_distribution": lang_dist,
        "versioned_templates": version_count,
        "datasets": dataset_count,
        "lint_rules": lint_rules_count,
        "auto_fixable_rules": auto_fixable_count,
        "security_rules": security_rules_count,
        "eval_dimensions": eval_dims_count,
        "probes": probe_count,
        "detectors": detector_count,
        "mcp_tools": mcp_tools_count,
        "templates": template_count,
    }

    if fmt == "json":
        click.echo(_json.dumps(stats_data, ensure_ascii=False, indent=2))
    else:
        console.print("[bold cyan]Prompt 项目统计[/bold cyan]")
        console.print(f"  📄 Prompt文件: [bold]{len(prompt_files)}[/bold] 个 ({total_size / 1024:.1f} KB)")
        console.print(f"  📝 总字符数: [bold]{total_chars:,}[/bold] | 总行数: [bold]{total_lines:,}[/bold]")
        if lang_dist:
            for lang, cnt in lang_dist.items():
                console.print(f"  🌐 语言分布: {lang} {cnt}个文件")
        console.print(f"  📋 版本管理: [bold]{version_count}[/bold] 个模板有版本记录")
        console.print(f"  📊 数据集: [bold]{dataset_count}[/bold] 个")
        console.print(f"  🔍 Lint规则: [bold]{lint_rules_count}[/bold]条(自动修复:[bold]{auto_fixable_count}[/bold]) | 安全规则: [bold]{security_rules_count}[/bold]条")
        console.print(f"  🎯 评估维度: [bold]{eval_dims_count}[/bold]个 | Probe: [bold]{probe_count}[/bold]个 | Detector: [bold]{detector_count}[/bold]个")
        console.print(f"  🔧 MCP工具: [bold]{mcp_tools_count}[/bold]个 | 内置模板: [bold]{template_count}[/bold]个")


@main.command(name="score")
@click.option("--target", "-t", required=True, help="目标Prompt文件")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
def score_cmd(target: str, fmt: str) -> None:
    """一键安全评分(0-100分)"""
    from ai_prompt_toolkit.output import console
    from ai_prompt_toolkit.cli_helpers import resolve_path
    import json as _json

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"文件不存在: {target}", err=True)
        sys.exit(3)

    text = target_path.read_text(encoding="utf-8")

    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard, Decision

    linter = PromptLinter()
    lint_result = linter.lint(target_path.name, text)
    lint_findings = lint_result.findings if hasattr(lint_result, 'findings') else []

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
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, 'score') else None)

    if fmt == "json":
        click.echo(_json.dumps(scorecard.to_dict(), ensure_ascii=False, indent=2))
    else:
        grade_colors = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bold red"}
        gc = grade_colors.get(scorecard.grade.value, "white")
        console.print(f"\n[bold]安全评分卡: [{gc}]{scorecard.overall_score}/100 ({scorecard.grade.value})[/{gc}][/bold]")
        console.print(f"  决策: [bold]{scorecard.decision.value.upper()}[/bold] | {scorecard.summary}")
        console.print(f"  发现: {scorecard.total_findings} (严重:{scorecard.critical_count} 高危:{scorecard.high_count} 中危:{scorecard.medium_count} 低危:{scorecard.low_count})")
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
    from ai_prompt_toolkit.output import console
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.security.engine import FusionEngine
    from ai_prompt_toolkit.security.prompt_scorecard import Decision
    import json as _json

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
        console.print(f"\n[bold]融合引擎分析结果:[/bold]")
        console.print(f"  风险分数: {result.risk_score:.4f} | 校准分数: {result.calibrated_score:.4f} | 置信度: {result.confidence:.4f}")
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
@click.option("--theme", type=click.Choice(["light", "dark", "huawei"]), default="light", help="主题(light/dark/huawei)")
def badge_cmd(target: str, output: str, compact: bool, theme: str) -> None:
    """生成安全评分徽章SVG"""
    from ai_prompt_toolkit.output import console, success
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
    from ai_prompt_toolkit.security.badge import generate_scorecard_badge_file

    target_path = resolve_path(target)
    if not target_path.exists():
        click.echo(f"文件不存在: {target}", err=True)
        sys.exit(3)

    text = target_path.read_text(encoding="utf-8")

    linter = PromptLinter()
    lint_result = linter.lint(target_path.name, text)
    lint_findings = lint_result.findings if hasattr(lint_result, 'findings') else []

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
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, 'score') else None)

    generate_scorecard_badge_file(scorecard, output, compact=compact, theme=theme)
    success(f"评分徽章已生成到 {output} (评分: {scorecard.overall_score}/100 {scorecard.grade.value})")


@main.command(name="rules-yaml")
@click.option("--init", "init_path", help="生成示例YAML规则文件到指定路径")
@click.option("--load", "load_path", help="加载YAML规则文件并检查")
@click.option("--target", "-t", help="使用自定义规则检查的目标文件")
def rules_yaml_cmd(init_path: str | None, load_path: str | None, target: str | None) -> None:
    """管理自定义Lint规则(YAML)"""
    from ai_prompt_toolkit.output import console, success, error
    from ai_prompt_toolkit.linter.rule_loader_yaml import load_rules_from_yaml, check_custom_rules, generate_sample_yaml

    if init_path:
        generate_sample_yaml(init_path)
        success(f"示例规则文件已生成到 {init_path}")
        return

    if load_path:
        try:
            rules = load_rules_from_yaml(load_path)
            if not rules:
                error("未加载到任何启用的规则")
                return
            console.print(f"[bold]已加载 {len(rules)} 条自定义规则:[/bold]")
            for r in rules:
                sev_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "cyan", "LOW": "green"}.get(r["severity"].value, "white")
                console.print(f"  [{sev_color}]{r['rule_id']}[/{sev_color}] {r['name']} ({r['severity'].value}) — {r['description'][:50]}")

            if target:
                from ai_prompt_toolkit.cli_helpers import resolve_path
                target_path = resolve_path(target)
                if not target_path.exists():
                    error(f"目标文件不存在: {target}")
                    return
                text = target_path.read_text(encoding="utf-8")
                findings = check_custom_rules(text, rules)
                if findings:
                    console.print(f"\n[bold yellow]发现 {len(findings)} 个问题:[/bold yellow]")
                    for f in findings:
                        console.print(f"  [{f.rule_id}] {f.description}")
                else:
                    success("自定义规则检查通过，未发现问题")
        except FileNotFoundError as e:
            error(str(e))
        return

    click.echo("使用 --init 生成示例规则 或 --load 加载规则文件")


@main.command(name="compliance")
@click.option("--target", "-t", required=True, help="合规扫描目标(文件或目录)")
@click.option("--format", "fmt", type=click.Choice(["cli", "json", "markdown", "sarif"]),
              default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
@click.option("--owasp-pct", "owasp_pct", type=float, default=0.0, help="OWASP LLM Top 10合规百分比(0-100)")
def compliance_cmd(target: str, fmt: str, output: str | None, owasp_pct: float) -> None:
    """华为云安全合规报告: 7域加权评分+OWASP映射+等保2.0"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, empty_state_tip
    from ai_prompt_toolkit.security.huaweicloud_compliance import compute_huaweicloud_compliance
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.types import Finding, Severity

    templates = discover_templates(target)
    if not templates:
        click.echo(empty_state_tip("compliance"))
        sys.exit(0)

    all_findings: list[Finding] = []
    injection_detector = InjectionDetector()
    pii_detector = PIIDetector()
    supply_chain_detector = SupplyChainDetector()

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        all_findings.extend(injection_detector.detect(text))
        pii_f = pii_detector.check(text)
        if pii_f:
            all_findings.append(pii_f)
        sc_f = supply_chain_detector.check(text)
        if sc_f:
            all_findings.append(sc_f)
        struct_f = check_structural(text)
        if struct_f:
            all_findings.append(struct_f)

    report = compute_huaweicloud_compliance(all_findings, owasp_compliance_pct=owasp_pct)

    if fmt == "json":
        if output:
            Path(output).write_text(report.to_json(), encoding="utf-8")
            click.echo(f"JSON报告: {output}")
        else:
            click.echo(report.to_json())
    elif fmt == "sarif":
        from ai_prompt_toolkit.report.sarif_reporter import write_sarif_report
        sarif_findings = []
        for d in report.domains:
            if d.findings_count > 0:
                sarif_findings.append(Finding(
                    rule_id=f"HC-{d.domain}",
                    severity=Severity.HIGH if d.critical_count > 0 else Severity.MEDIUM if d.high_count > 0 else Severity.LOW,
                    description=f"[{d.domain_name}] 评分{d.score}/{d.max_score} 发现{d.findings_count}个问题",
                ))
        output_path = output or "compliance-report.sarif.json"
        write_sarif_report(sarif_findings, output_path, source_file=target)
        click.echo(f"SARIF报告: {output_path}")
    elif fmt == "markdown":
        md = report.to_markdown()
        if output:
            Path(output).write_text(md, encoding="utf-8")
            click.echo(f"Markdown报告: {output}")
        else:
            click.echo(md)
    else:
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
            grade_color = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "red bold"}[report.grade.value]
            summary_lines = [
                f"[bold]综合评分: [{grade_color}]{report.overall_score}/100 ({report.grade.value})[/{grade_color}][/bold]",
                f"决策: {report.decision.value} | OWASP合规: {report.owasp_compliance_pct}%",
                f"文件: {len(templates)} | 发现: {report.total_findings} (CRITICAL:{report.critical_count} HIGH:{report.high_count})",
                f"",
                f"[dim]{report.summary}[/dim]",
            ]
            console.print(Panel("\n".join(summary_lines), title="华为云安全合规报告", border_style=grade_color))

            domain_table = Table(title="合规域详情", show_header=True, header_style="bold")
            domain_table.add_column("域", style="cyan")
            domain_table.add_column("评分", justify="right")
            domain_table.add_column("通过率", justify="right")
            domain_table.add_column("发现", justify="right")
            domain_table.add_column("CRITICAL", justify="right", style="red")
            domain_table.add_column("HIGH", justify="right", style="yellow")
            for d in report.domains:
                domain_table.add_row(
                    d.domain_name,
                    f"{d.score}/{d.max_score}",
                    f"{d.pass_rate:.0%}",
                    str(d.findings_count),
                    str(d.critical_count),
                    str(d.high_count),
                )
            console.print(domain_table)

            remediation_table = Table(title="修复建议", show_header=True, header_style="bold")
            remediation_table.add_column("域", style="cyan")
            remediation_table.add_column("建议")
            for d in report.domains:
                if d.findings_count > 0:
                    remediation_table.add_row(d.domain_name, d.remediation)
            if remediation_table.rows:
                console.print(remediation_table)
        except ImportError:
            click.echo(f"华为云安全合规: {report.overall_score}/100 ({report.grade.value}) 决策:{report.decision.value}")
            click.echo(f"发现: {report.total_findings} (CRITICAL:{report.critical_count} HIGH:{report.high_count})")
            click.echo(report.summary)
            for d in report.domains:
                click.echo(f"  {d.domain_name}: {d.score}/{d.max_score}")

    if output and fmt == "cli":
        report_data = report.to_dict()
        from ai_prompt_toolkit.cli_helpers import write_report
        write_report(report_data, output, fmt="json")

    exit_code = 0 if report.decision.value == "pass" else 1 if report.decision.value == "conditional" else 2
    sys.exit(exit_code)


from ai_prompt_toolkit.cli.commands import (  # noqa: E402,F401
    lint_commands,
    redteam_commands,
    compile_commands,
    abtest_commands,
    eval_commands,
    security_commands,
    dev_commands,
    dataset_commands,
    plugin_commands,
    template_commands,
)

