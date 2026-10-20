"""评估矩阵可视化报告——参考promptfoo Viewer静态HTML报告模式

核心特性:
- 静态HTML报告: 评估结果内嵌到自包含HTML, 零外部依赖
- 评估矩阵: provider × prompt × test case 三维可视化
- 色彩编码: pass/fail/warning状态直观展示
- 可折叠: 详细输出和断言结果可展开查看
- GEPA优化历史: 进化树+Pareto前沿可视化

技术栈:
- Jinja2模板渲染
- 内嵌CSS/JS, 无外部依赖
- Alpine.js轻量交互(可选CDN)
"""

from __future__ import annotations

import html
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_prompt_toolkit import __version__  # R236-P2-19: 报告页版本动态(同 R174 先例)


@dataclass
class MatrixCell:
    prompt_name: str
    evaluator_name: str
    test_case: str = ""
    score: float = 0.0
    max_score: float = 10.0
    passed: bool = False
    output: str = ""
    feedback: str = ""
    execution_time_ms: float = 0.0

    @property
    def status_class(self) -> str:
        if self.passed:
            ratio = self.score / self.max_score if self.max_score > 0 else 0
            if ratio >= 0.9:
                return "cell-excellent"
            elif ratio >= 0.7:
                return "cell-good"
            else:
                return "cell-pass"
        return "cell-fail"

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_name": self.prompt_name,
            "evaluator_name": self.evaluator_name,
            "test_case": self.test_case,
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "passed": self.passed,
            "output": self.output[:500],
            "feedback": self.feedback[:200],
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class MatrixReport:
    title: str = "AI Prompt Toolkit 评估矩阵"
    prompt_names: list[str] = field(default_factory=list)
    evaluator_names: list[str] = field(default_factory=list)
    test_cases: list[str] = field(default_factory=list)
    cells: list[MatrixCell] = field(default_factory=list)
    generated_at: str = ""
    summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "prompt_names": self.prompt_names,
            "evaluator_names": self.evaluator_names,
            "test_cases": self.test_cases,
            "cells": [c.to_dict() for c in self.cells],
            "generated_at": self.generated_at,
            "summary": self.summary,
        }


_EVAL_MATRIX_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>
:root {
  --bg: #0f172a; --surface: #1e293b; --border: #334155;
  --text: #e2e8f0; --text-dim: #94a3b8; --accent: #3b82f6;
  --green: #22c55e; --yellow: #eab308; --red: #ef4444; --orange: #f97316;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); padding: 24px; }
h1 { font-size: 24px; margin-bottom: 8px; }
.meta { color: var(--text-dim); font-size: 13px; margin-bottom: 24px; }
.summary-bar { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.summary-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px; min-width: 140px; }
.summary-card .label { font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }
.summary-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; }
.matrix-wrapper { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 600px; }
th { background: var(--surface); color: var(--text-dim); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; padding: 10px 12px; text-align: left; border-bottom: 2px solid var(--border); position: sticky; top: 0; }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: top; }
tr:hover td { background: rgba(59, 130, 246, 0.05); }
.cell-excellent { color: var(--green); font-weight: 700; }
.cell-good { color: #86efac; font-weight: 600; }
.cell-pass { color: var(--yellow); }
.cell-fail { color: var(--red); font-weight: 600; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-pass { background: rgba(34, 197, 94, 0.15); color: var(--green); }
.badge-fail { background: rgba(239, 68, 68, 0.15); color: var(--red); }
.detail-toggle { cursor: pointer; color: var(--accent); font-size: 12px; }
.detail-toggle:hover { text-decoration: underline; }
.detail-content { display: none; margin-top: 6px; padding: 8px; background: rgba(0,0,0,0.3); border-radius: 4px; font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; }
.detail-content.show { display: block; }
.score-bar { height: 4px; background: var(--border); border-radius: 2px; margin-top: 4px; }
.score-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text-dim); font-size: 12px; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<p class="meta">生成时间: {{ generated_at }} | 模板数: {{ prompt_count }} | 评估器数: {{ evaluator_count }}</p>

<div class="summary-bar">
  <div class="summary-card"><div class="label">通过率</div><div class="value" style="color:var(--green)">{{ pass_rate }}%</div></div>
  <div class="summary-card"><div class="label">平均分</div><div class="value">{{ avg_score }}</div></div>
  <div class="summary-card"><div class="label">总评估</div><div class="value">{{ total_cells }}</div></div>
  <div class="summary-card"><div class="label">失败数</div><div class="value" style="color:var(--red)">{{ fail_count }}</div></div>
</div>

<div class="matrix-wrapper">
<table>
<thead>
<tr>
  <th>模板 \\ 评估器</th>
  {% for ev in evaluator_names %}<th>{{ ev }}</th>{% endfor %}
</tr>
</thead>
<tbody>
{% for prompt in prompt_names %}
<tr>
  <td style="font-weight:600;white-space:nowrap">{{ prompt }}</td>
  {% for ev in evaluator_names %}
  {% set cell = get_cell(prompt, ev) %}
  {% if cell %}
  <td>
    <span class="{{ cell.status_class }}">{{ "%.1f"|format(cell.score) }}/{{ cell.max_score }}</span>
    <span class="badge {{ 'badge-pass' if cell.passed else 'badge-fail' }}">{{ 'PASS' if cell.passed else 'FAIL' }}</span>
    <div class="score-bar"><div class="score-bar-fill" style="width:{{ (cell.score / cell.max_score * 100)|round }}%;background:{{ 'var(--green)' if cell.passed else 'var(--red)' }}"></div></div>
    {% if cell.output or cell.feedback %}
    <span class="detail-toggle" onclick="this.nextElementSibling.classList.toggle('show')">详情</span>
    <div class="detail-content">{% if cell.feedback %}Feedback: {{ cell.feedback }}{% endif %}
{% if cell.output %}Output: {{ cell.output[:300] }}{% endif %}</div>
    {% endif %}
  </td>
  {% else %}
  <td style="color:var(--text-dim)">-</td>
  {% endif %}
  {% endfor %}
</tr>
{% endfor %}
</tbody>
</table>
</div>

<footer>AI Prompt Toolkit v{{ version }} | 评估矩阵报告 | GEPA反射式进化引擎</footer>

<script>
document.querySelectorAll('.detail-toggle').forEach(function(el) {
  el.addEventListener('click', function() {
    this.nextElementSibling.classList.toggle('show');
  });
});
</script>
</body>
</html>"""


def _get_cell(cells: list[MatrixCell], prompt: str, evaluator: str) -> MatrixCell | None:
    for c in cells:
        if c.prompt_name == prompt and c.evaluator_name == evaluator:
            return c
    return None


def generate_eval_matrix_html(
    report: MatrixReport,
    output_path: str | Path | None = None,
) -> str:
    try:
        from jinja2 import Template

        template = Template(_EVAL_MATRIX_HTML_TEMPLATE)
    except ImportError:
        template = None

    total = len(report.cells)
    passed = sum(1 for c in report.cells if c.passed)
    failed = total - passed
    avg = sum(c.score for c in report.cells) / total if total > 0 else 0
    pass_rate = (passed / total * 100) if total > 0 else 0

    context = {
        # R236-P2-19: 版本动态注入(原硬编码 v42.0.0 漂移)
        "version": __version__,
        "title": report.title,
        "generated_at": report.generated_at,
        "prompt_names": report.prompt_names,
        "evaluator_names": report.evaluator_names,
        "prompt_count": len(report.prompt_names),
        "evaluator_count": len(report.evaluator_names),
        "total_cells": total,
        "pass_rate": round(pass_rate, 1),
        "avg_score": round(avg, 2),
        "fail_count": failed,
        "get_cell": lambda p, e: _get_cell(report.cells, p, e),
    }

    if template:
        html_content: str = template.render(**context)
    else:
        html_content = _render_simple_html(report, context)

    if output_path:
        Path(output_path).write_text(html_content, encoding="utf-8")

    return html_content


def _render_simple_html(report: MatrixReport, context: dict[str, Any]) -> str:
    parts = [
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>",
        "<title>" + html.escape(report.title) + "</title>",
        "<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}",
        "table{border-collapse:collapse;width:100%}th,td{padding:8px 12px;border:1px solid #334155;text-align:left}",
        "th{background:#1e293b;color:#94a3b8;font-size:12px;text-transform:uppercase}",
        ".pass{color:#22c55e}.fail{color:#ef4444}</style></head><body>",
        f"<h1>{html.escape(report.title)}</h1>",
        f"<p>生成时间: {html.escape(report.generated_at)} | 通过率: {context['pass_rate']}% | 平均分: {context['avg_score']}</p>",
        "<table><thead><tr><th>模板</th>",
    ]
    for ev in report.evaluator_names:
        parts.append(f"<th>{html.escape(ev)}</th>")
    parts.append("</tr></thead><tbody>")
    for prompt in report.prompt_names:
        parts.append(f"<tr><td>{html.escape(prompt)}</td>")
        for ev in report.evaluator_names:
            cell = _get_cell(report.cells, prompt, ev)
            if cell:
                cls = "pass" if cell.passed else "fail"
                # 降级渲染器也不得静默丢feedback — R223实证: CI无jinja2走此路径,
                # feedback缺失致test_r28断言本地绿/CI红
                feedback = f" <small>{html.escape(cell.feedback[:120])}</small>" if cell.feedback else ""
                parts.append(
                    f"<td class='{cls}'>{cell.score:.1f}/{cell.max_score} {'PASS' if cell.passed else 'FAIL'}{feedback}</td>"
                )
            else:
                parts.append("<td>-</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></body></html>")
    return "".join(parts)


def generate_gepa_history_html(
    gepa_result: Any,
    output_path: str | Path | None = None,
) -> str:
    history = gepa_result.history if hasattr(gepa_result, "history") else []
    best_score = gepa_result.best_score if hasattr(gepa_result, "best_score") else 0
    initial_score = gepa_result.initial_score if hasattr(gepa_result, "initial_score") else 0

    parts = [
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='UTF-8'>",
        "<title>GEPA进化历史</title>",
        "<style>body{font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}",
        "h1{margin-bottom:8px}.stat{color:#94a3b8;font-size:13px;margin-bottom:16px}",
        "table{border-collapse:collapse;width:100%}th,td{padding:8px 12px;border:1px solid #334155;text-align:left}",
        "th{background:#1e293b;color:#94a3b8;font-size:12px}",
        ".seed{color:#3b82f6}.mutate{color:#22c55e}.merge{color:#f97316}</style></head><body>",
        "<h1>GEPA反射式进化历史</h1>",
        f"<p class='stat'>初始分数: {initial_score:.4f} | 最优分数: {best_score:.4f} | 提升: +{best_score - initial_score:.4f}</p>",
        "<table><thead><tr><th>#</th><th>事件</th><th>候选ID</th><th>分数</th><th>父ID</th></tr></thead><tbody>",
    ]
    for i, h in enumerate(history):
        event = h.get("event", "")
        cid = h.get("candidate_id", "")
        score = h.get("score", 0)
        parent = h.get("parent_id", "-")
        cls = event
        parts.append(
            f"<tr class='{cls}'><td>{i}</td><td>{html.escape(event)}</td><td>{cid}</td><td>{score:.4f}</td><td>{parent}</td></tr>"
        )
    parts.append("</tbody></table></body></html>")

    content = "".join(parts)
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    return content


def build_matrix_from_evaluator_results(
    template_id: str,
    text: str,
    evaluator_names: list[str] | None = None,
) -> MatrixReport:
    from ai_prompt_toolkit.evaluator_registry import EvaluatorRegistry

    registry = EvaluatorRegistry()
    results = registry.evaluate(template_id, text, evaluator_names=evaluator_names)

    report = MatrixReport(
        title=f"评估矩阵: {template_id}",
        prompt_names=[template_id],
        evaluator_names=[r.evaluator_name for r in results.results],
    )

    for r in results.results:
        cell = MatrixCell(
            prompt_name=template_id,
            evaluator_name=r.evaluator_name,
            score=r.score,
            max_score=r.max_score,
            passed=r.passed,
            feedback=str(r.details)[:200] if r.details else "",
            execution_time_ms=r.execution_time_ms,
        )
        report.cells.append(cell)

    total = len(report.cells)
    passed = sum(1 for c in report.cells if c.passed)
    report.summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total * 100) if total > 0 else 0,
    }

    return report
