"""CLI命令 — 模板/市场/i18n/基础命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit import __version__
from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.cli_helpers import read_prompt_text


@main.command()
@click.option("--source-locale", "-s", default="zh-CN", help="源语言(BCP 47)")
@click.option("--target-locale", "-t", default="en-US", help="目标语言(BCP 47)")
@click.option("--output", "-o", help="输出目录")
@click.option("--base-dir", help="i18n资源基础目录")
@click.option("--llm", is_flag=True, help="启用LLM辅助翻译(需配置Provider)")
@click.option("--provider", help="LLM Provider(provider:model_name)")
def i18n(
    source_locale: str, target_locale: str, output: str | None, base_dir: str | None, llm: bool, provider: str | None
) -> None:
    """国际化：批量翻译Prompt模板"""
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.i18n.translator import translate_template

    # P4-04: 默认模板目录经 repo_relative 解析(仓库根锚定, 消除 cwd 依赖)
    from ai_prompt_toolkit.linter.project_config import repo_relative

    templates_dir = resolve_path(base_dir) if base_dir else repo_relative("src/ai_prompt_toolkit/templates")
    if not templates_dir.exists():
        click.echo(f"错误: 模板目录不存在 — {templates_dir}", err=True)
        sys.exit(2)

    output_dir = resolve_path(output) if output else templates_dir.parent / f"templates_{target_locale}"
    output_dir.mkdir(parents=True, exist_ok=True)

    translated = 0
    for tpl_file in sorted(templates_dir.glob("*.md")):
        text = read_prompt_text(tpl_file)
        result = translate_template(text, source_locale, target_locale, use_llm=llm, provider=provider)
        out_file = output_dir / tpl_file.name
        out_file.write_text(result.translated_text, encoding="utf-8")
        translated += 1
        click.echo(f"  {tpl_file.name}: {result.untranslated_count}个未翻译段")

    click.echo(f"\ni18n完成 | {translated}个模板 | {source_locale} → {target_locale} | 输出: {output_dir}")


@main.command()
@click.option(
    "--action", "-a", type=click.Choice(["submit", "review", "deploy", "status"]), required=True, help="市场操作"
)
@click.option("--template", "-t", help="模板ID或文件路径")
@click.option("--config", help="市场配置YAML文件路径")
def market(action: str, template: str | None, config: str | None) -> None:
    """模板市场：提交/审核/部署/查看状态"""
    from ai_prompt_toolkit.market.service import MarketService
    from ai_prompt_toolkit.market.types import Template

    # R198: 真实API — MarketService(data_dir)而非config字典; submit需Template对象;
    # start_deploy返回DeployConfig(无url字段), 展示canary阶段
    client = MarketService(config)

    if action == "submit":
        if not template:
            click.echo("错误: 请指定--template", err=True)
            sys.exit(2)
        tpl = Template(id=template, name=template, version="1.0.0")
        submit_res = client.submit(tpl)
        click.echo(f"提交成功: {submit_res.id} → {submit_res.status.value}")
    elif action == "review":
        if not template:
            click.echo("错误: 请指定--template", err=True)
            sys.exit(2)
        review_res = client.start_review(template)
        click.echo(f"审核已启动: {review_res}")
    elif action == "deploy":
        if not template:
            click.echo("错误: 请指定--template", err=True)
            sys.exit(2)
        deploy_res = client.start_deploy(template)
        click.echo(f"部署已启动: {template} → {deploy_res.phase.value}")
    elif action == "status":
        if not template:
            click.echo("错误: 请指定--template", err=True)
            sys.exit(2)
        status_res = client.get_status(template)
        click.echo(
            f"模板: {status_res.get('template', {}).get('id', '?')} | 状态: {status_res.get('template', {}).get('status', '?')} | 评分: {status_res.get('lint', {}).get('lint_score', '-')}"
        )


@main.command(name="upgrade-fm")
@click.option("--target", "-t", required=True, help="目标目录或文件")
@click.option("--dry-run", is_flag=True, help="仅预览变更不写入")
@click.option("--locale", "-l", default="zh-CN", help="默认语言标签(BCP 47)")
def upgrade_fm(target: str, dry_run: bool, locale: str) -> None:
    """升级模板格式：旧版→v2.0(frontmatter+条件编译)"""
    from ai_prompt_toolkit.cli_helpers import resolve_path
    from ai_prompt_toolkit.template_upgrader import upgrade_template

    target_path = resolve_path(target)
    if target_path.is_file():
        files = [target_path]
    else:
        files = sorted(target_path.rglob("*.md"))

    if not files:
        click.echo("未找到.md文件", err=True)
        sys.exit(2)

    upgraded = 0
    for f in files:
        text = read_prompt_text(f)
        result = upgrade_template(text, default_locale=locale)
        if result.was_upgraded:
            if not dry_run:
                f.write_text(result.upgraded_text, encoding="utf-8")
            click.echo(f"  {'[dry-run] ' if dry_run else ''}{f.name}: v{result.old_version} → v{result.new_version}")
            upgraded += 1
        else:
            click.echo(f"  {f.name}: 无需升级")

    click.echo(f"\n升级完成 | {upgraded}/{len(files)}个文件已升级" + (" (dry-run)" if dry_run else ""))


@main.command(name="init")
@click.option("--target", "-t", default=".", help="项目目录(默认当前目录)")
@click.option("--non-interactive", is_flag=True, help="非交互模式")
@click.option("--ci", is_flag=True, help="生成CI/CD配置(GitHub Action+Docker+pre-commit)")
@click.option(
    "--template",
    type=click.Choice(["general", "harmonyos", "security", "rag", "code-review"]),
    default=None,
    help="项目模板",
)
@click.option(
    "--snippet",
    "snippet_mode",
    is_flag=True,
    help="R229-P2-22: 轻量片段模式 — 只打印 toml+pre-commit+CI 三段配置片段(不创建目录/不写文件), 供已有项目按需粘贴",
)
def init_project(target: str, non_interactive: bool, ci: bool, template: str | None, snippet_mode: bool) -> None:
    """初始化项目：创建项目结构 + 运行时配置 + lint 门禁配置"""
    from ai_prompt_toolkit.config import generate_config
    from ai_prompt_toolkit.linter.project_config import DEFAULT_PROMPTLINT_TOML, write_default_config
    from ai_prompt_toolkit.output import success

    if snippet_mode:
        # 轻量片段模式：零副作用（不建目录/不写文件），只打印三段配置。
        # toml 片段与 init / doctor --init 落盘同一真源（DEFAULT_PROMPTLINT_TOML），
        # pre-commit/CI 片段与 --ci 落盘内容同常量 —— 打印即所见即所得。
        click.echo("── 配置片段 1/3: promptlint.toml ──")
        click.echo(DEFAULT_PROMPTLINT_TOML.rstrip())
        click.echo("")
        click.echo("── 配置片段 2/3: .pre-commit-config.yaml (本地钩子) ──")
        click.echo(_PRECOMMIT_SNIPPET.rstrip())
        click.echo("")
        click.echo("── 配置片段 3/3: .github/workflows/prompt-ci.yml ──")
        click.echo(_CI_SNIPPET.rstrip())
        click.echo("")
        success("片段已输出 — 按需在已有项目粘贴（与 init --ci 落盘内容一致）")
        return

    target_path = Path(target).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    dirs = ["prompts", "tests", "configs"]
    for d in dirs:
        (target_path / d).mkdir(exist_ok=True)

    # 运行时配置(Provider/缓存/安全阈值 — eval/ab_test/compliance 消费) 原行为保留
    runtime_cfg = target_path / ".prompt-cli.toml"
    if not runtime_cfg.exists():
        generate_config(runtime_cfg)
        click.echo(f"  运行时配置已生成: {runtime_cfg.name}")
    else:
        click.echo(f"  运行时配置已存在: {runtime_cfg.name}")

    # R324: lint 门禁配置 promptlint.toml(lint 首选发现实际读取) — 使 init 一次性
    # 完成门禁+运行时双配置(此前 init 只出运行时配置, 门禁需另跑 doctor --init)
    lint_cfg, wrote = write_default_config(target_path)
    if wrote:
        click.echo(f"  lint 配置已生成: {lint_cfg.name} (lint 自动发现读取)")
    else:
        click.echo(f"  lint 配置已存在(未覆盖): {lint_cfg.name}")

    if template:
        _apply_template(target, template)

    if ci:
        _generate_ci_config(target)

    success(f"项目已初始化: {target_path}")


def _apply_template(target: str, template_name: str) -> None:
    from ai_prompt_toolkit.output import success

    target_path = Path(target).resolve()
    prompts_dir = target_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    template_map = {
        "general": "general-assistant.md",
        "harmonyos": "harmonyos-dev.md",
        "security": "security-auditor.md",
        "rag": "rag-assistant.md",
        "code-review": "code-reviewer.md",
    }

    tpl_file = template_map.get(template_name)
    if not tpl_file:
        return

    # R229 修复(既有缺陷): 模板在 src/ai_prompt_toolkit/templates/，需上溯三级
    # (commands→cli→ai_prompt_toolkit)。原 .parent.parent 指向不存在的 cli/templates/
    # → --template 一直静默 no-op（本轮回归测试捕获）
    src = Path(__file__).parent.parent.parent / "templates" / tpl_file
    if src.exists():
        dest = prompts_dir / tpl_file
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        success(f"模板已应用: {tpl_file}")


# R229-P2-22: CI 片段提升为模块常量 — init --ci 落盘与 init --snippet 打印
# 共用同一真源（避免两处硬编码漂移）
_CI_SNIPPET = """name: Prompt CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ai-prompt-toolkit
      - run: prompt-cli lint -t prompts/ --gate
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ai-prompt-toolkit
      - run: prompt-cli scan -t prompts/
"""

# pre-commit 本地钩子片段（与仓库自身 .pre-commit-config.yaml 的 prompt-lint/
# prompt-scan 钩子同 schema — 采用者粘进已有配置或独立成文件均可）
_PRECOMMIT_SNIPPET = """- repo: local
  hooks:
    - id: prompt-lint
      name: Prompt Lint
      entry: prompt-cli lint -t
      language: system
      files: '\\.prompt\\.md$|\\.prompt$'
      pass_filenames: true

    - id: prompt-scan
      name: Prompt Security Scan
      entry: prompt-cli scan -t
      language: system
      files: '\\.prompt\\.md$|\\.prompt$'
      pass_filenames: true
"""


def _generate_ci_config(target: str) -> None:
    from ai_prompt_toolkit.output import success

    target_path = Path(target).resolve()

    github_dir = target_path / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)

    (github_dir / "prompt-ci.yml").write_text(_CI_SNIPPET, encoding="utf-8")
    success("CI配置已生成: .github/workflows/prompt-ci.yml")


@main.command(name="locale")
@click.option("--set", "-s", "set_locale", help="设置语言(zh-CN/en-US)")
@click.option("--list", "-l", "list_locales", is_flag=True, help="列出支持的语言")
def locale_cmd(set_locale: str | None, list_locales: bool) -> None:
    """查看/设置界面语言"""
    from ai_prompt_toolkit.i18n.messages import get_current_locale, get_supported_locales
    from ai_prompt_toolkit.i18n.messages import set_locale as msg_set_locale

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
@click.option("--message", "-m", required=True, help="反馈内容")
@click.option(
    "--type", "-t", type=click.Choice(["bug", "feature", "improvement", "other"]), default="other", help="反馈类型"
)
def feedback_cmd(message: str, type: str) -> None:
    """提交用户反馈"""
    import json

    from ai_prompt_toolkit.output import success

    feedback_dir = Path.home() / ".ai-prompt-toolkit" / "feedback"
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


@main.command(name="rules-yaml")
@click.option("--init", "init_path", help="生成示例YAML规则文件到指定路径")
@click.option("--load", "load_path", help="加载YAML规则文件并检查")
@click.option("--target", "-t", help="使用自定义规则检查的目标文件")
def rules_yaml_cmd(init_path: str | None, load_path: str | None, target: str | None) -> None:
    """管理自定义Lint规则(YAML)"""
    from ai_prompt_toolkit.linter.rule_loader_yaml import check_custom_rules, generate_sample_yaml, load_rules_from_yaml
    from ai_prompt_toolkit.output import console, error, success

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
                sev_color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "cyan", "LOW": "green"}.get(
                    r["severity"].value, "white"
                )
                console.print(
                    f"  [{sev_color}]{r['rule_id']}[/{sev_color}] {r['name']} ({r['severity'].value}) — {r['description'][:50]}"
                )

            if target:
                from ai_prompt_toolkit.cli_helpers import resolve_path

                target_path = resolve_path(target)
                if not target_path.exists():
                    error(f"目标文件不存在: {target}")
                    return
                text = read_prompt_text(target_path)
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
