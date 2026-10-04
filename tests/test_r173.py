"""R173测试: 同义规则去重机制 + P181语境门控守护"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules import (
    SYNONYM_RULE_GROUPS,
    get_rule,
    run_all_checks,
    suppress_synonym_findings,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestSynonymSuppress:
    """同义去重: 主从同触→抑制从规则; 从规则独立触发→保留"""

    def test_registry_shape(self):
        assert "P094" in SYNONYM_RULE_GROUPS
        assert "P130" in SYNONYM_RULE_GROUPS["P094"]

    def test_suppress_when_main_present(self):
        findings = [
            Finding("P094", Severity.HIGH, "主", 1, 1),
            Finding("P130", Severity.HIGH, "从", 1, 1),
        ]
        kept = [f.rule_id for f in suppress_synonym_findings(findings)]
        assert kept == ["P094"]

    def test_keep_sub_when_alone(self):
        findings = [Finding("P130", Severity.HIGH, "从独立触发", 1, 1)]
        kept = [f.rule_id for f in suppress_synonym_findings(findings)]
        assert kept == ["P130"]

    def test_run_all_checks_applies_dedup(self):
        """语料同触场景: 01-R1文件曾同时触发P094+P130, 去重后仅P094"""
        from pathlib import Path

        corpus = Path("docs/archive/iterations/01-R1-改进清单-v1.0.md")  # R213: 根目录历史文档归档
        if not corpus.exists():
            pytest.skip("语料不存在")
        ids = {f.rule_id for f in run_all_checks(corpus.read_text(encoding="utf-8"))}
        assert not ({"P094", "P130"} <= ids), "P094与P130不应同时出现"

    def test_rules_still_registered(self):
        """去重不删规则 — 公开API稳定, 255条不变"""
        from ai_prompt_toolkit.linter.rules import get_all_rules

        assert (
            len(get_all_rules()) >= 264
        )  # R230-E: 精确总数由 test_rules_smoke_p021_p255.EXPECTED_TOTAL 单锚点锁, 此处只断言规则集未缩水
        assert get_rule("P130") is not None
