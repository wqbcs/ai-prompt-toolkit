"""R85: doctor --init + 首次引导提示"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main


def test_doctor_init_creates_config():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            assert result.exit_code == 0
            config_path = Path(tmpdir) / ".prompt-toolkit.yml"
            assert config_path.exists()
            content = config_path.read_text(encoding="utf-8")
            # R186: 配置生成对齐lint_config.LintConfig schema(可被lint自动发现链真实消费)
            assert "severity_threshold" in content
            assert "exclude_categories" in content
            assert "include_rules" in content
        finally:
            os.chdir(original_cwd)


def test_doctor_init_existing_config():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".prompt-toolkit.yml"
        config_path.write_text("existing: true", encoding="utf-8")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            assert result.exit_code == 0
            assert "已存在" in result.output
            content = config_path.read_text(encoding="utf-8")
            assert "existing: true" in content
        finally:
            os.chdir(original_cwd)


def test_config_has_harmonyos_section():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / ".prompt-toolkit.yml"
            content = config_path.read_text(encoding="utf-8")
            # R186: schema对齐lint_config, 断言真实可消费的键
            assert "exclude_rules" in content
            assert "include_categories" in content
        finally:
            os.chdir(original_cwd)


def test_config_has_output_scan_section():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / ".prompt-toolkit.yml"
            content = config_path.read_text(encoding="utf-8")
            assert "severity_threshold" in content  # R186: schema对齐
            assert "exclude_rules" in content  # R186: schema对齐
            assert "include_categories" in content  # R186: schema对齐
            assert "include_rules" in content  # R186: schema对齐
        finally:
            os.chdir(original_cwd)


def test_config_has_security_thresholds():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / ".prompt-toolkit.yml"
            content = config_path.read_text(encoding="utf-8")
            assert "severity_threshold" in content  # R186
            assert "exclude_categories" in content  # R186: schema对齐
        finally:
            os.chdir(original_cwd)


def test_doctor_no_config_shows_hint():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor"])
            assert "--init" in result.output
        finally:
            os.chdir(original_cwd)
