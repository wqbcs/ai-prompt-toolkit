"""R28: 评估矩阵可视化 + Playground + 华为云赛事贴合 测试套件"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.eval_matrix import (
    MatrixCell,
    MatrixReport,
    build_matrix_from_evaluator_results,
    generate_eval_matrix_html,
    generate_gepa_history_html,
)
from ai_prompt_toolkit.huawei_eval import (
    DimensionScore,
    evaluate_contest_readiness,
    evaluate_harmonyos_agent,
    evaluate_huawei_cloud,
)
from ai_prompt_toolkit.prompt_playground import (
    PlaygroundTemplate,
    extract_template_variables,
    generate_playground_html,
    render_template,
)

# ═══════════════════════════════════════
# MatrixCell 测试
# ═══════════════════════════════════════


class TestMatrixCell:
    def test_status_class_excellent(self):
        cell = MatrixCell(prompt_name="p", evaluator_name="e", score=9.5, max_score=10.0, passed=True)
        assert cell.status_class == "cell-excellent"

    def test_status_class_good(self):
        cell = MatrixCell(prompt_name="p", evaluator_name="e", score=7.5, max_score=10.0, passed=True)
        assert cell.status_class == "cell-good"

    def test_status_class_pass(self):
        cell = MatrixCell(prompt_name="p", evaluator_name="e", score=6.0, max_score=10.0, passed=True)
        assert cell.status_class == "cell-pass"

    def test_status_class_fail(self):
        cell = MatrixCell(prompt_name="p", evaluator_name="e", score=3.0, max_score=10.0, passed=False)
        assert cell.status_class == "cell-fail"

    def test_to_dict(self):
        cell = MatrixCell(prompt_name="p", evaluator_name="e", score=8.5, max_score=10.0, passed=True, feedback="good")
        d = cell.to_dict()
        assert d["score"] == 8.5
        assert d["passed"] is True


# ═══════════════════════════════════════
# MatrixReport 测试
# ═══════════════════════════════════════


class TestMatrixReport:
    def test_basic_creation(self):
        report = MatrixReport(title="Test Report")
        assert report.title == "Test Report"
        assert report.generated_at != ""

    def test_to_dict(self):
        report = MatrixReport(prompt_names=["p1"], evaluator_names=["e1"])
        d = report.to_dict()
        assert d["prompt_names"] == ["p1"]
        assert d["evaluator_names"] == ["e1"]


# ═══════════════════════════════════════
# generate_eval_matrix_html 测试
# ═══════════════════════════════════════


class TestEvalMatrixHtml:
    def test_generate_html(self):
        report = MatrixReport(
            title="Test Matrix",
            prompt_names=["template-a"],
            evaluator_names=["lint", "security"],
            cells=[
                MatrixCell("template-a", "lint", score=85.0, max_score=100.0, passed=True),
                MatrixCell("template-a", "security", score=9.0, max_score=10.0, passed=True),
            ],
        )
        html = generate_eval_matrix_html(report)
        assert "<!DOCTYPE html>" in html
        assert "Test Matrix" in html
        assert "template-a" in html
        assert "85.0" in html

    def test_generate_html_to_file(self):
        report = MatrixReport(
            prompt_names=["p1"],
            evaluator_names=["e1"],
            cells=[MatrixCell("p1", "e1", score=8.0, max_score=10.0, passed=True)],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.html"
            html = generate_eval_matrix_html(report, output_path=str(path))
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "p1" in content

    def test_generate_html_with_failures(self):
        report = MatrixReport(
            prompt_names=["p1"],
            evaluator_names=["e1"],
            cells=[MatrixCell("p1", "e1", score=3.0, max_score=10.0, passed=False, feedback="Missing constraints")],
        )
        html = generate_eval_matrix_html(report)
        assert "FAIL" in html
        assert "Missing constraints" in html


# ═══════════════════════════════════════
# generate_gepa_history_html 测试
# ═══════════════════════════════════════


class TestGepaHistoryHtml:
    def test_generate_history_html(self):
        from ai_prompt_toolkit.gepa import GEPAResult

        result = GEPAResult(
            best_instructions={"main": "optimized"},
            best_score=0.9,
            initial_score=0.5,
            improvement=0.4,
            candidates_explored=7,
            generations=3,
            frontier_size=3,
            history=[
                {"event": "seed", "candidate_id": 0, "score": 0.5},
                {"event": "mutate", "candidate_id": 1, "parent_id": 0, "score": 0.7, "predictor": "main"},
                {"event": "merge", "candidate_id": 2, "score": 0.9},
            ],
        )
        html = generate_gepa_history_html(result)
        assert "GEPA" in html
        assert "seed" in html
        assert "mutate" in html
        assert "merge" in html


# ═══════════════════════════════════════
# build_matrix_from_evaluator_results 测试
# ═══════════════════════════════════════


class TestBuildMatrixFromEvaluatorResults:
    def test_build_from_evaluator(self):
        report = build_matrix_from_evaluator_results(
            "test", "You are a professional AI assistant.", evaluator_names=["lint"]
        )
        assert len(report.cells) > 0
        assert report.cells[0].prompt_name == "test"


# ═══════════════════════════════════════
# PlaygroundTemplate 测试
# ═══════════════════════════════════════


class TestPlaygroundTemplate:
    def test_extract_variables(self):
        tpl = PlaygroundTemplate(content="Hello {{name}}, your task is {{task}}.")
        vars = tpl.extract_variables()
        assert vars == ["name", "task"]

    def test_extract_no_duplicates(self):
        tpl = PlaygroundTemplate(content="{{name}} and {{name}} again")
        vars = tpl.extract_variables()
        assert vars == ["name"]

    def test_render(self):
        tpl = PlaygroundTemplate(
            content="Hello {{name}}!",
            variable_values={"name": "World"},
        )
        assert tpl.render() == "Hello World!"

    def test_render_missing_var(self):
        tpl = PlaygroundTemplate(content="Hello {{name}}!")
        assert tpl.render() == "Hello {{name}}!"

    def test_to_dict(self):
        tpl = PlaygroundTemplate(
            name="test",
            content="Hello {{name}}",
            variable_values={"name": "World"},
        )
        tpl.extract_variables()
        d = tpl.to_dict()
        assert d["name"] == "test"
        assert d["rendered"] == "Hello World"
        assert "name" in d["variables"]


# ═══════════════════════════════════════
# extract_template_variables / render_template 测试
# ═══════════════════════════════════════


class TestTemplateFunctions:
    def test_extract_variables(self):
        vars = extract_template_variables("{{a}} and {{b}} and {{a}}")
        assert vars == ["a", "b"]

    def test_render_template(self):
        result = render_template("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_no_variables(self):
        result = render_template("No variables", {})
        assert result == "No variables"


# ═══════════════════════════════════════
# generate_playground_html 测试
# ═══════════════════════════════════════


class TestPlaygroundHtml:
    def test_generate_html(self):
        html = generate_playground_html()
        assert "<!DOCTYPE html>" in html
        assert "Playground" in html
        assert "petite-vue" in html

    def test_generate_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "playground.html"
            generate_playground_html(output_path=str(path))
            assert path.exists()


# ═══════════════════════════════════════
# 华为云赛事贴合评估 测试
# ═══════════════════════════════════════


class TestHarmonyosAgentEval:
    def test_basic_eval(self):
        result = evaluate_harmonyos_agent(
            "You are an ArkTS developer. Use @Entry and @Component. Handle onCreate lifecycle."
        )
        assert result.category == "harmonyos_agent"
        assert result.overall_score > 0
        assert len(result.dimensions) == 5

    def test_empty_text(self):
        result = evaluate_harmonyos_agent("Simple prompt without any keywords")
        assert result.overall_score < 3.0

    def test_full_text(self):
        text = "ArkTS @Entry @Component build() struct Stage模型 onCreate onDestroy UIAbility 分布式 Distributed 安全沙箱 ohos.permission LazyForEach 性能优化"
        result = evaluate_harmonyos_agent(text)
        assert result.overall_score > 5.0

    def test_dimension_feedback(self):
        result = evaluate_harmonyos_agent("Simple prompt")
        for d in result.dimensions:
            if d.score < 8.0:
                assert d.feedback != "" or d.score >= 8.0


class TestHuaweiCloudEval:
    def test_basic_eval(self):
        result = evaluate_huawei_cloud("Deploy on ModelArts. Use IAM AK/SK. API endpoint myhuaweicloud.com cn-north-4.")
        assert result.category == "huawei_cloud"
        assert result.overall_score > 0
        assert len(result.dimensions) == 5

    def test_empty_text(self):
        result = evaluate_huawei_cloud("Simple prompt")
        assert result.overall_score < 3.0


class TestContestReadiness:
    def test_basic_eval(self):
        result = evaluate_contest_readiness("ArkTS developer prompt with ModelArts and pangu API")
        assert "contest_score" in result
        assert "readiness_level" in result
        assert "recommendations" in result
        assert result["pangu_integration"] is True

    def test_no_integration(self):
        result = evaluate_contest_readiness("Generic AI assistant prompt")
        assert result["pangu_integration"] is False
        assert result["harmonyos_integration"] is False
        assert result["contest_score"] < 5.0

    def test_full_integration(self):
        text = "鸿蒙ArkTS @Entry @Component build() struct Stage模型 onCreate onDestroy UIAbility AbilityStage 分布式 Distributed 设备发现 安全沙箱 ohos.permission LazyForEach 性能优化 组件复用 ModelArts 推理部署 在线服务 IAM AK/SK Token myhuaweicloud.com cn-north-4 endpoint 昇腾 NPU CANN MindSpore 数据合规 GDPR 隐私保护"
        result = evaluate_contest_readiness(text)
        assert result["contest_score"] > 3.0
        assert result["pangu_integration"] is False
        assert result["harmonyos_integration"] is True

    def test_readiness_levels(self):
        assert evaluate_contest_readiness("x")["readiness_level"] in [
            "excellent",
            "good",
            "moderate",
            "basic",
            "insufficient",
        ]

    def test_recommendations_not_empty(self):
        result = evaluate_contest_readiness("Simple prompt")
        assert len(result["recommendations"]) > 0


class TestDimensionScore:
    def test_weighted_score(self):
        ds = DimensionScore(dimension="test", score=8.0, weight=1.5)
        assert ds.weighted_score == 12.0

    def test_to_dict(self):
        ds = DimensionScore(dimension="test", score=7.5, weight=1.2, feedback="ok")
        d = ds.to_dict()
        assert d["weighted_score"] == 9.0
