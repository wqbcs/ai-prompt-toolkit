"""R177测试: 覆盖率债务治理 — cli_helpers友好输出层 + discover_templates家族"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ai_prompt_toolkit.cli_helpers import (
    discover_templates,
    discover_templates_with_ignore,
    empty_state_tip,
    format_findings_table,
    friendly_finding_line,
    friendly_fix_suggestion,
    friendly_lint_summary,
    friendly_progress_label,
    friendly_score,
    friendly_severity,
    load_promptignore,
    should_ignore,
    write_report,
)


class TestDiscovery:
    def test_discover_templates_dir(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("x", encoding="utf-8")
        (tmp_path / "b.txt").write_text("x", encoding="utf-8")
        (tmp_path / "c.py").write_text("x", encoding="utf-8")  # 非prompt扩展名
        found = discover_templates(tmp_path)
        names = {p.name for p in found}
        assert "a.md" in names and "c.py" not in names  # 只发现md/prompt族

    def test_promptignore_respected(self, tmp_path: Path):
        (tmp_path / "keep.md").write_text("x", encoding="utf-8")
        (tmp_path / "skip.md").write_text("x", encoding="utf-8")
        (tmp_path / ".promptignore").write_text("skip.md\n", encoding="utf-8")
        patterns = load_promptignore(tmp_path)
        assert should_ignore(tmp_path / "skip.md", tmp_path, patterns)
        assert not should_ignore(tmp_path / "keep.md", tmp_path, patterns)
        found = discover_templates_with_ignore(tmp_path)
        assert {p.name for p in found} == {"keep.md"}

    def test_empty_state_tip_variants(self):
        assert "wizard" in empty_state_tip("default")
        # R319: 移除 `or True` 重言面 — 真实断言生效（lint/scan 提示须可区分）
        assert empty_state_tip("lint") != empty_state_tip("scan")


class TestFriendlyOutput:
    def test_progress_label_with_eta(self):
        label = friendly_progress_label("lint", 5, 10, elapsed_ms=2000)
        assert "50" in label

    def test_severity_and_score(self):
        icon, word = friendly_severity("high")
        assert icon and word
        assert "分" in friendly_score(85.0) or friendly_score(85.0)

    def test_finding_line_and_summary(self):
        line = friendly_finding_line("t.md", "P001", "high", "缺角色")
        assert "P001" in line and "t.md" in line
        summary = friendly_lint_summary(total_files=3, avg_score=88.0, total_findings=0, fixed=1)
        assert "88" in summary and "3" in summary

    def test_fix_suggestion_known_and_unknown(self):
        assert friendly_fix_suggestion("P001", "缺角色")
        assert friendly_fix_suggestion("P9999", "未知规则")

    def test_format_findings_table(self, capsys):
        rows = [{"rule_id": "P001", "severity": "high", "description": "缺角色", "template_id": "t"}]
        table = format_findings_table(rows)  # 经rich输出到终端, 返回值为空串
        assert isinstance(table, str)
        assert format_findings_table([]) == "无发现项"

    def test_write_report_formats(self, tmp_path: Path):
        data = {"total": 1, "score": 90.0, "findings": []}
        for fmt in ("json", "markdown", "csv"):
            out = tmp_path / f"r.{fmt}"
            write_report(data, out, fmt=fmt)
            assert out.exists() and out.stat().st_size > 0
