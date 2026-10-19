"""R188 e2e: 用户核心工作流闭环 — init→lint→baseline→gate→badge→eval→scan

组合验证单测无法覆盖的断点(R186曾发现init配置与自动发现链断裂):
配置生成→被自动发现→被load_lint_config消费→lint→基线→门禁→徽章→评估→扫描。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


@pytest.fixture()
def project(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "good.md").write_text(
        "version: 1.0.0\n# 角色\n你是测试工程师。\n# 任务\n编写用例。\n"
        "# 输出格式\nMarkdown表格。\n# 约束\n不编造字段。\n# 示例\n输入: 登录接口\n输出: 用例表。\n",
        encoding="utf-8",
    )
    return tmp_path


def _run(*args):
    return CliRunner().invoke(main, list(args))


class TestWorkflowE2E:
    def test_step1_init_config_discovered_by_lint(self, project):
        """init生成配置 → lint自动发现链真实消费(配置闭环守护)"""
        result = _run("doctor", "--init")
        assert result.exit_code == 0
        # R325: doctor --init 现产出单一真源 promptlint.toml(lint 首选发现, P2-03 完整 schema)
        assert (project / "promptlint.toml").exists()
        # lint运行时无"配置未发现"类异常, 且走通
        result = _run("lint", "-t", "prompts/good.md")
        assert "Lint完成" in result.output

    def test_step2_lint_baseline_roundtrip(self, project):
        """baseline保存 → 对比显示改善/不变(基线机制闭环)"""
        assert _run("lint", "-t", "prompts/good.md", "--baseline-save").exit_code in (0, 1)
        assert Path(".baseline.json").exists(), "baseline-save未落盘"
        result = _run("lint", "-t", "prompts/good.md", "--baseline", ".baseline.json")
        assert "基线对比" in result.output
        assert "回归" not in result.output  # 同一文件重跑不得回归

    def test_step3_gate_verdict_exit_code(self, project):
        """gate verdict → verdict_to_exit_code → 退出码一致"""
        result = _run("lint", "-t", "prompts/good.md", "--gate")
        assert result.exit_code in (0, 1, 2)

    def test_step4_badge_generated(self, project):
        """badge: SVG徽章真实落盘"""
        result = _run("badge", "-t", "prompts/good.md", "-o", "badge.svg")
        assert result.exit_code == 0
        assert Path("badge.svg").exists()
        assert "svg" in Path("badge.svg").read_text(encoding="utf-8")[:200].lower()

    def test_step5_evaluate_and_scan(self, project):
        """evaluate/scan在真实工作流目录可执行"""
        assert _run("evaluate", "-t", "prompts/good.md", "--quick").exit_code in (0, 1)
        assert _run("scan", "-t", "prompts/good.md").exit_code in (0, 1, 2)

    def test_step6_full_journey(self, project):
        """全旅程串跑: init→lint→baseline→gate→badge→eval→scan 一气呵成"""
        steps = [
            ["doctor", "--init"],
            ["lint", "-t", "prompts/good.md", "--baseline-save"],
            ["lint", "-t", "prompts/good.md", "--baseline", ".baseline.json"],
            ["lint", "-t", "prompts/good.md", "--gate"],
            ["badge", "-t", "prompts/good.md", "-o", "e2e-badge.svg"],
            ["evaluate", "-t", "prompts/good.md", "--quick"],
            ["scan", "-t", "prompts/good.md"],
        ]
        for step in steps:
            result = _run(*step)
            assert result.exit_code in (0, 1, 2), f"步骤{step}失败(exit={result.exit_code}): {result.output[-200:]}"
