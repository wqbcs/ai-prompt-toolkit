"""R185测试: 命令层冒烟第二批 — ab-test/canary/engine/eval-matrix/registry"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


@pytest.fixture()
def prompt_file(tmp_path: Path):
    p = tmp_path / "prompt.md"
    p.write_text(
        "version: 1.0.0\n# 角色\n你是安全合规助手。\n# 任务\n回答用户问题。\n"
        "# 输出格式\nJSON。\n# 约束\n不编造信息。\n",
        encoding="utf-8",
    )
    return p


class TestAbTestCommand:
    def test_abtest_with_config(self, runner, tmp_path):
        config = tmp_path / "ab.yaml"
        config.write_text(
            "models:\n  - openai:gpt-x\nprompt_templates:\n  - \"回答: {input}\"\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["ab-test", "-c", str(config), "-m", "openai:gpt-x"])
        # 无API key场景: 引擎报错/空结果均可, 但不得崩溃(exit 2=空模型)
        assert result.exit_code in (0, 1, 2)

    def test_abtest_empty_models(self, runner, tmp_path):
        config = tmp_path / "empty.yaml"
        config.write_text("models: []\n", encoding="utf-8")
        result = runner.invoke(main, ["ab-test", "-c", str(config)])
        assert result.exit_code == 2  # 空模型→empty_state_tip


class TestSecurityCommands:
    def test_canary_generate(self, runner, prompt_file, tmp_path):
        result = runner.invoke(
            main, ["canary", "-p", str(prompt_file), "--count", "2", "-o", str(tmp_path / "canary.json")]
        )
        assert result.exit_code in (0, 1)

    def test_engine_detection(self, runner, prompt_file):
        result = runner.invoke(main, ["engine", "-t", str(prompt_file)])
        assert result.exit_code in (0, 1)

    def test_engine_json(self, runner, prompt_file):
        result = runner.invoke(main, ["engine", "-t", str(prompt_file), "--format", "json"])
        assert result.exit_code in (0, 1)


class TestEvalSubcommands:
    def test_eval_matrix(self, runner, prompt_file, tmp_path):
        result = runner.invoke(main, ["eval-matrix", "-t", str(prompt_file)])
        assert result.exit_code in (0, 1, 2)

    def test_eval_registry_list(self, runner):
        if "eval-registry" not in main.commands:
            pytest.skip("eval-registry未注册")
        result = runner.invoke(main, ["eval-registry", "--help"])
        assert result.exit_code == 0

    def test_eval_config(self, runner):
        result = runner.invoke(main, ["eval-config", "--help"])
        assert result.exit_code == 0
