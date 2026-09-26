"""R103: 评分等级 + 首次运行引导"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ai_prompt_toolkit.evaluator import score_to_decision, score_to_grade


class TestR103GradeAndDecision:
    def test_grade_s(self):
        assert score_to_grade(9.5) == "S"
        assert score_to_grade(9.0) == "S"

    def test_grade_a(self):
        assert score_to_grade(8.5) == "A"
        assert score_to_grade(8.0) == "A"

    def test_grade_b(self):
        assert score_to_grade(7.0) == "B"
        assert score_to_grade(6.5) == "B"

    def test_grade_c(self):
        assert score_to_grade(5.5) == "C"
        assert score_to_grade(5.0) == "C"

    def test_grade_d(self):
        assert score_to_grade(4.0) == "D"
        assert score_to_grade(3.0) == "D"

    def test_grade_f(self):
        assert score_to_grade(2.0) == "F"
        assert score_to_grade(0.0) == "F"

    def test_decision_pass(self):
        assert score_to_decision(7.0) == "PASS"
        assert score_to_decision(5.0) == "PASS"

    def test_decision_fail(self):
        assert score_to_decision(4.9) == "FAIL"
        assert score_to_decision(0.0) == "FAIL"

    def test_decision_custom_threshold(self):
        assert score_to_decision(7.0, threshold=8.0) == "FAIL"
        assert score_to_decision(8.5, threshold=8.0) == "PASS"

    def test_doctor_init_shows_guide(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            os.chdir(td)
            try:
                result = runner.invoke(main, ["doctor", "--init"])
                config_path = Path(td) / ".prompt-toolkit.yml"
                assert config_path.exists()
            finally:
                os.chdir(old_cwd)
