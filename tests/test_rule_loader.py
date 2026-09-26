"""RuleLoader 模块测试 — 规则加载器 recommended/strict/huawei-cloud + 自定义规则"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.linter.rule_loader import RULESETS, RuleLoader
from ai_prompt_toolkit.linter.rules import LintRule, get_all_rules
from ai_prompt_toolkit.types import Severity


class TestRuleSets:
    def test_rulesets_has_expected_keys(self):
        assert set(RULESETS.keys()) == {"recommended", "strict", "huawei-cloud"}

    def test_recommended_rules_count(self):
        assert len(RULESETS["recommended"]) == 21

    def test_strict_rules_count(self):
        assert len(RULESETS["strict"]) == 30

    def test_huawei_cloud_rules_count(self):
        assert len(RULESETS["huawei-cloud"]) == 18

    def test_strict_is_superset_of_recommended(self):
        assert set(RULESETS["recommended"]).issubset(set(RULESETS["strict"]))

    def test_all_rule_ids_are_valid(self):
        all_rule_ids = {r.rule_id for r in get_all_rules()}
        for ruleset_name, ids in RULESETS.items():
            for rid in ids:
                assert rid in all_rule_ids, f"{ruleset_name} 包含无效规则ID: {rid}"


class TestRuleLoader:
    def setup_method(self):
        self.loader = RuleLoader()

    def test_load_default_recommended(self):
        rules = self.loader.load()
        assert len(rules) > 0
        for rule in rules:
            assert isinstance(rule, LintRule)
            assert rule.rule_id in RULESETS["recommended"]

    def test_load_strict(self):
        rules = self.loader.load(ruleset="strict")
        assert len(rules) == 30
        rule_ids = {r.rule_id for r in rules}
        assert rule_ids == set(RULESETS["strict"])

    def test_load_huawei_cloud(self):
        rules = self.loader.load(ruleset="huawei-cloud")
        assert len(rules) == 18

    def test_load_unknown_ruleset_falls_back_to_recommended(self):
        rules = self.loader.load(ruleset="nonexistent")
        rec_rules = self.loader.load(ruleset="recommended")
        assert len(rules) == len(rec_rules)

    def test_load_with_include_filter(self):
        rules = self.loader.load(include=["P001", "P006"])
        rule_ids = {r.rule_id for r in rules}
        assert rule_ids == {"P001", "P006"}

    def test_load_with_exclude_filter(self):
        rules = self.loader.load(ruleset="recommended", exclude=["P001", "P005"])
        rule_ids = {r.rule_id for r in rules}
        assert "P001" not in rule_ids
        assert "P005" not in rule_ids
        assert "P002" in rule_ids

    def test_load_with_include_and_exclude(self):
        rules = self.loader.load(
            ruleset="recommended",
            include=["P001", "P002", "P003"],
            exclude=["P002"],
        )
        rule_ids = {r.rule_id for r in rules}
        assert rule_ids == {"P001", "P003"}

    def test_load_include_nonexistent_rule(self):
        rules = self.loader.load(include=["P999"])
        assert len(rules) == 0

    def test_available_rulesets(self):
        rulesets = self.loader.available_rulesets()
        assert "recommended" in rulesets
        assert "strict" in rulesets
        assert "huawei-cloud" in rulesets

    def test_load_custom_rules_dir_not_exist(self):
        rules = self.loader.load(custom_rules_dir="/nonexistent/path")
        assert len(rules) > 0

    def test_load_custom_rules_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules = self.loader.load(custom_rules_dir=tmpdir)
            assert len(rules) > 0

    def test_load_custom_rules_with_valid_module(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rule_file = Path(tmpdir) / "custom_rule.py"
            rule_file.write_text(
                "from ai_prompt_toolkit.linter.rules import LintRule\n"
                "from ai_prompt_toolkit.types import Severity\n"
                "RULES = [LintRule('C001', 'custom rule', 'custom', Severity.MEDIUM, 'test', 'test')]\n",
                encoding="utf-8",
            )
            rules = self.loader.load(custom_rules_dir=tmpdir)
            rule_ids = {r.rule_id for r in rules}
            assert "C001" in rule_ids

    def test_load_custom_rules_skip_underscore_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            init_file = Path(tmpdir) / "__init__.py"
            init_file.write_text("RULES = []\n", encoding="utf-8")
            rules = self.loader.load(custom_rules_dir=tmpdir)
            rec_count = len(RULESETS["recommended"])
            assert len(rules) == rec_count

    def test_load_custom_rules_malformed_module_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad_rule.py"
            bad_file.write_text("this is not valid python {{{", encoding="utf-8")
            rules = self.loader.load(custom_rules_dir=tmpdir)
            assert len(rules) > 0

    def test_load_custom_rules_conflict_higher_severity_wins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rule_file = Path(tmpdir) / "conflict_rule.py"
            rule_file.write_text(
                "from ai_prompt_toolkit.linter.rules import LintRule\n"
                "from ai_prompt_toolkit.types import Severity\n"
                "RULES = [LintRule('P001', 'conflict rule', 'structure', Severity.CRITICAL, 'test', 'test')]\n",
                encoding="utf-8",
            )
            rules = self.loader.load(custom_rules_dir=tmpdir)
            for r in rules:
                if r.rule_id == "P001":
                    assert r.severity == Severity.CRITICAL
                    break

    def test_load_custom_rules_no_rules_attr_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            no_rules_file = Path(tmpdir) / "no_rules.py"
            no_rules_file.write_text("SOMETHING = []\n", encoding="utf-8")
            rules = self.loader.load(custom_rules_dir=tmpdir)
            rec_count = len(RULESETS["recommended"])
            assert len(rules) == rec_count
