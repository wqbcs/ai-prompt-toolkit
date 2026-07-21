"""CLI命令 — RedTeam/Security相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys

import click

from ai_prompt_toolkit.cli_core import main


@main.command(name="redteam")
@click.option("--target", "-t", help="目标文本文件路径(离线模式)")
@click.option("--probes", "-p", help="探测类型(逗号分隔，默认全部)")
@click.option("--provider", help="Provider配置(provider:model_name，在线模式)")
@click.option("--output", "-o", help="输出报告路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--owasp", help="按OWASP LLM Top 10分类过滤(如LLM01,LLM06)")
@click.option("--top-n", type=int, default=0, help="仅运行前N个Probe")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="最低严重性过滤")
@click.option("--compliance", type=click.Choice(["eu_ai_act", "china_algorithm"]), help="合规报告框架")
@click.option("--scorecard", is_flag=True, help="红队探测后自动运行安全评分卡")
def redteam_cmd(target: str | None, probes: str | None, provider: str | None,
                output: str | None, fmt: str, owasp: str | None,
                top_n: int, severity: str | None, compliance: str | None,
                scorecard: bool) -> None:
    """红队探测：对抗性安全测试"""
    from ai_prompt_toolkit.cli_helpers import empty_state_tip
    from ai_prompt_toolkit.redteam.detector import (
        ComplianceDetector,
        LeakageDetector,
        RefusalDetector,
    )
    from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator
    from ai_prompt_toolkit.redteam.probe import create_probe, get_available_probes, get_probes_by_owasp

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
        from ai_prompt_toolkit.ab_test.provider import create_provider
        from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
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
    else:
        click.echo(report.get_summary())

    if scorecard:
        from pathlib import Path as _P

        from ai_prompt_toolkit.security.badge import generate_scorecard_badge
        findings_count = sum(len(pr.findings) for pr in report.probe_results)
        total_probes = len(report.probe_results)
        passed = sum(1 for pr in report.probe_results if not pr.findings)
        svg = generate_scorecard_badge(total=total_probes, passed=passed, failed=findings_count)
        badge_path = "redteam-scorecard.svg"
        _P(badge_path).write_text(svg, encoding="utf-8")
        click.echo(f"安全评分卡: {badge_path}")
