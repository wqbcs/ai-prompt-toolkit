"""prompt-cli统一入口"""

from __future__ import annotations

import click

from ai_prompt_toolkit import __version__


@click.group()
@click.version_option(version=__version__, prog_name="prompt-cli")
def main() -> None:
    """AI提示词体系工具链 v27.0.0"""
    pass


@main.command()
@click.option("--source", "-s", required=True, help="源模板文件路径")
@click.option("--context", "-c", help="编译上下文JSON文件路径")
@click.option("--config", help="编译配置YAML文件路径")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--report", help="编译报告输出路径(JSON)")
def compile(source: str, context: str | None, config: str | None,
            output: str | None, report: str | None) -> None:
    """条件编译：按模型/语言/行业条件编译提示词模板"""
    click.echo(f"编译模板: {source}")
    if context:
        click.echo(f"上下文: {context}")
    if report:
        click.echo(f"报告输出: {report}")


@main.command(name="ab-test")
@click.option("--config", "-c", required=True, help="A/B测试配置YAML文件路径")
@click.option("--models", "-m", help="模型列表(逗号分隔)")
@click.option("--dataset", "-d", help="测试数据集路径")
@click.option("--output", "-o", help="输出报告路径")
def ab_test(config: str, models: str | None, dataset: str | None,
            output: str | None) -> None:
    """A/B测试：多模型并行对比提示词效果"""
    click.echo(f"A/B测试配置: {config}")
    if models:
        click.echo(f"模型: {models}")


@main.command()
@click.option("--target", "-t", required=True, help="扫描目标(文件或目录)")
@click.option("--config", help="安全扫描配置YAML文件路径")
@click.option("--incremental", is_flag=True, help="增量扫描模式")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli"]),
              default="cli", help="输出格式")
@click.option("--output", "-o", help="报告输出路径")
def scan(target: str, config: str | None, incremental: bool,
         fmt: str, output: str | None) -> None:
    """安全扫描：注入检测+继承链审计"""
    click.echo(f"安全扫描: {target}")
    if incremental:
        click.echo("增量扫描模式")


@main.command()
@click.option("--target", "-t", required=True, help="Lint目标(文件或目录)")
@click.option("--config", help="Lint配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]),
              default="cli", help="输出格式")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
def lint(target: str, config: str | None, fmt: str, fix: bool) -> None:
    """Prompt Linter：静态检查提示词质量"""
    click.echo(f"Lint: {target}")
    if fix:
        click.echo("自动修复模式")


if __name__ == "__main__":
    main()
