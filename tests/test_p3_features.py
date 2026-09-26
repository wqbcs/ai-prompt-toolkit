"""P3功能测试: Prompt优化+Tracing+PromptBuilder"""

from __future__ import annotations

from ai_prompt_toolkit.prompt_builder import PromptBuilder, build_from_template
from ai_prompt_toolkit.prompt_optimizer import (
    _OPTIMIZATION_STRATEGIES,
    OptimizationResult,
    OptimizationStep,
    _detect_issues,
    _evaluate_text,
    optimize_prompt,
)
from ai_prompt_toolkit.tracing import Span, Trace, Tracer


class TestPromptOptimizer:
    def test_detect_issues_empty(self):
        issues = _detect_issues(
            "你是一个专业的AI助手。请按照以下步骤执行：1. 分析 2. 回答。输出格式：JSON。约束：不超过500字。如果无法回答请说明。"
        )
        assert isinstance(issues, list)

    def test_detect_issues_short(self):
        issues = _detect_issues("帮我翻译")
        assert len(issues) > 0

    def test_evaluate_text(self):
        score = _evaluate_text("你是一个专业的AI助手。")
        assert 0 <= score <= 100

    def test_optimize_prompt_simple(self):
        result = optimize_prompt("帮我翻译", max_iterations=2)
        assert isinstance(result, OptimizationResult)
        assert result.original_score >= 0
        assert result.final_score >= 0

    def test_optimize_prompt_already_good(self):
        good_prompt = """你是一个专业的翻译助手。你的核心能力包括：中英翻译、术语管理、本地化。

请按照以下步骤执行：
1. 分析源文本的语义和风格
2. 确定目标语言的术语翻译
3. 生成自然流畅的翻译

输出格式：纯文本，保持原文段落结构。

约束条件：
- 输出长度不超过原文2倍
- 保持专业术语一致性

如果无法翻译，请回复"无法翻译，原因：..."。"""
        result = optimize_prompt(good_prompt, max_iterations=1)
        assert result.final_score >= result.original_score or result.iterations == 0

    def test_optimization_step_to_dict(self):
        step = OptimizationStep(
            strategy="add_role",
            strategy_name="角色定义强化",
            original_text="a",
            optimized_text="b",
            score_before=50.0,
            score_after=60.0,
            improvement=10.0,
        )
        d = step.to_dict()
        assert d["strategy"] == "add_role"
        assert d["improvement"] == 10.0

    def test_optimization_result_to_dict(self):
        result = OptimizationResult(
            original_text="a",
            optimized_text="b",
            original_score=50.0,
            final_score=70.0,
            total_improvement=20.0,
            iterations=2,
        )
        d = result.to_dict()
        assert d["final_score"] == 70.0
        assert d["iterations"] == 2

    def test_strategies_defined(self):
        assert len(_OPTIMIZATION_STRATEGIES) >= 6
        assert "add_role" in _OPTIMIZATION_STRATEGIES
        assert "add_structure" in _OPTIMIZATION_STRATEGIES


class TestTracer:
    def setup_method(self):
        Tracer.reset()

    def test_start_end_trace(self):
        tracer = Tracer()
        trace = tracer.start_trace("test")
        assert trace.name == "test"
        ended = tracer.end_trace()
        assert ended is not None
        assert ended.duration_ms >= 0

    def test_span_context_manager(self):
        tracer = Tracer()
        tracer.start_trace("test")
        with tracer.span("lint") as s:
            s.attributes["files"] = 5
        trace = tracer.end_trace()
        assert len(trace.spans) == 1
        assert trace.spans[0].name == "lint"
        assert trace.spans[0].attributes["files"] == 5

    def test_span_error_handling(self):
        tracer = Tracer()
        tracer.start_trace("test")
        try:
            with tracer.span("failing") as s:
                raise ValueError("test error")
        except ValueError:
            pass
        trace = tracer.end_trace()
        assert trace.spans[0].status == "error"

    def test_get_traces(self):
        tracer = Tracer()
        for i in range(3):
            tracer.start_trace(f"trace_{i}")
            tracer.end_trace()
        traces = tracer.get_traces()
        assert len(traces) == 3

    def test_export_json(self):
        tracer = Tracer()
        tracer.start_trace("export_test")
        with tracer.span("step1"):
            pass
        tracer.end_trace()
        json_str = tracer.export_json()
        assert "export_test" in json_str
        assert "step1" in json_str

    def test_summary(self):
        tracer = Tracer()
        tracer.start_trace("t1")
        with tracer.span("s1"):
            pass
        tracer.end_trace()
        summary = tracer.get_summary()
        assert summary["total_traces"] == 1
        assert summary["total_spans"] == 1

    def test_save_traces(self, tmp_path):
        tracer = Tracer(export_dir=str(tmp_path))
        tracer.start_trace("save_test")
        tracer.end_trace()
        count = tracer.save_traces()
        assert count == 1

    def test_singleton(self):
        t1 = Tracer.get_instance()
        t2 = Tracer.get_instance()
        assert t1 is t2

    def test_trace_to_dict(self):
        trace = Trace(trace_id="abc123", name="test")
        d = trace.to_dict()
        assert d["trace_id"] == "abc123"
        assert "spans" in d

    def test_span_to_dict(self):
        span = Span(span_id="sp1", name="lint", duration_ms=42.5)
        d = span.to_dict()
        assert d["name"] == "lint"
        assert d["duration_ms"] == 42.5


class TestPromptBuilder:
    def test_basic_build(self):
        prompt = PromptBuilder().set_role("翻译助手").add_instruction("翻译以下内容").build()
        assert "翻译助手" in prompt
        assert "翻译以下内容" in prompt

    def test_add_steps(self):
        prompt = PromptBuilder().set_role("助手").add_steps(["分析输入", "生成回答", "校验输出"]).build()
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt

    def test_add_example(self):
        prompt = PromptBuilder().add_instruction("翻译").add_example("Hello", "你好").build()
        assert "示例" in prompt
        assert "Hello" in prompt

    def test_add_constraint(self):
        prompt = (
            PromptBuilder().add_instruction("回答问题").add_constraint("不超过500字").add_constraint("使用中文").build()
        )
        assert "约束条件" in prompt
        assert "不超过500字" in prompt

    def test_add_variable(self):
        prompt = (
            PromptBuilder()
            .add_instruction("翻译{{content}}")
            .add_variable("content")
            .build(context={"content": "Hello World"})
        )
        assert "Hello World" in prompt

    def test_add_output_format(self):
        prompt = PromptBuilder().add_instruction("分析").add_output_format("JSON格式: {result: string}").build()
        assert "输出格式" in prompt

    def test_add_error_handling(self):
        prompt = PromptBuilder().add_instruction("回答").add_error_handling().build()
        assert "无法完成" in prompt

    def test_few_shot(self):
        prompt = (
            PromptBuilder()
            .add_instruction("翻译")
            .add_few_shot(
                [
                    {"input": "Hello", "output": "你好"},
                    {"input": "World", "output": "世界"},
                ]
            )
            .build()
        )
        assert "Hello" in prompt
        assert "World" in prompt

    def test_chaining(self):
        prompt = (
            PromptBuilder()
            .set_role("助手", skills=["分析", "推理"])
            .add_instruction("回答问题")
            .add_steps(["思考", "回答"])
            .add_constraint("简洁")
            .add_error_handling()
            .build()
        )
        assert "助手" in prompt
        assert "回答问题" in prompt

    def test_to_dict(self):
        builder = PromptBuilder().set_role("助手").add_instruction("test")
        d = builder.to_dict()
        assert d["role"] == "助手"
        assert d["blocks"] == 2

    def test_build_from_template(self):
        result = build_from_template("你好{{name}}，欢迎使用{{product}}", name="张三", product="AI助手")
        assert "张三" in result
        assert "AI助手" in result

    def test_build_from_template_missing_var(self):
        result = build_from_template("你好{{name}}", product="test")
        assert "[name]" in result
