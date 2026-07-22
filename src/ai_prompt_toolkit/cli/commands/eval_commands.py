"""CLI命令 — 评估相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import main


@main.command()
@click.option("--target", "-t", required=True, help="评估目标(文件或目录)")
@click.option("--dimensions", "-d", help="指定维度(逗号分隔，如D1,D5,D10)")
@click.option("--categories", help="指定类别(逗号分隔，如structure,security)")
@click.option("--threshold", type=float, default=0.0, help="质量阈值(0-10，低于此值退出码1)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
@click.option("--quick", is_flag=True, help="快速模式: 仅评估TOP10核心维度(D01-D10)")
@click.option("--save", "save_history", is_flag=True, help="保存评估结果到历史(SQLite)")
def evaluate(target: str, dimensions: str | None, categories: str | None,
             threshold: float, fmt: str, output: str | None, quick: bool,
             save_history: bool) -> None:
    """62维度质量评估：全面评估Prompt质量"""
    from ai_prompt_toolkit.cli_helpers import empty_state_tip, resolve_path, write_report
    from ai_prompt_toolkit.evaluator import evaluate_template

    target_path = resolve_path(target)
    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None
    if quick and dim_list is None:
        dim_list = [f"D{i:02d}" for i in range(1, 11)]
    cat_list = [c.strip() for c in categories.split(",")] if categories else None

    if target_path.is_dir():
        files = sorted(target_path.rglob("*.md"))
    else:
        files = [target_path]

    if not files:
        click.echo(empty_state_tip("evaluate"))
        sys.exit(2)

    reports = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        report = evaluate_template(
            str(f), text, dimensions=dim_list, categories=cat_list
        )
        reports.append(report)

    if fmt == "json":
        import json as _json
        data = {"reports": [r.to_dict() for r in reports]}
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
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
            tid = report.template_id if hasattr(report, "template_id") else "unknown"
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


@main.command(name="assert")
@click.option("--response", "-r", required=True, help="待验证的响应文本文件路径")
@click.option("--config", "-c", required=True, help="断言配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def assert_cmd(response: str, config: str, fmt: str) -> None:
    """断言验证：对LLM响应执行质量断言检查"""
    from ai_prompt_toolkit.assertion.engine import AssertionEngine
    from ai_prompt_toolkit.assertion.types import AssertionConfig, AssertType
    from ai_prompt_toolkit.cli_helpers import load_config, resolve_path

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
        create_judge,
        create_multi_judge,
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
def version_cmd(action: str, template: str | None, source: str | None, ver: int | None,
                version_a: int | None, version_b: int | None, author: str | None,
                message: str | None, fmt: str) -> None:
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
                trend_icon = f"[green]↑ +{diff:.1f}[/green]"
            elif diff < 0:
                trend_icon = f"[red]↓ {diff:.1f}[/red]"
            else:
                trend_icon = "[dim]= 0[/dim]"
            table.add_row(d["dimension_id"], str(d["score_a"]), str(d["score_b"]),
                         f"{diff:+.1f}", trend_icon)

        console.print(table)
        overall = result["overall_diff"]
        icon = "↑" if overall > 0 else "↓" if overall < 0 else "="
        console.print(f"\n总分变化: {icon} {overall:+.4f}")


@main.command(name="optimize")
@click.option("--source", "-s", required=True, help="源Prompt文件路径")
@click.option("--max-iterations", type=int, default=5, help="最大优化轮次")
@click.option("--min-improvement", type=float, default=1.0, help="最小改进阈值(分)")
@click.option("--output", "-o", help="输出优化后文件路径")
def optimize_cmd(source: str, max_iterations: int, min_improvement: float, output: str | None) -> None:
    """Prompt自动优化：基于Lint评估的迭代式自动优化"""
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.prompt_optimizer import optimize_prompt

    path = resolve_path(source)
    text = path.read_text(encoding="utf-8")

    click.echo(f"优化Prompt: {path.name} (最大{max_iterations}轮)")
    result = optimize_prompt(text, max_iterations=max_iterations, min_improvement=min_improvement)

    click.echo("\n优化完成:")
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


@main.command(name="stats")
@click.option("--target", "-t", help="目标文件或目录")
@click.option("--format", "fmt", type=click.Choice(["cli", "json"]), default="cli", help="输出格式")
def stats_cmd(target: str | None, fmt: str) -> None:
    """查看项目/文件的Prompt统计数据"""
    import json as _json

    from ai_prompt_toolkit.output import console

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
            zh_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            en_chars = sum(1 for c in text if c.isascii() and c.isalpha())
            if zh_chars > en_chars:
                lang_dist["中文"] = lang_dist.get("中文", 0) + 1
            elif en_chars > 0:
                lang_dist["英文"] = lang_dist.get("英文", 0) + 1
        except Exception:
            pass

    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.version_store import VersionStore

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

    stats_data = {
        "prompt_files": len(prompt_files),
        "total_chars": total_chars,
        "total_lines": total_lines,
        "total_size_kb": round(total_size / 1024, 1),
        "language_distribution": lang_dist,
        "versioned_templates": version_count,
        "datasets": dataset_count,
        "lint_rules": 55,
        "security_rules": "30+",
        "providers": 19,
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
        console.print("  🔍 Lint规则: [bold]55[/bold]条 | 安全规则: [bold]30+[/bold]条 | Provider: [bold]19[/bold]个")


@main.command(name="eval-config")
@click.option("--config", "-c", required=True, help="YAML评估配置文件路径")
@click.option("--base-dir", help="配置文件中相对路径的基准目录(默认配置文件所在目录)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
@click.option("--init", "init_config", is_flag=True, help="生成示例配置文件prompt-eval.yaml")
def eval_config_cmd(config: str, base_dir: str | None, fmt: str, output: str | None,
                    init_config: bool) -> None:
    """YAML声明式评估：通过配置文件批量执行lint/安全/断言评估(参考promptfoo)"""
    if init_config:
        from ai_prompt_toolkit.eval_config import DEFAULT_EVAL_CONFIG_YAML
        out_path = Path("prompt-eval.yaml")
        out_path.write_text(DEFAULT_EVAL_CONFIG_YAML, encoding="utf-8")
        click.echo(f"示例配置已生成: {out_path}")
        return

    from ai_prompt_toolkit.eval_config import EvalConfig, run_eval_config

    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"错误: 配置文件不存在: {config_path}", err=True)
        sys.exit(2)

    try:
        eval_config = EvalConfig.from_yaml(config_path)
    except Exception as e:
        click.echo(f"错误: 配置文件解析失败: {e}", err=True)
        sys.exit(2)

    base = base_dir or str(config_path.parent)
    results = run_eval_config(eval_config, base_dir=base)

    if fmt == "json":
        import json as _json
        output_data = results
        if output:
            from ai_prompt_toolkit.cli_helpers import write_report
            write_report(output_data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        console.print("[bold cyan]YAML声明式评估结果[/bold cyan]\n")

        for target in results["targets"]:
            if "error" in target:
                console.print(f"  [red]✗ {target['path']}: {target['error']}[/red]")
                continue

            status = "[green]✓ PASS[/green]" if target["passed"] else "[red]✗ FAIL[/red]"
            console.print(f"  {status} {target['path']} (provider: {target['provider']})")

            for ev in target["evaluators"]:
                ev_status = "[green]✓[/green]" if ev["passed"] else "[red]✗[/red]"
                score_str = f" (分数: {ev.get('score', 'N/A')})" if "score" in ev else ""
                threshold_str = f" 阈值: {ev['threshold']}" if ev["threshold"] > 0 else ""
                console.print(f"    {ev_status} [{ev['type']}]{score_str}{threshold_str}")

                if ev.get("details"):
                    for detail in ev["details"]:
                        if isinstance(detail, dict):
                            d_status = "[green]✓[/green]" if detail.get("passed") else "[red]✗[/red]"
                            console.print(f"      {d_status} {detail.get('name', 'assertion')}")
                            for d in detail.get("details", []):
                                console.print(f"        [dim]{d}[/dim]")

        summary = results["summary"]
        console.print(f"\n[bold]汇总: {summary['passed']}/{summary['total']} 通过, {summary['failed']} 失败[/bold]")

    if eval_config.output.save_history:
        click.echo("\n评估历史已保存")

    sys.exit(0 if results["summary"]["failed"] == 0 else 1)


@main.command(name="eval-registry")
@click.option("--target", "-t", required=True, help="评估目标(文件或目录)")
@click.option("--evaluators", "-e", help="评估器名称(逗号分隔, 如lint,security,g_eval,discrete_metric)")
@click.option("--type", "etype", help="按类型筛选评估器(quality/security/performance)")
@click.option("--tag", help="按标签筛选评估器")
@click.option("--threshold", type=float, default=0.0, help="分数阈值(0-10)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
def eval_registry_cmd(target: str, evaluators: str | None, etype: str | None,
                      tag: str | None, threshold: float, fmt: str,
                      output: str | None) -> None:
    """评估器注册表: 使用注册表中的评估器组合评估Prompt"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report
    from ai_prompt_toolkit.evaluator_registry import EvaluatorRegistry
    from ai_prompt_toolkit.g_eval import GEvalEvaluator, FaithfulnessEvaluator, HallucinationEvaluator, AgentEvaluator
    from ai_prompt_toolkit.discrete_eval import DiscreteMetricEvaluator

    registry = EvaluatorRegistry()
    registry.register(GEvalEvaluator())
    registry.register(FaithfulnessEvaluator())
    registry.register(HallucinationEvaluator())
    registry.register(AgentEvaluator())
    registry.register(DiscreteMetricEvaluator())

    target_path = resolve_path(target)
    if target_path.is_dir():
        files = sorted(target_path.rglob("*.md"))
    else:
        files = [target_path]

    if not files:
        click.echo("错误: 未找到评估目标文件", err=True)
        sys.exit(2)

    eval_names = [e.strip() for e in evaluators.split(",")] if evaluators else None
    thresholds = {name: threshold for name in (eval_names or [])}

    all_results = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        result = registry.evaluate(
            str(f), text,
            evaluator_names=eval_names,
            evaluator_type=etype,
            tag=tag,
            thresholds=thresholds,
        )
        all_results.append(result)

    if fmt == "json":
        import json as _json
        data = {"results": [r.to_dict() for r in all_results]}
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for result in all_results:
            status = "[PASS]" if result.overall_passed else "[FAIL]"
            click.echo(f"  {status} {result.template_id}: {result.overall_score:.2f}/10")
            for r in result.results:
                icon = "✓" if r.passed else "✗"
                click.echo(f"    {icon} [{r.evaluator_name}] {r.score:.2f}/{r.max_score:.0f}")
        if all_results:
            avg = sum(r.overall_score for r in all_results) / len(all_results)
            click.echo(f"\n总均分: {avg:.2f}/10")

    sys.exit(0 if all(r.overall_passed for r in all_results) else 1)


@main.command(name="data-generate")
@click.option("--template", "-t", help="模板文件路径(用于生成基于模板的测试数据)")
@click.option("--count", "-n", type=int, default=5, help="每类测试用例数量")
@click.option("--adversarial", is_flag=True, help="包含对抗性测试用例")
@click.option("--harmonyos", is_flag=True, help="包含鸿蒙/华为云专项测试用例")
@click.option("--multi-turn", is_flag=True, help="包含多轮对话测试用例")
@click.option("--output", "-o", help="输出数据集路径(JSON)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def data_generate_cmd(template: str | None, count: int, adversarial: bool,
                      harmonyos: bool, multi_turn: bool, output: str | None,
                      fmt: str) -> None:
    """自动生成测试数据集: 基于模板变异/对抗/鸿蒙/多轮对话"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report
    from ai_prompt_toolkit.test_generator import TestCaseGenerator

    gen = TestCaseGenerator(seed=42)
    template_text = ""
    if template:
        tpath = resolve_path(template)
        template_text = tpath.read_text(encoding="utf-8")

    ds = gen.generate_dataset(
        name="auto_generated",
        template_text=template_text,
        include_adversarial=adversarial,
        include_harmonyos=harmonyos,
        include_multi_turn=multi_turn,
        base_count=count,
    )

    if fmt == "json":
        import json as _json
        data = ds.to_dict()
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"数据集已保存: {output} ({ds.size}用例)")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"数据集: {ds.name} ({ds.size}用例)")
        click.echo(f"  ID: {ds.dataset_id}")
        for c in ds.cases:
            click.echo(f"  [{c.category}/{c.difficulty}] {c.input_text[:60]}...")


@main.command(name="prompt-optimize")
@click.option("--target", "-t", required=True, help="待优化的Prompt文件路径")
@click.option("--max-iterations", type=int, default=5, help="最大优化轮次")
@click.option("--min-improvement", type=float, default=0.5, help="最小改进阈值")
@click.option("--apply", "apply_changes", is_flag=True, help="直接应用优化结果(覆盖原文件)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出优化结果路径(JSON)")
def prompt_optimize_cmd(target: str, max_iterations: int, min_improvement: float,
                        apply_changes: bool, fmt: str, output: str | None) -> None:
    """Prompt自动优化: 评估→反馈→修改→再评估的迭代优化"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report
    from ai_prompt_toolkit.prompt_optimizer import optimize_prompt

    target_path = resolve_path(target)
    text = target_path.read_text(encoding="utf-8")

    result = optimize_prompt(text, max_iterations=max_iterations, min_improvement=min_improvement)

    if fmt == "json":
        import json as _json
        data = result.to_dict()
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"优化报告已保存: {output}")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"原始分数: {result.original_score:.1f}/100")
        click.echo(f"优化分数: {result.final_score:.1f}/100")
        click.echo(f"提升: +{result.total_improvement:.1f} ({result.iterations}轮优化)")
        if result.converged:
            click.echo("状态: 已收敛")
        for step in result.steps:
            click.echo(f"  步骤{step.strategy}: {step.score_before:.1f}→{step.score_after:.1f} (+{step.improvement:.1f})")

    if apply_changes and result.optimized_text != text:
        target_path.write_text(result.optimized_text, encoding="utf-8")
        click.echo(f"已应用优化结果: {target}")

    sys.exit(0)


@main.command(name="gepa-optimize")
@click.option("--target", "-t", required=True, help="Prompt文件路径")
@click.option("--metric", "-m", type=click.Choice(["exact_match", "contains_match", "regex_match", "lint_score", "llm_judge", "pangu_judge"]),
              default="lint_score", help="Feedback metric(默认lint_score)")
@click.option("--auto", type=click.Choice(["light", "medium", "heavy"]), default="light",
              help="优化预算(light=6候选/medium=12/heavy=18)")
@click.option("--predictors", "-p", help="预测器名称(逗号分隔, 默认main)")
@click.option("--trainset", help="训练集JSON文件路径")
@click.option("--reflection-model", help="反射模型(如gpt-4o, pangu-nlp)")
@click.option("--dry-run", is_flag=True, help="模拟运行(不实际调用LLM)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
def gepa_optimize_cmd(target: str, metric: str, auto: str, predictors: str | None,
                      trainset: str | None, reflection_model: str | None,
                      dry_run: bool, fmt: str, output: str | None) -> None:
    """GEPA反射式Prompt进化优化: 基于DSPy GEPA算法的迭代进化优化"""
    import json as _json
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report
    from ai_prompt_toolkit.gepa import gepa_optimize, FEEDBACK_METRICS

    target_path = resolve_path(target)
    text = target_path.read_text(encoding="utf-8")

    predictor_names = [p.strip() for p in predictors.split(",")] if predictors else ["main"]

    train_data = None
    if trainset:
        train_path = resolve_path(trainset)
        train_data = _json.loads(train_path.read_text(encoding="utf-8"))

    reflection_lm = None
    if reflection_model and not dry_run:
        try:
            from ai_prompt_toolkit.ab_test.providers import get_provider
            provider = get_provider(reflection_model)
            if provider:
                reflection_lm = lambda prompt: provider.call(prompt, model=reflection_model).get("text", "")
        except Exception:
            click.echo(f"警告: 无法加载反射模型 '{reflection_model}', 将使用启发式提议", err=True)

    if dry_run:
        click.echo("=== GEPA Dry Run ===")
        click.echo(f"目标: {target}")
        click.echo(f"Metric: {metric}")
        click.echo(f"预算: {auto}")
        click.echo(f"预测器: {predictor_names}")
        click.echo(f"训练集: {trainset or '(默认)'}")
        click.echo(f"反射模型: {reflection_model or '(启发式)'}")
        click.echo(f"Prompt长度: {len(text)} 字符")

        from ai_prompt_toolkit.linter.linter import PromptLinter
        linter = PromptLinter()
        lint_result = linter.lint("gepa-dry-run", text)
        click.echo(f"当前Lint分数: {lint_result.score:.1f}/100")
        sys.exit(0)

    result = gepa_optimize(
        text,
        metric=metric,
        auto=auto,
        trainset=train_data,
        reflection_lm=reflection_lm,
        predictor_names=predictor_names,
    )

    if fmt == "json":
        data = result.to_dict()
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"GEPA优化报告已保存: {output}")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(f"初始分数: {result.initial_score:.4f}")
        click.echo(f"最优分数: {result.best_score:.4f}")
        click.echo(f"提升: +{result.improvement:.4f}")
        click.echo(f"探索候选: {result.candidates_explored}")
        click.echo(f"进化代数: {result.generations}")
        click.echo(f"Pareto前沿: {result.frontier_size}")
        for h in result.history[-5:]:
            click.echo(f"  [{h['event']}] #{h['candidate_id']} score={h.get('score', 0):.4f}")

    if output and fmt != "json":
        data = result.to_dict()
        write_report(data, output, fmt="json")
        click.echo(f"报告已保存: {output}")

    sys.exit(0)


@main.command(name="prompt-version")
@click.option("--action", "-a", type=click.Choice(["save", "load", "list", "diff", "rollback", "ab-compare", "delete"]),
              required=True, help="版本操作")
@click.option("--name", "-n", help="Prompt名称")
@click.option("--source", "-s", help="源文件路径(save时读取)")
@click.option("--version-id", "-v", help="版本ID(load/diff/rollback/delete)")
@click.option("--version-a", help="版本A ID(diff/ab-compare)")
@click.option("--version-b", help="版本B ID(diff/ab-compare)")
@click.option("--score", type=float, help="Lint分数(save时)")
@click.option("--source-type", help="来源(manual/gepa/optimize/lint)")
@click.option("--tags", help="标签(逗号分隔)")
@click.option("--limit", "-l", type=int, default=20, help="列表条数")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def prompt_version_cmd(action: str, name: str | None, source: str | None,
                      version_id: str | None, version_a: str | None, version_b: str | None,
                      score: float, source_type: str, tags: str | None,
                      limit: int, fmt: str) -> None:
    """Prompt版本管理: 版本树/diff/回滚/A-B对比"""
    import json as _json
    from ai_prompt_toolkit.cli_helpers import resolve_path, empty_state_tip
    from ai_prompt_toolkit.prompt_version import PromptVersionStore

    store = PromptVersionStore()

    try:
        if action == "save":
            if not name:
                click.echo("错误: 请指定--name", err=True)
                sys.exit(2)
            content = ""
            if source:
                content = resolve_path(source).read_text(encoding="utf-8")
            elif not click.get_text_stream("stdin").isatty():
                content = click.get_text_stream("stdin").read()
            else:
                click.echo("错误: 请指定--source或通过管道传入内容", err=True)
                sys.exit(2)

            if score == 0.0:
                try:
                    from ai_prompt_toolkit.linter.linter import PromptLinter
                    linter = PromptLinter()
                    result = linter.lint(name, content)
                    score = result.score
                except Exception:
                    pass

            tag_list = [t.strip() for t in tags.split(",")] if tags else []
            v = store.save(name, content, score=score, source=source_type or "manual", tags=tag_list)
            click.echo(f"版本已保存: {name} #{v.version_id} (分数: {v.score:.1f})")

        elif action == "load":
            if not version_id:
                click.echo("错误: 请指定--version-id", err=True)
                sys.exit(2)
            v = store.load(version_id)
            if not v:
                click.echo(f"版本不存在: {version_id}", err=True)
                sys.exit(2)
            click.echo(v.content)

        elif action == "list":
            versions = store.list_versions(name, limit=limit)
            if not versions:
                click.echo(empty_state_tip("prompt-version"))
                sys.exit(0)
            if fmt == "json":
                click.echo(_json.dumps([v.to_dict() for v in versions], ensure_ascii=False, indent=2))
            else:
                for v in versions:
                    click.echo(f"  #{v.version_id} | {v.prompt_name} | {v.score:.1f} | {v.source} | {v.created_at}")

        elif action == "diff":
            if not version_a or not version_b:
                click.echo("错误: 请指定--version-a和--version-b", err=True)
                sys.exit(2)
            diff_result = store.diff(version_a, version_b)
            if fmt == "json":
                click.echo(_json.dumps(diff_result.to_dict(), ensure_ascii=False, indent=2))
            else:
                click.echo(f"Diff: #{version_a} → #{version_b}")
                click.echo(f"  +{diff_result.added_lines} -{diff_result.removed_lines} | 相似度: {diff_result.similarity:.2%}")
                if diff_result.diff_text:
                    for line in diff_result.diff_text.splitlines()[:30]:
                        if line.startswith("+") and not line.startswith("+++"):
                            click.echo(f"  [green]{line}[/green]")
                        elif line.startswith("-") and not line.startswith("---"):
                            click.echo(f"  [red]{line}[/red]")
                        else:
                            click.echo(f"  {line}")

        elif action == "rollback":
            if not version_id:
                click.echo("错误: 请指定--version-id", err=True)
                sys.exit(2)
            v = store.rollback(version_id)
            if not v:
                click.echo(f"回滚失败: 版本 {version_id} 不存在", err=True)
                sys.exit(2)
            click.echo(f"已回滚到: #{version_id} → 新版本 #{v.version_id} (分数: {v.score:.1f})")

        elif action == "ab-compare":
            if not version_a or not version_b:
                click.echo("错误: 请指定--version-a和--version-b", err=True)
                sys.exit(2)
            result = store.ab_compare(version_a, version_b)
            if fmt == "json":
                click.echo(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                click.echo(f"A/B对比: #{version_a} vs #{version_b}")
                click.echo(f"  版本A: {result.score_a:.1f}")
                click.echo(f"  版本B: {result.score_b:.1f}")
                click.echo(f"  胜出: {result.winner} (差异: {result.score_diff:+.1f})")

        elif action == "delete":
            if not version_id:
                click.echo("错误: 请指定--version-id", err=True)
                sys.exit(2)
            if store.delete_version(version_id):
                click.echo(f"已删除: #{version_id}")
            else:
                click.echo(f"版本不存在: {version_id}", err=True)
                sys.exit(2)

    finally:
        store.close()
