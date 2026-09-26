"""NIST AI Risk Management Framework (AI RMF 1.0) 映射

将Lint规则映射到NIST AI RMF的4大功能:
- GOVERN (G): AI风险治理
- MAP (M): AI风险识别与映射
- MEASURE (V): AI风险测量与分析
- MANAGE (T): AI风险管理决策

参考: https://www.nist.gov/artificial-intelligence/executive-order-safe-secure-and-trustworthy-artificial-intelligence
"""

from __future__ import annotations

from typing import Any

_NIST_RMF_MAPPING: dict[str, dict[str, list[str]]] = {
    "GOVERN": {
        "G1-01": ["P001", "P003", "P008"],
        "G1-02": ["P024", "P041", "P042"],
        "G1-03": ["P006", "P009", "P010"],
        "G2-01": ["P121", "P122", "P124"],
        "G2-02": ["P146", "P147", "P148"],
        "G3-01": ["P151", "P152", "P153"],
        "G3-02": ["P154", "P155", "P156"],
        "G4-01": ["P011", "P012", "P013"],
        "G4-02": ["P157", "P158", "P159"],
        "G6-01": ["P160", "P161", "P162"],
    },
    "MAP": {
        "M1-01": ["P006", "P007", "P010"],
        "M1-02": ["P031", "P032", "P033"],
        "M1-03": ["P166", "P167", "P168"],
        "M2-01": ["P004", "P005", "P037"],
        "M2-02": ["P038", "P039", "P040"],
        "M3-01": ["P043", "P044", "P045"],
        "M3-02": ["P169", "P170"],
        "M4-01": ["P131", "P132", "P133"],
        "M4-02": ["P134", "P135"],
    },
    "MEASURE": {
        "V1-01": ["P002", "P014", "P015"],
        "V1-02": ["P016", "P017", "P018"],
        "V2-01": ["P076", "P077", "P078"],
        "V2-02": ["P096", "P097", "P098"],
        "V3-01": ["P113", "P114", "P115"],
        "V3-02": ["P163", "P164", "P165"],
        "V4-01": ["P046", "P047", "P048"],
    },
    "MANAGE": {
        "T1-01": ["P007", "P008", "P031"],
        "T1-02": ["P032", "P033", "P034"],
        "T1-03": ["P161", "P162", "P163"],
        "T2-01": ["P039", "P040", "P077"],
        "T2-02": ["P164", "P165"],
        "T3-01": ["P009", "P024", "P041"],
        "T3-02": ["P166", "P167", "P168", "P169", "P170"],
        "T4-01": ["P149", "P150"],
        "T4-02": ["P146", "P147", "P148"],
    },
}


_EU_AI_ACT_MAPPING: dict[str, list[str]] = {
    "Article5-Prohibited": ["P161", "P163", "P169"],
    "Article9-Transparency": ["P001", "P002", "P003", "P011", "P012"],
    "Article10-DataQuality": ["P0E004", "P005", "P014", "P015", "P016"],
    "Article14-HumanOversight": ["P157", "P158", "P159"],
    "Article15-Accuracy": ["P002", "P014", "P016", "P017", "P018"],
    "Article15-Robustness": ["P006", "P007", "P031", "P032", "P033"],
    "Article52-Labeling": ["P001", "P008"],
}


def get_nist_rmf_mapping() -> dict[str, dict[str, list[str]]]:
    return _NIST_RMF_MAPPING


def get_eu_ai_act_mapping() -> dict[str, list[str]]:
    return _EU_AI_ACT_MAPPING


def get_rules_for_nist_subcategory(subcategory: str) -> list[str]:
    for _function, subcats in _NIST_RMF_MAPPING.items():
        if subcategory in subcats:
            return subcats[subcategory]
    return []


def get_nist_coverage_for_rules(rule_ids: list[str]) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for rule_id in rule_ids:
        matched = []
        for function, subcats in _NIST_RMF_MAPPING.items():
            for subcat, rules in subcats.items():
                if rule_id in rules:
                    matched.append(f"{function}/{subcat}")
        if matched:
            coverage[rule_id] = matched
    return coverage


def generate_nist_compliance_report(findings_rule_ids: list[str]) -> dict[str, Any]:
    covered_subcats: dict[str, list[str]] = {}
    for function, subcats in _NIST_RMF_MAPPING.items():
        for subcat, rules in subcats.items():
            triggered = [r for r in rules if r in findings_rule_ids]
            if triggered:
                covered_subcats[f"{function}/{subcat}"] = triggered
    function_coverage = {}
    for function in _NIST_RMF_MAPPING:
        total = len(_NIST_RMF_MAPPING[function])
        covered = len([s for s in covered_subcats if s.startswith(f"{function}/")])
        function_coverage[function] = {
            "total": total,
            "covered": covered,
            "pct": round(covered / max(total, 1) * 100, 1),
        }
    return {
        "framework": "NIST AI RMF 1.0",
        "triggered_subcategories": covered_subcats,
        "function_coverage": function_coverage,
        "total_subcategories_triggered": len(covered_subcats),
    }
