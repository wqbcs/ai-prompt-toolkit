"""CLI命令 — A/B测试相关命令。

从cli_core.main group导入并注册命令。
"""
from __future__ import annotations

import sys
import time

import click

from ai_prompt_toolkit.cli_core import main


@main.command(name="ab-test")
@click.option("--config", "-c", required=True, help="A/B测试配置YAML文件路径")
@click.option("--models", "-m", help="模型列表(逗号分隔)")
@click.option("--dataset", "-d", help="测试数据集路径")
@click.option("--output", "-o", help="输出报告路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def ab_test(config: str, models: str | None, dataset: str | None,
            output: str | None, fmt: str) -> None:
    """A/B测试：多模型并行对比提示词效果"""
    import asyncio
    import json as _json

    from ai_prompt_toolkit.ab_test.engine import ParallelEngine
    from ai_prompt_toolkit.ab_test.types import ABTestConfig, ModelConfig, ProviderType, TestDataset
    from ai_prompt_toolkit.cli_helpers import empty_state_tip, load_config, resolve_path, write_report

    cfg = load_config(config)
    model_list = models.split(",") if models else cfg.get("models", [])

    parsed_models = []
    for m in model_list:
        parts = m.strip().split(":")
        if len(parts) == 2:
            provider_str, model_name = parts
            try:
                provider = ProviderType(provider_str)
            except ValueError:
                click.echo(f"警告: 未知Provider '{provider_str}'，使用openai", err=True)
                provider = ProviderType.OPENAI
        else:
            provider = ProviderType.OPENAI
            model_name = m.strip()
        parsed_models.append(ModelConfig(provider=provider, model_name=model_name))

    if not parsed_models:
        click.echo(empty_state_tip("ab-test"))
        sys.exit(2)

    items = [{"input": "测试输入"}]
    if dataset:
        ds_path = resolve_path(dataset)
        with open(ds_path, encoding="utf-8") as f:
            data = _json.load(f)
            items = data if isinstance(data, list) else data.get("items", [{"input": str(data)}])

    ds = TestDataset(dataset_id="cli-ds", name="CLI数据集", items=items)
    templates = cfg.get("prompt_templates", ["请根据以下内容生成回复：{input}"])

    ab_config = ABTestConfig(
        test_id=f"cli-ab-{int(time.time())}",
        models=parsed_models,
        datasets=[ds],
        prompt_templates=templates,
    )

    engine = ParallelEngine(ab_config)

    click.echo(f"A/B测试 | 模型: {', '.join(m.provider.value + ':' + m.model_name for m in parsed_models)}")
    click.echo(f"数据集: {len(items)}条 | 模板: {len(templates)}个")

    results = asyncio.run(engine.run())
    summary = engine.get_summary()

    if fmt == "json":
        report_data = {"summary": summary, "results": [r.model_result.to_dict() for r in results]}
        if output:
            write_report(report_data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(report_data, ensure_ascii=False, indent=2))
    else:
        for name, stats in summary.items():
            click.echo(f"\n  {name}:")
            click.echo(f"    成功: {stats['success']}/{stats['total']}")
            click.echo(f"    平均延迟: {stats['avg_latency_ms']:.1f}ms")
            click.echo(f"    总费用: ${stats['total_cost']:.4f}")
            click.echo(f"    平均Token: {stats['avg_token_count']:.0f}")

    from ai_prompt_toolkit.ab_test.provider import get_cost_tracker
    cost_tracker = get_cost_tracker()
    if cost_tracker.spent > 0:
        click.echo(f"\n总费用: ${cost_tracker.spent:.4f} (剩余: ${cost_tracker.remaining:.2f})")
