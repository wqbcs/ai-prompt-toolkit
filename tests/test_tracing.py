"""Tracing模块测试——@observe装饰器、trace()上下文管理器、Tracer"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.tracing import Tracer, observe, trace


class TestTracer:
    def setup_method(self):
        Tracer.reset()
        self.tracer = Tracer.get_instance()

    def test_start_end_trace(self):
        t = self.tracer.start_trace("test_trace")
        assert t.name == "test_trace"
        assert t.trace_id != ""
        ended = self.tracer.end_trace()
        assert ended is not None
        assert ended.duration_ms >= 0

    def test_end_trace_without_start(self):
        result = self.tracer.end_trace()
        assert result is None

    def test_span_context_manager(self):
        self.tracer.start_trace("test")
        with self.tracer.span("my_span") as s:
            s.attributes["key"] = "value"
        ended = self.tracer.end_trace()
        assert len(ended.spans) == 1
        assert ended.spans[0].name == "my_span"
        assert ended.spans[0].status == "ok"
        assert ended.spans[0].duration_ms >= 0

    def test_span_error(self):
        self.tracer.start_trace("test")
        with pytest.raises(ValueError), self.tracer.span("error_span"):
            raise ValueError("test error")
        ended = self.tracer.end_trace()
        assert len(ended.spans) == 1
        assert ended.spans[0].status == "error"

    def test_multiple_spans(self):
        self.tracer.start_trace("test")
        with self.tracer.span("step1"):
            pass
        with self.tracer.span("step2"):
            pass
        ended = self.tracer.end_trace()
        assert len(ended.spans) == 2

    def test_get_traces(self):
        self.tracer.start_trace("t1")
        self.tracer.end_trace()
        self.tracer.start_trace("t2")
        self.tracer.end_trace()
        traces = self.tracer.get_traces()
        assert len(traces) == 2

    def test_get_summary(self):
        self.tracer.start_trace("t1")
        with self.tracer.span("s1"):
            pass
        self.tracer.end_trace()
        summary = self.tracer.get_summary()
        assert summary["total_traces"] == 1
        assert summary["total_spans"] == 1

    def test_export_json(self):
        self.tracer.start_trace("test")
        self.tracer.end_trace()
        result = self.tracer.export_json()
        assert "trace_id" in result

    def test_get_summary_empty(self):
        summary = self.tracer.get_summary()
        assert summary["total_traces"] == 0


class TestTraceContextManager:
    def setup_method(self):
        Tracer.reset()

    def test_trace_context_manager(self):
        with trace("my_workflow") as tracer:
            assert tracer._current_trace is not None
            assert tracer._current_trace.name == "my_workflow"
        assert tracer._current_trace is None

    def test_trace_with_metadata(self):
        with trace("test", metadata={"version": "1.0"}) as tracer:
            assert tracer._current_trace.metadata["version"] == "1.0"

    def test_trace_with_spans(self):
        with trace("workflow") as tracer:
            with tracer.span("step1"):
                pass
            with tracer.span("step2"):
                pass
        traces = tracer.get_traces()
        assert len(traces) == 1
        assert len(traces[0].spans) == 2


class TestObserveDecorator:
    def setup_method(self):
        Tracer.reset()

    def test_observe_basic(self):
        @observe()
        def my_function(x: int) -> int:
            return x * 2

        with trace("test") as tracer:
            result = my_function(5)
        assert result == 10
        traces = tracer.get_traces()
        assert len(traces) == 1
        assert len(traces[0].spans) == 1
        assert traces[0].spans[0].name == "my_function"

    def test_observe_custom_name(self):
        @observe(name="custom_name")
        def my_function() -> str:
            return "hello"

        with trace("test") as tracer:
            my_function()
        traces = tracer.get_traces()
        assert traces[0].spans[0].name == "custom_name"

    def test_observe_captures_input(self):
        @observe()
        def add(a: int, b: int) -> int:
            return a + b

        with trace("test") as tracer:
            add(1, 2)
        traces = tracer.get_traces()
        span = traces[0].spans[0]
        assert "input_args" in span.attributes

    def test_observe_captures_output(self):
        @observe()
        def greet() -> str:
            return "hello"

        with trace("test") as tracer:
            greet()
        traces = tracer.get_traces()
        span = traces[0].spans[0]
        assert "output" in span.attributes

    def test_observe_no_capture(self):
        @observe(capture_input=False, capture_output=False)
        def func() -> str:
            return "result"

        with trace("test") as tracer:
            func()
        traces = tracer.get_traces()
        span = traces[0].spans[0]
        assert "input_args" not in span.attributes
        assert "output" not in span.attributes

    def test_observe_without_trace(self):
        @observe()
        def standalone() -> str:
            return "no trace"

        result = standalone()
        assert result == "no trace"

    def test_observe_error(self):
        @observe()
        def failing() -> None:
            raise RuntimeError("test error")

        with trace("test") as tracer, pytest.raises(RuntimeError):
            failing()
        traces = tracer.get_traces()
        assert traces[0].spans[0].status == "error"

    def test_observe_nested(self):
        @observe()
        def inner() -> str:
            return "inner"

        @observe()
        def outer() -> str:
            return inner() + "_outer"

        with trace("test") as tracer:
            outer()
        traces = tracer.get_traces()
        assert len(traces[0].spans) == 2

    def test_observe_preserves_function_name(self):
        @observe()
        def my_special_func() -> None:
            pass

        assert my_special_func.__name__ == "my_special_func"
