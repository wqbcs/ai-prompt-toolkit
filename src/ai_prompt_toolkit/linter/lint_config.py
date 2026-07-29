"""Lint配置文件支持 — YAML格式配置

功能:
- load_lint_config: 加载YAML配置文件
- LintConfig: 结构化配置数据
- 合并CLI选项与配置文件(配置文件为默认值, CLI覆盖)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LintConfig:
    severity_threshold: str = "low"
    exclude_categories: list[str] = field(default_factory=list)
    include_categories: list[str] = field(default_factory=list)
    exclude_rules: list[str] = field(default_factory=list)
    include_rules: list[str] = field(default_factory=list)
    max_findings: int = 0
    fail_on: str = "high"
    custom_rules_dir: str = ""
    parallel: bool = False
    timeout_ms: int = 30000
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity_threshold": self.severity_threshold,
            "exclude_categories": self.exclude_categories,
            "include_categories": self.include_categories,
            "exclude_rules": self.exclude_rules,
            "include_rules": self.include_rules,
            "max_findings": self.max_findings,
            "fail_on": self.fail_on,
            "custom_rules_dir": self.custom_rules_dir,
            "parallel": self.parallel,
            "timeout_ms": self.timeout_ms,
            "extra": self.extra,
        }


def load_lint_config(path: str | Path) -> LintConfig:
    p = Path(path)
    if not p.exists():
        return LintConfig()
    content = p.read_text(encoding="utf-8")
    if p.suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(content) or {}
    elif p.suffix == ".json":
        import json
        data = json.loads(content)
    else:
        import yaml
        data = yaml.safe_load(content) or {}
    return LintConfig(
        severity_threshold=data.get("severity_threshold", "low"),
        exclude_categories=data.get("exclude_categories", []),
        include_categories=data.get("include_categories", []),
        exclude_rules=data.get("exclude_rules", []),
        include_rules=data.get("include_rules", []),
        max_findings=int(data.get("max_findings", 0)),
        fail_on=data.get("fail_on", "high"),
        custom_rules_dir=data.get("custom_rules_dir", ""),
        parallel=bool(data.get("parallel", False)),
        timeout_ms=int(data.get("timeout_ms", 30000)),
        extra={k: v for k, v in data.items() if k not in {
            "severity_threshold", "exclude_categories", "include_categories",
            "exclude_rules", "include_rules", "max_findings", "fail_on",
            "custom_rules_dir", "parallel", "timeout_ms",
        }},
    )


def merge_config_with_cli(config: LintConfig, cli_overrides: dict[str, Any]) -> LintConfig:
    result = LintConfig(
        severity_threshold=cli_overrides.get("severity_threshold", config.severity_threshold),
        exclude_categories=cli_overrides.get("exclude_categories", config.exclude_categories),
        include_categories=cli_overrides.get("include_categories", config.include_categories),
        exclude_rules=cli_overrides.get("exclude_rules", config.exclude_rules),
        include_rules=cli_overrides.get("include_rules", config.include_rules),
        max_findings=cli_overrides.get("max_findings", config.max_findings),
        fail_on=cli_overrides.get("fail_on", config.fail_on),
        custom_rules_dir=cli_overrides.get("custom_rules_dir", config.custom_rules_dir),
        parallel=cli_overrides.get("parallel", config.parallel),
        timeout_ms=cli_overrides.get("timeout_ms", config.timeout_ms),
        extra=config.extra,
    )
    return result
