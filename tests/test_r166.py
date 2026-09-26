"""R166测试: F3定价外部化(PricingCatalog, LiteLLM schema)"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ai_prompt_toolkit.linter.cost_tracker import CostTracker
from ai_prompt_toolkit.linter.token_analyzer import estimate_tokens
from ai_prompt_toolkit.pricing import (
    BUILTIN_PRICING_PATH,
    PricingCatalog,
    get_catalog,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestPricingCatalogLoad:
    def test_builtin_file_exists(self):
        assert BUILTIN_PRICING_PATH.exists()

    def test_builtin_loads_models(self):
        catalog = get_catalog(refresh=True)
        keys = catalog.model_keys
        assert "gpt-4o" in keys
        assert "pangu-large" in keys
        assert "deepseek-chat" in keys
        assert len(keys) >= 20

    def test_meta_keys_excluded(self):
        catalog = get_catalog(refresh=True)
        assert all(not k.startswith("_") for k in catalog.model_keys)

    def test_litellm_schema_fields(self):
        catalog = get_catalog(refresh=True)
        p = catalog.get("gpt-4o")
        assert p is not None
        assert p.input_cost_per_token == 2.5e-06
        assert p.output_cost_per_token == 1e-05
        assert p.max_tokens == 128000
        assert p.litellm_provider == "openai"


class TestPricingResolution:
    def test_exact_match_wins(self):
        catalog = PricingCatalog(
            {
                "gpt-4": {"input_cost_per_token": 1.0, "output_cost_per_token": 1.0},
                "gpt-4o": {"input_cost_per_token": 2.0, "output_cost_per_token": 2.0},
            }
        )
        assert catalog.get("gpt-4o").input_cost_per_token == 2.0

    def test_longest_prefix_match(self):
        """回归守护: 'pangu-nlp-7b' 必须命中长前缀而非被 'pangu' 挡住"""
        catalog = PricingCatalog(
            {
                "pangu": {"input_cost_per_token": 1.0, "output_cost_per_token": 1.0},
                "pangu-nlp-7b": {"input_cost_per_token": 7.0, "output_cost_per_token": 7.0},
            }
        )
        assert catalog.get("pangu-nlp-7b").input_cost_per_token == 7.0
        assert catalog.get("pangu-nlp-65b").input_cost_per_token == 1.0

    def test_prefix_match_gpt4o_regression(self):
        """回归守护: 'gpt-4o' 不得被 'gpt-4' 首个前缀命中(历史计价错误)"""
        catalog = PricingCatalog(
            {
                "gpt-4": {"input_cost_per_token": 3e-05, "output_cost_per_token": 6e-05},
                "gpt-4o": {"input_cost_per_token": 2.5e-06, "output_cost_per_token": 1e-05},
            }
        )
        assert catalog.get("gpt-4o").input_cost_per_token == 2.5e-06

    def test_unknown_falls_to_default(self):
        catalog = PricingCatalog(
            {
                "gpt-4o": {"input_cost_per_token": 2.5e-06, "output_cost_per_token": 1e-05},
                "default": {"input_cost_per_token": 3e-06, "output_cost_per_token": 1.5e-05},
            }
        )
        p = catalog.get_or_default("totally-unknown-model")
        assert p.input_cost_per_token == 3e-06

    def test_unknown_no_default_zero(self):
        catalog = PricingCatalog({"gpt-4o": {"input_cost_per_token": 1.0, "output_cost_per_token": 1.0}})
        p = catalog.get_or_default("nope")
        assert p.input_cost_per_token == 0.0

    def test_estimate_cost_math(self):
        catalog = PricingCatalog({"gpt-4o": {"input_cost_per_token": 2.5e-06, "output_cost_per_token": 1e-05}})
        cost = catalog.estimate_cost_usd("gpt-4o", 1000, 500)
        assert cost == pytest.approx(1000 * 2.5e-06 + 500 * 1e-05)


class TestPricingOverrideChain:
    def test_extra_path_overrides_builtin(self, tmp_path: Path):
        override = tmp_path / "custom.json"
        override.write_text(
            json.dumps(
                {
                    "gpt-4o": {"input_cost_per_token": 9.9, "output_cost_per_token": 9.9},
                }
            ),
            encoding="utf-8",
        )
        catalog = PricingCatalog.load(extra_paths=[override], include_user_override=False)
        assert catalog.get("gpt-4o").input_cost_per_token == 9.9

    def test_user_override_file(self, tmp_path: Path, monkeypatch):
        user_file = tmp_path / "pricing.json"
        user_file.write_text(
            json.dumps(
                {
                    "my-private-model": {"input_cost_per_token": 1e-05, "output_cost_per_token": 2e-05},
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("PROMPT_TOOLKIT_PRICING", str(user_file))
        monkeypatch.chdir(tmp_path)  # CWD下无.prompt-toolkit/pricing.json, 不产生额外覆盖
        catalog = PricingCatalog.load(include_user_override=True)
        assert catalog.get("my-private-model").input_cost_per_token == 1e-05
        assert catalog.get("gpt-4o") is not None  # 内置仍在

    def test_invalid_file_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError):
            PricingCatalog.load(extra_paths=[bad], include_user_override=False)

    def test_missing_file_skipped(self, tmp_path: Path):
        catalog = PricingCatalog.load(extra_paths=[tmp_path / "nonexistent.json"], include_user_override=False)
        assert catalog.get("gpt-4o") is not None


class TestConsumerIntegration:
    def test_cost_tracker_uses_catalog(self):
        tracker = CostTracker()
        rec = tracker.record("gpt-4o", input_tokens=1000, output_tokens=500, latency_ms=100)
        assert rec.cost_usd == pytest.approx(0.0075)

    def test_cost_tracker_unknown_model_uses_default(self):
        tracker = CostTracker()
        rec = tracker.record("unknown-model-xyz", input_tokens=1_000_000, output_tokens=0)
        assert rec.cost_usd == pytest.approx(3.0)  # default: 3e-06 * 1e6

    def test_token_analyzer_uses_catalog(self):
        result = estimate_tokens("a" * 1000, "gpt-4o")
        assert result.estimated_input_cost_usd > 0
        assert result.estimated_input_cost_usd < 0.01


class TestD4ExitCodeConsistency:
    """D4: verdict↔退出码语义一致性自检"""

    def test_determine_exit_code_mapping(self):
        from ai_prompt_toolkit.cli_helpers import determine_exit_code

        assert determine_exit_code(has_errors=True) == 3
        assert determine_exit_code(has_findings=True, error_severity="critical") == 2
        assert determine_exit_code(has_findings=True, error_severity="high") == 2
        assert determine_exit_code(has_findings=True, error_severity="medium") == 1
        assert determine_exit_code(has_findings=True, error_severity="low") == 0
        assert determine_exit_code(has_findings=False) == 0

    def test_verdict_to_exit_code_mapping(self):
        from ai_prompt_toolkit.linter.quality_gate import Verdict, verdict_to_exit_code

        assert verdict_to_exit_code(Verdict.PASS) == 0
        assert verdict_to_exit_code(Verdict.WARN) == 1
        assert verdict_to_exit_code(Verdict.FAIL) == 2

    def test_gate_evaluate_consistent_with_exit_codes(self):
        """门禁评估结果必须能直接映射到退出码, 无中间硬编码"""
        from ai_prompt_toolkit.linter.quality_gate import QualityGate, verdict_to_exit_code
        from ai_prompt_toolkit.types import Finding, Severity

        qg = QualityGate()
        clean = qg.evaluate([], score=95.0)
        assert verdict_to_exit_code(clean.verdict) == 0
        critical = qg.evaluate([Finding("P031", Severity.CRITICAL, "x", 1, 1)], score=95.0)
        assert verdict_to_exit_code(critical.verdict) == 2
        warn = qg.evaluate([Finding("P001", Severity.MEDIUM, "x", 1, 1)] * 5, score=95.0)
        assert verdict_to_exit_code(warn.verdict) == 1


class TestU1TraceExportCLI:
    """U1: lint --trace-json 落盘OTel trace"""

    def test_lint_trace_json(self, tmp_path: Path, monkeypatch):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        monkeypatch.setenv("PROMPT_TOOLKIT_TRACING", "memory")  # 启用内存后端(默认noop零开销)
        target = tmp_path / "p.md"
        target.write_text("You are a helpful assistant.", encoding="utf-8")
        trace_path = tmp_path / "trace.json"

        runner = CliRunner()
        result = runner.invoke(main, ["lint", "-t", str(target), "--trace-json", str(trace_path)])
        # lint可能因findings退出非0, 但trace必须落盘
        assert trace_path.exists(), f"trace未落盘: {result.output}"
        data = json.loads(trace_path.read_text(encoding="utf-8"))
        assert data["spans"], "spans为空"
        span = data["spans"][0]
        assert span["name"] == "prompt.lint"
        assert span["attributes"]["gen_ai.operation.name"] == "lint"
        assert "gen_ai.system" in span["attributes"]
        assert "otlp" in data

    def test_lint_no_trace_by_default(self, tmp_path: Path):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        target = tmp_path / "p.md"
        target.write_text("You are a helpful assistant.", encoding="utf-8")
        runner = CliRunner()
        runner.invoke(main, ["lint", "-t", str(target)])
        assert not (tmp_path / "trace.json").exists()


class TestU1SpanTreeAndTraceView:
    """U1完整版: span树构建 + prompt-cli trace --file 渲染"""

    def test_build_span_tree_nesting(self):
        from ai_prompt_toolkit.linter.otel_tracer import build_span_tree

        spans = [
            {"span_id": "root", "parent_span_id": "", "name": "root", "start_time": 1, "duration_ms": 10},
            {"span_id": "c1", "parent_span_id": "root", "name": "child1", "start_time": 2, "duration_ms": 5},
            {"span_id": "c2", "parent_span_id": "root", "name": "child2", "start_time": 3, "duration_ms": 3},
            {"span_id": "gc", "parent_span_id": "c1", "name": "grandchild", "start_time": 4, "duration_ms": 1},
        ]
        tree = build_span_tree(spans)
        assert len(tree) == 1
        root = tree[0]
        assert root["span"]["name"] == "root"
        assert [c["span"]["name"] for c in root["children"]] == ["child1", "child2"]
        assert root["children"][0]["children"][0]["span"]["name"] == "grandchild"

    def test_build_span_tree_orphan_to_root(self):
        from ai_prompt_toolkit.linter.otel_tracer import build_span_tree

        spans = [
            {"span_id": "a", "parent_span_id": "missing", "name": "orphan", "start_time": 2},
            {"span_id": "b", "parent_span_id": "", "name": "root", "start_time": 1},
        ]
        tree = build_span_tree(spans)
        assert [n["span"]["name"] for n in tree] == ["root", "orphan"]

    def test_trace_view_renders_file(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        monkeypatch.setenv("PROMPT_TOOLKIT_TRACING", "memory")
        target = tmp_path / "p.md"
        target.write_text("You are a helpful assistant.", encoding="utf-8")
        trace_path = tmp_path / "t.json"

        runner = CliRunner()
        runner.invoke(main, ["lint", "-t", str(target), "--trace-json", str(trace_path)])
        assert trace_path.exists()

        result = runner.invoke(main, ["trace", "-f", str(trace_path)])
        assert "prompt.lint" in result.output
        assert "Metrics" in result.output

    def test_trace_view_missing_file_exit3(self, tmp_path):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["trace", "-f", str(tmp_path / "nope.json")])
        assert result.exit_code == 3
        assert "不存在" in result.output
