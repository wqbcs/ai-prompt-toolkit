"""OWASP LLM Top 10 2026 映射 — Lint规则到OWASP风险项对照表

R228-P2-21: 2025→2026 标准迁移（OWASP 2026 版 2026-08-03 发布，10 项里 8 项换位、
LLM07 System Prompt Leakage → LLM08 Hidden Context Exposure 改名）。
重键表与 2026 风险定义在 probe_framework（单一真源）:
  OWASP_LLM_TOP_10_2026 / OWASP_2025_TO_2026 / normalize_owasp_refs
本表 _OWASP_RULE_MAPPING 已按 2026 键重键；规则文件里的硬编码 2025 号在
apply_owasp_refs 边界统一 normalize 到 2026（避免逐文件改 ~90 处字面量）。

映射原则（2026 键）:
- security类规则 → LLM01/LLM10/LLM03/LLM08/LLM09
- structure/quality类规则 → LLM03(Excessive Agency)/LLM07(Misinformation)
- compliance类规则 → LLM02/LLM04/LLM08
- performance类规则 → LLM06(Unbounded Consumption)
- agent类规则 → LLM03(Excessive Agency)
- rag类规则 → LLM09/LLM07
- harmonyos类规则 → LLM03(特定平台安全)
- multimodal类规则 → LLM01/LLM09

参考: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
（2025→2026 重键: LLM03→04, 04→05, 05→10, 06→03, 07→08, 08→09, 09→07, 10→06）
"""

from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.linter.rules import _RULE_MAP
from ai_prompt_toolkit.probe_framework import normalize_owasp_refs

_OWASP_RULE_MAPPING: dict[str, list[str]] = {
    "LLM01": [
        "P006",
        "P007",
        "P010",
        "P031",
        "P032",
        "P033",
        "P034",
        "P038",
        "P039",
        "P040",
        "P076",
        "P077",
        "P078",
        "P096",
        "P097",
        "P113",
        "P131",
        "P132",
        "P133",
        "P134",
        "P135",
        "P161",
        "P163",
        "P166",
        "P167",
        "P176",
        "P177",
        "P178",
        "P179",
        "P180",
        "P181",
        "P182",
        "P183",
        "P184",
        "P185",
        "P186",
        "P187",
        "P188",
        "P189",
        "P190",
        "P191",
        "P192",
        "P193",
        "P194",
        "P195",
        "P196",
        "P197",
        "P200",
        "P201",
        "P202",
        "P205",
        "P206",
        "P209",
        "P210",
        "P211",
        "P212",
        "P213",
        "P214",
        "P215",
        "P216",
        "P217",
        "P219",
        "P063",
        "P064",
        "P065",
        "P079",
        "P086",
        "P087",
        "P088",
        "P089",
        "P090",
        "P091",
    ],
    "LLM02": [
        "P006",
        "P009",
        "P024",
        "P041",
        "P042",
        "P043",
        "P044",
        "P045",
        "P046",
        "P081",
        "P082",
        "P083",
        "P114",
        "P115",
        "P168",
        "P169",
        "P180",
        "P193",
        "P195",
        "P218",
        "P220",
        "P066",
        "P067",
        "P068",
        "P092",
        "P093",
        "P094",
        "P095",
        "P139",
        "P241",
        "P243",
        "P245",
        "P251",
        "P252",
        "P253",
        "P254",
        "P255",
    ],
    "LLM04": [
        "P024",
        "P047",
        "P048",
        "P049",
        "P098",
        "P099",
        "P100",
        "P150",
        "P221",
        "P222",
        "P223",
        "P224",
        "P225",
        "P233",
        "P235",
    ],
    "LLM05": [
        "P029",
        "P035",
        "P036",
        "P037",
        "P096",
        "P097",
        "P098",
        "P099",
        "P051",
        "P080",
        "P228",
        "P229",
        "P230",
        "P238",
        "P239",
        "P240",
        "P249",
        "P250",
    ],
    "LLM10": [
        "P007",
        "P008",
        "P031",
        "P032",
        "P033",
        "P034",
        "P052",
        "P053",
        "P076",
        "P077",
        "P078",
        "P099",
        "P151",
        "P161",
        "P164",
        "P071",
        "P072",
        "P073",
    ],
    "LLM03": [
        "P008",
        "P030",
        "P041",
        "P042",
        "P043",
        "P044",
        "P045",
        "P046",
        "P050",
        "P054",
        "P055",
        "P121",
        "P122",
        "P123",
        "P124",
        "P125",
        "P126",
        "P127",
        "P128",
        "P129",
        "P130",
        "P141",
        "P142",
        "P143",
        "P144",
        "P145",
        "P146",
        "P147",
        "P148",
        "P156",
        "P157",
        "P159",
        "P171",
        "P172",
        "P173",
        "P174",
        "P175",
        "P178",
        "P179",
        "P187",
        "P188",
        "P190",
        "P191",
        "P192",
        "P194",
        "P198",
        "P199",
        "P200",
        "P203",
        "P204",
        "P069",
        "P070",
        "P074",
        "P075",
        "P154",
        "P226",
        "P227",
        "P231",
        "P232",
        "P234",
        "P236",
        "P237",
        "P246",
        "P247",
        "P248",
    ],
    "LLM08": [
        "P006",
        "P009",
        "P024",
        "P041",
        "P042",
        "P043",
        "P084",
        "P085",
        "P116",
        "P117",
        "P152",
        "P158",
        "P162",
        "P165",
        "P203",
        "P204",
        "P140",
        "P242",
        "P244",
    ],
    "LLM09": [
        "P035",
        "P036",
        "P037",
        "P039",
        "P040",
        "P096",
        "P097",
        "P098",
        "P136",
        "P137",
        "P138",
        "P159",
    ],
    "LLM07": [
        "P015",
        "P016",
        "P017",
        "P018",
        "P019",
        "P020",
        "P025",
        "P026",
        "P027",
        "P028",
        "P056",
        "P057",
        "P058",
        "P059",
        "P060",
        "P061",
        "P062",
        "P101",
        "P102",
        "P103",
        "P104",
        "P105",
        "P119",
        "P120",
        "P167",
        "P170",
        "P181",
        "P182",
        "P184",
        "P186",
        "P189",
        "P196",
        "P197",
        "P207",
        "P208",
        "P001",
        "P002",
        "P003",
        "P005",
        "P021",
        "P022",
        "P106",
        "P107",
        "P108",
        "P109",
        "P110",
        "P111",
        "P112",
        "P118",
    ],
    "LLM06": [
        "P004",
        "P011",
        "P012",
        "P013",
        "P014",
        "P023",
        "P144",
        "P149",
        "P153",
        "P155",
        "P160",
        "P196",
        "P197",
    ],
}


def apply_owasp_refs() -> None:
    """把 2026 映射表注入各规则 owasp_refs，并把规则文件里硬编码的 2025 时代
    字面量统一重键到 2026（单一边界 — R228-P2-21）。

    顺序: 先重键规则既有（文件字面量, 2025）引用, 再合并 2026 映射表。
    重键是 LLM01-10 上的双射, 对已是 2026 的引用会二次重键——因此仅在规则字面量
    尚为 2025 时安全, 这正是本函数的调用时机（模块首次加载/重载, 字面量重新取 2025）。
    """
    # Step 1: 重键规则文件里的 2025 字面量 → 2026
    # （变量名 existing_rule 避免与 Step 2 的 rule: LintRule|None 同名冲突 — mypy 类型推断）
    for existing_rule in _RULE_MAP.values():
        existing_rule.owasp_refs = normalize_owasp_refs(existing_rule.owasp_refs)
    # Step 2: 合并 2026 映射表（表已是 2026 键, 不再重键）
    for owasp_ref, rule_ids in _OWASP_RULE_MAPPING.items():
        for rid in rule_ids:
            rule = _RULE_MAP.get(rid)
            if rule is not None and owasp_ref not in rule.owasp_refs:
                rule.owasp_refs.append(owasp_ref)


def get_rules_by_owasp(owasp_ref: str) -> list[str]:
    return _OWASP_RULE_MAPPING.get(owasp_ref, [])


def get_owasp_coverage() -> dict[str, dict[str, Any]]:
    from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2026

    result = {}
    for ref, info in OWASP_LLM_TOP_10_2026.items():
        rule_ids = _OWASP_RULE_MAPPING.get(ref, [])
        result[ref] = {
            "name": info["name"],
            "lint_rules": rule_ids,
            "probes": info["probes"],
            "lint_coverage": len(rule_ids),
        }
    return result


def generate_owasp_report() -> str:
    from ai_prompt_toolkit.linter.rules import get_all_rules

    coverage = get_owasp_coverage()
    total_rules = len(get_all_rules())
    mapped_rules = set()
    for _ref, data in coverage.items():
        mapped_rules.update(data["lint_rules"])
    lines = [
        "── OWASP LLM Top 10 映射覆盖率报告 ──",
        f"总Lint规则: {total_rules} | 已映射: {len(mapped_rules)} | 覆盖率: {len(mapped_rules) / total_rules * 100:.1f}%",
        "",
    ]
    for ref in sorted(coverage.keys()):
        data = coverage[ref]
        lines.append(f"{ref}: {data['name']}")
        lines.append(f"  Lint规则: {data['lint_coverage']}条 | Probe: {len(data['probes'])}个")
        if data["lint_rules"]:
            lines.append(f"  规则: {', '.join(data['lint_rules'][:10])}{'...' if len(data['lint_rules']) > 10 else ''}")
    unmapped = total_rules - len(mapped_rules)
    lines.append(f"\n未映射规则数: {unmapped}")
    return "\n".join(lines)
