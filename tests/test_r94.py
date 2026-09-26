"""R94: eval --preset + table/yaml格式 + doctor --init weight_preset"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ai_prompt_toolkit.evaluator import get_weight_preset


class TestR94EvalPresetAndFormat:
    def test_eval_preset_security_heavy(self):
        preset = get_weight_preset("security-heavy")
        assert preset is not None
        assert preset.name == "security-heavy"
        assert preset._overrides is not None

    def test_eval_preset_harmonyos_strict(self):
        preset = get_weight_preset("harmonyos-strict")
        assert preset is not None
        assert preset.name == "harmonyos-strict"

    def test_eval_preset_all_exist(self):
        for name in (
            "default",
            "security-heavy",
            "quality-balanced",
            "performance-first",
            "harmonyos-strict",
            "redteam-ready",
            "cost-efficient",
        ):
            p = get_weight_preset(name)
            assert p is not None, f"preset {name} not found"

    def test_doctor_init_includes_weight_preset(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            os.chdir(td)
            try:
                result = runner.invoke(main, ["doctor", "--init"])
                config_path = Path(td) / ".prompt-toolkit.yml"
                assert config_path.exists()
                content = config_path.read_text(encoding="utf-8")
                assert "weight_preset" in content
            finally:
                os.chdir(old_cwd)

    def test_eval_cli_preset_option(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手，请回答用户的问题。", encoding="utf-8")
            result = runner.invoke(main, ["evaluate", "-t", str(fp), "--preset", "security-heavy", "--format", "json"])
            assert result.exit_code in (0, 1), f"exit_code={result.exit_code}, output={result.output}"

    def test_eval_table_format(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手。", encoding="utf-8")
            result = runner.invoke(main, ["evaluate", "-t", str(fp), "--format", "table"])
            assert result.exit_code in (0, 1)

    def test_eval_yaml_format(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.md"
            fp.write_text("你是一个AI助手。", encoding="utf-8")
            result = runner.invoke(main, ["evaluate", "-t", str(fp), "--format", "yaml"])
            assert result.exit_code in (0, 1)
