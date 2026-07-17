"""CLI编排辅助模块 — 路径校验/配置加载/报告写入/退出码判定"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml


def resolve_path(path_str: str, must_exist: bool = True) -> Path:
    p = Path(path_str).resolve()
    if must_exist and not p.exists():
        print(f"错误: 路径不存在 — {p}", file=sys.stderr)
        sys.exit(2)
    return p


def load_context(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        print(f"错误: 上下文文件不存在 — {p}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: JSON格式错误 — {p}:{e.lineno}:{e.colno} {e.msg}", file=sys.stderr)
        sys.exit(2)
    return data if isinstance(data, dict) else {"_root": data}


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        print(f"错误: 配置文件不存在 — {p}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"错误: YAML格式错误 — {p}: {e}", file=sys.stderr)
        sys.exit(2)
    return data if isinstance(data, dict) else {}


def discover_templates(target: str | Path) -> list[Path]:
    p = Path(target) if not isinstance(target, Path) else target
    if p.is_file():
        return [p] if p.suffix == ".md" else []
    if p.is_dir():
        return sorted(p.rglob("*.md"))
    print(f"错误: 目标不存在 — {p}", file=sys.stderr)
    sys.exit(2)


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


def _generate_html_report(data: dict[str, Any]) -> str:
    from ai_prompt_toolkit.report.html_reporter import generate_html_report
    return generate_html_report(data)


def determine_exit_code(
    has_errors: bool = False,
    has_findings: bool = False,
    error_severity: str | None = None,
) -> int:
    if has_errors:
        return 3
    if has_findings:
        if error_severity in ("high", "critical"):
            return 1
        if error_severity == "medium":
            return 2
        return 0
    return 0


def format_findings_table(findings: Sequence[dict[str, Any]]) -> str:
    if not findings:
        return "无发现项"
    lines = []
    for f in findings:
        sev = f.get("severity", "info")
        rid = f.get("rule_id", "")
        desc = f.get("description", "")
        marker = {"high": "✗", "medium": "⚠", "low": "ℹ", "info": "ℹ"}.get(sev, "•")
        lines.append(f"  {marker} [{rid}] {desc}")
    return "\n".join(lines)


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
