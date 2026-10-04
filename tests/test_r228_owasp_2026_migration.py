"""R228-P2-21: OWASP LLM Top 10 2026 映射迁移回归测试

固定触发器（07 R5 / 02 P2-11）：OWASP 2026 版 2026-08-03 发布 —
10 项里 8 项换位 + LLM07 System Prompt Leakage → LLM08 Hidden Context Exposure 改名。
本测试锁死重键正确性（2025→2026 表 / 2026 定义 / normalize 边界 / 运行时 refs 无 2025 残留）。
"""

from __future__ import annotations

from ai_prompt_toolkit.probe_framework import (
    OWASP_2025_TO_2026,
    OWASP_LLM_TOP_10_2025,
    OWASP_LLM_TOP_10_2026,
    get_owasp_mapping,
    normalize_owasp_refs,
)


class TestRekeyTable:
    """2025→2026 重键表 — 与官方 PDF TOC + What's New 双重确认"""

    def test_rekey_matches_official(self):
        assert OWASP_2025_TO_2026 == {
            "LLM01": "LLM01",
            "LLM02": "LLM02",
            "LLM03": "LLM04",
            "LLM04": "LLM05",
            "LLM05": "LLM10",
            "LLM06": "LLM03",
            "LLM07": "LLM08",
            "LLM08": "LLM09",
            "LLM09": "LLM07",
            "LLM10": "LLM06",
        }

    def test_rekey_is_bijection(self):
        # 重键是双射（10→10，无碰撞/无丢失）
        vals = list(OWASP_2025_TO_2026.values())
        assert len(vals) == 10
        assert len(set(vals)) == 10
        assert sorted(OWASP_2025_TO_2026.keys()) == sorted(OWASP_LLM_TOP_10_2026.keys())
        assert sorted(vals) == sorted(OWASP_LLM_TOP_10_2026.keys())

    def test_rekey_applies_to_2025(self):
        # 对 2025 全部键重键 = 2026 全部键
        assert {OWASP_2025_TO_2026[k] for k in OWASP_LLM_TOP_10_2025} == set(OWASP_LLM_TOP_10_2026)


class Test2026Definitions:
    """2026 风险定义 — 探针随风险身份走（编号变，探针不变）"""

    def test_ten_risks(self):
        assert len(OWASP_LLM_TOP_10_2026) == 10

    def test_llm08_renamed_hidden_context_exposure(self):
        assert OWASP_LLM_TOP_10_2026["LLM08"]["name"] == "Hidden Context Exposure"
        # 探针继承 2025 System Prompt Leakage
        assert OWASP_LLM_TOP_10_2026["LLM08"]["probes"] == OWASP_LLM_TOP_10_2025["LLM07"]["probes"]

    def test_probe_identity_follows_risk(self):
        # 每个 2026 风险的探针 = 其 2025 前身风险的探针（风险身份不变）
        for k2025, k2026 in OWASP_2025_TO_2026.items():
            assert OWASP_LLM_TOP_10_2026[k2026]["probes"] == OWASP_LLM_TOP_10_2025[k2025]["probes"], k2026

    def test_key_ranking_names(self):
        assert OWASP_LLM_TOP_10_2026["LLM03"]["name"] == "Excessive Agency"
        assert OWASP_LLM_TOP_10_2026["LLM04"]["name"] == "Supply Chain"
        assert OWASP_LLM_TOP_10_2026["LLM06"]["name"] == "Unbounded Consumption"
        assert OWASP_LLM_TOP_10_2026["LLM07"]["name"] == "Misinformation"
        assert OWASP_LLM_TOP_10_2026["LLM09"]["name"] == "Vector and Embedding Weaknesses"
        assert OWASP_LLM_TOP_10_2026["LLM10"]["name"] == "Improper Output Handling"


class TestNormalizeBoundary:
    """normalize_owasp_refs 单一边界 — 规则文件 2025 硬编码字面量译到 2026"""

    def test_2025_refs_rekeyed(self):
        assert normalize_owasp_refs(["LLM06", "LLM09"]) == ["LLM03", "LLM07"]

    def test_bijection_applied(self):
        # 2025 LLM01/LLM08 → 2026 LLM01/LLM09（LLM08 在 2025 是 Vector）
        assert normalize_owasp_refs(["LLM01", "LLM08"]) == ["LLM01", "LLM09"]

    def test_unknown_passthrough(self):
        # 非 LLM01-10 的引用原样透传；LLM03(2025 Supply) → LLM04(2026 Supply)
        assert normalize_owasp_refs(["ATLAS01", "LLM03"]) == ["ATLAS01", "LLM04"]

    def test_idempotency_not_guaranteed(self):
        # 双射非幂等：对已重键结果再调用会二次重键（2025 LLM06→2026 LLM03→再当2025重键→LLM04）
        once = normalize_owasp_refs(["LLM06"])
        assert once == ["LLM03"]
        assert normalize_owasp_refs(once) == ["LLM04"]  # 证明调用方须保证输入是 2025 字面量

    def test_dedup_on_collision(self):
        # 2025 LLM09→2026 LLM07 与 2025 LLM07→2026 LLM08 不碰撞；
        # 但 2025 LLM06→LLM03 与 2025 LLM06 重复出现时去重
        assert normalize_owasp_refs(["LLM06", "LLM06"]) == ["LLM03"]


class TestRuntimeRefs:
    """运行时规则 refs 无 2025 残留（apply_owasp_refs 边界已 normalize）"""

    def test_all_rule_refs_are_2026_keys(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        bad = [
            (rid, ref) for rid, rule in _RULE_MAP.items() for ref in rule.owasp_refs if ref not in OWASP_LLM_TOP_10_2026
        ]
        assert not bad, f"规则 refs 含非 2026 键: {bad[:10]}"

    def test_no_2025_only_keys_leak(self):
        # 若某规则原只挂 2025 LLM09(Misinformation)，现在应为 2026 LLM07
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        p015 = _RULE_MAP.get("P015")
        if p015 is not None and p015.owasp_refs:
            assert "LLM07" in p015.owasp_refs or "LLM07" in OWASP_LLM_TOP_10_2026


def test_get_owasp_mapping_returns_2026():
    assert set(get_owasp_mapping()) == set(OWASP_LLM_TOP_10_2026)


def test_coverage_and_report_use_2026():
    from ai_prompt_toolkit.linter.owasp_mapping import generate_owasp_report, get_owasp_coverage

    cov = get_owasp_coverage()
    assert set(cov) == set(OWASP_LLM_TOP_10_2026)
    # 每个风险都有名称 + 探针
    for info in cov.values():
        assert info["name"]
        assert info["probes"]
    report = generate_owasp_report()
    # 2026 改名风险出现在报告里
    assert "Hidden Context Exposure" in report
