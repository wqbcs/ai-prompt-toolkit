"""自动测试数据生成测试——TestCaseGenerator"""

from __future__ import annotations

from ai_prompt_toolkit.test_generator import TestCase, TestCaseGenerator, TestDataset


class TestTestCase:
    def test_to_dict(self):
        tc = TestCase(test_id="abc123", input_text="测试输入", expected_output="测试输出", category="test")
        d = tc.to_dict()
        assert d["test_id"] == "abc123"
        assert d["input_text"] == "测试输入"


class TestTestDataset:
    def test_size(self):
        ds = TestDataset(
            dataset_id="ds1",
            name="test",
            cases=[
                TestCase(test_id="1", input_text="a"),
                TestCase(test_id="2", input_text="b"),
            ],
        )
        assert ds.size == 2

    def test_to_dict(self):
        ds = TestDataset(dataset_id="ds1", name="test", cases=[])
        d = ds.to_dict()
        assert d["size"] == 0


class TestTestCaseGenerator:
    def test_generate_from_template(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_from_template("你是专业助手", count=5)
        assert len(cases) == 5
        for c in cases:
            assert c.input_text != ""
            assert c.test_id != ""
            assert c.category != ""

    def test_generate_from_template_count(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_from_template("你是助手", count=10)
        assert len(cases) == 10

    def test_generate_harmonyos_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_harmonyos_cases(count=5)
        assert len(cases) == 5
        for c in cases:
            assert c.category in ["harmonyos_arkts", "harmonyos_distributed", "huawei_cloud", "pangu", "ascend_npu"]

    def test_generate_adversarial_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_adversarial_cases(count=5)
        assert len(cases) == 5
        for c in cases:
            assert c.difficulty == "hard"
            assert c.category in [
                "injection",
                "jailbreak",
                "info_leak",
                "constraint_bypass",
                "social_engineering",
                "encoding_bypass",
            ]

    def test_generate_multi_turn_cases(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_multi_turn_cases(count=3)
        assert len(cases) == 3
        for c in cases:
            assert "multi_turn" in c.category

    def test_generate_dataset_full(self):
        gen = TestCaseGenerator(seed=42)
        ds = gen.generate_dataset(
            "test_dataset",
            template_text="你是专业助手, 必须回答问题",
            include_adversarial=True,
            include_harmonyos=True,
            include_multi_turn=True,
            base_count=3,
        )
        assert ds.size > 0
        assert ds.name == "test_dataset"
        assert ds.dataset_id != ""

    def test_generate_dataset_no_template(self):
        gen = TestCaseGenerator(seed=42)
        ds = gen.generate_dataset("auto_dataset")
        assert ds.size > 0

    def test_generate_dataset_minimal(self):
        gen = TestCaseGenerator(seed=42)
        ds = gen.generate_dataset(
            "minimal",
            template_text="你是助手",
            include_adversarial=False,
            include_harmonyos=False,
            include_multi_turn=False,
            base_count=3,
        )
        assert ds.size == 3

    def test_generate_adversarial_max(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_adversarial_cases(count=20)
        assert len(cases) <= 8

    def test_multi_turn_max(self):
        gen = TestCaseGenerator(seed=42)
        cases = gen.generate_multi_turn_cases(count=10)
        assert len(cases) <= 3

    def test_deterministic_with_same_generator(self):
        gen = TestCaseGenerator(seed=42)
        cases1 = gen.generate_from_template("你是助手", count=3)
        cases2 = gen.generate_from_template("你是助手", count=3)
        assert len(cases1) == len(cases2)
