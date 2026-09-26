"""promptkit.toml配置文件支持

参考:
- pyproject.toml (PEP 518)
- Ruff ruff.toml
- promptfoo promptfooconfig.yaml

支持的配置项:
- [lint] rules/exclude/threshold/fix
- [cache] maxsize/ttl/enabled
- [output] format/color
- [lts] group_id/stream_id/endpoint/enabled
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LintConfig:
    rules: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    threshold: float = 0.0
    fix: bool = False


@dataclass
class CacheConfig:
    maxsize: int = 1024
    ttl: int = 1800
    enabled: bool = True


@dataclass
class OutputConfig:
    format: str = "cli"
    color: bool = True


@dataclass
class LTSConfig:
    group_id: str = ""
    stream_id: str = ""
    endpoint: str = ""
    enabled: bool = False


@dataclass
class PromptKitConfig:
    lint: LintConfig = field(default_factory=LintConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    lts: LTSConfig = field(default_factory=LTSConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lint": {
                "rules": self.lint.rules,
                "exclude": self.lint.exclude,
                "threshold": self.lint.threshold,
                "fix": self.lint.fix,
            },
            "cache": {
                "maxsize": self.cache.maxsize,
                "ttl": self.cache.ttl,
                "enabled": self.cache.enabled,
            },
            "output": {
                "format": self.output.format,
                "color": self.output.color,
            },
            "lts": {
                "group_id": self.lts.group_id,
                "stream_id": self.lts.stream_id,
                "endpoint": self.lts.endpoint,
                "enabled": self.lts.enabled,
            },
        }


def _parse_toml_value(value: str) -> Any:
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def _parse_toml_simple(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_section = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            if current_section not in result:
                result[current_section] = {}
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            parsed = _parse_toml_value(val)
            if current_section:
                result[current_section][key] = parsed
            else:
                result[key] = parsed
    return result


def _dict_to_config(data: dict[str, Any]) -> PromptKitConfig:
    lint_data = data.get("lint", {})
    cache_data = data.get("cache", {})
    output_data = data.get("output", {})
    lts_data = data.get("lts", {})

    lint = LintConfig(
        rules=lint_data.get("rules", [])
        if isinstance(lint_data.get("rules"), list)
        else str(lint_data.get("rules", "")).split(","),
        exclude=lint_data.get("exclude", [])
        if isinstance(lint_data.get("exclude"), list)
        else str(lint_data.get("exclude", "")).split(","),
        threshold=float(lint_data.get("threshold", 0)),
        fix=bool(lint_data.get("fix", False)),
    )
    cache = CacheConfig(
        maxsize=int(cache_data.get("maxsize", 1024)),
        ttl=int(cache_data.get("ttl", 1800)),
        enabled=bool(cache_data.get("enabled", True)),
    )
    output = OutputConfig(
        format=str(output_data.get("format", "cli")),
        color=bool(output_data.get("color", True)),
    )
    lts = LTSConfig(
        group_id=str(lts_data.get("group_id", "")),
        stream_id=str(lts_data.get("stream_id", "")),
        endpoint=str(lts_data.get("endpoint", "")),
        enabled=bool(lts_data.get("enabled", False)),
    )
    return PromptKitConfig(lint=lint, cache=cache, output=output, lts=lts)


def load_promptkit_config(path: str | Path | None = None) -> PromptKitConfig:
    if path is None:
        candidates = [
            Path("promptkit.toml"),
            Path(".promptkit.toml"),
            Path("pyproject.toml"),
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        else:
            return PromptKitConfig()
    path = Path(path)
    if not path.exists():
        return PromptKitConfig()

    text = path.read_text(encoding="utf-8")

    if path.name == "pyproject.toml":
        try:
            import tomllib

            data = tomllib.loads(text)
            tool_data = data.get("tool", {}).get("promptkit", {})
            return _dict_to_config(tool_data)
        except ImportError:
            pass

    parsed = _parse_toml_simple(text)

    if path.name == "pyproject.toml":
        tool_data = parsed.get("tool", {})
        if isinstance(tool_data, dict):
            return _dict_to_config(tool_data.get("promptkit", {}))
        return PromptKitConfig()

    return _dict_to_config(parsed)


def generate_example_config() -> str:
    return """\
# AI Prompt Toolkit 配置文件
# 放置于项目根目录: promptkit.toml

[lint]
rules = []
exclude = ["P005", "P019"]
threshold = 60.0
fix = false

[cache]
maxsize = 1024
ttl = 1800
enabled = true

[output]
format = "cli"
color = true

[lts]
group_id = ""
stream_id = ""
endpoint = ""
enabled = false
"""
