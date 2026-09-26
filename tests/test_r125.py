"""R125 测试: OWASP映射覆盖率报告"""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.owasp_mapping import generate_owasp_report, get_owasp_coverage


class TestR125OWASPReport:
    def test_generate_owasp_report(self):
        report = generate_owasp_report()
        assert "OWASP" in report
        assert "覆盖率" in report
        assert "LLM01" in report
        assert "LLM10" in report

    def test_owasp_coverage_all_10(self):
        coverage = get_owasp_coverage()
        assert len(coverage) == 10
        for ref in [f"LLM{i:02d}" for i in range(1, 11)]:
            assert ref in coverage

    def test_owasp_coverage_has_rules(self):
        coverage = get_owasp_coverage()
        total_mapped = sum(d["lint_coverage"] for d in coverage.values())
        assert total_mapped > 0

    def test_lint_owasp_report_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = Path(tmpdir) / "test.md"
            fpath.write_text("测试prompt", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(main, ["lint", "-t", str(fpath), "--owasp-report"])
            assert "OWASP" in result.output
            assert "LLM01" in result.output
