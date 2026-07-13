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
    title = data.get("template_id", data.get("scan_target", "Report"))
    findings = data.get("findings", [])
    rows = ""
    for f in findings:
        sev = f.get("severity", "info")
        color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(sev, "#3b82f6")
        rows += f'<tr><td style="color:{color};font-weight:bold">{sev.upper()}</td>'
        rows += f'<td>{f.get("rule_id", "")}</td><td>{f.get("description", "")}</td>'
        rows += f'<td>{f.get("remediation", "")}</td></tr>\n'
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title} - 扫描报告</title>
<style>body{{font-family:system-ui;max-width:960px;margin:2rem auto;padding:0 1rem}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:8px;border:1px solid #e5e7eb}}
th{{background:#f9fafb}}h1{{color:#1e293b}}</style></head>
<body><h1>扫描报告: {title}</h1>
<table><thead><tr><th>严重级别</th><th>规则ID</th><th>描述</th><th>修复建议</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""


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
        return 1
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
