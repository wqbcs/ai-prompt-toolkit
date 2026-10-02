"""交互式Lint解释增强 — 详细上下文+OWASP参考+修复示例

功能:
- explain_finding: 单个finding的详细解释
- explain_results: 批量解释lint结果
- 包含: 规则描述+OWASP映射+修复步骤+代码示例+风险等级
- R220-B1: explain 输出加 per-finding "静默(waiver)" 提示 — FP killer 解药
  (用户看到误报能判断+静默单条规则, 而非禁用整个工具)
- R220-B2: location 走 R218 契约单一事实源(parse_location), 去除 "0"/"1"
  硬编码哨兵(R219 同型修复, 用户"避免硬编码")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.linter.owasp_mapping import _OWASP_RULE_MAPPING
from ai_prompt_toolkit.linter.rules import _RULE_MAP
from ai_prompt_toolkit.types import parse_location

if TYPE_CHECKING:
    from ai_prompt_toolkit.types import Finding

_RISK_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
_RISK_LABEL = {"critical": "严重", "high": "高危", "medium": "中等", "low": "低危"}


def explain_finding(finding: Finding, lang: str = "zh") -> dict[str, Any]:
    rule = _RULE_MAP.get(finding.rule_id)
    if not rule:
        return {"rule_id": finding.rule_id, "description": finding.description, "error": "rule_not_found"}
    if lang == "en":
        desc = rule.description_en or rule.description
        rem = rule.remediation_en or rule.remediation
    else:
        desc = rule.description
        rem = rule.remediation
    owasp_refs = rule.owasp_refs
    owasp_details = []
    for ref in owasp_refs:
        mapped_rules = _OWASP_RULE_MAPPING.get(ref, [])
        owasp_details.append(
            {
                "ref": ref,
                "related_rules": [r for r in mapped_rules if r != finding.rule_id][:5],
            }
        )
    sev = rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity)
    explanation = {
        "rule_id": finding.rule_id,
        "rule_name": rule.name,
        "severity": sev,
        "risk_level": _RISK_LABEL.get(sev, "未知"),
        "risk_emoji": _RISK_EMOJI.get(sev, "•"),
        "category": rule.category,
        "family": rule.family,
        "description": desc,
        "remediation": rem,
        "owasp_refs": owasp_details,
    }
    # R220-B2: location 契约("") = 文件级 / "L:<line>" / "L:<line>:C:<col>"),
    # 走 parse_location 单一事实源, 文件级不显示行(不猜行, 不硬编码 "0"/"1" 哨兵)
    line1, _col1 = parse_location(str(finding.location or ""))
    if line1 is not None:
        explanation["location"] = f"行{line1}"
    return explanation


def explain_results(findings: list[Finding], lang: str = "zh") -> list[dict[str, Any]]:
    return [explain_finding(f, lang=lang) for f in findings]


def format_explanation(expl: dict[str, Any]) -> str:
    lines = []
    emoji = expl.get("risk_emoji", "•")
    lines.append(
        f"{emoji} [{expl['rule_id']}] {expl.get('rule_name', '')} — {expl.get('risk_level', '')}({expl.get('severity', '')})"
    )
    lines.append(f"  类别: {expl.get('category', '')} | 家族: {expl.get('family', '')}")
    lines.append(f"  描述: {expl.get('description', '')}")
    lines.append(f"  修复: {expl.get('remediation', '')}")
    if expl.get("location"):
        lines.append(f"  位置: {expl['location']}")
    # R220-B1: 静默(waiver)提示 — FP killer 解药。文件级作用域(waivers.py,
    # 行级 waiver 地基已就绪见 L3-13, 提示诚实标注文件级不误导)。
    lines.append(f"  静默: promptlint:ignore {expl.get('rule_id', '')} (文件级豁免)")
    if expl.get("owasp_refs"):
        for o in expl["owasp_refs"]:
            related = ", ".join(o["related_rules"][:3]) if o["related_rules"] else "无"
            lines.append(f"  OWASP: {o['ref']} (关联规则: {related})")
    return "\n".join(lines)
