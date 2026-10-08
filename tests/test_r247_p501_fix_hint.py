"""R247-P5-01: --fix-hint 旗标测试（lint + scan 双路径）

P5-01 板行口径："每条 finding 消息必须含下一步"——remediation 数据 267/267
在位但 CLI 默认面零展示，本轮加 opt-in 旗标闭环"最后一公里"。
确定性：纯展示面，默认 off 时既有输出逐字节不变（回归护栏）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "ai_prompt_toolkit" / "templates" / "code-reviewer.md"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _lint(*extra: str) -> object:
    return CliRunner().invoke(main, ["lint", "-s", str(TEMPLATE), *extra])


class TestFixHintLintPath:
    def test_default_off_no_hint_lines(self, runner: CliRunner):
        """默认面（gate 契约）不含 修复: 行——逐字节不变护栏。"""
        res = _lint()
        assert "修复:" not in res.output

    def test_flag_on_shows_hint(self, runner: CliRunner):
        res = _lint("--fix-hint")
        assert "修复:" in res.output

    def test_hint_value_matches_rule_remediation(self, runner: CliRunner):
        """提示值=规则自带 remediation（单一真源 LintRule）。"""
        from ai_prompt_toolkit.linter.rules import get_rule

        res = _lint("--fix-hint")
        rule = get_rule("P012")
        assert rule is not None
        # P012 在该模板有 finding（冒烟已证）
        assert rule.remediation in res.output

    def test_hint_indented_under_finding(self, runner: CliRunner):
        """提示行缩进在 finding 行下（展示形态稳定）。"""
        res = _lint("--fix-hint")
        lines = res.output.splitlines()
        hint_lines = [i for i, l in enumerate(lines) if "修复:" in l]
        assert hint_lines
        for i in hint_lines:
            assert lines[i].startswith("      修复:")
            assert "P" in lines[i - 1]  # 上一行是 finding 行

    def test_fix_hint_with_explain_coexist(self, runner: CliRunner):
        """与 --explain 同开不冲突（两语义不同位：finding 级 vs 规则级）。"""
        res = _lint("--fix-hint", "--explain")
        assert "修复:" in res.output

    def test_json_format_ignores_fix_hint(self, runner: CliRunner, tmp_path: Path):
        """机器面契约：--format json 不受旗标影响（fix-hint 是 CLI 展示面）。"""
        out = tmp_path / "r.json"
        res = CliRunner().invoke(main, ["lint", "-s", str(TEMPLATE), "--format", "json", "-o", str(out), "--fix-hint"])
        import json

        data = json.loads(out.read_text(encoding="utf-8"))
        # json 面结构不受影响（无"修复:"展示行混入机器通道）
        assert "修复:" not in json.dumps(data, ensure_ascii=False)


class TestFixHintScanPath:
    def _scan(self, *extra: str) -> object:
        return CliRunner().invoke(main, ["scan", "-t", str(TEMPLATE), *extra])

    def test_scan_default_off(self, runner: CliRunner):
        res = self._scan()
        assert "修复:" not in res.output

    def test_scan_flag_on_shows_hint(self, runner: CliRunner):
        res = self._scan("--fix-hint")
        assert "修复:" in res.output

    def test_scan_hint_indented(self, runner: CliRunner):
        res = self._scan("--fix-hint")
        lines = res.output.splitlines()
        hint_lines = [i for i, l in enumerate(lines) if "修复:" in l]
        assert hint_lines
        for i in hint_lines:
            assert lines[i].startswith("      修复:")
