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
    "cache_enabled": True,
    "cache_ttl_seconds": 86400,
    "eval_config_path": "",
    "npu_enabled": False,
    "huawei_region": "cn-north-4",
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
    cache_enabled: bool = True
    cache_ttl_seconds: int = 86400
    eval_config_path: str = ""
    npu_enabled: bool = False
    huawei_region: str = "cn-north-4"

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
            data: dict[str, Any] = tomllib.load(f)
        tool_section = data.get("tool", {})
        result: dict[str, Any] = tool_section.get("prompt-cli", data)
        return result
    except Exception:
        return {}


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
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

    unknown_keys = set(merged.keys()) - valid_keys
    if unknown_keys and project_config:
        import sys as _sys

        print(f"警告: 配置文件 {project_config} 包含未知字段: {', '.join(sorted(unknown_keys))}", file=_sys.stderr)

    validation_errors = _validate_config_values(filtered)
    if validation_errors:
        import sys as _sys

        for err_msg in validation_errors:
            print(f"配置错误: {err_msg}", file=_sys.stderr)

    return PromptCliConfig(**filtered)


def _validate_config_values(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    qg_score = data.get("quality_gate_min_score")
    if qg_score is not None and (not isinstance(qg_score, (int, float)) or qg_score < 0 or qg_score > 100):
        errors.append(f"quality_gate_min_score 必须在 0-100 之间, 当前值: {qg_score}")

    debounce = data.get("debounce_delay_ms")
    if debounce is not None and (not isinstance(debounce, (int, float)) or debounce < 0):
        errors.append(f"debounce_delay_ms 必须 >= 0, 当前值: {debounce}")

    cost = data.get("cost_limit_usd")
    if cost is not None and (not isinstance(cost, (int, float)) or cost < 0):
        errors.append(f"cost_limit_usd 必须 >= 0, 当前值: {cost}")

    timeout = data.get("timeout_seconds")
    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        errors.append(f"timeout_seconds 必须 > 0, 当前值: {timeout}")

    retries = data.get("max_retries")
    if retries is not None and (not isinstance(retries, int) or retries < 0):
        errors.append(f"max_retries 必须 >= 0 整数, 当前值: {retries}")

    return errors


CONFIG_TEMPLATE_TOML = """\
# AI Prompt Toolkit 项目配置
# 参考: promptfoo promptfooconfig.yaml

[tool.prompt-cli]
# Lint配置
lint_on_save = true
lint_on_type = false
quality_gate_min_score = 90

# 安全配置
security_scan = true
pii_detection = true
zh_injection = true

# Provider配置
default_provider = "openai"
default_model = "gpt-4o-mini"

# 性能配置
cache_enabled = true
cache_ttl_seconds = 86400
max_retries = 3
timeout_seconds = 30.0
cost_limit_usd = 10.0

# 华为云配置
npu_enabled = false
huawei_region = "cn-north-4"

# 评估配置(声明式YAML评估配置文件路径)
# eval_config_path = "prompt-eval.yaml"

# 自定义模板目录
# template_dirs = ["./prompts"]

# 规则严重性覆盖
# [tool.prompt-cli.severity_overrides]
# P012 = "low"
# P048 = "info"
"""


def generate_config(output_path: str | Path | None = None, fmt: str = "toml") -> Path:
    if output_path is None:
        if fmt == "yaml":
            output_path = Path(".prompt-cli.yaml")
        else:
            output_path = Path(".prompt-cli.toml")
    output_path = Path(output_path)

    if fmt == "toml":
        output_path.write_text(CONFIG_TEMPLATE_TOML, encoding="utf-8")
    elif fmt == "yaml":
        import yaml

        config_data = {
            "lint_on_save": True,
            "lint_on_type": False,
            "quality_gate_min_score": 90,
            "security_scan": True,
            "pii_detection": True,
            "default_provider": "openai",
            "default_model": "gpt-4o-mini",
            "cache_enabled": True,
            "cache_ttl_seconds": 86400,
            "npu_enabled": False,
            "huawei_region": "cn-north-4",
        }
        output_path.write_text(yaml.dump(config_data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    return output_path


@dataclass
class ConfigWatchState:
    path: Path
    mtime: float
    content_hash: str


class ConfigWatcher:
    """配置文件热加载监视器 — MD5哈希轮询检测变化, 自动重载配置

    参考: watchdog库轮询模式 + dynaconf hot-reload
    - 支持项目配置(.prompt-cli.toml/yaml) + 全局配置(~/.config/prompt-cli/config.toml)
    - MD5哈希比较检测变化(比mtime更可靠)
    - 防抖机制避免频繁重载
    - 回调通知配置变更
    """

    def __init__(
        self,
        *,
        poll_interval: float = 2.0,
        debounce_seconds: float = 1.0,
        on_reload: Any | None = None,
    ) -> None:
        self._poll_interval = poll_interval
        self._debounce_seconds = debounce_seconds
        self._on_reload = on_reload
        self._watches: list[ConfigWatchState] = []
        self._last_reload_time: float = 0.0
        self._running = False
        self._current_config: PromptCliConfig | None = None

    def add_watch(self, path: Path) -> None:
        if not path.exists():
            return
        content_hash = self._compute_hash(path)
        mtime = path.stat().st_mtime
        self._watches.append(ConfigWatchState(path=path, mtime=mtime, content_hash=content_hash))

    def start(self, project_dir: Path | None = None) -> PromptCliConfig:
        self._current_config = load_config(project_dir)

        global_config = _GLOBAL_CONFIG_DIR / "config.toml"
        self.add_watch(global_config)

        project_config = _find_project_config(project_dir)
        if project_config:
            self.add_watch(project_config)

        self._running = True
        return self._current_config

    def stop(self) -> None:
        self._running = False

    @property
    def current_config(self) -> PromptCliConfig:
        if self._current_config is None:
            self._current_config = load_config()
        return self._current_config

    def check_and_reload(self) -> bool:
        import time

        if not self._watches:
            return False

        now = time.time()
        if now - self._last_reload_time < self._debounce_seconds:
            return False

        changed = False
        for ws in self._watches:
            if not ws.path.exists():
                continue
            new_hash = self._compute_hash(ws.path)
            if new_hash != ws.content_hash:
                ws.content_hash = new_hash
                ws.mtime = ws.path.stat().st_mtime
                changed = True

        if changed:
            self._current_config = load_config()
            self._last_reload_time = now
            if self._on_reload:
                self._on_reload(self._current_config)
            return True
        return False

    def poll_loop(self) -> None:
        import time

        while self._running:
            self.check_and_reload()
            time.sleep(self._poll_interval)

    @staticmethod
    def _compute_hash(path: Path) -> str:
        import hashlib

        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""


_watcher: ConfigWatcher | None = None


def get_watcher() -> ConfigWatcher:
    global _watcher
    if _watcher is None:
        _watcher = ConfigWatcher()
    return _watcher
