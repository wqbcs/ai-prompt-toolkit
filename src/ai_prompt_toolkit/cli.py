"""prompt-cli统一入口"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

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
            return data["template_type"]
    except _yaml.YAMLError:
        pass
    return "prompt"


@click.group()
@click.version_option(version=__version__, prog_name="prompt-cli")
def main() -> None:
    """AI提示词体系工具链"""
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
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_context, write_report, determine_exit_code
    from ai_prompt_toolkit.compiler import compile_template, CompileContext

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
        click.echo(f"编译错误: {e}", err=True)
        sys.exit(3)

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
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_config, write_report
    from ai_prompt_toolkit.ab_test.types import ABTestConfig, ModelConfig, ProviderType, TestDataset
    from ai_prompt_toolkit.ab_test.engine import ParallelEngine
    from ai_prompt_toolkit.ab_test.statistics import StatisticalAnalyzer
    from ai_prompt_toolkit.ab_test.recommender import Recommender

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
        click.echo("错误: 未指定任何模型", err=True)
        sys.exit(2)

    items = [{"input": "测试输入"}]
    if dataset:
        import json as _json
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


@main.command()
@click.option("--target", "-t", required=True, help="评估目标(文件或目录)")
@click.option("--dimensions", "-d", help="指定维度(逗号分隔，如D1,D5,D10)")
@click.option("--categories", help="指定类别(逗号分隔，如structure,security)")
@click.option("--threshold", type=float, default=0.0, help="质量阈值(0-10，低于此值退出码1)")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--output", "-o", help="输出报告路径(JSON)")
def evaluate(target: str, dimensions: str | None, categories: str | None,
             threshold: float, fmt: str, output: str | None) -> None:
    """62维度质量评估：全面评估Prompt质量"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, write_report
    from ai_prompt_toolkit.evaluator import evaluate_template

    target_path = resolve_path(target)
    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None
    cat_list = [c.strip() for c in categories.split(",")] if categories else None

    if target_path.is_dir():
        files = sorted(target_path.rglob("*.md"))
    else:
        files = [target_path]

    if not files:
        click.echo("错误: 未找到.md文件", err=True)
        sys.exit(2)

    reports = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        report = evaluate_template(
            str(f), text, dimensions=dim_list, categories=cat_list
        )
        reports.append(report)

    if fmt == "json":
        import json as _json
        data = {"reports": [r.to_dict() for r in reports]}
        if output:
            write_report(data, output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        total_score = 0.0
        total_count = 0
        low_items = []
        for report in reports:
            scores = report.scores
            if not scores:
                continue
            avg = sum(s.score for s in scores) / len(scores) if scores else 0
            total_score += avg
            total_count += 1
            tid = report.template_id if hasattr(report, 'template_id') else 'unknown'
            click.echo(f"  {tid}: 均分 {avg:.1f}/10 ({len(scores)}维度)")
            if threshold > 0 and avg < threshold:
                low_items.append((tid, avg))

        if total_count > 0:
            click.echo(f"\n总均分: {total_score / total_count:.1f}/10")

        if low_items:
            click.echo(f"\n低于阈值({threshold})的模板({len(low_items)}个):")
            for tid, score in low_items[:5]:
                click.echo(f"  {tid}: {score:.1f}/10")

    exit_code = 0
    if threshold > 0:
        for report in reports:
            scores = report.scores
            avg = sum(s.score for s in scores) / len(scores) if scores else 0
            if avg < threshold:
                exit_code = 1
                break
    sys.exit(exit_code)


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
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector

    templates = discover_templates(target)
    if not templates:
        click.echo("未发现.md模板文件")
        sys.exit(0)

    detector = InjectionDetector()
    all_findings = []
    total = len(templates)

    for i, tpl_path in enumerate(templates, 1):
        text = tpl_path.read_text(encoding="utf-8")
        findings = detector.detect(text)
        findings_data = [f.to_dict() for f in findings]
        all_findings.extend(findings_data)
        if fmt == "cli" and findings_data:
            for f in findings_data:
                sev = f.get("severity", "info")
                marker = {"high": "✗", "critical": "✗✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                click.echo(f"  {marker} [{tpl_path.name}] {f.get('rule_id', '')}: {f.get('description', '')}")

    high_count = sum(1 for f in all_findings if f.get("severity") in ("high", "critical"))
    medium_count = sum(1 for f in all_findings if f.get("severity") == "medium")
    low_count = sum(1 for f in all_findings if f.get("severity") == "low")

    click.echo(f"\n扫描完成 | 文件: {total} | 发现: {len(all_findings)} "
               f"(高:{high_count} 中:{medium_count} 低:{low_count})")

    if output and all_findings:
        report_data = {
            "scan_target": target,
            "total_files": total,
            "findings": all_findings,
            "risk_level": "critical" if high_count > 0 and any(f.get("severity") == "critical" for f in all_findings)
                         else "high" if high_count > 0
                         else "medium" if medium_count > 0
                         else "low" if low_count > 0 else "none",
        }
        write_report(report_data, output, fmt=fmt)
        click.echo(f"报告: {output}")

    sys.exit(determine_exit_code(has_findings=len(all_findings) > 0,
                                  error_severity="high" if high_count > 0 else None))


@main.command()
@click.option("--target", "-t", required=True, help="Lint目标(文件或目录)")
@click.option("--config", help="Lint配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "html", "cli"]),
              default="cli", help="输出格式")
@click.option("--fix", is_flag=True, help="自动修复可修复的问题")
@click.option("--output", "-o", help="报告输出路径")
def lint(target: str, config: str | None, fmt: str, fix: bool, output: str | None) -> None:
    """Prompt Linter：静态检查提示词质量"""
    from ai_prompt_toolkit.cli_helpers import discover_templates, write_report, determine_exit_code
    from ai_prompt_toolkit.linter.linter import PromptLinter

    templates = discover_templates(target)
    if not templates:
        click.echo("未发现.md模板文件")
        sys.exit(0)

    linter = PromptLinter()
    all_results = []
    total_findings = 0
    total_score = 0.0

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        template_type = _detect_template_type(text)
        result = linter.lint(tpl_path.name, text, fix=fix, template_type=template_type)
        all_results.append(result)
        total_findings += result.failed_count
        total_score += result.score

        if fmt == "cli" and result.findings:
            for f in result.findings:
                sev = f.severity.value if hasattr(f.severity, 'value') else str(f.severity)
                marker = {"high": "✗", "medium": "⚠", "low": "ℹ"}.get(sev, "•")
                click.echo(f"  {marker} [{tpl_path.name}] {f.rule_id}: {f.description}")

    avg_score = total_score / max(len(all_results), 1)
    click.echo(f"\nLint完成 | 文件: {len(templates)} | 平均分: {avg_score:.1f}/100 | 问题: {total_findings}")

    if fix and any(r.auto_fixed for r in all_results):
        fixed = sum(len(r.fixed_findings) for r in all_results if r.auto_fixed)
        click.echo(f"自动修复: {fixed} 处")

    if output:
        report_data = {
            "_report_type": "lint",
            "lint_target": target,
            "total_files": len(templates),
            "average_score": round(avg_score, 1),
            "total_findings": total_findings,
            "results": [r.to_dict() for r in all_results],
        }
        write_report(report_data, output, fmt=fmt)
        click.echo(f"报告: {output}")

    has_errors = any(r.has_errors for r in all_results)
    sys.exit(determine_exit_code(has_findings=total_findings > 0, error_severity="high" if has_errors else None))


@main.command()
@click.option("--source-locale", "-s", default="zh-CN", help="源语言(BCP 47)")
@click.option("--target-locale", "-t", default="en-US", help="目标语言(BCP 47)")
@click.option("--output", "-o", help="输出目录")
@click.option("--base-dir", help="i18n资源基础目录")
def i18n(source_locale: str, target_locale: str, output: str | None,
         base_dir: str | None) -> None:
    """国际化：多语言翻译和质量报告"""
    from ai_prompt_toolkit.i18n.manager import I18nManager
    mgr = I18nManager(base_dir=base_dir)
    click.echo(f"翻译: {source_locale} → {target_locale}")
    report = mgr.generate(source_locale, target_locale, output)
    click.echo(f"覆盖率: {report.coverage_pct:.1f}%")
    click.echo(f"质量: {report.quality_pct:.1f}%")
    click.echo(f"已翻译: {report.translated}/{report.total_keys}")
    if report.missing > 0:
        click.echo(f"缺失: {report.missing}")


@main.command()
@click.option("--action", "-a", type=click.Choice(["submit", "review", "deploy", "status"]),
              required=True, help="市场操作")
@click.option("--template", "-t", help="模板ID或文件路径")
@click.option("--config", help="市场配置YAML文件路径")
def market(action: str, template: str | None, config: str | None) -> None:
    """模板市场：提交、评审、灰度发布"""
    from ai_prompt_toolkit.market.service import MarketService
    svc = MarketService()

    if action == "status" and template:
        status = svc.get_status(template)
        click.echo(json.dumps(status, ensure_ascii=False, indent=2))
    elif action == "submit" and template:
        from ai_prompt_toolkit.market.types import Template
        tpl = Template(id=template, name=template, version="1.0")
        try:
            svc.submit(tpl)
            click.echo(f"模板提交成功: {template}")
        except ValueError as e:
            click.echo(f"错误: {e}", err=True)
            sys.exit(1)
    else:
        click.echo(f"市场操作: {action}")
        if template:
            click.echo(f"模板: {template}")


@main.command(name="upgrade-fm")
@click.option("--target", "-t", required=True, help="目标目录或文件")
@click.option("--dry-run", is_flag=True, help="仅预览变更不写入")
@click.option("--locale", "-l", default="zh-CN", help="默认语言标签(BCP 47)")
def upgrade_fm(target: str, dry_run: bool, locale: str) -> None:
    """Front Matter升级：v2→v3(新增i18n_status/market_status/lint_score)"""
    from ai_prompt_toolkit.cli_helpers import discover_templates
    from ai_prompt_toolkit.frontmatter import upgrade_markdown_file

    templates = discover_templates(target)
    if not templates:
        click.echo("未发现.md模板文件")
        sys.exit(0)

    upgraded = 0
    errors_total = 0

    for tpl_path in templates:
        text = tpl_path.read_text(encoding="utf-8")
        new_text, errors = upgrade_markdown_file(text)

        if errors and errors[0].startswith("No front matter"):
            continue

        errors_total += len(errors)
        for e in errors:
            click.echo(f"  ⚠ [{tpl_path.name}] {e}")

        if dry_run:
            click.echo(f"  预览: {tpl_path.name} (i18n/market/lint_score字段已添加)")
        else:
            tpl_path.write_text(new_text, encoding="utf-8")
            click.echo(f"  升级: {tpl_path.name}")
        upgraded += 1

    click.echo(f"\nFront Matter升级完成 | 文件: {upgraded} | 验证问题: {errors_total}")
    if dry_run:
        click.echo("(dry-run模式，未写入文件)")


@main.command(name="init")
@click.option("--target", "-t", default=".", help="项目目录(默认当前目录)")
@click.option("--non-interactive", is_flag=True, help="非交互模式")
def init_project(target: str, non_interactive: bool) -> None:
    """新用户引导：3步创建AI提示词项目"""
    from ai_prompt_toolkit.onboarding import run_onboarding

    result = run_onboarding(target, non_interactive=non_interactive)
    steps = result["steps_completed"]
    errors = result.get("errors", [])

    if steps == 3:
        click.echo(f"\n引导完成! 创建了 {result['files_created']} 个文件，3步全部成功")
    else:
        click.echo(f"\n引导完成 {steps}/3 步")
        for e in errors:
            click.echo(f"  错误: {e}", err=True)

    sys.exit(0 if steps == 3 else 1)


@main.command(name="assert")
@click.option("--response", "-r", required=True, help="待验证的响应文本文件路径")
@click.option("--config", "-c", required=True, help="断言配置YAML文件路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
def assert_cmd(response: str, config: str, fmt: str) -> None:
    """断言验证：对LLM响应执行质量断言检查"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_config, write_report
    from ai_prompt_toolkit.assertion.types import AssertType, AssertionConfig
    from ai_prompt_toolkit.assertion.engine import AssertionEngine

    resp_path = resolve_path(response)
    resp_text = resp_path.read_text(encoding="utf-8")
    cfg = load_config(config)

    assertions_cfg = cfg.get("assertions", [])
    configs = []
    for item in assertions_cfg:
        atype = AssertType(item.get("type", "contains"))
        configs.append(AssertionConfig(
            assert_type=atype,
            value=item.get("value", ""),
            threshold=item.get("threshold", 0.8),
            weight=item.get("weight", 1.0),
        ))

    if not configs:
        click.echo("错误: 未配置任何断言", err=True)
        sys.exit(2)

    engine = AssertionEngine()
    results = engine.evaluate_batch(configs, response=resp_text)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if fmt == "json":
        import json as _json
        data = {"passed": passed, "total": total, "results": [r.to_dict() for r in results]}
        click.echo(_json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for r in results:
            icon = "✓" if r.passed else "✗"
            click.echo(f"  {icon} [{r.assert_type.value}] {r.reason} (分数: {r.score:.2f})")
        click.echo(f"\n断言结果: {passed}/{total} 通过")

    sys.exit(0 if passed == total else 1)


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


@main.command(name="redteam")
@click.option("--target", "-t", help="目标文本文件路径(离线模式)")
@click.option("--probes", "-p", help="探测类型(逗号分隔，默认全部)")
@click.option("--provider", help="Provider配置(provider:model_name，在线模式)")
@click.option("--output", "-o", help="输出报告路径")
@click.option("--format", "fmt", type=click.Choice(["json", "cli"]), default="cli", help="输出格式")
@click.option("--owasp", help="按OWASP LLM Top 10分类过滤(如LLM01,LLM06)")
@click.option("--top-n", type=int, default=0, help="仅运行前N个Probe")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="最低严重性过滤")
def redteam_cmd(target: str | None, probes: str | None, provider: str | None,
                output: str | None, fmt: str, owasp: str | None,
                top_n: int, severity: str | None) -> None:
    """红队探测：对抗性安全测试"""
    from ai_prompt_toolkit.redteam.probe import create_probe, get_available_probes, get_probes_by_owasp
    from ai_prompt_toolkit.redteam.detector import create_detector, get_available_detectors, LeakageDetector, ComplianceDetector, RefusalDetector
    from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator

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
        click.echo("错误: 无可用Probe", err=True)
        sys.exit(2)

    detectors = [LeakageDetector(), ComplianceDetector(), RefusalDetector()]
    orchestrator = ExplorationOrchestrator(probes=probe_instances, detectors=detectors)

    if provider:
        from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType
        from ai_prompt_toolkit.ab_test.provider import create_provider
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

    if fmt == "json":
        import json as _json
        if output:
            from ai_prompt_toolkit.cli_helpers import write_report
            write_report(report.to_dict(), output, fmt="json")
            click.echo(f"报告已保存: {output}")
        else:
            click.echo(_json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        click.echo(report.get_summary())


if __name__ == "__main__":
    main()
