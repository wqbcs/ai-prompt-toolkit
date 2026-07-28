"""OWASP LLM Top 10 2025 映射 — P001-P150 Lint规则到OWASP风险项对照表

映射原则:
- security类规则 → LLM01/LLM05/LLM06/LLM07/LLM08
- structure/quality类规则 → LLM06(Excessive Agency)/LLM09(Misinformation)
- compliance类规则 → LLM02/LLM03/LLM07
- performance类规则 → LLM10(Unbounded Consumption)
- agent类规则 → LLM06(Excessive Agency)
- rag类规则 → LLM08/LLM09
- harmonyos类规则 → LLM06(特定平台安全)
- multimodal类规则 → LLM01/LLM08

参考: https://owasp.org/www-project-top-10-for-large-language-model-applications/
"""
from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.linter.rules import _RULE_MAP

_OWASP_RULE_MAPPING: dict[str, list[str]] = {
    "LLM01": [
        "P006", "P007", "P010", "P031", "P032", "P033", "P034", "P038",
        "P039", "P040", "P076", "P077", "P078", "P096", "P097", "P113",
        "P131", "P132", "P133", "P134", "P135", "P161", "P163", "P166", "P167",
        "P176", "P177", "P178", "P179", "P180",
        "P181", "P182", "P183", "P184", "P185",
        "P186", "P187", "P188", "P189", "P190",
        "P191", "P192", "P193", "P194", "P195",
        "P196", "P197", "P200",
        "P201", "P202", "P205",
        "P206", "P209", "P210",
        "P211", "P212", "P213", "P214", "P215",
        "P216", "P217", "P219",
    ],
    "LLM02": [
        "P006", "P009", "P024", "P041", "P042", "P043", "P044", "P045",
        "P046", "P081", "P082", "P083", "P114", "P115", "P168", "P169",
        "P180",
        "P193", "P195",
        "P218", "P220",
    ],
    "LLM03": [
        "P024", "P047", "P048", "P049", "P098", "P099", "P100",
    ],
    "LLM04": [
        "P029", "P035", "P036", "P037", "P096", "P097", "P098", "P099",
    ],
    "LLM05": [
        "P007", "P008", "P031", "P032", "P033", "P034", "P052", "P053",
        "P076", "P077", "P078", "P099", "P151", "P161", "P164",
    ],
    "LLM06": [
        "P008", "P030", "P041", "P042", "P043", "P044", "P045", "P046",
        "P050", "P054", "P055", "P121", "P122", "P123", "P124", "P125",
        "P126", "P127", "P128", "P129", "P130",
        "P141", "P142", "P143", "P144", "P145",
        "P146", "P147", "P148", "P156", "P157", "P159",
        "P171", "P172", "P173", "P174", "P175",
        "P178", "P179",
        "P187", "P188", "P190",
        "P191", "P192", "P194",
        "P198", "P199", "P200",
        "P203", "P204",
    ],
    "LLM07": [
        "P006", "P009", "P024", "P041", "P042", "P043", "P084", "P085",
        "P116", "P117", "P152", "P158", "P162", "P165",
        "P203", "P204",
    ],
    "LLM08": [
        "P035", "P036", "P037", "P039", "P040", "P096", "P097", "P098",
        "P136", "P137", "P138", "P159",
    ],
    "LLM09": [
        "P015", "P016", "P017", "P018", "P019", "P020", "P025", "P026",
        "P027", "P028", "P056", "P057", "P058", "P059", "P060", "P061",
        "P062", "P101", "P102", "P103", "P104", "P105", "P119", "P120", "P167", "P170",
        "P181", "P182", "P184",
        "P186", "P189",
        "P196", "P197",
        "P207", "P208",
    ],
    "LLM10": [
        "P004", "P011", "P012", "P013", "P014", "P023", "P144", "P149",
        "P153", "P155", "P160",
        "P196", "P197",
    ],
}


def apply_owasp_refs() -> None:
    for owasp_ref, rule_ids in _OWASP_RULE_MAPPING.items():
        for rid in rule_ids:
            rule = _RULE_MAP.get(rid)
            if rule is not None:
                if owasp_ref not in rule.owasp_refs:
                    rule.owasp_refs.append(owasp_ref)


def get_rules_by_owasp(owasp_ref: str) -> list[str]:
    return _OWASP_RULE_MAPPING.get(owasp_ref, [])


def get_owasp_coverage() -> dict[str, dict[str, Any]]:
    from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2025
    result = {}
    for ref, info in OWASP_LLM_TOP_10_2025.items():
        rule_ids = _OWASP_RULE_MAPPING.get(ref, [])
        result[ref] = {
            "name": info["name"],
            "lint_rules": rule_ids,
            "probes": info["probes"],
            "lint_coverage": len(rule_ids),
        }
    return result
