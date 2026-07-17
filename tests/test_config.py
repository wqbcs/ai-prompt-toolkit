"""统一配置管理模块测试"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from ai_prompt_toolkit.config import (
    PromptCliConfig, load_config, _DEFAULTS, _ENV_PREFIX,
    _find_project_config, _load_env_overrides,
)


class TestPromptCliConfig:
    def test_default_values(self):
        cfg = PromptCliConfig()
        assert cfg.lint_on_save is True
        assert cfg.lint_on_type is False
        assert cfg.security_scan is True
        assert cfg.quality_gate_min_score == 60
        assert cfg.debounce_delay_ms == 300
        assert cfg.cost_limit_usd == 10.0
        assert cfg.default_provider == "openai"
        assert cfg.default_model == "gpt-4o-mini"

    def test_to_dict(self):
        cfg = PromptCliConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["lint_on_save"] is True
        assert d["quality_gate_min_score"] == 60


class TestLoadConfig:
    def test_load_config_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = load_config()
        assert cfg.lint_on_save is True
        assert cfg.lint_on_type is False

    def test_load_config_env_override(self):
        env = {
            f"{_ENV_PREFIX}LINT_ON_SAVE": "false",
            f"{_ENV_PREFIX}QUALITY_GATE_MIN_SCORE": "80",
            f"{_ENV_PREFIX}COST_LIMIT_USD": "5.0",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_config()
        assert cfg.lint_on_save is False
        assert cfg.quality_gate_min_score == 80
        assert cfg.cost_limit_usd == 5.0

    def test_load_config_env_bool_true(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}LINT_ON_TYPE": "true"}, clear=False):
            cfg = load_config()
        assert cfg.lint_on_type is True

    def test_load_config_env_bool_invalid(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}LINT_ON_TYPE": "invalid"}, clear=False):
            cfg = load_config()
        assert cfg.lint_on_type is False


class TestEnvOverrides:
    def test_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            overrides = _load_env_overrides()
        assert overrides == {}

    def test_bool_override(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}SECURITY_SCAN": "0"}, clear=True):
            overrides = _load_env_overrides()
        assert overrides.get("security_scan") is False

    def test_int_override(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}MAX_RETRIES": "5"}, clear=True):
            overrides = _load_env_overrides()
        assert overrides.get("max_retries") == 5

    def test_float_override(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}TIMEOUT_SECONDS": "60.0"}, clear=True):
            overrides = _load_env_overrides()
        assert overrides.get("timeout_seconds") == 60.0

    def test_invalid_int(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}MAX_RETRIES": "abc"}, clear=True):
            overrides = _load_env_overrides()
        assert "max_retries" not in overrides

    def test_invalid_float(self):
        with patch.dict(os.environ, {f"{_ENV_PREFIX}COST_LIMIT_USD": "xyz"}, clear=True):
            overrides = _load_env_overrides()
        assert "cost_limit_usd" not in overrides


class TestFindProjectConfig:
    def test_no_config_file(self, tmp_path):
        result = _find_project_config(tmp_path)
        assert result is None

    def test_find_toml(self, tmp_path):
        config_file = tmp_path / ".prompt-cli.toml"
        config_file.write_text('[tool.prompt-cli]\nlint_on_save = false\n', encoding="utf-8")
        result = _find_project_config(tmp_path)
        assert result is not None
        assert result.name == ".prompt-cli.toml"

    def test_find_yaml(self, tmp_path):
        config_file = tmp_path / ".prompt-cli.yaml"
        config_file.write_text('lint_on_save: false\n', encoding="utf-8")
        result = _find_project_config(tmp_path)
        assert result is not None
        assert result.name == ".prompt-cli.yaml"


class TestDefaults:
    def test_all_defaults_have_matching_fields(self):
        cfg = PromptCliConfig()
        for key in _DEFAULTS:
            assert hasattr(cfg, key), f"Missing field: {key}"

    def test_env_prefix_format(self):
        assert _ENV_PREFIX == "PROMPT_CLI_"
        assert _ENV_PREFIX.endswith("_")
