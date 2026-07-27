"""62维度评估框架测试 — evaluate_template/EvaluationReport/DimensionScore/维度API"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.evaluator import (
    DimensionScore,
    EvaluationReport,
    evaluate_template,
    get_all_dimensions,
    get_dimensions_by_category,
)


class TestEvaluateTemplate:
    def test_basic_evaluation(self):
        result = evaluate_template("test", "你是一个专业的AI助手，请以JSON格式输出。不要超过500字。如果失败请回退。")
        assert result.overall_score > 0
        assert result.dimension_count == 130
        assert len(result.scores) == 130

    def test_empty_prompt(self):
        result = evaluate_template("empty", "")
        assert result.overall_score >= 0
        assert result.dimension_count == 130

    def test_rich_prompt(self):
        text = (
            "你是一位专业的云架构师。\n"
            "请以JSON格式输出架构设计方案。\n"
            "不要超过500字。\n"
            "如果失败请回退到默认方案。\n"
            "示例：如下的输出格式\n"
            "评估标准：准确性和完整性\n"
            "让我们一步步思考。\n"
        )
        result = evaluate_template("rich", text)
        assert result.overall_score > 10
        assert result.dimension_count == 130

    def test_with_dimensions_filter(self):
        result = evaluate_template("test", "你是一个专业的助手", dimensions=["D01", "D02", "D03"])
        assert result.dimension_count == 3
        assert len(result.scores) == 3

    def test_with_dimensions_short_id_normalized(self):
        result = evaluate_template("test", "你是一个专业的助手", dimensions=["D1", "D2", "D3"])
        assert result.dimension_count == 3
        score_ids = {s.dimension_id for s in result.scores}
        assert "D01" in score_ids
        assert "D02" in score_ids
        assert "D03" in score_ids

    def test_with_categories_filter(self):
        result = evaluate_template("test", "测试", categories=["structure"])
        assert result.dimension_count > 0
        for s in result.scores:
            assert s.category == "structure"

    def test_evaluation_time_recorded(self):
        result = evaluate_template("test", "测试")
        assert result.evaluation_time_ms >= 0


class TestEvaluationReport:
    def test_to_dict(self):
        result = evaluate_template("test", "你是一个专业的AI助手")
        d = result.to_dict()
        assert "template_id" in d
        assert "overall_score" in d
        assert "scores" in d
        assert "dimension_count" in d

    def test_percentage(self):
        result = evaluate_template("test", "你是一个专业的AI助手")
        assert 0 <= result.percentage <= 100

    def test_max_possible_score(self):
        result = evaluate_template("test", "测试")
        assert result.max_possible_score > 0


class TestDimensionScore:
    def test_basic_properties(self):
        ds = DimensionScore(dimension_id="D01", name="角色清晰度", category="structure", weight=1.0, score=8.5)
        assert ds.dimension_id == "D01"
        assert ds.name == "角色清晰度"
        assert ds.score == 8.5

    def test_to_dict(self):
        ds = DimensionScore(dimension_id="D01", name="角色清晰度", category="structure", weight=1.0, score=8.5)
        d = ds.to_dict()
        assert d["dimension_id"] == "D01"
        assert d["score"] == 8.5

    def test_normalized(self):
        ds = DimensionScore(dimension_id="D01", name="测试", category="structure", weight=1.0, score=8.0, max_score=10.0)
        assert ds.normalized == pytest.approx(0.8)


class TestDimensionAPIs:
    def test_get_all_dimensions(self):
        dims = get_all_dimensions()
        assert len(dims) == 130
        assert dims[0]["id"] == "D01"
        assert dims[-1]["id"] == "D130"

    def test_get_dimensions_by_category(self):
        structure = get_dimensions_by_category("structure")
        assert len(structure) > 0
        for d in structure:
            assert d["category"] == "structure"

    def test_get_dimensions_by_category_security(self):
        security = get_dimensions_by_category("security")
        assert len(security) > 0

    def test_get_dimensions_by_category_unknown(self):
        result = get_dimensions_by_category("nonexistent")
        assert result == []

    def test_all_dimensions_have_required_fields(self):
        dims = get_all_dimensions()
        for d in dims:
            assert "id" in d
            assert "name" in d
            assert "category" in d
            assert "weight" in d
