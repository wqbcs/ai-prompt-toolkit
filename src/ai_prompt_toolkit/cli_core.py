"""prompt-cli统一入口"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

# R212: __main__自别名 — `python -m ai_prompt_toolkit.cli_core` 时本模块以
# __main__身份执行, 而命令簇(L708 import)导包 ai_prompt_toolkit.cli_core 会
# 加载出第二个模块实例(双main group, 命令丢失)。在命令簇import之前把
# __main__ 注册为规范名, 使全进程共享同一 group。
if __name__ == "__main__" and __package__:
    sys.modules[f"{__package__}.cli_core"] = sys.modules[__name__]

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
            template_type: str = str(data["template_type"])
            return template_type
    except _yaml.YAMLError:
        pass
    return "prompt"


def _generate_sarif(results: list[Any], target: str) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.rules import get_rule
    from ai_prompt_toolkit.sarif_report import REPO_URL

    # R201: 显式dict标注 — 嵌套字典字面量推断为dict[str,Collection[str]], 下标报错
    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ai-prompt-toolkit",
                        "version": __version__,
                        "informationUri": REPO_URL,
                        "rules": [],
                    }
                },
                "results": [],
            }
        ],
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
                    "properties": {"severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity)},
                }
                if rule_def:
                    rule_entry["helpUri"] = f"https://ai-prompt-toolkit.dev/rules/{f.rule_id}"
                    if rule_def.remediation:
                        rule_entry["fullDescription"] = {
                            "text": f"{rule_def.description}\n\nFix: {rule_def.remediation}"
                        }
                    if rule_def.owasp_refs:
                        rule_entry["properties"]["owaspRefs"] = rule_def.owasp_refs
                    rule_entry["properties"]["category"] = rule_def.category
                    rule_entry["properties"]["precision"] = "high" if rule_def.category == "security" else "medium"
                sarif["runs"][0]["tool"]["driver"]["rules"].append(rule_entry)
            sev_map = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sarif["runs"][0]["results"].append(
                {
                    "ruleId": f.rule_id,
                    "level": sev_map.get(sev, "warning"),
                    "message": {"text": f.description},
                    "locations": [{"physicalLocation": {"artifactLocation": {"uri": result.template_id}}}],
                }
            )
    return sarif


def _component_stats() -> str:
    """R194: 动态计算组件统计, 替代硬编码(防规则/工具数漂移后口径不一致)"""
    try:
        from ai_prompt_toolkit.evaluator import get_all_dimensions
        from ai_prompt_toolkit.linter.rules import get_all_rules
        from ai_prompt_toolkit.mcp_server import _get_tool_dispatch
        from ai_prompt_toolkit.redteam.detector import BaseDetector
        from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

        lint = len(get_all_rules())
        dims = len(get_all_dimensions())
        tools = len(_get_tool_dispatch())
        # R212-7: probes口径统一 — 原 BaseProbe.__subclasses__()=94(单体系子类),
        # 徽章=23(probe_framework注册表), 全局注册表=116, 三口径漂移。
        # 统一以R207统一注册表(含冲突去重)为唯一事实源, 与test_r207断言同口径。
        probes = len(get_global_probe_registry())
        detectors = len(BaseDetector.__subclasses__())
        return (
            f"组件统计: {lint}条Lint规则 | {dims}评估维度 | {tools} MCP工具 | {probes} Probes | {detectors} Detectors"
        )
    except Exception:
        return "组件统计: (加载中不可用)"


def _is_decorative_output_allowed() -> bool:
    """R226: 装饰性输出(首跑欢迎横幅等)仅允许出现在交互 TTY 且非协议调用。

    全新环境(CI runner 的 HOME 无 .initialized marker)时, 首跑欢迎横幅
    (ASCII 首字符是前导\\n)会写入 stdout, 把 --stdio 的 hello 挤到第二行 —
    CI 3.11 实证: json.loads 报 line 2 column 1 (char 1)。协议/机器通道
    (stdio/重定向的 json 输出)的 stdout 是神圣契约, 装饰性输出绝不污染。
    """
    if not sys.stdout.isatty():
        return False
    # `echo '{...}' | prompt-cli lint --stdio`: stdout 虽是 TTY 但协议仍是
    # 机器契约, 横幅必须静默
    return "--stdio" not in sys.argv[1:]


@click.group()
@click.version_option(
    version=__version__,
    prog_name="prompt-cli",
    message="%(prog)s %(version)s\n\n" + _component_stats(),
)
def main() -> None:
    """AI提示词体系工具链"""
    from ai_prompt_toolkit.easter_eggs import is_first_run, show_welcome

    if is_first_run() and _is_decorative_output_allowed():
        show_welcome()


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell: str) -> None:
    """生成Shell自动补全脚本(bash/zsh/fish)

    使用方式:
      prompt-cli completion bash > ~/.prompt-cli-completion.bash && echo 'source ~/.prompt-cli-completion.bash' >> ~/.bashrc
      prompt-cli completion zsh > ~/.zsh/completion/_prompt-cli && echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc
      prompt-cli completion fish > ~/.config/fish/completions/prompt-cli.fish
    """
    from click.shell_completion import get_completion_class

    prog_name = "prompt-cli"
    complete_var = f"_PROMPT_CLI_COMPLETE={shell}_source"
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

            _local = frame.f_locals if frame else {}
            _cf = _local.get("_completed_files", [])
            _af = _local.get("_all_file_names", [])
            _cmd = _local.get("resume_cmd_hint", "lint")
            if _cf and _af:
                pending = [f for f in _af if f not in set(_cf)]
                save_progress(_cmd, [], _cf, pending)
                click.echo(
                    f"\n\n⏹ 操作已取消。进度已保存({_cmd}: {len(_cf)}/{len(_af)})，使用 --resume 恢复。", err=True
                )
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


@main.command(name="doctor")
@click.option("--provider", "-p", help="仅检查指定Provider(如openai,anthropic)")
@click.option("--json", "as_json", is_flag=True, help="JSON格式输出")
@click.option("--init", "init_config", is_flag=True, help="首次运行: 自动生成 promptlint.toml lint 配置模板")
@click.option(
    "--gate",
    "gate_mode",
    is_flag=True,
    help="R225-P2-08: 门禁工具自检(版本/规则数/基线/依赖/豁免) — 排查'为什么CI没跑'",
)
def doctor_cmd(provider: str | None, as_json: bool, init_config: bool, gate_mode: bool) -> None:
    """健康检查：检测Provider连接状态和API Key配置（--gate: 门禁工具自检）"""
    if gate_mode:
        _doctor_gate(as_json)
        return
    if init_config:
        from pathlib import Path as _ConfigPath

        from ai_prompt_toolkit.linter.project_config import write_default_config

        # R325: 与 init 共用 write_default_config 单一真源, 生成 lint 首选 promptlint.toml
        # (P2-03 完整 schema: fail_on/waivers/severity_overrides/gap)。此前 doctor --init
        # 独写 .prompt-toolkit.yml(YAML 子集, severity_threshold=low, 仅 cwd 发现)与 init 的
        # promptlint.toml 双源 → 两文件并存时 lint 只读 promptlint.toml, 后者被静默忽略
        # (同族断点, R324 只修了 init 腿)。.prompt-toolkit.yml 仍被 lint YAML rc 回退发现
        # (存量向后兼容), 但不再由任何命令生成。
        config_path, wrote = write_default_config(_ConfigPath("."))
        if wrote:
            click.echo(f"lint 配置已生成: {config_path.name} (lint 自动发现读取)")
        else:
            click.echo(f"lint 配置已存在(未覆盖): {config_path.name}")
        return

    # R325: 用 P2-03 首选发现判"是否已有 lint 配置"(promptlint.toml/pyproject); 规则/维度
    # 数动态计算(防 255/130 硬编码漂移, 与 _component_stats 同口径); 提示指向新真源
    from ai_prompt_toolkit.evaluator import get_all_dimensions
    from ai_prompt_toolkit.linter.project_config import find_project_config
    from ai_prompt_toolkit.linter.rules import get_all_rules

    if find_project_config() is None and not as_json:
        _rule_n = len(get_all_rules())
        _dim_n = len(get_all_dimensions())
        # U3: 首次运行引导 — 快速入门+配置模板生成提示
        click.echo(
            "提示: 未找到 lint 配置, 运行 prompt-cli doctor --init 生成 promptlint.toml 模板\n"
            "\n快速入门:\n"
            f"  prompt-cli lint -t ./prompt.md            静态质量检查({_rule_n}条规则, 零Token)\n"
            "  prompt-cli lint -t ./prompts --gate       CI门禁模式(verdict退出码)\n"
            "  prompt-cli scan -t ./prompt.md            安全纵深扫描(注入/PII/供应链)\n"
            f"  prompt-cli eval -t ./prompt.md            {_dim_n}维质量评估\n"
            "  prompt-cli redteam -t ./prompt.md         红队对抗探测(OWASP映射)\n"
        )
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

    # R231: --json 协议通道 stdout 神圣(纯数据) — 进度提示走 stderr(R226 同纪律)
    click.echo("正在检查Provider健康状态...", err=as_json)
    results = run_health_check(targets)

    if as_json:
        import json as _json

        click.echo(
            _json.dumps(
                [
                    {
                        "provider": r.provider.value,
                        "label": r.label,
                        "status": r.status,
                        "latency_ms": r.latency_ms,
                        "error": r.error,
                        "api_key_configured": r.api_key_configured,
                        "endpoint": r.endpoint,
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
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


def _doctor_gate(as_json: bool) -> None:
    """R225-P2-08: 门禁工具自检 — 用户排查"为什么CI没跑"的一站式

    检查项:
    1. 版本与三处一致性(pyproject/__init__/README徽章)
    2. 规则注册表数量(与 docs/rules.md 声明口径)
    3. 基线文件存在性与新鲜度(baselines/templates-baseline.json)
    4. 双基线阈值可复现(check_false_positives/check_miss_rate 快速跑)
    5. 依赖健康(core 依赖可导入 + 环境一致性快照)
    6. waiver 面(audit-waivers 汇总)

    退出码: 0=全绿 1=存在黄/红项
    """
    # P4-04: 项目内资产路径经 repo_relative 解析(仓库根锚定, 消除 cwd 依赖)
    from ai_prompt_toolkit.linter.project_config import repo_relative as _repo

    checks: list[dict[str, object]] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    # 1. 版本一致性
    from ai_prompt_toolkit import __version__

    pyproject_v = None
    _pyproject = _repo("pyproject.toml")
    if _pyproject.exists():
        import re as _re

        m = _re.search(r'^version\s*=\s*"([\w.]+)"', _pyproject.read_text(encoding="utf-8"), _re.MULTILINE)
        pyproject_v = m.group(1) if m else None
    if pyproject_v == __version__:
        add("版本一致性", "ok", f"__version__ = pyproject = {__version__}")
    else:
        add("版本一致性", "fail", f"__version__={__version__} vs pyproject={pyproject_v}")

    # 2. 规则注册表
    from ai_prompt_toolkit.linter.rules import get_all_rules

    rules = get_all_rules()
    add("规则注册表", "ok", f"{len(rules)} 条规则加载正常")

    # 3. 基线文件 + P3-15 完整性(尺子可篡改=双基线数字不可信)
    baseline = _repo("baselines/templates-baseline.json")
    if baseline.exists():
        import json as _json

        try:
            snap = _json.loads(baseline.read_text(encoding="utf-8"))
            add("增量门禁基线", "ok", f"baselines/templates-baseline.json ({snap.get('total_findings', '?')} findings)")
        except _json.JSONDecodeError:
            add("增量门禁基线", "fail", "基线文件存在但 JSON 非法")
        try:
            from ai_prompt_toolkit.linter.baseline import verify_baseline

            _bv = verify_baseline(baseline)
            _status = _bv["status"]
            if _status == "ok":
                add("基线完整性", "ok", f"content_sha256 一致 ({_bv.get('sha256', '')[:12]}…)")
            elif _status == "tampered":
                add(
                    "基线完整性",
                    "warn",
                    "findings 段与 content_sha256 不匹配 — 可能被篡改; 有意变更请重存(独立 commit+理由)",
                )
            else:  # legacy(无哈希字段) / missing / corrupt — 不阻断
                add("基线完整性", "ok", f"{_status}(向后兼容, 无 content_sha256 字段时静默)")
        except Exception as _e:
            # 完整性面异常显性化(A3 纪律: 禁静默吞异常) — 该面为增强自检,
            # 降级 warn 不影响主六项, 但异常本身必须可见
            add("基线完整性", "warn", f"完整性检查自身异常(降级): {type(_e).__name__}: {_e}")
    else:
        add("增量门禁基线", "warn", "baselines/templates-baseline.json 缺失 — CI 增量门禁(--incremental)将失败")

    # 4. 双基线(快速复现: 与 CI 阈值一致)
    try:
        from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate

        fp = run_false_positives()
        fp_rate = fp.get("global_rate", 0.0) if isinstance(fp, dict) else getattr(fp, "global_rate", 0.0)
        add("双基线: 误报率", "ok" if fp_rate <= 0.01 else "fail", f"{fp_rate:.2%} (阈值 1.00%)")
        mr = run_miss_rate()
        mr_rate = mr.get("global_rate", 0.0) if isinstance(mr, dict) else getattr(mr, "global_rate", 0.0)
        add("双基线: 漏检率", "ok" if mr_rate <= 0.05 else "fail", f"{mr_rate:.2%} (阈值 5.00%)")
    except Exception as e:
        add("双基线", "fail", f"复现失败: {e}")

    # 5. 依赖健康
    missing_deps: list[str] = []
    for mod in ("click", "rich", "yaml", "jsonschema", "cachetools", "jinja2"):
        try:
            __import__(mod)
        except ImportError:
            missing_deps.append(mod)
    if missing_deps:
        add("core 依赖", "fail", f"缺失: {', '.join(missing_deps)}")
    else:
        add("core 依赖", "ok", "6 个 core 依赖全部可导入")

    # 6. waiver 面
    try:
        from ai_prompt_toolkit.cli_helpers import discover_templates
        from ai_prompt_toolkit.linter.waivers import parse_waivers

        tpl_dir = _repo("src/ai_prompt_toolkit/templates")
        if tpl_dir.exists():
            files = discover_templates(str(tpl_dir))
            waived_total = 0
            for f in files:
                text = f.read_text(encoding="utf-8")
                waived_total += len(parse_waivers(text))
            add(
                "waiver 面",
                "ok",
                f"内置模板 waiver 声明 {waived_total} 处 (审计: prompt-cli audit-waivers -t {tpl_dir})",
            )
        else:
            add("waiver 面", "warn", "未找到模板目录, 跳过")
    except Exception as e:
        add("waiver 面", "warn", f"扫描失败: {e}")

    if as_json:
        import json as _json

        click.echo(_json.dumps({"version": __version__, "checks": checks}, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="prompt-cli 门禁工具自检 (doctor --gate)")
        table.add_column("检查项", style="bold")
        table.add_column("状态", width=8)
        table.add_column("详情")
        styles = {"ok": "[green]✓[/green]", "warn": "[yellow]⚠[/yellow]", "fail": "[red]✗[/red]"}
        for c in checks:
            table.add_row(str(c["check"]), styles.get(str(c["status"]), str(c["status"])), str(c["detail"]))
        console.print(table)

    failed = sum(1 for c in checks if c["status"] == "fail")
    warned = sum(1 for c in checks if c["status"] == "warn")
    if not as_json:
        if failed:
            click.echo(f"❌ 自检失败: {failed} 项红, {warned} 项黄 — 修复后重跑")
        elif warned:
            click.echo(f"⚠️ 自检有黄项: {warned} 项 — 见上表")
        else:
            click.echo("✅ 门禁工具健康 — CI 该跑的都跑得起来")
    sys.exit(1 if failed else 0)


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
    from ai_prompt_toolkit.probe_framework import ProbeRunner, list_probes
    from ai_prompt_toolkit.probe_framework import list_detectors as list_det

    if target == "list":
        probe_list = list_probes()
        det_list = list_det()
        click.echo("可用探针(Probe):")
        for p in probe_list:
            click.echo(f"  {p['name']:25s} [{p['severity']:8s}] {p['description']}")
        click.echo("\n可用检测器(Detector):")
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
        probe_names: list[str] | None = _QUICK_PROBES
    else:
        # R197: 显式标注 — 与quick分支的list[str]联合None, 防两分支类型不一致
        probe_names = [p.strip() for p in probes.split(",") if p.strip()] if probes else None
    detector_names = [d.strip() for d in detectors.split(",") if d.strip()] if detectors else None

    runner = ProbeRunner(probe_names=probe_names, detector_names=detector_names, max_payloads_per_probe=max_payloads)
    click.echo(f"正在运行Probe扫描({runner._probes.__len__()}探针, {len(runner._detectors)}检测器)...")

    report = runner.run(target_path.name, text)

    click.echo(f"\n{'=' * 60}")
    click.echo(f"Probe扫描报告: {report.template_id}")
    click.echo(f"{'=' * 60}")
    click.echo(f"探针数: {report.total_probes} | Payload数: {report.total_payloads} | 检出: {report.total_detections}")
    click.echo(f"风险评分: {report.risk_score:.1f}/10.0")

    # R207-4: 三因子分解可见性 — 评分从"命中率x10"升级为severity x probability
    # x impact后, 分解对用户定位风险来源是决策依据, 不能只藏在JSON里
    if report.risk_factors:
        f = report.risk_factors
        click.echo(
            f"  因子分解: severity={f.get('severity', 0):.2f} x "
            f"probability={f.get('probability', 0):.2f} x impact={f.get('impact', 0):.2f} "
            f"(命中率={f.get('hit_rate', 0):.0%})"
        )

    # R207-4: OWASP Agentic Top 10 2026评估 — Agent特征prompt才输出
    agentic = report.agentic_assessment
    if agentic and agentic.get("asi_count", 0) > 0:
        click.echo(f"\nOWASP Agentic风险评估(命中{agentic['asi_count']}项):")
        for asi_ref, info in agentic["asi_findings"].items():
            click.echo(f"  {asi_ref} {info['name_zh']}: {info['total_findings']}处检出")
            click.echo(f"    缓解: {info['mitigation']}")
    elif agentic and agentic.get("asi_count", 0) == 0:
        click.echo("\nOWASP Agentic风险评估: 无命中(已评估)")

    if report.probe_summary:
        click.echo("\n探针检出统计:")
        for name, count in sorted(report.probe_summary.items(), key=lambda x: -x[1]):
            if count > 0:
                click.echo(f"  {name:25s} {count} 检出")

    if report.detector_summary:
        click.echo("\n检测器统计:")
        for name, count in sorted(report.detector_summary.items(), key=lambda x: -x[1]):
            click.echo(f"  {name:25s} {count} 次")

    if report.recommendations:
        click.echo("\n防御建议:")
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


@main.group(name="dataset")
def dataset_group() -> None:
    """数据集管理: 创建/导入/运行测试用例集"""


@main.group(name="plugin")
def plugin_group() -> None:
    """插件管理: 注册/列表/启用/禁用"""


@main.command(name="compliance")
@click.option("--target", "-t", required=True, help="合规扫描目标(文件或目录)")
@click.option(
    "--format", "fmt", type=click.Choice(["cli", "json", "markdown", "sarif"]), default="cli", help="输出格式"
)
@click.option("--output", "-o", help="报告输出路径")
@click.option("--owasp-pct", "owasp_pct", type=float, default=0.0, help="OWASP LLM Top 10合规百分比(0-100)")
def compliance_cmd(target: str, fmt: str, output: str | None, owasp_pct: float) -> None:
    """华为云安全合规报告: 7域加权评分+OWASP映射+等保2.0"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, empty_state_tip
    from ai_prompt_toolkit.security.huaweicloud_compliance import compute_huaweicloud_compliance
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector
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
                sarif_findings.append(
                    Finding(
                        rule_id=f"HC-{d.domain}",
                        severity=Severity.HIGH
                        if d.critical_count > 0
                        else Severity.MEDIUM
                        if d.high_count > 0
                        else Severity.LOW,
                        description=f"[{d.domain_name}] 评分{d.score}/{d.max_score} 发现{d.findings_count}个问题",
                    )
                )
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
                "",
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
            click.echo(
                f"华为云安全合规: {report.overall_score}/100 ({report.grade.value}) 决策:{report.decision.value}"
            )
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
    abtest_commands,
    compile_commands,
    dataset_commands,
    dev_commands,
    eval_commands,
    lint_commands,
    plugin_commands,
    redteam_commands,
    security_commands,
    template_commands,
)

# R212: __main__守卫必须在命令簇import之后 — 原位于文件中段(命令注册前),
# 导致 `python -m ai_prompt_toolkit.cli_core` 只显示3/68条命令。
if __name__ == "__main__":
    main()
