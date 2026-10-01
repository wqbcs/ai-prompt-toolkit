"""R212-5: 四维健康分 (Security/Quality/Completeness/Cost, A–F) 单测

反指标膨胀纪律验证: 四维分数全部机械派生自现有组件(无新启发式/无手调权重):
- letter_grade 边界与 PromptScorecard 的 A–F 一致(90/75/60/40)
- _cost_score 档位表离散可审计(边界值取上限档)
- completeness = 100*(1-违反数/6), 复用 scorecard 的 _STRUCTURE_RULE_IDS
- overall_grade = 四维最低档(短板决定, 非平均)
- CLI `score --format json` 只增 health 字段, 旧消费者字段不受影响
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.security.health_score import _cost_score, compute_health_score, letter_grade
from ai_prompt_toolkit.types import Finding, Severity

_CLEAN_PROMPT = "version: 1.0.0\n# 角色\n你是测试工程师。\n# 任务\n编写用例。\n# 输出\nJSON格式。\n"


def _finding(rule_id: str) -> Finding:
    return Finding(rule_id=rule_id, severity=Severity.MEDIUM, description="t", remediation="t")


class TestLetterGrade:
    def test_boundaries(self):
        assert letter_grade(100) == "A"
        assert letter_grade(90) == "A"
        assert letter_grade(89) == "B"
        assert letter_grade(75) == "B"
        assert letter_grade(74) == "C"
        assert letter_grade(60) == "C"
        assert letter_grade(59) == "D"
        assert letter_grade(40) == "D"
        assert letter_grade(39) == "F"
        assert letter_grade(0) == "F"


class TestCostScore:
    def test_bands(self):
        assert _cost_score(0.0) == 100
        assert _cost_score(2.00) == 100  # 边界值取上限档
        assert _cost_score(2.01) == 80
        assert _cost_score(5.00) == 80
        assert _cost_score(5.01) == 60
        assert _cost_score(10.00) == 60
        assert _cost_score(10.01) == 40
        assert _cost_score(20.00) == 40
        assert _cost_score(20.01) == 20
        assert _cost_score(999.0) == 20


class TestComputeHealthScore:
    def test_structure_keys(self):
        h = compute_health_score([], 100.0, "你是助手")
        for key in ("security", "quality", "completeness", "cost", "overall_grade"):
            assert key in h, f"缺少维度: {key}"
        for dim in ("security", "quality", "completeness", "cost"):
            assert "score" in h[dim] and "grade" in h[dim]
        assert "tokens" in h["cost"] and "cost_per_1k_calls_usd" in h["cost"] and "model" in h["cost"]
        assert h["completeness"]["violated"] == []

    def test_no_findings_all_high(self):
        h = compute_health_score([], 100.0, "你是助手")
        assert h["security"]["score"] == 100
        assert h["quality"]["score"] == 100
        assert h["completeness"]["score"] == 100
        assert h["overall_grade"] == "A"

    def test_completeness_counts_structure_violations(self):
        # 6条关键结构规则, 违反2条 → round(100*(1-2/6)) = 67
        findings = [_finding("P001"), _finding("P005"), _finding("P100")]  # P100不在结构集
        h = compute_health_score(findings, 80.0, "你是助手")
        assert h["completeness"]["score"] == 67
        assert h["completeness"]["violated"] == ["P001", "P005"]
        assert h["completeness"]["grade"] == "C"

    def test_overall_is_weakest_dimension(self, monkeypatch):
        """短板决定总评级: Cost落F → overall必为F(其余三维A)"""

        class _FakeEstimate:
            estimated_tokens = 5000
            estimated_input_cost_usd = 0.05
            estimated_output_cost_usd = 0.02

        class _FakeResult:
            estimate = _FakeEstimate()

        import ai_prompt_toolkit.linter.token_analyzer as ta

        monkeypatch.setattr(ta, "analyze_prompt_tokens", lambda text, model="default": _FakeResult())
        # 千次成本 70 USD > $20 档 → Cost=20(F); 无finding → 其余三维100(A)
        h = compute_health_score([], 100.0, "x" * 100)
        assert h["cost"]["score"] == 20
        assert h["cost"]["grade"] == "F"
        assert h["security"]["score"] == 100
        assert h["quality"]["score"] == 100
        assert h["overall_grade"] == "F"

    def test_lint_score_none_falls_back_to_security(self):
        h = compute_health_score([], None, "你是助手")
        assert h["quality"] == h["security"]


class TestCliJsonCompat:
    """score --format json: 新增health字段, 旧字段结构不变(只增不改)"""

    def test_json_has_health_and_scorecard(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "p.md").write_text(_CLEAN_PROMPT, encoding="utf-8")
        result = CliRunner().invoke(main, ["score", "-t", "p.md", "--format", "json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "health" in payload
        health = payload["health"]
        assert health["overall_grade"] in ("A", "B", "C", "D", "F")
        for dim in ("security", "quality", "completeness", "cost"):
            assert dim in health and "grade" in health[dim] and "score" in health[dim]
        # 旧scorecard字段仍在(向后兼容)
        assert "overall_score" in payload or "score" in payload or "grade" in payload
