"""测试安全严重性评分体系"""

from __future__ import annotations

from ai_prompt_toolkit.security.scorer import SecurityScore, SecurityScorer
from ai_prompt_toolkit.types import Finding, Severity


class TestSecurityScorer:
    def test_known_rule_scoring(self):
        scorer = SecurityScorer()
        finding = Finding(rule_id="INJ-007", severity=Severity.CRITICAL, description="越狱攻击")
        score = scorer.score(finding)
        assert score.base_score >= 9.0
        assert score.severity == Severity.CRITICAL
        assert score.attack_vector.value == "user_input"

    def test_pii_scoring(self):
        scorer = SecurityScorer()
        finding = Finding(rule_id="PII001", severity=Severity.CRITICAL, description="PII泄露")
        score = scorer.score(finding)
        assert score.base_score >= 7.0

    def test_unknown_rule_scoring(self):
        scorer = SecurityScorer()
        finding = Finding(rule_id="CUSTOM-001", severity=Severity.MEDIUM, description="自定义规则")
        score = scorer.score(finding)
        assert score.base_score == 5.0
        assert score.severity == Severity.MEDIUM

    def test_batch_scoring(self):
        scorer = SecurityScorer()
        findings = [
            Finding(rule_id="INJ-007", severity=Severity.CRITICAL, description="越狱"),
            Finding(rule_id="INJ-012", severity=Severity.MEDIUM, description="输出操纵"),
        ]
        scores = scorer.score_batch(findings)
        assert len(scores) == 2
        assert scores[0].base_score > scores[1].base_score

    def test_overall_score(self):
        scorer = SecurityScorer()
        findings = [
            Finding(rule_id="INJ-007", severity=Severity.CRITICAL, description="越狱"),
            Finding(rule_id="INJ-012", severity=Severity.MEDIUM, description="输出操纵"),
            Finding(rule_id="INJ-015", severity=Severity.LOW, description="情感操纵"),
        ]
        result = scorer.overall_score(findings)
        assert result["total"] == 3
        assert result["max_score"] >= 7.0
        assert len(result["top_risks"]) == 3

    def test_overall_score_empty(self):
        scorer = SecurityScorer()
        result = scorer.overall_score([])
        assert result["total"] == 0
        assert result["max_score"] == 0.0

    def test_to_dict(self):
        scorer = SecurityScorer()
        finding = Finding(rule_id="INJ-001", severity=Severity.HIGH, description="指令覆盖")
        score = scorer.score(finding)
        d = score.to_dict()
        assert "base_score" in d
        assert "severity" in d
        assert "attack_vector" in d
        assert "rationale" in d

    def test_severity_label(self):
        score = SecurityScore(
            base_score=9.5,
            impact_score=9.0,
            exploitability_score=8.0,
            severity=Severity.CRITICAL,
            attack_vector=__import__(
                "ai_prompt_toolkit.security.scorer", fromlist=["AttackVector"]
            ).AttackVector.USER_INPUT,
            attack_complexity=__import__(
                "ai_prompt_toolkit.security.scorer", fromlist=["AttackComplexity"]
            ).AttackComplexity.LOW,
            privileges_required=__import__(
                "ai_prompt_toolkit.security.scorer", fromlist=["PrivilegesRequired"]
            ).PrivilegesRequired.NONE,
            user_interaction=__import__(
                "ai_prompt_toolkit.security.scorer", fromlist=["UserInteraction"]
            ).UserInteraction.NONE,
            scope=__import__("ai_prompt_toolkit.security.scorer", fromlist=["ImpactScope"]).ImpactScope.CHANGED,
        )
        assert score.severity_label == "CRITICAL"
