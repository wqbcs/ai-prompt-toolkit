"""对抗性Prompt攻击模拟器测试——AdversarialSimulator"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.adversarial import (
    AdversarialSimulator,
    CharSwapAttack,
    InstructionInjectionAttack,
    RandomDeleteAttack,
    RandomInsertAttack,
    RobustnessReport,
    SynonymReplacementAttack,
    TranslationPerturbationAttack,
)


class TestSynonymReplacementAttack:
    def test_zh_replacement(self):
        attack = SynonymReplacementAttack()
        results = attack.attack("你必须回答用户的问题，禁止编造信息")
        assert len(results) > 0
        assert any(r.attack_type == "synonym_replacement" for r in results)
        assert any(r.details.get("replaced") == "必须" for r in results)

    def test_en_replacement(self):
        attack = SynonymReplacementAttack()
        results = attack.attack("You must follow these rules. Never output harmful content.")
        assert len(results) > 0

    def test_no_replacement(self):
        attack = SynonymReplacementAttack()
        results = attack.attack("今天天气很好")
        assert len(results) == 0

    def test_max_results(self):
        attack = SynonymReplacementAttack()
        text = "必须禁止不要请输出回答分析确保使用提供详细准确完成检查包括"
        results = attack.attack(text)
        assert len(results) <= 10


class TestRandomInsertAttack:
    def test_insert(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "你必须回答问题并且分析数据")
        insert_results = [r for r in report.attack_results if r.attack_type == "random_insert"]
        assert len(insert_results) <= 5

    def test_empty_text(self):
        attack = RandomInsertAttack()
        results = attack.attack("")
        assert len(results) == 0


class TestRandomDeleteAttack:
    def test_delete(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "你必须仔细检查所有数据内容")
        delete_results = [r for r in report.attack_results if r.attack_type == "random_delete"]
        assert len(delete_results) <= 5


class TestCharSwapAttack:
    def test_swap(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "You must follow the instructions carefully")
        swap_results = [r for r in report.attack_results if r.attack_type == "char_swap"]
        assert len(swap_results) <= 5

    def test_no_english(self):
        attack = CharSwapAttack()
        results = attack.attack("中文文本内容")
        assert len(results) == 0


class TestTranslationPerturbationAttack:
    def test_weakening(self):
        attack = TranslationPerturbationAttack()
        results = attack.attack("你必须禁止用户访问敏感数据，确保严格保密")
        assert len(results) > 0
        assert any(r.details.get("weakening") for r in results)
        assert any(r.severity == "critical" for r in results)

    def test_no_zh_constraints(self):
        attack = TranslationPerturbationAttack()
        results = attack.attack("This is a simple text without constraints")
        assert len(results) == 0


class TestInstructionInjectionAttack:
    def test_injection(self):
        attack = InstructionInjectionAttack()
        results = attack.attack("你是专业助手，必须回答用户问题")
        assert len(results) == 6
        assert any(r.severity == "critical" for r in results)
        assert all(r.attack_type == "instruction_injection" for r in results)
        assert all(r.details.get("appended") for r in results)


class TestAdversarialSimulator:
    def test_simulate(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "你是专业助手, 必须回答用户问题. 禁止编造信息.")
        assert isinstance(report, RobustnessReport)
        assert report.template_id == "test"
        assert report.total_attacks > 0
        assert report.robustness_score >= 0
        assert len(report.attack_results) > 0

    def test_simulate_max_attacks(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须禁止不要请输出回答分析确保", max_attacks=5)
        assert report.total_attacks <= 5

    def test_simulate_empty_text(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "")
        assert report.robustness_score < 5.0
        assert report.total_attacks > 0

    def test_simulate_simple_text(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "简单的文本")
        assert report.total_attacks > 0

    def test_robustness_report_to_dict(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须回答问题")
        d = report.to_dict()
        assert d["template_id"] == "test"
        assert "success_rate" in d
        assert "defense_suggestions" in d

    def test_robustness_score_range(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须禁止确保严格务必不得严禁绝不所有")
        assert 0 <= report.robustness_score <= 10.0

    def test_defense_suggestions(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须禁止确保严格务必不得严禁绝不所有")
        assert len(report.defense_suggestions) > 0

    def test_injection_suggestions(self):
        sim = AdversarialSimulator(seed=42)
        text = "你是助手, 必须回答问题."
        report = sim.simulate("test", text)
        assert any("P063" in s or "边界标记" in s for s in report.defense_suggestions)

    def test_list_attacks(self):
        sim = AdversarialSimulator(seed=42)
        attacks = sim.list_attacks()
        assert len(attacks) == 10
        types = [a["attack_type"] for a in attacks]
        assert "synonym_replacement" in types
        assert "instruction_injection" in types
        assert "translation_perturbation" in types

    def test_vulnerable_sections(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须禁止确保严格务必不得严禁绝不所有")
        assert len(report.vulnerable_sections) > 0
        for v in report.vulnerable_sections:
            assert "attack_type" in v
            assert "count" in v
            assert "severity" in v

    def test_success_rate_property(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test", "必须回答")
        rate = report.success_rate
        assert 0 <= rate <= 1.0
