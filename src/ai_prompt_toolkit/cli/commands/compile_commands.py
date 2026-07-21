"""CLI命令 — 编译相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import main


@main.command()
@click.option("--source", "-s", required=True, help="源模板文件路径")
@click.option("--context", "-c", help="编译上下文JSON文件路径")
@click.option("--config", help="编译配置YAML文件路径")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--report", help="编译报告输出路径(JSON)")
def compile(source: str, context: str | None, config: str | None,
            output: str | None, report: str | None) -> None:
    """条件编译：按模型/语言/行业条件编译提示词模板"""
    from ai_prompt_toolkit.cli_helpers import determine_exit_code, load_context, resolve_path, write_report
    from ai_prompt_toolkit.compiler import CompileContext, compile_template

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
