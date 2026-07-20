"""Lint规则热加载 — 从YAML文件加载自定义Lint规则

参考:
- garak (YAML-based probe/detector configuration)
- prompt-armor (YAML rules configuration)
- ruff (pyproject.toml rule configuration)

支持:
- 自定义规则YAML文件
- 运行时加载/重载
- 规则开关(enable/disable)
- 自定义严重级别和描述
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ai_prompt_toolkit.types import Finding, Severity


_SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


def _compile_pattern(pattern_str: str, flags: list[str] | None = None) -> re.Pattern[str]:
    flag_val = 0
    if flags:
        for f in flags:
            if f == "ignorecase":
                flag_val |= re.IGNORECASE
            elif f == "multiline":
                flag_val |= re.MULTILINE
            elif f == "dotall":
                flag_val |= re.DOTALL
    return re.compile(pattern_str, flag_val)


def load_rules_from_yaml(yaml_path: str | Path) -> list[dict[str, Any]]:
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"规则YAML文件不存在: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "rules" not in data:
        return []

    loaded: list[dict[str, Any]] = []
    for rule_data in data["rules"]:
        if not rule_data.get("enabled", True):
            continue

        rule_id = rule_data.get("id", "CUSTOM-000")
        name = rule_data.get("name", "自定义规则")
        category = rule_data.get("category", "custom")
        severity_str = rule_data.get("severity", "medium")
        severity = _SEVERITY_MAP.get(severity_str, Severity.MEDIUM)
        description = rule_data.get("description", "")
        remediation = rule_data.get("remediation", "")
        pattern_str = rule_data.get("pattern", "")
        flags = rule_data.get("flags", [])

        if not pattern_str:
            continue

        try:
            compiled = _compile_pattern(pattern_str, flags)
        except re.error as e:
            continue

        loaded.append({
            "rule_id": rule_id,
            "name": name,
            "category": category,
            "severity": severity,
            "description": description,
            "remediation": remediation,
            "pattern": compiled,
        })

    return loaded


def check_custom_rules(text: str, rules: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        matches = rule["pattern"].findall(text)
        if matches:
            findings.append(Finding(
                rule_id=rule["rule_id"],
                severity=rule["severity"],
                description=f"{rule['description']} (匹配 {len(matches)} 处)",
                remediation=rule["remediation"],
                details={"matches": len(matches), "category": rule["category"]},
            ))
    return findings


def generate_sample_yaml(output_path: str | Path) -> None:
    sample = {
        "rules": [
            {
                "id": "CUSTOM-001",
                "name": "公司敏感词检测",
                "category": "compliance",
                "severity": "high",
                "description": "检测Prompt中是否包含公司内部代号",
                "remediation": "移除内部代号或使用通用描述替代",
                "pattern": r"(?:项目代号|内部代号)\s*[:：]\s*\w+",
                "flags": ["ignorecase"],
                "enabled": True,
            },
            {
                "id": "CUSTOM-002",
                "name": "禁止URL检测",
                "category": "security",
                "severity": "medium",
                "description": "检测Prompt中是否包含外部URL",
                "remediation": "移除外部URL或使用占位符",
                "pattern": r"https?://[^\s]+",
                "flags": [],
                "enabled": True,
            },
        ]
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(sample, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
