"""统一配置管理模块

配置层级优先级(高→低):
1. 环境变量(PROMPT_CLI_*)
2. 项目配置文件(.prompt-cli.toml / .prompt-cli.yaml)
3. 用户全局配置(~/.config/prompt-cli/config.toml)
4. 代码默认值

参考: pydantic-settings层级模式, dynaconf多源合并
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_DEFAULTS: dict[str, Any] = {
    "lint_on_save": True,
    "lint_on_type": False,
    "security_scan": True,
    "pii_detection": True,
    "zh_injection": True,
    "quality_gate_min_score": 60,
    "debounce_delay_ms": 300,
    "cost_limit_usd": 10.0,
    "max_retries": 3,
    "timeout_seconds": 30.0,
    "default_provider": "openai",
    "default_model": "gpt-4o-mini",
    "sarif_schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
    "template_dirs": [],
    "severity_overrides": {},
}

_ENV_PREFIX = "PROMPT_CLI_"

_PROJECT_CONFIG_NAMES = [".prompt-cli.toml", ".prompt-cli.yaml", ".prompt-cli.yml"]

_GLOBAL_CONFIG_DIR = Path.home() / ".config" / "prompt-cli"


@dataclass
class PromptCliConfig:
    lint_on_save: bool = True
    lint_on_type: bool = False
    security_scan: bool = True
    pii_detection: bool = True
    zh_injection: bool = True
    quality_gate_min_score: int = 60
    debounce_delay_ms: int = 300
    cost_limit_usd: float = 10.0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"
    sarif_schema: str = ""
    template_dirs: list[str] = field(default_factory=list)
    severity_overrides: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        import dataclasses
        return dataclasses.asdict(self)


def _find_project_config(start_dir: Path | None = None) -> Path | None:
    current = (start_dir or Path.cwd()).resolve()
    for _ in range(20):
        for name in _PROJECT_CONFIG_NAMES:
            candidate = current / name
            if candidate.exists():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomli as tomllib
            except ImportError:
                return {}
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("prompt-cli", data)
    except Exception:
        return {}


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_config_file(path: Path) -> dict[str, Any]:
    if path.suffix == ".toml":
        return _load_toml(path)
    elif path.suffix in (".yaml", ".yml"):
        return _load_yaml(path)
    return {}


def _load_env_overrides() -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, default in _DEFAULTS.items():
        env_key = _ENV_PREFIX + key.upper()
        env_val = os.environ.get(env_key)
        if env_val is not None:
            if isinstance(default, bool):
                overrides[key] = env_val.lower() in ("1", "true", "yes")
            elif isinstance(default, int):
                try:
                    overrides[key] = int(env_val)
                except ValueError:
                    pass
            elif isinstance(default, float):
                try:
                    overrides[key] = float(env_val)
                except ValueError:
                    pass
            elif isinstance(default, str):
                overrides[key] = env_val
    return overrides


def load_config(project_dir: Path | None = None) -> PromptCliConfig:
    merged: dict[str, Any] = dict(_DEFAULTS)

    global_config = _GLOBAL_CONFIG_DIR / "config.toml"
    if global_config.exists():
        file_data = _load_config_file(global_config)
        merged.update(file_data)

    project_config = _find_project_config(project_dir)
    if project_config:
        file_data = _load_config_file(project_config)
        merged.update(file_data)

    env_overrides = _load_env_overrides()
    merged.update(env_overrides)

    valid_keys = {f.name for f in PromptCliConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in merged.items() if k in valid_keys}

    return PromptCliConfig(**filtered)
