"""HTML报告生成器 — 交互式折叠

功能:
- 生成独立的HTML报告(含内联CSS/JS)
- 交互式折叠: 按严重度/类别/规则分组
- 深色/浅色主题切换
- 搜索过滤
- 统计图表(纯CSS实现, 无外部依赖)
"""
from __future__ import annotations

import html
import time
from pathlib import Path

from ai_prompt_toolkit import __version__


def generate_html_report(
    results: list[dict],
    target: str,
    output_path: str | None = None,
) -> str:
    total = len(results)
    critical = sum(1 for r in results if r.get("severity") == "CRITICAL")
    high = sum(1 for r in results if r.get("severity") == "HIGH")
    medium = sum(1 for r in results if r.get("severity") == "MEDIUM")
    low = sum(1 for r in results if r.get("severity") == "LOW")
    score = results[0].get("score", 0) if results else 0

    categories: dict[str, list[dict]] = {}
    for r in results:
        cat = r.get("category", "other")
        categories.setdefault(cat, []).append(r)

    cat_sections = ""
    for cat, items in sorted(categories.items()):
        items_html = ""
        for item in items:
            sev_class = _sev_class(item.get("severity", "MEDIUM"))
            items_html += f"""
            <div class="finding {sev_class}">
                <div class="finding-header" onclick="toggleDetail(this)">
                    <span class="rule-id">{html.escape(str(item.get('rule_id', '')))}</span>
                    <span class="severity-badge {sev_class}">{html.escape(str(item.get('severity', '')))}</span>
                    <span class="finding-name">{html.escape(str(item.get('message', item.get('name', ''))))}</span>
                </div>
                <div class="finding-detail" style="display:none">
                    <p><strong>规则:</strong> {html.escape(str(item.get('rule_id', '')))} — {html.escape(str(item.get('name', '')))}</p>
                    <p><strong>严重度:</strong> {html.escape(str(item.get('severity', '')))}</p>
                    <p><strong>类别:</strong> {html.escape(str(item.get('category', '')))}</p>
                    <p><strong>消息:</strong> {html.escape(str(item.get('message', '')))}</p>
                    {f'<p><strong>修复建议:</strong> {html.escape(str(item.get("remediation", "")))}</p>' if item.get('remediation') else ''}
                </div>
            </div>"""
        cat_sections += f"""
        <div class="category-section">
            <div class="category-header" onclick="toggleCategory(this)">
                <span class="toggle-icon">&#9654;</span>
                <span class="category-name">{html.escape(cat)}</span>
                <span class="category-count">{len(items)}</span>
            </div>
            <div class="category-body" style="display:none">
                {items_html}
            </div>
        </div>"""

    report_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prompt Lint Report — {html.escape(target)}</title>
<style>
:root {{ --bg: #f8f9fa; --card: #fff; --text: #212529; --border: #dee2e6; --accent: #0d6efd; }}
[data-theme="dark"] {{ --bg: #1a1a2e; --card: #16213e; --text: #e0e0e0; --border: #334155; --accent: #60a5fa; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.header {{ background: var(--card); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
.header h1 {{ font-size: 24px; margin-bottom: 8px; }}
.header .meta {{ color: #6c757d; font-size: 14px; }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 20px 0; }}
.stat-card {{ background: var(--card); border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
.stat-card .value {{ font-size: 28px; font-weight: 700; }}
.stat-card .label {{ font-size: 12px; color: #6c757d; text-transform: uppercase; }}
.critical .value {{ color: #dc3545; }} .high .value {{ color: #fd7e14; }} .medium .value {{ color: #ffc107; }} .low .value {{ color: #20c997; }}
.toolbar {{ display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }}
.toolbar input {{ padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--card); color: var(--text); width: 300px; font-size: 14px; }}
.toolbar button {{ padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; background: var(--card); color: var(--text); cursor: pointer; font-size: 14px; }}
.toolbar button:hover {{ background: var(--accent); color: #fff; }}
.category-section {{ margin-bottom: 8px; }}
.category-header {{ background: var(--card); padding: 12px 16px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
.category-header:hover {{ background: var(--accent); color: #fff; }}
.toggle-icon {{ transition: transform 0.2s; font-size: 12px; }}
.toggle-icon.open {{ transform: rotate(90deg); }}
.category-name {{ font-weight: 600; flex: 1; }}
.category-count {{ background: var(--accent); color: #fff; border-radius: 12px; padding: 2px 8px; font-size: 12px; }}
.category-body {{ padding: 8px 0 8px 20px; }}
.finding {{ background: var(--card); border-radius: 6px; margin: 6px 0; border-left: 4px solid var(--border); }}
.finding.critical {{ border-left-color: #dc3545; }} .finding.high {{ border-left-color: #fd7e14; }} .finding.medium {{ border-left-color: #ffc107; }} .finding.low {{ border-left-color: #20c997; }}
.finding-header {{ padding: 8px 12px; cursor: pointer; display: flex; gap: 8px; align-items: center; }}
.finding-header:hover {{ background: rgba(0,0,0,0.03); }}
.rule-id {{ font-family: monospace; font-weight: 600; font-size: 13px; color: var(--accent); }}
.severity-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
.severity-badge.critical {{ background: #dc3545; color: #fff; }} .severity-badge.high {{ background: #fd7e14; color: #fff; }} .severity-badge.medium {{ background: #ffc107; color: #000; }} .severity-badge.low {{ background: #20c997; color: #fff; }}
.finding-name {{ flex: 1; font-size: 14px; }}
.finding-detail {{ padding: 12px 16px; border-top: 1px solid var(--border); font-size: 13px; }}
.finding-detail p {{ margin: 4px 0; }}
.score-bar {{ height: 8px; border-radius: 4px; background: #e9ecef; margin-top: 8px; overflow: hidden; }}
.score-fill {{ height: 100%; border-radius: 4px; background: linear-gradient(90deg, #dc3545, #fd7e14, #ffc107, #20c997); }}
</style>
</head>
<body data-theme="light">
<div class="container">
    <div class="header">
        <h1>Prompt Lint Report</h1>
        <div class="meta">
            Target: <strong>{html.escape(target)}</strong> | 
            Rules: 180 | 
            Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} | 
            v{__version__}
        </div>
        <div class="score-bar"><div class="score-fill" style="width:{max(0, min(100, score*10))}%"></div></div>
    </div>
    <div class="stats">
        <div class="stat-card critical"><div class="value">{critical}</div><div class="label">Critical</div></div>
        <div class="stat-card high"><div class="value">{high}</div><div class="label">High</div></div>
        <div class="stat-card medium"><div class="value">{medium}</div><div class="label">Medium</div></div>
        <div class="stat-card low"><div class="value">{low}</div><div class="label">Low</div></div>
        <div class="stat-card"><div class="value">{total}</div><div class="label">Total</div></div>
        <div class="stat-card"><div class="value">{score:.1f}</div><div class="label">Score</div></div>
    </div>
    <div class="toolbar">
        <input type="text" id="search" placeholder="搜索规则ID/消息..." oninput="filterFindings(this.value)">
        <button onclick="toggleAll(true)">全部展开</button>
        <button onclick="toggleAll(false)">全部折叠</button>
        <button onclick="toggleTheme()">切换主题</button>
    </div>
    <div id="categories">{cat_sections}</div>
</div>
<script>
function toggleCategory(el) {{
    const body = el.nextElementSibling;
    const icon = el.querySelector('.toggle-icon');
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    icon.classList.toggle('open', !isOpen);
}}
function toggleDetail(el) {{
    const detail = el.nextElementSibling;
    detail.style.display = detail.style.display === 'none' ? 'block' : 'none';
}}
function toggleAll(open) {{
    document.querySelectorAll('.category-body').forEach(b => b.style.display = open ? 'block' : 'none');
    document.querySelectorAll('.toggle-icon').forEach(i => i.classList.toggle('open', open));
}}
function toggleTheme() {{
    const body = document.body;
    body.dataset.theme = body.dataset.theme === 'dark' ? 'light' : 'dark';
}}
function filterFindings(query) {{
    const q = query.toLowerCase();
    document.querySelectorAll('.finding').forEach(f => {{
        const text = f.textContent.toLowerCase();
        f.style.display = text.includes(q) ? '' : 'none';
    }});
}}
</script>
</body>
</html>"""

    if output_path:
        Path(output_path).write_text(report_html, encoding="utf-8")

    return report_html


def _sev_class(severity: str) -> str:
    s = str(severity).upper()
    if s == "CRITICAL":
        return "critical"
    if s == "HIGH":
        return "high"
    if s == "MEDIUM":
        return "medium"
    return "low"
