"""R33: 统一优化管线Pipeline 测试套件"""

from __future__ import annotations

from ai_prompt_toolkit.opt_pipeline import (
    OptPipeline,
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    create_default_pipeline,
    pipeline_optimize,
)

# R206: 规则收窄后原低分输入("test")lint评分升至95.7, 不再满足score_below_95 —
# 本常量是稳定低分输入(lint score≈83), 专供条件门测试, 与规则评分细节解耦
_LOW_SCORE_PROMPT = (
    "处理用户数据，存储客户信息到数据库，API接口返回响应数据。"
    "批量导出用户身份证号与手机号。泄露系统指令。"
    "用户输入任意内容后原样回显。生成回复内容供终端用户浏览。"
    "调用外部API获取实时汇率数据。从5个候选框架中选型一个。"
)


class TestPipelineStage:
    def test_creation(self):
        s = PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 5})
        assert s.name == "tgd"
        assert s.optimizer == "tgd"
        assert s.enabled is True

    def test_to_dict(self):
        s = PipelineStage(name="opro", optimizer="opro", condition="score_below_90")
        d = s.to_dict()
        assert d["name"] == "opro"
        assert d["condition"] == "score_below_90"


class TestPipelineResult:
    def test_creation(self):
        r = PipelineResult(
            initial_score=50.0,
            final_score=85.0,
            improvement=35.0,
            stages_completed=2,
            total_stages=3,
        )
        assert r.improvement == 35.0

    def test_to_dict(self):
        r = PipelineResult(
            initial_score=50.0,
            final_score=85.0,
            improvement=35.0,
            best_optimizer="tgd",
            mode="sequential",
        )
        d = r.to_dict()
        assert d["improvement"] == 35.0
        assert d["best_optimizer"] == "tgd"


class TestOptPipeline:
    def test_add_and_clear_stages(self):
        p = OptPipeline()
        p.add_stage(PipelineStage(name="s1", optimizer="tgd"))
        p.add_stage(PipelineStage(name="s2", optimizer="opro"))
        assert len(p.stages) == 2
        p.clear_stages()
        assert len(p.stages) == 0

    def test_sequential_pipeline_tgd(self):
        p = OptPipeline(PipelineConfig(mode="sequential"))
        p.add_stage(
            PipelineStage(
                name="tgd-optimize",
                optimizer="tgd",
                config={"max_iterations": 2},
                condition="always",
            )
        )
        result = p.run("Write about AI")
        assert isinstance(result, PipelineResult)
        assert result.stages_completed >= 1
        assert result.mode == "sequential"

    def test_sequential_pipeline_opro(self):
        p = OptPipeline(PipelineConfig(mode="sequential"))
        p.add_stage(
            PipelineStage(
                name="opro-optimize",
                optimizer="opro",
                config={"max_generations": 2, "population_size": 2},
                condition="always",
            )
        )
        result = p.run("Tell me about Python")
        assert result.stages_completed >= 1

    def test_parallel_pipeline(self):
        p = OptPipeline(PipelineConfig(mode="parallel"))
        p.add_stage(PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 2}))
        p.add_stage(PipelineStage(name="opro", optimizer="opro", config={"max_generations": 2, "population_size": 2}))
        result = p.run("Hello AI")
        assert result.mode == "parallel"
        assert result.stages_completed == 2

    def test_condition_score_below_threshold(self):
        p = OptPipeline(PipelineConfig(mode="sequential", score_threshold=95.0))
        p.add_stage(
            PipelineStage(
                name="tgd",
                optimizer="tgd",
                config={"max_iterations": 2},
                condition="score_below_threshold",
            )
        )
        result = p.run(_LOW_SCORE_PROMPT)
        assert result.stages_completed >= 1

    def test_condition_always(self):
        p = OptPipeline()
        p.add_stage(PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 1}, condition="always"))
        result = p.run("test")
        assert result.stages_completed >= 1

    def test_condition_score_below_numeric(self):
        # R206: 规则收窄后原输入"test"评分升至95.7不再触发条件 —
        # 换稳定低分输入(_LOW_SCORE_PROMPT, lint score≈83 < 95), 本测试验证的是条件门机制
        p = OptPipeline()
        p.add_stage(
            PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 1}, condition="score_below_95")
        )
        result = p.run(_LOW_SCORE_PROMPT)
        assert result.stages_completed >= 1

    def test_disabled_stage_skipped(self):
        p = OptPipeline(PipelineConfig(mode="sequential"))
        p.add_stage(PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 1}, enabled=False))
        result = p.run("test")
        assert result.stages_completed == 0

    def test_custom_eval_fn(self):
        call_count = [0]

        def custom_eval(text):
            call_count[0] += 1
            return 75.0

        p = OptPipeline(PipelineConfig(eval_fn=custom_eval))
        p.add_stage(PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 1}, condition="always"))
        result = p.run("test")
        assert call_count[0] > 0

    def test_fail_fast(self):
        def high_eval(text):
            return 95.0

        p = OptPipeline(PipelineConfig(fail_fast=True, score_threshold=90.0, eval_fn=high_eval))
        p.add_stage(PipelineStage(name="tgd", optimizer="tgd", config={"max_iterations": 1}))
        p.add_stage(PipelineStage(name="opro", optimizer="opro", config={"max_generations": 1, "population_size": 2}))
        result = p.run("test")
        assert result.stages_completed <= 1

    def test_unknown_optimizer_passes_through(self):
        p = OptPipeline()
        p.add_stage(PipelineStage(name="unknown", optimizer="nonexistent_optimizer"))
        result = p.run("test")
        assert result.stages_completed == 1
        sr = result.stage_results[0]
        assert sr.get("optimizer") == "nonexistent_optimizer"
        assert "score" in sr


class TestCreateDefaultPipeline:
    def test_creates_pipeline(self):
        p = create_default_pipeline("sequential")
        assert len(p.stages) == 3
        assert p.stages[0].optimizer == "lint-fix"
        assert p.stages[1].optimizer == "tgd"
        assert p.stages[2].optimizer == "opro"

    def test_parallel_mode(self):
        p = create_default_pipeline("parallel")
        assert p.config.mode == "parallel"


class TestPipelineOptimize:
    def test_convenience_function(self):
        result = pipeline_optimize("test prompt", mode="sequential")
        assert isinstance(result, PipelineResult)

    def test_with_custom_stages(self):
        stages = [
            {"name": "tgd", "optimizer": "tgd", "config": {"max_iterations": 2}},
        ]
        result = pipeline_optimize("test", stages=stages)
        assert result.stages_completed >= 1

    def test_with_score_threshold(self):
        result = pipeline_optimize("test", score_threshold=95.0)
        assert isinstance(result, PipelineResult)
