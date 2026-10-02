"""R220-B1/B2: explain 接线增强 + location 契约单一事实源

- B1: format_explanation 输出 per-finding "静默(waiver)" 提示 — FP killer 解药
  (用户看到误报能静默单条规则, 而非禁用整个工具)。提示诚实标注"文件级"(
  waivers.py 当前是文件级作用域, 行级地基见 L3-13, 不误导)。
- B2: explain 的 location 展示走 R218 契约 parse_location 单一事实源, 去除
  "0"/"1" 硬编码哨兵判定(R219 同型, 用户"避免硬编码")。文件级("") → 不显示行
  (不猜行); 行级(L:<line>:C:<col>) → 干净显示行号。
"""

from ai_prompt_toolkit.linter.explain import explain_finding, format_explanation
from ai_prompt_toolkit.types import Finding, Severity


def _f(rule_id: str, location: str = "") -> Finding:
    return Finding(rule_id, Severity.MEDIUM, "desc", location=location, remediation="remed")


# ---- B2: location 契约 ----


def test_b2_file_level_no_line_shown():
    """文件级 finding(location='') → explain 不猜行, format 无"位置"行。"""
    expl = explain_finding(_f("P107", location=""))
    assert "location" not in expl, "文件级 finding 不应显示行号(不猜行)"
    text = format_explanation(expl)
    assert "位置" not in text, f"文件级不应有位置行: {text!r}"


def test_b2_line_level_shows_clean_line():
    """行级 finding(L:5:C:2) → 干净显示"行5"(非原始契约字符串)。"""
    expl = explain_finding(_f("P107", location="L:5:C:2"))
    assert expl.get("location") == "行5", f"行级应显示 行5: {expl.get('location')!r}"


def test_b2_line_only_shows_line():
    """仅行(L:3, 无列) → 显示"行3"。"""
    expl = explain_finding(_f("P107", location="L:3"))
    assert expl.get("location") == "行3"


def test_b2_legacy_numeric_via_contract_not_hardcoded():
    """旧纯数字哨兵("1")不再靠硬编码 in ('0','1') 判定, 而走 parse_location
    契约统一解析 — 文档化行为: 纯数字按 R218 兼容口径解析为行号。"""
    expl = explain_finding(_f("P107", location="1"))
    # 关键: 不再被硬编码吞掉; 走契约 → 行1(与 LSP 历史口径一致)
    assert expl.get("location") == "行1"


# ---- B1: per-finding 静默(waiver)提示 ----


def test_b1_waiver_hint_present_with_rule_id():
    """format_explanation 含"静默"行, 带正确 rule_id + 文件级作用域标注。"""
    expl = explain_finding(_f("P107"))
    text = format_explanation(expl)
    assert "静默" in text, f"缺静默提示: {text!r}"
    assert "promptlint:ignore P107" in text, f"静默提示须带正确 rule_id: {text!r}"
    assert "文件级豁免" in text, "静默提示须诚实标注文件级作用域"


def test_b1_waiver_hint_matches_distinct_rules():
    """不同规则的静默提示各带各的 rule_id(不串号)。"""
    t_p001 = format_explanation(explain_finding(_f("P001")))
    t_p006 = format_explanation(explain_finding(_f("P006")))
    assert "promptlint:ignore P001" in t_p001
    assert "promptlint:ignore P006" in t_p006
    assert "P006" not in t_p001.split("静默")[-1], "P001 静默行不应串到 P006"


def test_b1_waiver_hint_coexists_with_owasp():
    """静默提示与既有 OWASP/修复/描述行共存, 不破坏原有输出结构。"""
    expl = explain_finding(_f("P006"))  # P006 有 OWASP 映射
    text = format_explanation(expl)
    assert "描述" in text and "修复" in text and "静默" in text and "OWASP" in text


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
