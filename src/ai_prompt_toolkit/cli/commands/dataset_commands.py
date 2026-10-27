"""CLI命令 — 数据集管理相关命令。

从cli_core.main group导入并注册命令。
"""

from __future__ import annotations

from pathlib import Path

import click

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.cli_helpers import read_prompt_text


@main.group(name="dataset")
def dataset_group() -> None:
    """数据集管理: 创建/导入/运行测试用例集"""


@dataset_group.command(name="create")
@click.option("--name", "-n", required=True, help="数据集名称")
@click.option("--description", "-d", default="", help="数据集描述")
@click.option("--tags", "-t", default="", help="标签(逗号分隔)")
def dataset_create(name: str, description: str, tags: str) -> None:
    """创建新数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success

    store = DatasetStore()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    ds = store.create_dataset(name, description=description, tags=tag_list)
    success(f"数据集已创建: {ds.dataset_id} ({name})")
    store.close()


@dataset_group.command(name="list")
@click.option("--page", default=1, help="页码")
@click.option("--page-size", default=20, help="每页数量")
def dataset_list(page: int, page_size: int) -> None:
    """列出所有数据集"""
    from rich.table import Table

    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import console

    store = DatasetStore()
    datasets, total = store.list_datasets(page, page_size)
    table = Table(title=f"数据集 (共{total}个)")
    table.add_column("ID", style="cyan")
    table.add_column("名称", style="white")
    table.add_column("描述")
    table.add_column("用例数", style="green")
    table.add_column("标签")
    table.add_column("更新时间")
    for ds in datasets:
        table.add_row(
            ds.dataset_id, ds.name, ds.description[:30], str(ds.case_count), ",".join(ds.tags[:3]), ds.updated_at[:16]
        )
    console.print(table)
    store.close()


@dataset_group.command(name="add-case")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--input", "-i", required=True, help="输入文本")
@click.option("--expected", "-e", default="", help="期望输出")
@click.option("--tags", "-t", default="", help="标签(逗号分隔)")
def dataset_add_case(dataset: str, input: str, expected: str, tags: str) -> None:
    """添加测试用例"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success

    store = DatasetStore()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    c = store.add_case(dataset, input, expected_output=expected, tags=tag_list)
    success(f"用例已添加: {c.case_id}")
    store.close()


@dataset_group.command(name="import")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--file", "-f", required=True, help="导入文件路径(JSON/CSV)")
def dataset_import(dataset: str, file: str) -> None:
    """从JSON/CSV文件导入用例"""
    import sys

    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success

    store = DatasetStore()
    p = Path(file)
    if not p.exists():
        click.echo(f"文件不存在: {file}", err=True)
        sys.exit(2)
    content = read_prompt_text(p)
    if p.suffix == ".json":
        import json

        items = json.loads(content)
        count = store.import_json(dataset, items)
    elif p.suffix == ".csv":
        count = store.import_csv(dataset, content)
    else:
        click.echo("仅支持.json/.csv格式", err=True)
        sys.exit(2)
    success(f"已导入{count}条用例")
    store.close()


@dataset_group.command(name="export")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--format", "-f", type=click.Choice(["json", "csv"]), default="json", help="导出格式")
@click.option("--output", "-o", help="输出文件路径")
def dataset_export(dataset: str, format: str, output: str | None) -> None:
    """导出数据集"""
    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success

    store = DatasetStore()
    if format == "csv":
        data = store.export_csv(dataset)
    else:
        data = store.export_json(dataset)
    if output:
        Path(output).write_text(data, encoding="utf-8")
        success(f"已导出到: {output}")
    else:
        click.echo(data)
    store.close()


@dataset_group.command(name="run")
@click.option("--dataset", "-d", required=True, help="数据集ID")
@click.option("--type", "-t", type=click.Choice(["all", "lint", "scan", "evaluate"]), default="all", help="运行类型")
def dataset_run(dataset: str, type: str) -> None:
    """对数据集批量运行lint/scan/evaluate"""
    from rich.table import Table

    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import console

    store = DatasetStore()
    results = store.run_dataset(dataset, run_type=type)
    table = Table(title=f"数据集运行结果 ({type})")
    table.add_column("用例ID", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("Lint分数")
    table.add_column("扫描问题")
    table.add_column("评估分数")
    for r in results:
        status_style = "green" if r.status == "completed" else "red"
        table.add_row(
            r.case_id[:8],
            f"[{status_style}]{r.status}[/]",
            f"{r.lint_score:.1f}",
            str(r.scan_findings),
            f"{r.eval_score:.1f}",
        )
    console.print(table)
    store.close()


@dataset_group.command(name="delete")
@click.option("--dataset", "-d", required=True, help="数据集ID")
def dataset_delete(dataset: str) -> None:
    """删除数据集"""
    import sys

    from ai_prompt_toolkit.dataset import DatasetStore
    from ai_prompt_toolkit.output import success

    store = DatasetStore()
    if store.delete_dataset(dataset):
        success(f"数据集已删除: {dataset}")
    else:
        click.echo(f"数据集不存在: {dataset}", err=True)
        sys.exit(2)
    store.close()
