"""Lint智能修复建议+LSP服务端测试 — P2-01/P2-02"""

from __future__ import annotations

from ai_prompt_toolkit.linter.fix_suggestions import (
    _MANUAL_FIX_STEPS,
    compute_score_impact,
    format_suggestions,
    get_fix_suggestions,
)
from ai_prompt_toolkit.linter.lsp_server import _HAS_LSP, _compute_score, _lint_to_diagnostics
from ai_prompt_toolkit.types import Finding, Severity


class TestScoreImpact:
    def test_critical_high_impact(self):
        f = Finding(rule_id="P001", severity=Severity.CRITICAL, description="security issue")
        impact = compute_score_impact(f)
        assert impact > 0

    def test_low_low_impact(self):
        f = Finding(rule_id="P010", severity=Severity.LOW, description="minor issue")
        impact = compute_score_impact(f)
        assert impact > 0

    def test_critical_greater_than_low(self):
        f_crit = Finding(rule_id="P001", severity=Severity.CRITICAL, description="critical")
        f_low = Finding(rule_id="P010", severity=Severity.LOW, description="low")
        assert compute_score_impact(f_crit) > compute_score_impact(f_low)

    def test_impact_proportional_to_severity(self):
        impacts = {}
        for sev in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]:
            f = Finding(rule_id="P001", severity=sev, description="test")
            impacts[sev] = compute_score_impact(f)
        assert impacts[Severity.CRITICAL] > impacts[Severity.HIGH]
        assert impacts[Severity.HIGH] > impacts[Severity.MEDIUM]
        assert impacts[Severity.MEDIUM] > impacts[Severity.LOW]


class TestGetFixSuggestions:
    def test_empty_findings(self):
        suggestions = get_fix_suggestions([], "test text")
        assert suggestions == []

    def test_sorted_by_impact(self):
        findings = [
            Finding(rule_id="P010", severity=Severity.LOW, description="low impact"),
            Finding(rule_id="P001", severity=Severity.CRITICAL, description="critical"),
            Finding(rule_id="P005", severity=Severity.MEDIUM, description="medium"),
        ]
        suggestions = get_fix_suggestions(findings, "short")
        assert suggestions[0].priority_rank == 1
        assert suggestions[0].finding.severity == Severity.CRITICAL

    def test_auto_fixable_detection(self):
        findings = [
            Finding(
                rule_id="P016", severity=Severity.MEDIUM, description="歧义词检测", details={"ambiguous_word": "可能"}
            ),
        ]
        text = "你可能会完成这个任务"
        suggestions = get_fix_suggestions(findings, text)
        assert any(s.auto_fixable for s in suggestions)

    def test_manual_steps_provided(self):
        findings = [
            Finding(rule_id="P001", severity=Severity.HIGH, description="缺少角色定义"),
        ]
        suggestions = get_fix_suggestions(findings, "帮我翻译")
        assert len(suggestions) == 1
        assert len(suggestions[0].manual_steps) > 0

    def test_priority_rank_assigned(self):
        findings = [
            Finding(rule_id=f"P{i:03d}", severity=Severity.MEDIUM, description=f"issue {i}") for i in range(1, 6)
        ]
        suggestions = get_fix_suggestions(findings, "test")
        ranks = [s.priority_rank for s in suggestions]
        assert ranks == sorted(ranks)
        assert ranks[0] == 1

    def test_suggestion_to_dict(self):
        findings = [Finding(rule_id="P001", severity=Severity.HIGH, description="test")]
        suggestions = get_fix_suggestions(findings, "test")
        d = suggestions[0].to_dict()
        assert "rule_id" in d
        assert "score_impact" in d
        assert "priority_rank" in d
        assert "auto_fixable" in d


class TestFormatSuggestions:
    def test_empty(self):
        result = format_suggestions([])
        assert "棒" in result or "没有" in result

    def test_with_suggestions(self):
        findings = [
            Finding(rule_id="P001", severity=Severity.HIGH, description="缺少角色定义"),
            Finding(rule_id="P016", severity=Severity.MEDIUM, description="歧义词"),
        ]
        suggestions = get_fix_suggestions(findings, "你可能会完成")
        result = format_suggestions(suggestions)
        assert "修复建议" in result
        assert "P001" in result

    def test_verbose_mode(self):
        findings = [Finding(rule_id="P001", severity=Severity.HIGH, description="test")]
        suggestions = get_fix_suggestions(findings, "test")
        result = format_suggestions(suggestions, verbose=True)
        assert "总影响" in result


class TestManualFixSteps:
    def test_known_rules_have_steps(self):
        for rule_id in ["P001", "P005", "P016", "P025"]:
            if rule_id in _MANUAL_FIX_STEPS:
                assert len(_MANUAL_FIX_STEPS[rule_id]) > 0

    def test_unknown_rule_fallback(self):
        findings = [Finding(rule_id="P999", severity=Severity.HIGH, description="unknown")]
        suggestions = get_fix_suggestions(findings, "test")
        assert len(suggestions[0].manual_steps) > 0


class TestLSPDiagnostics:
    def test_lint_to_diagnostics_clean(self):
        text = "# 好的Prompt\n你是一个专业的翻译助手。请将以下内容翻译为英文，输出不超过500字。"
        diags = _lint_to_diagnostics(text)
        assert isinstance(diags, list)

    def test_lint_to_diagnostics_with_issues(self):
        text = "帮我翻译"
        diags = _lint_to_diagnostics(text)
        assert len(diags) > 0
        assert "code" in diags[0]
        assert "message" in diags[0]
        assert "severity" in diags[0]

    def test_compute_score(self):
        text = "# 测试\n你是一个翻译助手。"
        score = _compute_score(text)
        assert "score" in score
        assert "total_rules" in score
        assert "passed" in score
        assert "failed" in score

    def test_lsp_availability(self):
        assert isinstance(_HAS_LSP, bool)
