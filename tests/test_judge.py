"""LLM-as-Judge评估模块测试"""

from unittest.mock import patch

from ai_prompt_toolkit.ab_test.judge import (
    _PAIR_PATTERN,
    _SCORE_PATTERN,
    BUILTIN_DIMENSIONS,
    AbsoluteJudgeResult,
    JudgeDimension,
    LLMJudge,
    PairwiseJudgeResult,
    create_judge,
    create_multi_judge,
)


class TestScoreParsing:
    def test_absolute_score_pattern(self):
        text = "分析理由...\n\n[[4]]"
        match = _SCORE_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "4"

    def test_absolute_score_no_match(self):
        text = "没有分数标记"
        match = _SCORE_PATTERN.search(text)
        assert match is None

    def test_pairwise_pattern_a(self):
        text = "分析...\n[[A]]"
        match = _PAIR_PATTERN.search(text)
        assert match is not None
        assert match.group(1).upper() == "A"

    def test_pairwise_pattern_b(self):
        text = "分析...\n[[B]]"
        match = _PAIR_PATTERN.search(text)
        assert match is not None
        assert match.group(1).upper() == "B"

    def test_pairwise_pattern_c(self):
        text = "分析...\n[[C]]"
        match = _PAIR_PATTERN.search(text)
        assert match is not None
        assert match.group(1).upper() == "C"

    def test_pairwise_lowercase(self):
        text = "分析...\n[[a]]"
        match = _PAIR_PATTERN.search(text)
        assert match is not None


class TestBuiltinDimensions:
    def test_six_core_dimensions(self):
        core = ["relevance", "accuracy", "fluency", "completeness", "safety", "helpfulness"]
        for dim_id in core:
            assert dim_id in BUILTIN_DIMENSIONS
            assert BUILTIN_DIMENSIONS[dim_id].weight > 0

    def test_rag_dimensions(self):
        rag = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        for dim_id in rag:
            assert dim_id in BUILTIN_DIMENSIONS

    def test_safety_highest_weight(self):
        safety_weight = BUILTIN_DIMENSIONS["safety"].weight
        for dim_id, dim in BUILTIN_DIMENSIONS.items():
            if dim_id != "safety":
                assert safety_weight >= dim.weight


class TestJudgeDimension:
    def test_to_dict(self):
        dim = JudgeDimension("test_dim", "测试维度", "描述", 1.5)
        d = dim.to_dict()
        assert d["dimension_id"] == "test_dim"
        assert d["name"] == "测试维度"
        assert d["weight"] == 1.5


class TestAbsoluteJudgeResult:
    def test_to_dict(self):
        dim = JudgeDimension("relevance", "相关性")
        result = AbsoluteJudgeResult(dimension=dim, score=4.0, reasoning="good", judge_model="gpt-4")
        d = result.to_dict()
        assert d["score"] == 4.0
        assert d["judge_model"] == "gpt-4"
        assert d["dimension"]["dimension_id"] == "relevance"


class TestPairwiseJudgeResult:
    def test_to_dict(self):
        result = PairwiseJudgeResult(winner="A", confidence=0.9, reasoning="A is better")
        d = result.to_dict()
        assert d["winner"] == "A"
        assert d["confidence"] == 0.9


class TestLLMJudgeParsing:
    def test_parse_absolute_with_score(self):
        with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType

            config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
            judge = LLMJudge(config)

        score, reasoning = judge._parse_absolute("回答相关且准确\n\n[[4]]")
        assert score == 4.0
        assert "回答相关且准确" in reasoning

    def test_parse_absolute_clamp_score(self):
        with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType

            config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
            judge = LLMJudge(config)

        score, _ = judge._parse_absolute("[[10]]")
        assert score == 5.0

        score, _ = judge._parse_absolute("[[0]]")
        assert score == 1.0

    def test_parse_absolute_no_score(self):
        with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType

            config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
            judge = LLMJudge(config)

        score, _ = judge._parse_absolute("无法判断")
        assert score == 3.0

    def test_parse_pairwise(self):
        with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType

            config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
            judge = LLMJudge(config)

        winner, _ = judge._parse_pairwise("A更好\n[[A]]")
        assert winner == "A"

    def test_parse_pairwise_no_match(self):
        with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
            from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType

            config = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
            judge = LLMJudge(config)

        winner, _ = judge._parse_pairwise("无法判断")
        assert winner == "C"


class TestCreateJudge:
    def test_create_judge_default(self):
        judge = create_judge()
        assert judge is not None

    def test_create_judge_custom(self):
        judge = create_judge(
            judge_model="claude-3-haiku",
            provider="anthropic",
            dimensions=["relevance", "accuracy"],
            mode="absolute",
        )
        assert judge is not None


class TestCreateMultiJudge:
    def test_create_multi_judge(self):
        configs = [
            {"provider": "openai", "model": "gpt-4o-mini"},
            {"provider": "anthropic", "model": "claude-3-haiku"},
        ]
        ensemble = create_multi_judge(configs, aggregation="majority_vote")
        assert ensemble is not None
        assert len(ensemble._judges) == 2
