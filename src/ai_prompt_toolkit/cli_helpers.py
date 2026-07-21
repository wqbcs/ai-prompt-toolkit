"""CLI编排辅助模块 — 路径校验/配置加载/报告写入/退出码判定"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml

from ai_prompt_toolkit.errors import ConfigError, ValidationError


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
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON格式错误 — {p}:{e.lineno}:{e.colno} {e.msg}") from e
    return data if isinstance(data, dict) else {"_root": data}


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        raise ConfigError(f"配置文件不存在 — {p}")
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML格式错误 — {p}: {e}") from e
    return data if isinstance(data, dict) else {}


def discover_templates(target: str | Path) -> list[Path]:
    p = Path(target) if not isinstance(target, Path) else target
    if p.is_file():
        return [p] if p.suffix in (".md", ".prompt") or p.name.endswith(".prompt.md") else []
    if p.is_dir():
        results: list[Path] = []
        for pattern in ("*.md", "*.prompt", "*.prompt.md"):
            results.extend(p.rglob(pattern))
        return sorted(set(results))
    raise ValidationError(f"目标不存在 — {p}", field="target")


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
    "lint": "没有发现Lint问题！你的Prompt质量很棒。试试 --gate 选项运行Quality Gate检查。",
    "scan": "没有发现安全风险！你的Prompt很安全。建议定期扫描以保持安全。",
    "evaluate": "评估结果为空。请确保目标文件包含有效的Prompt内容。",
    "version": "暂无版本记录。使用 'prompt-cli version create -s <file>' 创建第一个版本。",
    "market": "模板市场暂无模板。使用 'prompt-cli market publish' 发布你的第一个模板。",
    "ab-test": "暂无A/B测试结果。使用 'prompt-cli ab-test -c <config>' 开始第一次测试。",
    "redteam": "红队探测暂无结果。使用 'prompt-cli redteam -s <file>' 开始安全测试。",
    "default": "暂无结果。试试 'prompt-cli wizard' 开始使用工具链。",
}


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
    elapsed_str = f" ({elapsed_ms/1000:.1f}s)" if elapsed_ms > 0 else ""
    eta_str = ""
    if elapsed_ms > 0 and current > 0:
        remaining = (elapsed_ms / current) * (total - current)
        if remaining > 1000:
            eta_str = f" ~{remaining/1000:.0f}s剩余"
    return f"{label}: {current}/{total} ({pct}%){elapsed_str}{eta_str}"


_SEVERITY_STYLING = {
    "critical": ("🔴", "CRITICAL"),
    "high": ("✗", "HIGH"),
    "medium": ("⚠", "MEDIUM"),
    "low": ("ℹ", "LOW"),
    "info": ("💡", "INFO"),
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


def friendly_finding_line(template_id: str, rule_id: str, severity: str, description: str, is_multimodal: bool = False) -> str:
    marker, label = friendly_severity(severity)
    prefix = "[MM] " if is_multimodal else ""
    return f"  {marker} [{template_id}] {prefix}{rule_id} ({label}): {description}"


def friendly_lint_summary(total_files: int, avg_score: float, total_findings: int, fixed: int = 0) -> str:
    lines = [
        f"\n{'='*50}",
        f"  Lint完成 | 文件: {total_files} | 评分: {friendly_score(avg_score)} | 问题: {total_findings}",
    ]
    if fixed:
        lines.append(f"  🔧 自动修复: {fixed} 处")
    if avg_score >= 90:
        lines.append(f"  🎉 优秀！Prompt质量超过90分")
    elif avg_score >= 80:
        lines.append(f"  👍 良好！小优化可达90+")
    elif avg_score >= 70:
        lines.append(f"  💡 建议关注标记问题，提升Prompt质量")
    else:
        lines.append(f"  ⚡ 建议优先修复HIGH/CRITICAL问题")
    lines.append(f"{'='*50}")
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
