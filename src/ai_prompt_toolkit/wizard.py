"""交互式向导模式 — 五步引导用户完成lint/scan/evaluate/ab-test/redteam"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

_WIZARD_STEPS = ["选择功能", "选择目标", "配置参数", "预览确认", "执行"]


def _discover_md_files(base: str = ".") -> list[str]:
    p = Path(base)
    files = sorted(p.rglob("*.md"))
    return [str(f) for f in files[:50]]


def _pick_from_list(prompt_text: str, items: list[str], allow_custom: bool = True) -> str:
    if not items:
        if allow_custom:
            answer: str = click.prompt(prompt_text, type=str)
            return answer
        click.echo("无可选项")
        return ""
    click.echo(f"\n{prompt_text}:")
    for i, item in enumerate(items, 1):
        display = item if len(item) <= 80 else item[:77] + "..."
        click.echo(f"  {i}. {display}")
    if allow_custom:
        click.echo("  0. 自定义输入")
    while True:
        choice = click.prompt("请选择", type=int, default=1)
        if 1 <= choice <= len(items):
            picked: str = str(items[choice - 1])
            return picked
        if choice == 0 and allow_custom:
            custom: str = click.prompt("请输入", type=str)
            return custom
        click.echo(f"无效选择，请输入0-{len(items)}")


def _confirm_step(step_num: int, step_name: str, details: dict[str, Any]) -> bool:
    click.echo(f"\n{'=' * 50}")
    click.echo(f"步骤 {step_num}/5: {step_name}")
    click.echo(f"{'=' * 50}")
    for k, v in details.items():
        click.echo(f"  {k}: {v}")
    return click.confirm("确认以上配置?", default=True)


def _build_and_execute(command: str, args: dict[str, Any]) -> int:
    from click.testing import CliRunner

    from ai_prompt_toolkit.cli import main

    cmd_parts = [command]
    for k, v in args.items():
        if isinstance(v, bool):
            if v:
                cmd_parts.append(f"--{k}")
        elif v is not None and v != "":
            cmd_parts.append(f"--{k}")
            cmd_parts.append(str(v))

    click.echo(f"\n执行命令: prompt-cli {' '.join(cmd_parts)}")
    click.echo("-" * 50)

    runner = CliRunner()
    result = runner.invoke(main, cmd_parts)
    click.echo(result.output)

    if result.exit_code != 0 and result.exception:
        click.echo(f"执行异常: {result.exception}", err=True)

    return result.exit_code


def wizard_lint() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  Prompt Linter 向导")
    click.echo("  逐步引导你完成Prompt质量检查")
    click.echo("=" * 50)

    md_files = _discover_md_files()
    target = _pick_from_list("选择Lint目标", md_files)

    fmt_choices = ["cli", "json", "html"]
    click.echo("\n选择输出格式:")
    for i, c in enumerate(fmt_choices, 1):
        click.echo(f"  {i}. {c}")
    fmt_idx = click.prompt("请选择", type=int, default=1)
    fmt = fmt_choices[min(fmt_idx - 1, 2)]

    fix = click.confirm("自动修复可修复的问题?", default=False)
    output = click.prompt("输出报告路径(留空不保存)", default="", show_default=False)

    args: dict[str, Any] = {"target": target, "format": fmt, "fix": fix}
    if output:
        args["output"] = output

    if not _confirm_step(4, "预览确认", {"命令": "lint", **args}):
        click.echo("已取消")
        return 0

    return _build_and_execute("lint", args)


def wizard_scan() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  安全扫描 向导")
    click.echo("  逐步引导你完成Prompt安全检查")
    click.echo("=" * 50)

    md_files = _discover_md_files()
    target = _pick_from_list("选择扫描目标", md_files)

    fmt_choices = ["cli", "json", "html"]
    click.echo("\n选择输出格式:")
    for i, c in enumerate(fmt_choices, 1):
        click.echo(f"  {i}. {c}")
    fmt_idx = click.prompt("请选择", type=int, default=1)
    fmt = fmt_choices[min(fmt_idx - 1, 2)]

    incremental = click.confirm("增量扫描模式?", default=False)
    output = click.prompt("输出报告路径(留空不保存)", default="", show_default=False)

    args: dict[str, Any] = {"target": target, "format": fmt, "incremental": incremental}
    if output:
        args["output"] = output

    if not _confirm_step(4, "预览确认", {"命令": "scan", **args}):
        click.echo("已取消")
        return 0

    return _build_and_execute("scan", args)


def wizard_evaluate() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  80维度质量评估 向导")
    click.echo("  逐步引导你完成Prompt质量评估")
    click.echo("=" * 50)

    md_files = _discover_md_files()
    target = _pick_from_list("选择评估目标", md_files)

    quick = click.confirm("快速模式(仅TOP10核心维度)?", default=True)
    dimensions = ""
    if not quick:
        dimensions = click.prompt("指定维度(逗号分隔，如D1,D5,D10，留空全部)", default="", show_default=False)
    threshold = click.prompt("质量阈值(0-10，低于此值告警)", type=float, default=0.0)

    fmt_choices = ["cli", "json"]
    click.echo("\n选择输出格式:")
    for i, c in enumerate(fmt_choices, 1):
        click.echo(f"  {i}. {c}")
    fmt_idx = click.prompt("请选择", type=int, default=1)
    fmt = fmt_choices[min(fmt_idx - 1, 1)]

    save = click.confirm("保存评估结果到历史?", default=False)
    output = click.prompt("输出报告路径(留空不保存)", default="", show_default=False)

    args: dict[str, Any] = {"target": target, "format": fmt, "quick": quick, "save": save, "threshold": threshold}
    if dimensions:
        args["dimensions"] = dimensions
    if output:
        args["output"] = output

    if not _confirm_step(4, "预览确认", {"命令": "evaluate", **args}):
        click.echo("已取消")
        return 0

    return _build_and_execute("evaluate", args)


def wizard_ab_test() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  A/B测试 向导")
    click.echo("  逐步引导你完成多模型对比测试")
    click.echo("=" * 50)

    from ai_prompt_toolkit.ab_test.types import ProviderType

    providers = [p.value for p in ProviderType]
    click.echo("\n选择Provider和模型(格式: provider:model_name):")
    for i, p in enumerate(providers[:10], 1):
        click.echo(f"  {i}. {p}")
    click.echo("  (更多Provider请直接输入，如 openai:gpt-4o)")

    # R201: 显式list[str]标注 — 消除var-annotated
    model_inputs: list[str] = []
    while True:
        m = click.prompt(f"模型#{len(model_inputs) + 1}(留空结束)", default="", show_default=False)
        if not m:
            break
        if ":" not in m:
            provider_choice = click.prompt("选择Provider编号或输入名称", type=str)
            try:
                idx = int(provider_choice)
                if 1 <= idx <= len(providers):
                    m = f"{providers[idx - 1]}:{m}"
            except ValueError:
                m = f"{provider_choice}:{m}"
        model_inputs.append(m)
        if len(model_inputs) >= 5:
            break

    if not model_inputs:
        click.echo("至少需要一个模型")
        return 1

    dataset = click.prompt("测试数据集路径(留空使用默认)", default="", show_default=False)
    output = click.prompt("输出报告路径(留空不保存)", default="", show_default=False)

    import tempfile

    import yaml

    default_config = {
        "models": model_inputs,
        "prompt_templates": ["请根据以下内容生成回复：{input}"],
    }
    tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8")  # noqa: SIM115 — Windows下子进程读取前须close
    tmp_name = tmp.name
    try:
        yaml.dump(default_config, tmp, allow_unicode=True, default_flow_style=False)
        tmp.close()

        args: dict[str, Any] = {"config": tmp_name, "models": ",".join(model_inputs)}
        if dataset:
            args["dataset"] = dataset
        if output:
            args["output"] = output

        if not _confirm_step(4, "预览确认", {"命令": "ab-test", **args}):
            click.echo("已取消")
            return 0

        return _build_and_execute("ab-test", args)
    finally:
        try:
            import os

            os.unlink(tmp_name)
        except OSError:
            pass


def wizard_redteam() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  红队探测 向导")
    click.echo("  逐步引导你完成对抗性安全测试")
    click.echo("=" * 50)

    from ai_prompt_toolkit.redteam.probe import get_available_probes

    mode = click.confirm("使用在线模式(Provider)?", default=False)
    provider = ""
    target = ""
    if mode:
        provider = click.prompt("Provider配置(如 openai:gpt-4o)", type=str)
    else:
        md_files = _discover_md_files()
        target = _pick_from_list("选择目标文本文件", md_files)

    available = get_available_probes()
    click.echo(f"\n可用Probe({len(available)}个):")
    for i, p in enumerate(available[:20], 1):
        click.echo(f"  {i}. {p}")
    if len(available) > 20:
        click.echo(f"  ... 还有{len(available) - 20}个")

    all_probes = click.confirm("运行全部Probe?", default=True)
    probes = ""
    if not all_probes:
        probes = click.prompt("指定Probe(逗号分隔)", type=str)

    severity_choices = ["", "critical", "high", "medium", "low"]
    click.echo("\n最低严重性过滤:")
    for i, s in enumerate(severity_choices):
        click.echo(f"  {i}. {s or '不限'}")
    sev_idx = click.prompt("请选择", type=int, default=0)
    severity = severity_choices[sev_idx] if sev_idx > 0 else ""

    compliance_choices = ["", "eu_ai_act", "china_algorithm"]
    click.echo("\n合规报告框架:")
    for i, c in enumerate(compliance_choices):
        click.echo(f"  {i}. {c or '不生成'}")
    comp_idx = click.prompt("请选择", type=int, default=0)
    compliance = compliance_choices[comp_idx] if comp_idx > 0 else ""

    output = click.prompt("输出报告路径(留空不保存)", default="", show_default=False)

    args: dict[str, Any] = {}
    if mode and provider:
        args["provider"] = provider
    elif target:
        args["target"] = target
    if probes:
        args["probes"] = probes
    if severity:
        args["severity"] = severity
    if compliance:
        args["compliance"] = compliance
    if output:
        args["output"] = output

    if not _confirm_step(4, "预览确认", {"命令": "redteam", **args}):
        click.echo("已取消")
        return 0

    return _build_and_execute("redteam", args)


def wizard_recommend() -> int:
    click.echo("\n" + "=" * 50)
    click.echo("  智能模板推荐 向导")
    click.echo("  根据你的场景推荐最佳Prompt模板")
    click.echo("=" * 50)

    category_choices = [
        "general",
        "development",
        "security",
        "translation",
        "service",
        "nlp",
        "optimization",
        "deployment",
    ]
    click.echo("\n选择场景分类:")
    for i, c in enumerate(category_choices, 1):
        click.echo(f"  {i}. {c}")
    cat_idx = click.prompt("请选择(留空不限)", type=int, default=0)
    category = category_choices[cat_idx - 1] if 1 <= cat_idx <= len(category_choices) else None

    industry_choices = ["通用", "华为云", "科技", "金融", "教育", "电商", "媒体"]
    click.echo("\n选择行业:")
    for i, ind in enumerate(industry_choices, 1):
        click.echo(f"  {i}. {ind}")
    ind_idx = click.prompt("请选择(留空不限)", type=int, default=0)
    industry = industry_choices[ind_idx - 1] if 1 <= ind_idx <= len(industry_choices) else None

    model_choices = ["pangu", "qwen", "deepseek", "gpt-4", "claude-3"]
    click.echo("\n选择目标模型:")
    for i, m in enumerate(model_choices, 1):
        click.echo(f"  {i}. {m}")
    mod_idx = click.prompt("请选择(留空不限)", type=int, default=0)
    model = model_choices[mod_idx - 1] if 1 <= mod_idx <= len(model_choices) else None

    args: dict[str, Any] = {"top-n": 5}
    if category:
        args["category"] = category
    if industry:
        args["industry"] = industry
    if model:
        args["model"] = model

    if not _confirm_step(4, "预览确认", {"命令": "recommend", **args}):
        click.echo("已取消")
        return 0

    return _build_and_execute("recommend", args)


_WIZARD_MAP = {
    "1": ("Prompt Linter — 静态检查提示词质量", wizard_lint),
    "2": ("安全扫描 — 注入检测+继承链审计", wizard_scan),
    "3": ("80维度评估 — 全面评估Prompt质量", wizard_evaluate),
    "4": ("A/B测试 — 多模型并行对比", wizard_ab_test),
    "5": ("红队探测 — 对抗性安全测试", wizard_redteam),
    "6": ("智能推荐 — 根据场景推荐最佳模板", wizard_recommend),
}


def run_wizard(command: str | None = None) -> int:
    _COMMAND_MAP = {
        "lint": wizard_lint,
        "scan": wizard_scan,
        "evaluate": wizard_evaluate,
        "ab-test": wizard_ab_test,
        "redteam": wizard_redteam,
        "recommend": wizard_recommend,
    }
    if command:
        cmd_key = command.lower().strip()
        wizard_fn = _COMMAND_MAP.get(cmd_key)
        if wizard_fn:
            return wizard_fn()
        click.echo(f"未知命令: {command}，可选: {', '.join(_COMMAND_MAP.keys())}", err=True)
        return 1

    click.echo("\n" + "=" * 50)
    click.echo("  AI提示词工具链 交互式向导")
    click.echo("  像TurboTax一样简单，5步完成")
    click.echo("=" * 50)

    click.echo("\n选择要执行的功能:")
    for k, (desc, _) in _WIZARD_MAP.items():
        click.echo(f"  {k}. {desc}")

    choice = click.prompt("请选择(1-6)", type=str, default="1")
    if choice not in _WIZARD_MAP:
        click.echo(f"无效选择: {choice}")
        return 1

    _, wizard_fn = _WIZARD_MAP[choice]
    return wizard_fn()
