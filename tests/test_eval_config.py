"""eval_config模块测试 — YAML声明式评估配置"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from ai_prompt_toolkit.eval_config import (
    EvalConfig, EvalTarget, EvaluatorDef, AssertionDef,
    ProviderDef, OutputDef,
    run_assertion, run_eval_config,
)


class TestEvalConfigParsing:
    def test_from_dict_minimal(self):
        data = {"targets": [{"path": "test.md"}]}
        config = EvalConfig.from_dict(data)
        assert len(config.targets) == 1
        assert config.targets[0].path == "test.md"

    def test_from_dict_full(self):
        data = {
            "targets": [
                {"path": "a.md", "provider": "pangu", "model": "pangu-nlp"},
                {"path": "b.md", "provider": "openai", "model": "gpt-4o"},
            ],
            "evaluators": [
                {"type": "lint", "threshold": 90},
                {"type": "assertion", "assertions": [
                    {"name": "test", "contains": ["hello"], "regex": "world"},
                ]},
            ],
            "providers": {
                "openai": {"api_key_env": "OPENAI_KEY", "base_url": "https://api.openai.com/v1"},
            },
            "output": {"format": "json", "path": "results.json", "save_history": True},
        }
        config = EvalConfig.from_dict(data)
        assert len(config.targets) == 2
        assert config.targets[0].provider == "pangu"
        assert len(config.evaluators) == 2
        assert config.evaluators[0].threshold == 90
        assert len(config.evaluators[1].assertions) == 1
        assert config.evaluators[1].assertions[0].regex == "world"
        assert "openai" in config.providers
        assert config.output.save_history is True

    def test_from_yaml_file(self):
        yaml_content = """
targets:
  - path: templates/test.md
evaluators:
  - type: lint
    threshold: 85
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write(yaml_content)
            f.flush()
            config = EvalConfig.from_yaml(f.name)
            assert len(config.targets) == 1
            assert config.evaluators[0].threshold == 85

    def test_from_yaml_not_found(self):
        with pytest.raises(FileNotFoundError):
            EvalConfig.from_yaml("/nonexistent/path.yaml")

    def test_target_string_shorthand(self):
        data = {"targets": ["simple.md"]}
        config = EvalConfig.from_dict(data)
        assert config.targets[0].path == "simple.md"
        assert config.targets[0].provider == "openai"


class TestAssertionExecution:
    def test_contains_pass(self):
        result = run_assertion("hello world", AssertionDef(name="test", contains=["hello"]))
        assert result["passed"] is True

    def test_contains_fail(self):
        result = run_assertion("hello world", AssertionDef(name="test", contains=["missing"]))
        assert result["passed"] is False
        assert "缺少关键词" in result["details"][0]

    def test_contains_any_pass(self):
        result = run_assertion("hello", AssertionDef(name="test", contains_any=["hello", "world"]))
        assert result["passed"] is True

    def test_contains_any_fail(self):
        result = run_assertion("foo", AssertionDef(name="test", contains_any=["hello", "world"]))
        assert result["passed"] is False

    def test_regex_pass(self):
        result = run_assertion("输出格式如下", AssertionDef(name="test", regex="输出格式|格式如下"))
        assert result["passed"] is True

    def test_regex_fail(self):
        result = run_assertion("no match here", AssertionDef(name="test", regex="输出格式"))
        assert result["passed"] is False

    def test_not_contains_pass(self):
        result = run_assertion("safe text", AssertionDef(name="test", not_contains=["danger"]))
        assert result["passed"] is True

    def test_not_contains_fail(self):
        result = run_assertion("danger text", AssertionDef(name="test", not_contains=["danger"]))
        assert result["passed"] is False

    def test_icontains_pass(self):
        result = run_assertion("Hello World", AssertionDef(name="test", icontains=["hello"]))
        assert result["passed"] is True

    def test_icontains_fail(self):
        result = run_assertion("Goodbye", AssertionDef(name="test", icontains=["hello"]))
        assert result["passed"] is False

    def test_multiple_conditions(self):
        result = run_assertion(
            "hello world",
            AssertionDef(name="multi", contains=["hello"], not_contains=["danger"])
        )
        assert result["passed"] is True


class TestRunEvalConfig:
    def test_run_with_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = EvalConfig(
                targets=[EvalTarget(path="nonexistent.md")],
                evaluators=[EvaluatorDef(type="lint", threshold=90)],
            )
            results = run_eval_config(config, base_dir=tmpdir)
            assert results["summary"]["total"] == 1
            assert "error" in results["targets"][0]

    def test_run_with_real_template(self):
        template_dir = Path(__file__).parent.parent / "src" / "ai_prompt_toolkit" / "templates"
        cs_path = template_dir / "customer-service.md"
        if not cs_path.exists():
            pytest.skip("模板文件不存在")

        config = EvalConfig(
            targets=[EvalTarget(path=str(cs_path))],
            evaluators=[EvaluatorDef(type="lint", threshold=80)],
        )
        results = run_eval_config(config, base_dir=Path.cwd())
        assert results["summary"]["total"] == 1
        assert len(results["targets"][0]["evaluators"]) >= 1

    def test_run_assertion_evaluator(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 角色\n你是一个专业助手\n# 约束\n不得编造信息\n# 输出格式\n回复控制在500字以内")
            f.flush()

            config = EvalConfig(
                targets=[EvalTarget(path=f.name)],
                evaluators=[EvaluatorDef(
                    type="assertion",
                    assertions=[
                        AssertionDef(name="角色定义", contains=["你是"]),
                        AssertionDef(name="约束检查", contains_any=["约束", "限制", "不得"]),
                        AssertionDef(name="格式检查", regex="输出格式|格式如下"),
                    ],
                )],
            )
            results = run_eval_config(config)
            assert results["summary"]["total"] == 1
            assert results["targets"][0]["passed"] is True


class TestEvalConfigDataclasses:
    def test_eval_target_defaults(self):
        t = EvalTarget(path="test.md")
        assert t.provider == "openai"
        assert t.model == "gpt-4o-mini"

    def test_evaluator_def_defaults(self):
        e = EvaluatorDef(type="lint")
        assert e.threshold == 0.0
        assert e.assertions == []

    def test_provider_def_defaults(self):
        p = ProviderDef()
        assert p.max_retries == 3
        assert p.timeout == 30.0

    def test_output_def_defaults(self):
        o = OutputDef()
        assert o.format == "json"
        assert o.save_history is False
