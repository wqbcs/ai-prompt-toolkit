"""prompt-cli统一入口 — v28.0.0 CLI深度集成版"""
from __future__ import annotations

import json
import sys
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
    """AI提示词体系工具链 v28.0.0"""
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
def ab_test(config: str, models: str | None, dataset: str | None,
            output: str | None) -> None:
    """A/B测试：多模型并行对比提示词效果"""
    from ai_prompt_toolkit.cli_helpers import resolve_path, load_config
    cfg = load_config(config)
    model_list = models.split(",") if models else cfg.get("models", [])
    click.echo(f"A/B测试 | 模型: {', '.join(model_list)}")
    if dataset:
        click.echo(f"数据集: {dataset}")
    click.echo("提示: Provider真实API调用需要配置环境变量(OPENAI_API_KEY等)")


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


if __name__ == "__main__":
    main()
