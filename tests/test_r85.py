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
            assert "lint:" in content
            assert "scan:" in content
            assert "evaluate:" in content
            assert "security:" in content
            assert "output_scan:" in content
            assert "harmonyos:" in content
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
            assert "stage_model: true" in content
            assert "min_api: 12" in content
            assert "target_api: 14" in content
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
            assert "enabled: true" in content
            assert "no_refusal" in content
            assert "bias" in content
            assert "toxicity" in content
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
            assert "block_threshold: 0.7" in content
            assert "warn_threshold: 0.35" in content
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
