"""专业级HTML报告生成器 — 安全扫描 + Lint 双模报告

参考 ESLint HTML Reporter / Snyk 报告风格:
- 顶部摘要仪表盘(SVG圆环图 + 关键指标)
- 按严重级别分组折叠面板
- 每个发现项含: 规则ID / 描述 / 位置 / 修复建议
- 批量扫描: 多文件摘要 + 单文件详情
- 暗色/亮色主题切换
- 响应式布局
"""
from __future__ import annotations

import html as html_mod
from datetime import datetime, timezone
from typing import Any

from ai_prompt_toolkit import __version__


def generate_html_report(data: dict[str, Any]) -> str:
    report_type = data.get("_report_type", "scan")
    if report_type == "lint":
        return generate_lint_html(data)
    return generate_scan_html(data)


def generate_scan_html(data: dict[str, Any]) -> str:
    data = dict(data)
    data["_report_type"] = "scan"
    findings: list[dict[str, Any]] = data.get("findings", [])
    scan_target = data.get("scan_target", data.get("template_id", "未知目标"))
    total_files = data.get("total_files", 1)
    scan_time = data.get("scan_time_ms", data.get("elapsed_ms", 0))

    critical = [f for f in findings if f.get("severity") == "critical"]
    high = [f for f in findings if f.get("severity") == "high"]
    medium = [f for f in findings if f.get("severity") == "medium"]
    low = [f for f in findings if f.get("severity") in ("low", "info")]
    total = len(findings)

    risk_level = data.get("risk_level", _assess_overall_risk(findings))
    risk_color = _risk_color(risk_level)
    risk_label = _risk_label(risk_level)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    donut_svg = _svg_donut(critical=len(critical), high=len(high),
                           medium=len(medium), low=len(low))

    summary_cards = _summary_cards(total, len(critical), len(high), len(medium), len(low),
                                   total_files, scan_time)

    grouped_sections = []
    for label, items, color, icon in [
        ("严重", critical, "#dc2626", "🔴"),
        ("高危", high, "#ef4444", "🟠"),
        ("中危", medium, "#f59e0b", "🟡"),
        ("低危/信息", low, "#22c55e", "🟢"),
    ]:
        if items:
            grouped_sections.append(_findings_section(label, items, color, icon))

    return _wrap_template(
        title=f"安全扫描报告 — {html_mod.escape(str(scan_target))}",
        risk_badge=f'<span style="background:{risk_color};color:#fff;padding:4px 14px;'
                   f'border-radius:20px;font-weight:700;font-size:1.1rem">'
                   f'{html_mod.escape(risk_label)}</span>',
        subtitle=f"扫描目标: {html_mod.escape(str(scan_target))}",
        donut=donut_svg,
        summary=summary_cards,
        body="\n".join(grouped_sections),
        timestamp=now,
        version=__version__,
    )


def generate_lint_html(data: dict[str, Any]) -> str:
    data = dict(data)
    data["_report_type"] = "lint"
    lint_target = data.get("lint_target", data.get("template_id", "未知目标"))
    total_files = data.get("total_files", 1)
    avg_score = data.get("average_score", 0)
    total_findings = data.get("total_findings", 0)
    results: list[dict[str, Any]] = data.get("results", [])

    all_findings: list[dict[str, Any]] = []
    for r in results:
        all_findings.extend(r.get("findings", []))

    high = [f for f in all_findings if f.get("severity") == "high"]
    medium = [f for f in all_findings if f.get("severity") == "medium"]
    low = [f for f in all_findings if f.get("severity") in ("low", "info")]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    score_color = "#22c55e" if avg_score >= 80 else "#f59e0b" if avg_score >= 60 else "#ef4444"
    score_svg = _svg_score_gauge(avg_score, score_color)

    score_value_html = f'<span style="font-size:2rem;color:{score_color}">{avg_score:.1f}</span>/100'
    summary = (
        f'<div class="summary-grid">'
        f'{_card("平均评分", score_value_html, "#1e293b")}'
        f'{_card("总文件数", str(total_files), "#6366f1")}'
        f'{_card("问题总数", str(total_findings), "#ef4444")}'
        f'{_card("高危", str(len(high)), "#dc2626")}'
        f'{_card("中危", str(len(medium)), "#f59e0b")}'
        f'{_card("低危", str(len(low)), "#22c55e")}'
        f'</div>'
    )

    file_sections = []
    for r in results:
        tid = r.get("template_id", "未知")
        score = r.get("score", 0)
        r_findings = r.get("findings", [])
        if not r_findings:
            continue
        sc = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
        items_html = ""
        for f in r_findings:
            sev = f.get("severity", "info")
            sev_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(sev, "#3b82f6")
            items_html += (
                f'<div class="finding-item">'
                f'<span class="sev-badge" style="background:{sev_color}">{html_mod.escape(sev.upper())}</span>'
                f'<code>{html_mod.escape(f.get("rule_id", ""))}</code> '
                f'{html_mod.escape(f.get("description", ""))}'
                f'{" — " + html_mod.escape(f.get("remediation", "")) if f.get("remediation") else ""}'
                f'</div>'
            )
        file_sections.append(
            f'<details class="file-section"><summary>'
            f'<span class="file-score" style="background:{sc}">{score:.0f}</span> '
            f'{html_mod.escape(tid)} ({len(r_findings)}个问题)</summary>'
            f'<div class="findings-list">{items_html}</div></details>'
        )

    return _wrap_template(
        title=f"Lint质量报告 — {html_mod.escape(str(lint_target))}",
        risk_badge=f'<span style="background:{score_color};color:#fff;padding:4px 14px;'
                   f'border-radius:20px;font-weight:700;font-size:1.1rem">'
                   f'{avg_score:.0f}分</span>',
        subtitle=f"Lint目标: {html_mod.escape(str(lint_target))}",
        donut=score_svg,
        summary=summary,
        body="\n".join(file_sections),
        timestamp=now,
        version=__version__,
    )


def _assess_overall_risk(findings: list[dict[str, Any]]) -> str:
    severities = {f.get("severity", "info") for f in findings}
    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities or "info" in severities:
        return "low"
    return "none"


def _risk_color(level: str) -> str:
    return {"critical": "#7f1d1d", "high": "#dc2626", "medium": "#f59e0b",
            "low": "#22c55e", "none": "#6b7280"}.get(level, "#6b7280")


def _risk_label(level: str) -> str:
    return {"critical": "极高风险", "high": "高风险", "medium": "中等风险",
            "low": "低风险", "none": "无风险"}.get(level, "未知")


def _svg_donut(critical: int, high: int, medium: int, low: int) -> str:
    total = critical + high + medium + low
    if total == 0:
        return ('<svg viewBox="0 0 120 120" width="120" height="120">'
                '<circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="14"/>'
                '<text x="60" y="65" text-anchor="middle" font-size="18" font-weight="700" fill="#22c55e">'
                '安全</text></svg>')

    segments = [
        (critical, "#7f1d1d"), (high, "#ef4444"), (medium, "#f59e0b"), (low, "#22c55e"),
    ]
    circumference = 2 * 3.14159 * 50
    offset = 0
    paths = ""
    for count, color in segments:
        if count == 0:
            continue
        pct = count / total
        dash = pct * circumference
        gap = circumference - dash
        rotation = (offset / total) * 360 - 90
        paths += (f'<circle cx="60" cy="60" r="50" fill="none" stroke="{color}" '
                  f'stroke-width="14" stroke-dasharray="{dash:.2f} {gap:.2f}" '
                  f'transform="rotate({rotation:.2f} 60 60)"/>')
        offset += count

    return (f'<svg viewBox="0 0 120 120" width="140" height="140">'
            f'{paths}'
            f'<text x="60" y="55" text-anchor="middle" font-size="22" font-weight="700" fill="#1e293b">'
            f'{total}</text>'
            f'<text x="60" y="72" text-anchor="middle" font-size="10" fill="#64748b">发现项</text>'
            f'</svg>')


def _svg_score_gauge(score: float, color: str) -> str:
    circumference = 2 * 3.14159 * 50
    dash = (score / 100) * circumference
    gap = circumference - dash
    return (f'<svg viewBox="0 0 120 120" width="140" height="140">'
            f'<circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="14"/>'
            f'<circle cx="60" cy="60" r="50" fill="none" stroke="{color}" stroke-width="14" '
            f'stroke-dasharray="{dash:.2f} {gap:.2f}" transform="rotate(-90 60 60)" '
            f'stroke-linecap="round"/>'
            f'<text x="60" y="60" text-anchor="middle" font-size="24" font-weight="700" fill="{color}">'
            f'{score:.0f}</text>'
            f'<text x="60" y="75" text-anchor="middle" font-size="10" fill="#64748b">评分</text>'
            f'</svg>')


def _card(label: str, value: str, accent: str) -> str:
    return (f'<div class="card" style="border-left:4px solid {accent}">'
            f'<div class="card-label">{html_mod.escape(label)}</div>'
            f'<div class="card-value">{value}</div></div>')


def _summary_cards(total: int, critical: int, high: int, medium: int, low: int,
                   files: int, elapsed: float) -> str:
    return (
        f'<div class="summary-grid">'
        f'{_card("发现项总数", str(total), "#6366f1")}'
        f'{_card("严重", str(critical), "#7f1d1d")}'
        f'{_card("高危", str(high), "#ef4444")}'
        f'{_card("中危", str(medium), "#f59e0b")}'
        f'{_card("低危/信息", str(low), "#22c55e")}'
        f'{_card("扫描文件", str(files), "#3b82f6")}'
        f'{_card("耗时", f"{elapsed:.1f}ms" if elapsed else "-", "#8b5cf6")}'
        f'</div>'
    )


def _findings_section(label: str, items: list[dict[str, Any]], color: str,
                      icon: str) -> str:
    rows = ""
    for idx, f in enumerate(items, 1):
        sev = f.get("severity", "info")
        rid = html_mod.escape(f.get("rule_id", ""))
        desc = html_mod.escape(f.get("description", ""))
        location = html_mod.escape(f.get("location", ""))
        remediation = html_mod.escape(f.get("remediation", ""))
        details = f.get("details", {})

        details_html = ""
        if details:
            details_items = ""
            for k, v in details.items():
                val = html_mod.escape(str(v)) if not isinstance(v, list) else html_mod.escape(", ".join(str(x) for x in v))
                details_items += f"<dt>{html_mod.escape(str(k))}</dt><dd>{val}</dd>"
            details_html = f'<details class="details-expand"><summary>详情</summary><dl class="details-dl">{details_items}</dl></details>'

        remediation_html = ""
        if remediation:
            remediation_html = f'<div class="remediation"><strong>修复建议:</strong> {remediation}</div>'

        rows += (
            f'<div class="finding-item" data-severity="{html_mod.escape(sev)}">'
            f'<div class="finding-header">'
            f'<span class="sev-badge" style="background:{color}">{html_mod.escape(sev.upper())}</span>'
            f'<code class="rule-id">{rid}</code>'
            f'<span class="finding-num">#{idx}</span>'
            f'</div>'
            f'<div class="finding-desc">{desc}</div>'
            f'{"<div class=\"finding-location\"><strong>位置:</strong> " + location + "</div>" if location else ""}'
            f'{remediation_html}'
            f'{details_html}'
            f'</div>'
        )

    return (
        f'<section class="severity-group">'
        f'<h3 style="color:{color};border-bottom:2px solid {color}">'
        f'{icon} {html_mod.escape(label)} ({len(items)})</h3>'
        f'<div class="findings-list">{rows}</div>'
        f'</section>'
    )


def _wrap_template(title: str, risk_badge: str, subtitle: str, donut: str,
                   summary: str, body: str, timestamp: str, version: str = "0.0.0") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--primary:#6366f1;--bg:#ffffff;--surface:#f8fafc;--text:#1e293b;--text2:#64748b;--border:#e2e8f0}}
[data-theme="dark"]{{--primary:#818cf8;--bg:#0f172a;--surface:#1e293b;--text:#f1f5f9;--text2:#94a3b8;--border:#334155}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
background:var(--bg);color:var(--text);line-height:1.6;padding:2rem;transition:background .3s,color .3s}}
.container{{max-width:1100px;margin:0 auto}}
header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:2rem;
padding-bottom:1.5rem;border-bottom:1px solid var(--border)}}
.header-left{{display:flex;align-items:center;gap:1rem}}
h1{{font-size:1.5rem;font-weight:700}}
.subtitle{{color:var(--text2);font-size:.9rem;margin-top:.25rem}}
.theme-toggle{{background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:6px 14px;cursor:pointer;font-size:.85rem;color:var(--text)}}
.theme-toggle:hover{{border-color:var(--primary)}}
.dashboard{{display:flex;gap:2rem;align-items:flex-start;margin-bottom:2rem;
padding:1.5rem;background:var(--surface);border-radius:12px;border:1px solid var(--border)}}
.donut-area{{flex-shrink:0}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem;flex:1}}
.card{{background:var(--bg);padding:1rem;border-radius:8px;border:1px solid var(--border)}}
.card-label{{font-size:.8rem;color:var(--text2);text-transform:uppercase;letter-spacing:.05em}}
.card-value{{font-size:1.4rem;font-weight:700;margin-top:.25rem}}
.severity-group{{margin-bottom:1.5rem}}
.severity-group h3{{font-size:1.1rem;padding:.5rem 0;display:flex;align-items:center;gap:.5rem}}
.findings-list{{display:flex;flex-direction:column;gap:.75rem}}
.finding-item{{background:var(--surface);padding:1rem;border-radius:8px;border:1px solid var(--border)}}
.finding-header{{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem}}
.sev-badge{{color:#fff;padding:2px 10px;border-radius:4px;font-size:.75rem;font-weight:700;letter-spacing:.05em}}
.rule-id{{font-family:'SF Mono',Consolas,monospace;font-size:.85rem;color:var(--primary)}}
.finding-num{{margin-left:auto;color:var(--text2);font-size:.8rem}}
.finding-desc{{font-size:.95rem;margin-bottom:.5rem}}
.finding-location{{font-size:.85rem;color:var(--text2)}}
.remediation{{font-size:.85rem;color:var(--text2);background:var(--bg);padding:.5rem .75rem;
border-radius:6px;margin-top:.5rem;border-left:3px solid #22c55e}}
.details-expand{{margin-top:.5rem}}
.details-expand summary{{cursor:pointer;font-size:.85rem;color:var(--primary)}}
.details-dl{{display:grid;grid-template-columns:auto 1fr;gap:.25rem 1rem;margin-top:.5rem;
font-size:.8rem;font-family:monospace}}
.details-dl dt{{color:var(--text2)}}
.details-dl dd{{color:var(--text)}}
.file-section{{margin-bottom:.75rem}}
.file-section summary{{cursor:pointer;padding:.75rem 1rem;background:var(--surface);
border:1px solid var(--border);border-radius:8px;font-weight:600;display:flex;align-items:center;gap:.75rem}}
.file-section summary:hover{{border-color:var(--primary)}}
.file-score{{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;
border-radius:50%;color:#fff;font-weight:700;font-size:.8rem}}
footer{{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--border);text-align:center;
font-size:.8rem;color:var(--text2)}}
@media(max-width:768px){{
.dashboard{{flex-direction:column}}
.summary-grid{{grid-template-columns:repeat(2,1fr)}}
}}
</style>
</head>
<body>
<div class="container">
<header>
<div class="header-left">
<div>
<h1>{title}</h1>
<div class="subtitle">{subtitle}</div>
</div>
{risk_badge}
</div>
<button class="theme-toggle" onclick="toggleTheme()">切换主题</button>
</header>

<div class="dashboard">
<div class="donut-area">{donut}</div>
{summary}
</div>

{body}

<footer>生成时间: {timestamp} | ai-prompt-toolkit v{version}</footer>
</div>

<script>
function toggleTheme(){{{{
const t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
document.documentElement.setAttribute('data-theme',t);
localStorage.setItem('theme',t);
}}}}
(function(){{{{
const s=localStorage.getItem('theme');
if(s)document.documentElement.setAttribute('data-theme',s);
else if(window.matchMedia('(prefers-color-scheme:dark)').matches)
document.documentElement.setAttribute('data-theme','dark');
}}}})();
</script>
</body>
</html>"""
