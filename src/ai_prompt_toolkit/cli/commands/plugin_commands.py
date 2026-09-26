"""CLI命令 — 插件管理相关命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

import click

from ai_prompt_toolkit.cli_core import main


@main.group(name="plugin")
def plugin_group() -> None:
    """插件管理: 注册/列表/启用/禁用"""


@plugin_group.command(name="list")
def plugin_list() -> None:
    """列出已注册插件"""
    from rich.table import Table

    from ai_prompt_toolkit.output import console
    from ai_prompt_toolkit.plugin import PluginManager

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
    from ai_prompt_toolkit.output import success
    from ai_prompt_toolkit.plugin import PluginManager

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
    from ai_prompt_toolkit.output import success
    from ai_prompt_toolkit.plugin import PluginManager

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
    from ai_prompt_toolkit.output import success
    from ai_prompt_toolkit.plugin import PluginManager

    mgr = PluginManager.get_instance()
    p = mgr.get_plugin(name)
    if not p:
        click.echo(f"插件不存在: {name}", err=True)
        return
    p.disable()
    success(f"插件已禁用: {name}")
