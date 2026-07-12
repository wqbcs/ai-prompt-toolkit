"""RuleLoader — 规则加载器，参考Checkov Registry模式

支持recommended/strict/huawei-cloud三种内置规则集
支持custom_rules_dir加载自定义规则
"""
from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

from ai_prompt_toolkit.linter.rules import LintRule, get_all_rules, _ALL_RULES, _RULE_MAP

logger = logging.getLogger(__name__)

RULESETS: dict[str, list[str]] = {
    "recommended": [
        "P001", "P002", "P003", "P004", "P005",
        "P006", "P007", "P010",
        "P011", "P012", "P016", "P017", "P018", "P020",
    ],
    "strict": [
        "P001", "P002", "P003", "P004", "P005",
        "P006", "P007", "P008", "P009", "P010",
        "P011", "P012", "P013", "P014", "P015",
        "P016", "P017", "P018", "P019", "P020",
    ],
    "huawei-cloud": [
        "P001", "P002", "P003", "P004",
        "P006", "P007", "P008", "P010",
        "P012", "P016", "P017", "P018", "P020",
    ],
}


class RuleLoader:
    def __init__(self) -> None:
        self._custom_rules: list[LintRule] = []

    def load(self, ruleset: str = "recommended",
             custom_rules_dir: str | Path | None = None,
             include: list[str] | None = None,
             exclude: list[str] | None = None) -> list[LintRule]:
        base_ids = set(RULESETS.get(ruleset, RULESETS["recommended"]))
        rules: dict[str, LintRule] = {}
        for rule in get_all_rules():
            if rule.rule_id in base_ids:
                rules[rule.rule_id] = rule
        if custom_rules_dir:
            custom = self._load_custom_rules(custom_rules_dir)
            for rule in custom:
                if rule.rule_id in rules:
                    existing = rules[rule.rule_id]
                    if rule.severity.value > existing.severity.value:
                        rules[rule.rule_id] = rule
                        logger.info("规则冲突 %s: 使用更严格级别 %s → %s",
                                    rule.rule_id, existing.severity.value, rule.severity.value)
                else:
                    rules[rule.rule_id] = rule
        if include:
            rules = {k: v for k, v in rules.items() if k in set(include)}
        if exclude:
            exclude_set = set(exclude)
            rules = {k: v for k, v in rules.items() if k not in exclude_set}
        self._custom_rules = list(rules.values())
        return list(rules.values())

    def _load_custom_rules(self, custom_dir: str | Path) -> list[LintRule]:
        p = Path(custom_dir)
        if not p.exists():
            logger.warning("自定义规则目录不存在: %s", p)
            return []
        loaded: list[LintRule] = []
        for py_file in p.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                module_name = f"_custom_rules_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    if hasattr(module, "RULES"):
                        for rule_data in module.RULES:
                            if isinstance(rule_data, LintRule):
                                loaded.append(rule_data)
            except Exception as e:
                logger.warning("加载自定义规则失败 %s: %s — 跳过", py_file.name, e)
        if loaded:
            logger.info("加载 %d 条自定义规则", len(loaded))
        return loaded

    def available_rulesets(self) -> list[str]:
        return list(RULESETS.keys())
