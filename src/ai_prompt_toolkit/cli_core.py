"""prompt-cli统一入口"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
            template_type: str = str(data["template_type"])
            return template_type
    except _yaml.YAMLError:
        pass
    return "prompt"


def _generate_sarif(results: list, target: str) -> dict:
    from ai_prompt_toolkit.linter.rules import get_rule

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ai-prompt-toolkit",
                        "version": __version__,
                        "informationUri": "https://github.com/ai-prompt-toolkit",
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


@click.group()
@click.version_option(
    version=__version__,
    prog_name="prompt-cli",
    message="%(prog)s %(version)s\n\n组件统计: 150条Lint规则 | 90评估维度 | 59 MCP工具 | 23+ Probes | 11+ Detectors | 25 Providers",
)
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


@main.command(name="doctor")
@click.option("--provider", "-p", help="仅检查指定Provider(如openai,anthropic)")
@click.option("--json", "as_json", is_flag=True, help="JSON格式输出")
@click.option("--init", "init_config", is_flag=True, help="首次运行: 自动生成.prompt-toolkit.yml配置模板")
def doctor_cmd(provider: str | None, as_json: bool, init_config: bool) -> None:
    """健康检查：检测Provider连接状态和API Key配置"""
    if init_config:
        from pathlib import Path as _ConfigPath

        config_path = _ConfigPath(".prompt-toolkit.yml")
        if config_path.exists():
            click.echo(f"配置文件已存在: {config_path}")
        else:
            # R186: 生成lint自动发现链可消费的YAML schema(键对齐lint_config.LintConfig)
            config_content = """# ai-prompt-toolkit Lint配置(自动发现: .lint-rc.yml/.prompt-toolkit.yml)
severity_threshold: low
exclude_categories: []
include_categories: []
exclude_rules: []
include_rules: []
"""
            config_path.write_text(config_content, encoding="utf-8")
            click.echo(f"配置模板已生成: {config_path}")
        return

    from pathlib import Path as _ConfigPath

    _config_path = _ConfigPath(".prompt-toolkit.yml") if _ConfigPath(".prompt-toolkit.yml").exists() else None
    if not _config_path and not as_json:
        # U3: 首次运行引导 — 快速入门+配置模板生成提示
        click.echo(
            "提示: 未找到配置文件, 运行 prompt-cli doctor --init 生成 .prompt-toolkit.yml 模板\n"
            "\n快速入门:\n"
            "  prompt-cli lint -t ./prompt.md            静态质量检查(255条规则, 零Token)\n"
            "  prompt-cli lint -t ./prompts --gate       CI门禁模式(verdict退出码)\n"
            "  prompt-cli scan -t ./prompt.md            安全纵深扫描(注入/PII/供应链)\n"
            "  prompt-cli eval -t ./prompt.md            130维质量评估\n"
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

    click.echo("正在检查Provider健康状态...")
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
        probe_names = _QUICK_PROBES
    else:
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


if __name__ == "__main__":
    main()


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
