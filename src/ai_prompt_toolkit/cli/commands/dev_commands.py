"""CLI命令 — 开发工具相关命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import main


@main.command(name="baseline")
@click.option("--json", "as_json", is_flag=True, help="JSON输出(供CI断言)")
@click.option(
    "--fail-above-miss",
    type=float,
    default=None,
    help="漏检率>阈值时退出码1(CI棘轮用, 如0.05)",
)
@click.option(
    "--fail-above-fp",
    type=float,
    default=None,
    help="误报率>阈值时退出码1(CI棘轮用, 如0.01)",
)
def baseline_cmd(as_json: bool, fail_above_miss: float | None, fail_above_fp: float | None) -> None:
    """一条命令自证双基线 — 漏检(检测能力面) + 误报(噪音面)。

    样本(60干净prompt + 113 golden攻击探针)随包分发, 任何机器 pip install
    后即可复现, 无需克隆仓库。确定性度量: 零LLM, 每次运行结果一致。
    """
    import json

    from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate

    miss = run_miss_rate()
    fp = run_false_positives()

    if as_json:
        print(json.dumps({"miss": miss, "false_positives": fp}, ensure_ascii=False, indent=2))
    else:
        click.echo("══ 双基线自证 (确定性 · 零LLM · 可复现) ══")
        click.echo("")
        click.echo(
            f"漏检面  {miss['global_rate']:.2%}  |  探针 {miss['probe_count']} 条 · 期望命中单元 {miss['expected_total']}"
        )
        for lang, v in miss["per_language"].items():
            click.echo(f"        语言[{lang}]: {v['missed']}/{v['expected']} = {v['miss_rate']:.2%}")
        if miss["zero_detect_rules"]:
            click.echo(f"        ⚠ 零检出规则: {', '.join(miss['zero_detect_rules'])}")
        click.echo("")
        click.echo(
            f"误报面  {fp['global_rate']:.2%}  |  干净样本 {fp['sample_count']} 个 · checker {fp['checker_count']} 条"
        )
        if fp["high_fp_rules"]:
            for r in fp["high_fp_rules"]:
                click.echo(
                    f"        ⚠ {r['rule_id']}: {r['false_positives']}/{fp['sample_count']} = {r['false_positive_rate']:.0%}"
                )
        else:
            click.echo("        无高误报规则(>10%样本命中)")
        click.echo("")
        click.echo("样本数据随包分发: data/clean_prompts + data/golden_attacks.json")

    if fail_above_miss is not None and miss["global_rate"] > fail_above_miss:
        click.echo(f"FAIL: 漏检率 {miss['global_rate']:.2%} > 阈值 {fail_above_miss:.2%}", err=True)
        sys.exit(1)
    if fail_above_fp is not None and fp["global_rate"] > fail_above_fp:
        click.echo(f"FAIL: 误报率 {fp['global_rate']:.2%} > 阈值 {fail_above_fp:.2%}", err=True)
        sys.exit(1)


@main.command(name="watch")
@click.option("--target", "-t", required=True, help="监视目标(文件或目录)")
@click.option(
    "--command", "-c", type=click.Choice(["lint", "scan", "evaluate"]), default="lint", help="文件变更时执行的命令"
)
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
            from ai_prompt_toolkit.cli_helpers import discover_templates
            from ai_prompt_toolkit.linter.linter import PromptLinter

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
            from ai_prompt_toolkit.cli_helpers import discover_templates
            from ai_prompt_toolkit.security.injection_detector import InjectionDetector

            templates = discover_templates(t)
            detector = InjectionDetector()
            total_findings = 0
            for tpl in templates:
                text = tpl.read_text(encoding="utf-8")
                findings = detector.detect(text)
                total_findings += len(findings)
            click.echo(f"[scan] {len(templates)} 文件 | {total_findings} 风险")
        elif command == "evaluate":
            from ai_prompt_toolkit.cli_helpers import resolve_path
            from ai_prompt_toolkit.evaluator import evaluate_template

            tp = resolve_path(t, must_exist=False)
            if tp.is_file():
                text = tp.read_text(encoding="utf-8")
                report = evaluate_template(str(tp), text)
                scores = report.scores
                avg = sum(s.score for s in scores) / len(scores) if scores else 0
                click.echo(f"[evaluate] {tp.name} | 均分: {avg:.1f}/10")

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


@main.command(name="wizard")
@click.option(
    "--command",
    "-c",
    type=click.Choice(["lint", "scan", "evaluate", "ab-test", "redteam"]),
    help="直接指定命令(跳过功能选择)",
)
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
    from ai_prompt_toolkit.benchmark import run_benchmark, run_full_benchmark

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
            click.echo(
                f"\n平均耗时: {report['summary']['avg_duration_ms']:.2f}ms | 回归数: {report['summary']['regressions']}"
            )
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
def recommend_cmd(category: str | None, industry: str | None, model: str | None, top_n: int, as_json: bool) -> None:
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


@main.command(name="mcp")
@click.option("--validate-only", is_flag=True, help="仅校验工具注册表与tools_list一致性后退出(供CI/冒烟)")
def mcp_cmd(validate_only: bool) -> None:
    """MCP Server：标准stdio JSON-RPC(供Claude Desktop/Cursor等MCP客户端接入)"""
    from ai_prompt_toolkit.mcp_server import _validate_tools_dispatch_sync, run_server

    if validate_only:
        _validate_tools_dispatch_sync()
        click.echo("OK: MCP工具注册表与tools_list一致")
        return
    run_server()
