"""R176测试: 覆盖率债务治理 — exceptions契约 + ab_test并行引擎关键路径"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_prompt_toolkit.ab_test.types import ModelConfig, ProviderType, TestStatus
from ai_prompt_toolkit.exceptions import (
    ABTestError,
    CompileError,
    LintError,
    MarketError,
    PromptToolkitError,
    ProviderError,
    RedTeamError,
    SecurityError,
)


class TestExceptionContract:
    """统一异常体系契约: 层次结构/错误码/用户消息/debug_detail"""

    def test_hierarchy(self):
        assert issubclass(CompileError, PromptToolkitError)
        assert issubclass(LintError, PromptToolkitError)
        assert issubclass(SecurityError, PromptToolkitError)
        assert issubclass(ABTestError, PromptToolkitError)
        assert issubclass(ProviderError, ABTestError)  # 二层继承
        assert issubclass(RedTeamError, PromptToolkitError)
        assert issubclass(MarketError, PromptToolkitError)

    def test_error_codes_unique(self):
        codes = [
            cls.error_code
            for cls in (
                PromptToolkitError,
                CompileError,
                LintError,
                SecurityError,
                ABTestError,
                ProviderError,
                RedTeamError,
                MarketError,
            )
        ]
        assert len(codes) == len(set(codes)), "错误码必须唯一"

    def test_str_format_and_to_dict(self):
        err = LintError("规则引擎异常")
        assert str(err) == "[E200] Lint检查异常"
        d = err.to_dict()
        assert d["error_code"] == "E200"
        assert d["user_message"] == "Lint检查异常"
        assert d["debug_detail"] == "规则引擎异常"  # message落入debug_detail

    def test_override_fields(self):
        err = PromptToolkitError("x", error_code="E999", user_message="自定义", debug_detail="堆栈")
        assert err.error_code == "E999"
        assert err.user_message == "自定义"

    def test_compile_error_context(self):
        err = CompileError("语法错误", line=3, directive="if", suggestion="检查缩进")
        assert err.error_code == "E100"
        assert "Line 3" in err.debug_detail
        assert "if" in err.user_message
        assert "检查缩进" in str(err)

    def test_provider_error_context(self):
        err = ProviderError("超时", provider="openai", suggestion="检查API Key")
        assert err.error_code == "E410"
        assert "openai" in err.user_message
        assert "检查API Key" in str(err)


def _make_engine(models: list[ModelConfig]):
    from ai_prompt_toolkit.ab_test.engine import ParallelEngine

    with patch("ai_prompt_toolkit.ab_test.engine.create_provider") as cp:
        config = type("C", (), {})()  # 占位, 实际用types.ABTestConfig
        from ai_prompt_toolkit.ab_test.types import ABTestConfig

        cfg = ABTestConfig(test_id="t", models=models)
        engine = ParallelEngine(cfg)
    return engine


def _ok_result(config: ModelConfig, prompt: str, text: str = "ok"):
    from ai_prompt_toolkit.ab_test.types import ModelResult

    return ModelResult(model_config=config, prompt_template=prompt, response=text, status=TestStatus.COMPLETED)


class TestParallelEngine:
    """核心并行引擎: provider初始化/进度/重试/取消"""

    def _config(self, models):
        from ai_prompt_toolkit.ab_test.types import ABTestConfig

        return ABTestConfig(test_id="t", models=models)

    def test_init_providers_and_progress(self):
        engine = _make_engine([ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")])
        assert "openai:gpt-x" in engine._providers
        assert engine.progress.total == 0
        assert engine.progress.percentage == 0.0
        assert engine.results == []

    def test_cancel_flag(self):
        engine = _make_engine([ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")])
        engine.cancel()
        assert engine._cancelled is True

    @pytest.mark.asyncio
    async def test_invoke_success_first_attempt(self):
        engine = _make_engine([ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")])
        provider = engine._providers["openai:gpt-x"]
        provider.invoke = AsyncMock(
            return_value=_ok_result(
                provider._config
                if hasattr(provider, "_config")
                else ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x"),
                "p",
            )
        )
        out = await engine._invoke_with_retry(provider, "p", {"q": "x"}, max_retries=1)
        assert out.success is True
        assert out.attempt == 1

    @pytest.mark.asyncio
    async def test_invoke_retries_on_exception(self):
        engine = _make_engine([ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")])
        provider = engine._providers["openai:gpt-x"]
        cfg = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")
        provider.invoke = AsyncMock(side_effect=[RuntimeError("boom"), _ok_result(cfg, "p")])
        out = await engine._invoke_with_retry(provider, "p", {"q": "x"}, max_retries=2, timeout=5)
        assert out.success is True
        assert out.attempt == 2  # 第二次成功

    @pytest.mark.asyncio
    async def test_invoke_cancelled(self):
        engine = _make_engine([ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")])
        provider = engine._providers["openai:gpt-x"]
        engine.cancel()
        out = await engine._invoke_with_retry(provider, "p", {"q": "x"}, max_retries=1)
        assert out.success is False
        assert out.error == "cancelled"


class TestEngineRunPaths:
    """run/run_pairwise 主路径端到端(mock provider, 不发真实请求)"""

    def _dataset(self):
        from ai_prompt_toolkit.ab_test.types import TestDataset

        return TestDataset(dataset_id="d", name="d", items=[{"input": f"问题{i}"} for i in range(3)])

    @pytest.mark.asyncio
    async def test_run_end_to_end(self):
        from ai_prompt_toolkit.ab_test.engine import ParallelEngine
        from ai_prompt_toolkit.ab_test.types import ABTestConfig, ModelConfig

        cfg = ABTestConfig(
            test_id="t",
            models=[ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")],
            datasets=[self._dataset()],
            prompt_templates=["回答: {input}"],
        )
        with patch("ai_prompt_toolkit.ab_test.engine.create_provider") as cp:
            engine = ParallelEngine(cfg)
        provider = engine._providers["openai:gpt-x"]
        cfg_m = ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-x")
        provider.invoke = AsyncMock(side_effect=lambda prompt, **kw: _ok_result(cfg_m, prompt, f"答:{prompt}"))

        outputs = await engine.run(max_concurrency=2)
        assert len(outputs) == 3
        assert all(o.success for o in outputs)
        assert engine.progress.total == 3
        assert engine.progress.completed == 3

    @pytest.mark.asyncio
    async def test_run_pairwise_end_to_end(self):
        from ai_prompt_toolkit.ab_test.engine import ParallelEngine
        from ai_prompt_toolkit.ab_test.types import ABTestConfig, ModelConfig

        cfg = ABTestConfig(
            test_id="t",
            models=[
                ModelConfig(provider=ProviderType.OPENAI, model_name="a"),
                ModelConfig(provider=ProviderType.OPENAI, model_name="b"),
            ],
        )
        with patch("ai_prompt_toolkit.ab_test.engine.create_provider") as cp:
            engine = ParallelEngine(cfg)
        pa = engine._providers["openai:a"]
        pb = engine._providers["openai:b"]
        ca = ModelConfig(provider=ProviderType.OPENAI, model_name="a")
        cb = ModelConfig(provider=ProviderType.OPENAI, model_name="b")
        pa.invoke = AsyncMock(side_effect=lambda prompt, **kw: _ok_result(ca, prompt))
        pb.invoke = AsyncMock(side_effect=lambda prompt, **kw: _ok_result(cb, prompt))

        pairs = await engine.run_pairwise(ca, cb, self._dataset(), "模板 {input}")
        assert len(pairs) == 3
        assert all(oa.success and ob.success for oa, ob in pairs)
