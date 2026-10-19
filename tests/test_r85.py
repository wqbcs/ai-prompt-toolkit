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
            config_path = Path(tmpdir) / "promptlint.toml"
            assert config_path.exists()
            content = config_path.read_text(encoding="utf-8")
            # R325: doctor --init 现与 init 共用单一真源 promptlint.toml(P2-03 schema)
            assert "fail_on" in content
            assert "include_rules" in content
        finally:
            os.chdir(original_cwd)


def test_doctor_init_existing_config():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "promptlint.toml"
        config_path.write_text('fail_on = "medium"\n# user edit\n', encoding="utf-8")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            assert result.exit_code == 0
            assert "已存在" in result.output
            content = config_path.read_text(encoding="utf-8")
            assert "user edit" in content
        finally:
            os.chdir(original_cwd)


def test_config_has_harmonyos_section():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / "promptlint.toml"
            content = config_path.read_text(encoding="utf-8")
            # R325: P2-03 schema — 断言门禁级 + 全局豁免面存在
            assert "fail_on" in content
            assert "waivers" in content
        finally:
            os.chdir(original_cwd)


def test_config_has_output_scan_section():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / "promptlint.toml"
            content = config_path.read_text(encoding="utf-8")
            assert "fail_on" in content  # R325: 单一真源 schema
            assert "exclude_rules" in content  # R325: 单一真源 schema
            assert "severity_overrides" in content  # R325: 单一真源 schema
            assert "include_rules" in content  # R325: 单一真源 schema
        finally:
            os.chdir(original_cwd)


def test_config_has_security_thresholds():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(main, ["doctor", "--init"])
            config_path = Path(tmpdir) / "promptlint.toml"
            content = config_path.read_text(encoding="utf-8")
            assert "fail_on" in content  # R325: 单一真源门禁级
            assert "gap" in content  # R325: 单一真源 gap 门禁
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
