"""R109 测试: lint --tui交互式终端界面"""

from __future__ import annotations

from unittest.mock import MagicMock

from ai_prompt_toolkit.tui_browser import _score_to_grade, render_interactive_results


class TestR109TUIGrade:
    def test_grade_s(self):
        assert _score_to_grade(98) == "S"

    def test_grade_a(self):
        assert _score_to_grade(88) == "A"

    def test_grade_b(self):
        assert _score_to_grade(72) == "B"

    def test_grade_c(self):
        assert _score_to_grade(58) == "C"

    def test_grade_d(self):
        assert _score_to_grade(42) == "D"

    def test_grade_f(self):
        assert _score_to_grade(30) == "F"


class TestR109TUIRender:
    def test_render_no_crash(self):
        finding = MagicMock()
        finding.rule_id = "P196"
        finding.description = "test finding"
        finding.severity = MagicMock()
        finding.severity.value = "high"
        finding.category = "inference_security"

        result = MagicMock()
        result.template_id = "test.md"
        result.findings = [finding]

        try:
            render_interactive_results([result], 85.0, 1, 1)
        except Exception as e:
            raise AssertionError(f"render_interactive_results crashed: {e}") from e

    def test_render_empty(self):
        try:
            render_interactive_results([], 100.0, 0, 0)
        except Exception as e:
            raise AssertionError(f"render_interactive_results crashed with empty: {e}") from e
