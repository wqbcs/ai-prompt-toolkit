"""安全评分徽章SVG生成测试"""

from __future__ import annotations

from ai_prompt_toolkit.security.badge import (
    _escape_xml,
    _text_width,
    generate_score_svg,
    generate_scorecard_badge,
    generate_scorecard_badge_file,
)
from ai_prompt_toolkit.security.prompt_scorecard import (
    Decision,
    DimensionScore,
    Grade,
    PromptScorecard,
)


def _make_scorecard(score: int, grade: Grade, decision: Decision) -> PromptScorecard:
    return PromptScorecard(
        overall_score=score,
        grade=grade,
        decision=decision,
        dimensions=[
            DimensionScore(name="Lint质量", max_points=25, earned=20),
            DimensionScore(name="注入防御", max_points=25, earned=20),
        ],
        total_findings=2,
        critical_count=0,
        high_count=0,
        medium_count=2,
        low_count=0,
    )


class TestTextWidth:
    def test_basic(self):
        w = _text_width("score")
        assert w > 0

    def test_longer_text_wider(self):
        assert _text_width("security") > _text_width("a")


class TestEscapeXml:
    def test_ampersand(self):
        assert _escape_xml("a&b") == "a&amp;b"

    def test_angle_brackets(self):
        assert _escape_xml("<b>") == "&lt;b&gt;"

    def test_quotes(self):
        assert _escape_xml('"hi"') == "&quot;hi&quot;"

    def test_no_escape_needed(self):
        assert _escape_xml("hello") == "hello"


class TestCompactBadge:
    def test_generates_svg(self):
        sc = _make_scorecard(90, Grade.A, Decision.ALLOW)
        svg = generate_scorecard_badge(sc, compact=True)
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "90/100" in svg
        assert "A" in svg

    def test_grade_colors(self):
        for grade in Grade:
            sc = _make_scorecard(50, grade, Decision.WARN)
            svg = generate_scorecard_badge(sc, compact=True)
            assert "<svg" in svg


class TestStandardBadge:
    def test_generates_svg(self):
        sc = _make_scorecard(85, Grade.B, Decision.ALLOW)
        svg = generate_scorecard_badge(sc, compact=False)
        assert "<svg" in svg
        assert "85/100" in svg
        assert "B" in svg
        assert "ALLOW" in svg

    def test_block_decision(self):
        sc = _make_scorecard(25, Grade.F, Decision.BLOCK)
        svg = generate_scorecard_badge(sc, compact=False)
        assert "BLOCK" in svg
        assert "#cf222e" in svg

    def test_warn_decision(self):
        sc = _make_scorecard(55, Grade.D, Decision.WARN)
        svg = generate_scorecard_badge(sc, compact=False)
        assert "WARN" in svg


class TestScoreSvg:
    def test_generates_svg(self):
        svg = generate_score_svg(95, Grade.A)
        assert "<svg" in svg
        assert "95/100" in svg
        assert "A" in svg
        assert "prompt" in svg

    def test_f_grade(self):
        svg = generate_score_svg(20, Grade.F)
        assert "#cf222e" in svg


class TestBadgeFile:
    def test_writes_file(self, tmp_path):
        sc = _make_scorecard(80, Grade.B, Decision.ALLOW)
        output = tmp_path / "badge.svg"
        generate_scorecard_badge_file(sc, str(output))
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<svg" in content

    def test_creates_parent_dirs(self, tmp_path):
        sc = _make_scorecard(70, Grade.C, Decision.WARN)
        output = tmp_path / "sub" / "dir" / "badge.svg"
        generate_scorecard_badge_file(sc, str(output))
        assert output.exists()
