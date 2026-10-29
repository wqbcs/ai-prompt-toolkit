"""CLI编排辅助模块 — 路径校验/配置加载/报告写入/退出码判定"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import yaml

from ai_prompt_toolkit.errors import ConfigError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


def resolve_path(path_str: str, must_exist: bool = True) -> Path:
    p = Path(path_str).resolve()
    if must_exist and not p.exists():
        raise ValidationError(f"路径不存在 — {p}", field="path")
    return p


def load_context(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        raise ConfigError(f"上下文文件不存在 — {p}")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON格式错误 — {p}:{e.lineno}:{e.colno} {e.msg}") from e
    return data if isinstance(data, dict) else {"_root": data}


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        raise ConfigError(f"配置文件不存在 — {p}")
    try:
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML格式错误 — {p}: {e}") from e
    return data if isinstance(data, dict) else {}


# R252-I-2: 目录扫描默认排除目录（单一真源，lint/scan/auto_discover 共用）。
# 依据：竞品 Whitney/agentlint 同构实践——"finding inside a dependency tree /
# test fixture is a false positive from the developer's perspective"。这些目录是
# 依赖树/构建产物/缓存，永不承载用户 prompt 语料；rglob 命中它们=FP 假象 + 扫描变慢。
# 纯数据驱动（frozenset，非 if/else 链）。与 .promptignore 正交：后者是用户可加
# 的*额外*排除层；本清单是硬排除（依赖树非语料，无真实"重新包含 node_modules"需求）。
DEFAULT_EXCLUDE_DIRS = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        "site-packages",
        ".prompt-toolkit-cache",
        ".mypy_cache",
        ".ruff_cache",
        "target",
    }
)


def _in_default_excluded(path: Path, base: Path) -> bool:
    """path 相对 base 的任一段落在 DEFAULT_EXCLUDE_DIRS 内 → 排除。
    对非 base 下文件（相对失败）返回 False（不排除，交给上层判定）。"""
    try:
        rel = path.relative_to(base)
    except ValueError:
        return False
    return any(part in DEFAULT_EXCLUDE_DIRS for part in rel.parts)


def discover_templates(target: str | Path) -> list[Path]:
    p = Path(target) if not isinstance(target, Path) else target
    if p.is_file():
        # R341-F-2: 显式文件目标扩展名无关 — 存在即 lint 目标。
        # 原仅认 .md/.prompt: .txt 等真实存在的文件被静默丢弃 → 假"很干净" rc=0
        # (对 0 个文件宣称干净 = 安全工具契约破损; 目录 glob 面不受影响)
        return [p]
    if p.is_dir():
        results: list[Path] = []
        for pattern in ("*.md", "*.prompt", "*.prompt.md"):
            results.extend(p.rglob(pattern))
        # R252-I-2: 剔除依赖树/构建产物/缓存下的文件（FP 削减，单一真源）
        return sorted({r for r in results if not _in_default_excluded(r, p)})
    raise ValidationError(f"目标不存在 — {p}", field="target")


def read_prompt_text(path: Path) -> str:
    """R341-F-2: prompt 文件统一读取面 — UTF-8 严格。

    显式目标扩展名无关后, 二进制/非 UTF-8 目标会真实进入 lint 循环 —
    裸 read_text 抛 UnicodeDecodeError → 顶层 Traceback。此处统一转
    ValidationError(顶层捕获 → 人话报错 + rc=2, 与"目标不存在"同退出码)。
    i18n 解码面不在范围(反清单约束: 不做 GBK 等回退)。
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValidationError(f"文件非有效 UTF-8, 无法解码 — {path}", field="target") from e


def git_changed_since_rev(rev: str, cwd: Path | None = None, base_dir: str = ".") -> list[Path] | None:
    """P2-17: git 原生增量 — 返回 <rev> 之后有变更(含 rev 内新增/删除)的
    prompt 模板路径(相对 base_dir 的 Path 列表)。

    语义边界(诚实声明, 5 年不变量③):
    - 只覆盖 **tracked 且相对 rev 有变更** 的文件 — untracked(未入 git 的
      全新文件)不在 diff 内, 不覆盖; 这是 brownfield "对变更负责" 的
      设计语义, 非缺陷
    - 删除文件在 diff --name-only 内但已不存在 → 调用方按 exists() 过滤
    - 非 git 仓库 / rev 不存在 / git 不可用 → 返回 None(调用方给清晰错误)

    复用 --changed 的 subprocess 形态(零新依赖, git 是仓库固有前提)。
    """
    import subprocess

    cmd = ["git", "diff", "--name-only", rev, "--", "*.md", "*.prompt", "*.prompt.md"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or base_dir)
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    out = Path(base_dir)
    files = [out / line.strip() for line in proc.stdout.splitlines() if line.strip()]
    # 删除文件已不存在 → 过滤(门禁只对现存文件有效)
    return [p for p in files if p.exists()]


def git_show_at_ref(ref: str, path: str, cwd: Path | None = None) -> str | None:
    """P3-20: 基线防伪造 — 读 git <ref> 上 <path> 的内容 (git show ref:path)。

    安全语义: ref 由 operator/CI 提供(平台事件给出的 base 分支或 base sha),
    PR 作者无法篡改该 ref 上的基线文件 — 堵住 "--incremental --baseline 读
    PR head 工作树基线 = 门禁自废" 的自抑制伪造缺口。
    参照系: path 可仓库根相对(CI 标准形态)或 CWD 相对(任意子目录) — 内部
    解析为绝对路径后经 git rev-parse --show-toplevel 转仓库根相对, 与
    worktree 读取面同一参照系(R331 code_review P3: 双参照致子目录运行误导
    报错); 仓库外路径=不存在。
    非 git 仓库 / ref 不存在 / 该 ref 上路径不存在 / 仓库外路径 → 返回 None
    (调用方给清晰错误, 安全失败)。
    与 git_changed_since_rev 同形态(零新依赖, git 是仓库固有前提)。
    """
    import subprocess

    base = Path.cwd() if cwd is None else Path(cwd)
    p = Path(path)
    p = p if p.is_absolute() else base / p
    try:
        root_proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=base, timeout=30
        )
    except (OSError, FileNotFoundError, subprocess.SubprocessError):
        return None
    if root_proc.returncode != 0:
        return None
    try:
        # resolve(两侧)对齐符号链接面; strict=False 默认 — ref 上存在而工作树
        # 不存在的文件也能解析
        rel = p.resolve().relative_to(Path(root_proc.stdout.strip()).resolve())
    except (ValueError, OSError):
        return None  # 仓库外路径(或不可解析) — 安全失败
    # git rev:path 语法要求正斜杠(仓库根相对); Windows 的 Path str 为反斜杠
    # (baselines\baseline.json) → as_posix 归一, 否则 git show 找不到路径
    # (Windows 独有坑实测抓出)
    posix_path = rel.as_posix()
    cmd = ["git", "show", f"{ref}:{posix_path}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=base, timeout=30)
    except (OSError, FileNotFoundError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def load_promptignore(directory: Path) -> list[str]:
    """加载 .promptignore 模式。P4-04: 发现走 project_config 单一真源
    (向上查找, git 根锚定, 就近优先) — 此前只查 directory 一层,
    子目录运行找不到仓库根的 ignore 文件。匹配 base 保持 directory
    (patterns 是相对被扫目录的, 发现位置不影响匹配口径)。"""
    from ai_prompt_toolkit.linter.project_config import find_promptignore

    ignore_file = find_promptignore(directory)
    if ignore_file is None:
        return []
    lines = ignore_file.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def should_ignore(filepath: Path, base_dir: Path, patterns: list[str]) -> bool:
    import fnmatch

    try:
        rel = filepath.relative_to(base_dir)
        rel_str = str(rel).replace("\\", "/")
    except ValueError:
        return False
    ignored = False
    for pat in patterns:
        if pat.startswith("!"):
            if fnmatch.fnmatch(rel_str, pat[1:]):
                ignored = False
        else:
            if fnmatch.fnmatch(rel_str, pat) or fnmatch.fnmatch(rel_str, pat.rstrip("/") + "/*"):
                ignored = True
    return ignored


def discover_templates_with_ignore(target: str | Path, ignore_file: str | None = None) -> list[Path]:
    templates = discover_templates(target)
    base = Path(target) if not isinstance(target, Path) else target
    if not base.is_dir():
        return templates
    patterns = []
    if ignore_file:
        ip = Path(ignore_file)
        if ip.exists():
            patterns = [
                l.strip()
                for l in ip.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.strip().startswith("#")
            ]
    if not patterns:
        patterns = load_promptignore(base)
    if not patterns:
        return templates
    return [t for t in templates if not should_ignore(t, base, patterns)]


def auto_discover_targets(target: str | None = None) -> list[Path]:
    if target:
        return discover_templates(target)
    cwd = Path.cwd()
    results: list[Path] = []
    for pattern in ("*.prompt.md", "*.prompt", "*.md"):
        results.extend(cwd.glob(pattern))
    if not results:
        for d in ("prompts", "templates", "_scenarios"):
            dp = cwd / d
            if dp.is_dir():
                for pattern in ("*.md", "*.prompt", "*.prompt.md"):
                    results.extend(dp.rglob(pattern))
    return sorted(set(results))[:50]


# R348: 报告面墙钟字段 — 确定性楔子契约覆盖裁决面(findings/score/verdict),
# 墙钟在契约外(与 test_stdio_protocol.py 剥离 lint_time_ms 同口径)。
# 落盘报告工件必须同输入重跑逐字节一致(README『SARIF/JSON 确定性序列化』声明)。
_WALLCLOCK_KEYS = frozenset({"lint_time_ms", "scan_time_ms"})


def report_result_dicts(results: list[Any]) -> list[dict[str, Any]]:
    """报告 results 行: to_dict 去墙钟字段 — 确定性裁决面工件(供落盘报告)。"""
    return [{k: v for k, v in r.to_dict().items() if k not in _WALLCLOCK_KEYS} for r in results]


def write_report(data: dict[str, Any], path: str | Path, fmt: str = "json") -> None:
    p = Path(path) if not isinstance(path, Path) else path
    p.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif fmt == "html":
        html = _generate_html_report(data)
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
    elif fmt == "markdown":
        md = _generate_markdown_report(data)
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)
    elif fmt == "yaml":
        import yaml

        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    elif fmt == "csv":
        _generate_csv_report(data, p)


def _generate_csv_report(data: dict[str, Any], path: Path) -> None:
    import csv

    results = data.get("results", [])
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["template_id", "rule_id", "severity", "description"])
        for r in results:
            tid = r.get("template_id", "")
            for finding in r.get("findings", []):
                sev = finding.get("severity", "")
                if hasattr(sev, "value"):
                    sev = sev.value
                writer.writerow([tid, finding.get("rule_id", ""), sev, finding.get("description", "")])


def _generate_html_report(data: dict[str, Any]) -> str:
    from ai_prompt_toolkit.report.html_reporter import generate_html_report

    return generate_html_report(data)


def _generate_markdown_report(data: dict[str, Any]) -> str:
    from ai_prompt_toolkit.report.markdown_reporter import generate_markdown_report

    return generate_markdown_report(data)


def determine_exit_code(
    has_errors: bool = False,
    has_findings: bool = False,
    error_severity: str | None = None,
) -> int:
    if has_errors:
        return 3
    if has_findings:
        if error_severity in ("high", "critical"):
            return 2
        if error_severity == "medium":
            return 1
        return 0
    return 0


def expand_rule_ids(spec: str) -> list[str]:
    """R213-P1-7: 逗号分隔的规则ID规范 → 具体规则ID列表(支持前缀)。

    "P161" 精确; "P16" 前缀 → 全部 P16x; 未知条目(无精确也无前缀匹配)
    忽略并 stderr 警告(错字不该弄崩 lint — fail safe, 与 waiver 同纪律)。
    参考: ContextHound --excludeRules 的 prefix-glob 语义。
    """
    import sys as _sys

    from ai_prompt_toolkit.linter.rules import get_all_rules  # 局部导入防循环引用

    known = {r.rule_id for r in get_all_rules()}
    out: set[str] = set()
    for tok in spec.split(","):
        tok = tok.strip().upper()
        if not tok:
            continue
        if tok in known:
            out.add(tok)
            continue
        matched = {r for r in known if r.startswith(tok)}
        if matched:
            out |= matched
        else:
            print(f"警告: 规则 {tok} 不存在(精确与前缀均无匹配), 已忽略", file=_sys.stderr)
    return sorted(out)


EXIT_CODE_MEANINGS = {
    0: "PASS — 通过，无问题",
    1: "WARN — 警告，存在中等风险",
    2: "FAIL — 失败，存在高危/严重风险",
    3: "ERROR — 执行错误",
}


def format_findings_table(findings: Sequence[dict[str, Any]]) -> str:
    if not findings:
        return "无发现项"
    from ai_prompt_toolkit.output import findings_list

    findings_list(findings)
    return ""


_EMPTY_STATE_TIPS: dict[str, str] = {
    "lint": """
 ┌──────────────────────────────────────┐
 │  ✨ Lint结果为空 — 你的Prompt很干净！  │
 │                                      │
 │  3步快速开始:                         │
 │  1. prompt-cli init -t general       │
 │  2. prompt-cli lint -t ./prompts     │
 │  3. prompt-cli lint --gate -t ./prompts │
 └──────────────────────────────────────┘""",
    "scan": """
 ┌──────────────────────────────────────┐
 │  🛡️ 安全扫描为空 — 无安全风险！       │
 │                                      │
 │  建议: 定期运行 scan 以保持安全       │
 │  prompt-cli scan -t ./prompts        │
 └──────────────────────────────────────┘""",
    "evaluate": """
 ┌──────────────────────────────────────┐
 │  📊 评估结果为空                      │
 │                                      │
 │  请确保目标包含有效Prompt:            │
 │  prompt-cli evaluate -t ./prompts    │
 │  prompt-cli evaluate -t . --quick    │
 └──────────────────────────────────────┘""",
    "version": "暂无版本记录。使用 'prompt-cli version create -s <file>' 创建第一个版本。",
    "market": "模板市场暂无模板。使用 'prompt-cli market publish' 发布你的第一个模板。",
    "ab-test": """
 ┌──────────────────────────────────────┐
 │  🧪 暂无A/B测试结果                   │
 │                                      │
 │  快速开始:                            │
 │  prompt-cli ab-test -c config.yaml   │
 └──────────────────────────────────────┘""",
    "redteam": """
 ┌──────────────────────────────────────┐
 │  🎯 红队探测暂无结果                   │
 │                                      │
 │  快速开始:                            │
 │  prompt-cli redteam -t ./prompt.md   │
 │  prompt-cli redteam --owasp LLM01    │
 └──────────────────────────────────────┘""",
    "default": "暂无结果。试试 'prompt-cli wizard' 开始使用工具链。",
}


def lint_grade(score: float) -> str:
    """Lint百分制→等级(与security/prompt_scorecard的等级阈值一致: A≥90/B≥75/C≥60)"""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def clean_result_next_steps(avg_score: float, file_count: int) -> str:
    """D3: lint全部通过时的空状态引导 — 分数/等级/下一步命令建议"""
    grade = lint_grade(avg_score)
    return (
        f"\n✨ 全部通过 — 等级 {grade} ({avg_score:.1f}/100), 共{file_count}个文件\n"
        "下一步建议:\n"
        "  prompt-cli badge -t <目标>                  生成质量徽章(SVG)\n"
        "  prompt-cli eval -t <目标>                   130维深度质量评估\n"
        "  prompt-cli lint -t <目标> --baseline-save   保存基线, 后续--changed增量检查\n"
        "  prompt-cli scan -t <目标>                   安全纵深扫描(注入/PII/供应链)"
    )


def empty_state_tip(command: str) -> str:
    return _EMPTY_STATE_TIPS.get(command, _EMPTY_STATE_TIPS["default"])


def friendly_progress_label(stage: str, current: int, total: int, elapsed_ms: float = 0) -> str:
    labels = {
        "lint": "Lint检查",
        "scan": "安全扫描",
        "evaluate": "质量评估",
        "compile": "条件编译",
        "redteam": "红队探测",
        "ab-test": "A/B测试",
        "default": "处理中",
    }
    label = labels.get(stage, labels["default"])
    pct = int(current / max(total, 1) * 100)
    elapsed_str = f" ({elapsed_ms / 1000:.1f}s)" if elapsed_ms > 0 else ""
    eta_str = ""
    if elapsed_ms > 0 and current > 0:
        remaining = (elapsed_ms / current) * (total - current)
        if remaining > 1000:
            eta_str = f" ~{remaining / 1000:.0f}s剩余"
    return f"{label}: {current}/{total} ({pct}%){elapsed_str}{eta_str}"


_SEVERITY_STYLING = {
    "critical": ("🔴", "CRITICAL"),
    "high": ("✗", "HIGH"),
    "medium": ("⚠", "MEDIUM"),
    "low": ("ℹ", "LOW"),
    "info": ("💡", "INFO"),
}

_SEVERITY_RICH_STYLE = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim",
    "info": "blue",
}

_SCORE_EMOJI = {
    (90, 101): "🌟",
    (80, 90): "✅",
    (70, 80): "⚠️",
    (60, 70): "🔶",
    (0, 60): "❌",
}


def friendly_severity(severity: str) -> tuple[str, str]:
    key = severity.lower() if isinstance(severity, str) else str(severity).lower()
    return _SEVERITY_STYLING.get(key, ("•", key.upper()))


def friendly_score(score: float) -> str:
    for (lo, hi), emoji in _SCORE_EMOJI.items():
        if lo <= score < hi:
            return f"{emoji} {score:.1f}/100"
    return f"{score:.1f}/100"


def friendly_finding_line(
    template_id: str, rule_id: str, severity: str, description: str, is_multimodal: bool = False
) -> str:
    marker, label = friendly_severity(severity)
    prefix = "[MM] " if is_multimodal else ""
    return f"  {marker} [{template_id}] {prefix}{rule_id} ({label}): {description}"


def friendly_lint_summary(total_files: int, avg_score: float, total_findings: int, fixed: int = 0) -> str:
    lines = [
        f"\n{'=' * 50}",
        f"  Lint完成 | 文件: {total_files} | 评分: {friendly_score(avg_score)} | 问题: {total_findings}",
    ]
    if fixed:
        lines.append(f"  🔧 自动修复: {fixed} 处")
    if avg_score >= 90:
        lines.append("  🎉 优秀！Prompt质量超过90分")
    elif avg_score >= 80:
        lines.append("  👍 良好！小优化可达90+")
    elif avg_score >= 70:
        lines.append("  💡 建议关注标记问题，提升Prompt质量")
    else:
        lines.append("  ⚡ 建议优先修复HIGH/CRITICAL问题")
    lines.append(f"{'=' * 50}")
    return "\n".join(lines)


def friendly_fix_suggestion(rule_id: str, description: str) -> str:
    _QUICK_FIXES = {
        "P001": "💡 在Prompt开头添加明确的# 角色定义",
        "P003": "💡 添加'约束'章节，使用'必须/不得'等确定性表述",
        "P009": "💡 添加'审计追踪'章节，记录关键决策点",
        "P010": "💡 添加'错误处理'章节，覆盖空输入/异常/歧义场景",
        "P018": "💡 添加Few-shot示例，展示期望的输入/输出格式",
        "P020": "💡 添加'输出质量标准'，明确评分维度和合格线",
        "P025": "💡 添加输出长度约束，如'控制在500字以内'",
        "P051": "🔒 移除硬编码凭据，使用{{API_KEY}}占位符",
        "P054": "📱 替换Android API为@ohos等效接口",
    }
    return _QUICK_FIXES.get(rule_id, f"💡 修复 {rule_id}: {description}")


def print_rich_findings(results: list[Any], console: Any = None) -> None:
    try:
        from rich.console import Console as _Console
        from rich.panel import Panel as _Panel  # noqa: F401 — 可用性探测
        from rich.text import Text as _Text
    except ImportError:
        for result in results:
            for f in result.findings:
                sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                click.echo(friendly_finding_line(result.template_id, f.rule_id, sev, f.description))
        return

    if console is None:
        console = _Console()

    for result in results:
        if not result.findings:
            console.print(f"  [green]✓[/green] {result.template_id}: [green]No issues[/green]")
            continue
        for f in result.findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sev_key = sev.lower()
            style = _SEVERITY_RICH_STYLE.get(sev_key, "white")
            marker, label = friendly_severity(sev)
            is_mm = f.rule_id.startswith("MM-")
            prefix = "[MM] " if is_mm else ""
            text = _Text()
            text.append(f"  {marker} ")
            text.append(f"[{result.template_id}] ", style="cyan")
            text.append(f"{prefix}{f.rule_id} ", style="bold")
            text.append(f"({label}) ", style=style)
            text.append(f.description[:120])
            console.print(text)
            if sev in ("high", "critical"):
                suggestion = friendly_fix_suggestion(f.rule_id, f.description)
                console.print(f"    [dim]{suggestion}[/dim]")


def print_rich_lint_summary(
    total_files: int, avg_score: float, total_findings: int, fixed: int = 0, console: Any = None
) -> None:
    try:
        from rich.console import Console as _Console
        from rich.panel import Panel as _Panel
    except ImportError:
        click.echo(friendly_lint_summary(total_files, avg_score, total_findings, fixed))
        return

    if console is None:
        console = _Console()

    if avg_score >= 90:
        score_color = "green"
        verdict = "🎉 优秀！"
    elif avg_score >= 80:
        score_color = "cyan"
        verdict = "👍 良好！"
    elif avg_score >= 70:
        score_color = "yellow"
        verdict = "💡 建议优化"
    else:
        score_color = "red"
        verdict = "⚡ 需修复HIGH/CRITICAL"

    lines = [
        f"文件: [bold]{total_files}[/bold]  |  评分: [{score_color}]{avg_score:.1f}/100[/{score_color}]  |  问题: [bold]{total_findings}[/bold]",
    ]
    if fixed:
        lines.append(f"🔧 自动修复: [bold green]{fixed}[/bold green] 处")
    lines.append(verdict)

    console.print(_Panel("\n".join(lines), title="Lint完成", border_style=score_color))


def print_rich_evaluate_summary(reports: list[Any], threshold: float = 0.0, console: Any = None) -> None:
    try:
        from rich.console import Console as _Console
        from rich.table import Table as _Table
    except ImportError:
        return

    if console is None:
        console = _Console()

    table = _Table(title="评估报告", show_lines=False)
    table.add_column("模板", style="cyan", width=30)
    table.add_column("均分", width=10)
    table.add_column("维度", width=8)
    table.add_column("状态", width=8)

    low_items = []
    for report in reports:
        scores = report.scores
        if not scores:
            continue
        avg = sum(s.score for s in scores) / len(scores)
        tid = report.template_id if hasattr(report, "template_id") else "unknown"
        if avg >= 8:
            status = "[green]✓[/green]"
        elif avg >= 6:
            status = "[yellow]⚠[/yellow]"
        else:
            status = "[red]✗[/red]"
        table.add_row(tid, f"{avg:.1f}/10", str(len(scores)), status)
        if threshold > 0 and avg < threshold:
            low_items.append((tid, avg))

    console.print(table)

    if low_items:
        console.print(f"\n[red]低于阈值({threshold})的模板({len(low_items)}个):[/red]")
        for tid, score in low_items[:5]:
            console.print(f"  [red]{tid}[/red]: {score:.1f}/10")
