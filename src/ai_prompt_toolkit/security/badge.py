"""安全评分徽章SVG生成 — CI/CD可视化和README嵌入

参考:
- shields.io (标准badge格式)
- OpenSSF Scorecard badges
- GitHub Actions status badges

生成SVG徽章, 可嵌入README或CI报告:
- 评分等级(A-F)对应颜色
- 分数+等级+决策三段式布局
- 支持紧凑/标准两种尺寸
"""
from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.security.prompt_scorecard import Decision, Grade, PromptScorecard


_GRADE_COLORS: dict[Grade, str] = {
    Grade.A: "#2ea44f",
    Grade.B: "#57ab5a",
    Grade.C: "#d29922",
    Grade.D: "#db6d28",
    Grade.F: "#cf222e",
}

_DECISION_COLORS: dict[Decision, str] = {
    Decision.ALLOW: "#2ea44f",
    Decision.WARN: "#d29922",
    Decision.BLOCK: "#cf222e",
}


def _text_width(text: str, char_width: float = 7.0, padding: float = 12.0) -> float:
    return len(text) * char_width + padding


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_scorecard_badge(scorecard: PromptScorecard, *, compact: bool = False) -> str:
    grade_color = _GRADE_COLORS.get(scorecard.grade, "#555555")
    decision_color = _DECISION_COLORS.get(scorecard.decision, "#555555")

    score_text = f"{scorecard.overall_score}/100"
    grade_text = scorecard.grade.value
    decision_text = scorecard.decision.value.upper()

    if compact:
        return _compact_badge(score_text, grade_text, grade_color)

    return _standard_badge(score_text, grade_text, decision_text, grade_color, decision_color)


def _compact_badge(score_text: str, grade_text: str, color: str) -> str:
    left_w = _text_width("score")
    right_w = _text_width(f"{score_text} {grade_text}")
    total_w = left_w + right_w
    h = 20

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}">
  <rect width="{left_w}" height="{h}" fill="#555555" rx="3"/>
  <rect x="{left_w}" width="{right_w}" height="{h}" fill="{color}" rx="3"/>
  <rect x="{left_w}" width="3" height="{h}" fill="{color}"/>
  <text x="{left_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml("score")}</text>
  <text x="{left_w + right_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml(f"{score_text} {grade_text}")}</text>
</svg>'''


def _standard_badge(
    score_text: str, grade_text: str, decision_text: str,
    grade_color: str, decision_color: str,
) -> str:
    seg1_w = _text_width("security")
    seg2_w = _text_width(f"{score_text} {grade_text}")
    seg3_w = _text_width(decision_text)
    total_w = seg1_w + seg2_w + seg3_w
    h = 20

    x2 = seg1_w
    x3 = seg1_w + seg2_w

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}">
  <rect width="{seg1_w}" height="{h}" fill="#555555" rx="3"/>
  <rect x="{x2}" width="{seg2_w}" height="{h}" fill="{grade_color}"/>
  <rect x="{x3}" width="{seg3_w}" height="{h}" fill="{decision_color}" rx="3"/>
  <rect x="{x2}" width="3" height="{h}" fill="{grade_color}"/>
  <rect x="{x3}" width="3" height="{h}" fill="{decision_color}"/>
  <text x="{seg1_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml("security")}</text>
  <text x="{x2 + seg2_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml(f"{score_text} {grade_text}")}</text>
  <text x="{x3 + seg3_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml(decision_text)}</text>
</svg>'''


def generate_scorecard_badge_file(scorecard: PromptScorecard, output_path: str, *, compact: bool = False) -> None:
    from pathlib import Path
    svg = generate_scorecard_badge(scorecard, compact=compact)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def generate_score_svg(score: int, grade: Grade) -> str:
    color = _GRADE_COLORS.get(grade, "#555555")
    score_text = f"{score}/100"
    grade_text = grade.value

    left_w = _text_width("prompt")
    right_w = _text_width(f"{score_text} {grade_text}")
    total_w = left_w + right_w
    h = 20

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}">
  <rect width="{left_w}" height="{h}" fill="#555555" rx="3"/>
  <rect x="{left_w}" width="{right_w}" height="{h}" fill="{color}" rx="3"/>
  <rect x="{left_w}" width="3" height="{h}" fill="{color}"/>
  <text x="{left_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml("prompt")}</text>
  <text x="{left_w + right_w / 2}" y="14" fill="#ffffff" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" font-weight="bold">{_escape_xml(f"{score_text} {grade_text}")}</text>
</svg>'''
