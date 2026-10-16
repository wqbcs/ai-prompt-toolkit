"""自定义Lint规则YAML DSL加载器

用户可通过YAML文件定义自定义Lint规则，无需修改源码:

```yaml
rules:
  - id: CUSTOM001
    name: 禁止使用特定词汇
    category: custom
    severity: medium
    pattern: "禁止词汇|bad.word"
    message: "Prompt包含禁止词汇"
    remediation: "移除禁止词汇"
```

支持: 正则匹配、关键词匹配、长度检查、存在性检查
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_SEVERITY_MAP = {
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
    "info": Severity.LOW,
}


@dataclass
class CustomRuleDef:
    rule_id: str
    name: str
    category: str
    severity: Severity
    pattern: str = ""
    keywords: list[str] = field(default_factory=list)
    message: str = ""
    remediation: str = ""
    check_type: str = "regex"

    def __post_init__(self) -> None:
        if self.keywords is None:
            self.keywords = []


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        import json

        if path.suffix == ".json":
            rules: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return rules
        raise ImportError("自定义规则需要PyYAML: pip install pyyaml") from None


def load_custom_rules(rules_dir: str | Path) -> list[CustomRuleDef]:
    rules_dir = Path(rules_dir)
    if not rules_dir.exists():
        return []
    custom_rules = []
    for f in sorted(rules_dir.glob("*.yml")):
        data = _load_yaml(f)
        for r in data.get("rules", []):
            severity = _SEVERITY_MAP.get(r.get("severity", "medium"), Severity.MEDIUM)
            custom_rules.append(
                CustomRuleDef(
                    rule_id=r.get("id", "CUSTOM000"),
                    name=r.get("name", ""),
                    category=r.get("category", "custom"),
                    severity=severity,
                    pattern=r.get("pattern", ""),
                    keywords=r.get("keywords", []),
                    message=r.get("message", ""),
                    remediation=r.get("remediation", ""),
                    check_type=r.get("check_type", "regex"),
                )
            )
    for f in sorted(rules_dir.glob("*.yaml")):
        if f.suffix == ".G.yml":
            continue
        data = _load_yaml(f)
        for r in data.get("rules", []):
            severity = _SEVERITY_MAP.get(r.get("severity", "medium"), Severity.MEDIUM)
            custom_rules.append(
                CustomRuleDef(
                    rule_id=r.get("id", "CUSTOM000"),
                    name=r.get("name", ""),
                    category=r.get("category", "custom"),
                    severity=severity,
                    pattern=r.get("pattern", ""),
                    keywords=r.get("keywords", []),
                    message=r.get("message", ""),
                    remediation=r.get("remediation", ""),
                    check_type=r.get("check_type", "regex"),
                )
            )
    return custom_rules


def register_custom_rules(custom_rules: list[CustomRuleDef]) -> list[str]:
    registered = []
    for cr in custom_rules:
        rule = LintRule(
            cr.rule_id,
            cr.name,
            cr.category,
            cr.severity,
            cr.message,
            cr.remediation,
            family="custom",
        )
        _RULE_MAP[cr.rule_id] = rule
        registered.append(cr.rule_id)
    return registered


def check_custom_rule(text: str, rule_def: CustomRuleDef) -> Finding | None:
    if rule_def.check_type == "regex" and rule_def.pattern:
        if re.search(rule_def.pattern, text, re.IGNORECASE):
            return Finding(rule_def.rule_id, rule_def.severity, rule_def.message)
    elif rule_def.check_type == "keyword" and rule_def.keywords:
        for kw in rule_def.keywords:
            if kw.lower() in text.lower():
                return Finding(rule_def.rule_id, rule_def.severity, rule_def.message)
    elif rule_def.check_type == "not_contains" and rule_def.keywords:
        found = any(kw.lower() in text.lower() for kw in rule_def.keywords)
        if not found:
            return Finding(rule_def.rule_id, rule_def.severity, rule_def.message)
    elif rule_def.check_type == "min_length" and rule_def.pattern:
        min_len = int(rule_def.pattern) if rule_def.pattern.isdigit() else 0
        if len(text) < min_len:
            return Finding(rule_def.rule_id, rule_def.severity, rule_def.message)
    return None
