"""R217: P261 不可见字符交错/BiDi反转注入面 回归（B5新规则模板第三次复用）

- P261(HIGH): 5TP探针命中 + 3子pattern隔离 + 5TN不命中(信源TN逐条承载)
  + 已知缺口守卫(组合变音符/软连字, 信源evasion_tests) + P260辖区切分守卫
- 注册表: 261规则, HIGH严重度, LLM01
- 58 clean 零命中(信源FP验证后字符集, ZWJ/BOM排除; 纯RTL文字不触发)
"""

from __future__ import annotations

import json

import pytest

from ai_prompt_toolkit.baselines import CLEAN_DIR as _CLEAN_DIR
from ai_prompt_toolkit.baselines import GOLDEN_FILE


def _lint(text: str, name: str = "t"):
    from ai_prompt_toolkit.linter import lint_template

    return lint_template(name, text, apply_waivers=False)


def _rules(findings) -> set[str]:
    return {f.rule_id for f in findings}


def _p261(finding_or_findings):
    fs = finding_or_findings if isinstance(finding_or_findings, list) else [finding_or_findings]
    return [f for f in fs if f.rule_id == "P261"]


def _probe(name: str) -> dict:
    g = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    return next(p for p in g["probes"] if p["name"] == name)


class TestR217Registry:
    def test_p261_registered_high(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        from ai_prompt_toolkit.types import Severity

        assert "P261" in _RULE_MAP
        assert _RULE_MAP["P261"].severity == Severity.HIGH
        assert "LLM01" in _RULE_MAP["P261"].owasp_refs

    def test_total_261(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules

        assert (
            len(get_all_rules()) >= 264
        )  # R230-E: 精确总数由 test_rules_smoke_p021_p255.EXPECTED_TOTAL 单锚点锁, 此处只断言规则集未缩水


class TestR217P261TruePositives:
    def test_five_tp_probes_hit(self):
        for n in (
            "atk74_zw_interleaved",
            "atk75_zwnj_interleaved",
            "atk76_bidi_rlo",
            "atk77_bidi_escaped",
            "atk78_wj_interleaved",
        ):
            p = _probe(n)
            assert "P261" in _rules(_lint(p["text"], n).findings), n

    def test_subpattern_isolation(self):
        # 每个TP命中对应子pattern(子pattern隔离 — 哪类不可见字符报哪类)
        expected_sub = {
            "atk74_zw_interleaved": "zero_width_interleaved",
            "atk75_zwnj_interleaved": "zero_width_interleaved",
            "atk76_bidi_rlo": "bidi_control",
            "atk77_bidi_escaped": "escaped_form",
            "atk78_wj_interleaved": "zero_width_interleaved",
        }
        for n, sub in expected_sub.items():
            p = _probe(n)
            f = _p261(_lint(p["text"], n).findings)[0]
            assert f.details["sub_pattern"] == sub, n

    def test_four_consecutive_zw_hit(self):
        # 3-4连续zw 归 P261 辖区(3+交错含连续; R215-review HIGH"1-4 zw 双漏"面的3+部分)
        assert "P261" in _rules(_lint("data \u200b\u200b\u200b\u200b payload").findings)

    def test_two_zw_no_hit(self):
        # 2零宽 < 3(信源单字符触发=65K语料15误报, 3+收紧) → 不命中
        assert "P261" not in _rules(_lint("data \u200b\u200b payload here").findings)

    def test_escaped_uppercase_hit(self):
        # 转义形态大写 \u202E 命中(IGNORECASE — P260子4 大写同形异码召回缺口同型教训)
        assert "P261" in _rules(_lint("\\u202E payload").findings)


class TestR217P261TrueNegatives:
    """ATR-2026-00276 信源 5TN 逐条承载(误报陷阱防线 — 单元承载, 不入clean)"""

    def test_arabic_rtl_text_no_hit(self):
        # TN1: 纯阿拉伯RTL文字(固有方向性, 无override控制字符) → 不命中
        assert "P261" not in _rules(_lint("Please translate this Arabic text: \u0645\u0631\u062d\u0628\u0627").findings)

    def test_whitespace_discussion_no_hit(self):
        # TN2: 空白处理讨论(无实际零宽字符) → 不命中
        text = "Normalize whitespace: remove duplicate spaces and trim leading/trailing spaces from the input text."
        assert "P261" not in _rules(_lint(text).findings)

    def test_bidi_word_mention_no_hit(self):
        # TN3: 提及"BiDi"词(无实际控制字符) → 不命中
        assert "P261" not in _rules(_lint("How do I handle BiDi text in my web application?").findings)

    def test_trojan_source_reference_no_hit(self):
        # TN4: 学术引用(Trojan Source 论文)无实际控制字符 → 不命中
        text = "The Trojan Source paper (arxiv 2106.09898) describes BiDi-based attacks on source code."
        assert "P261" not in _rules(_lint(text).findings)

    def test_plain_ascii_no_hit(self):
        # TN5: 纯ASCII → 不命中
        assert "P261" not in _rules(_lint("Normal ASCII text without any special Unicode characters.").findings)

    def test_zwj_emoji_no_hit(self):
        # 信源evasion_tests emoji-zwj-fp: ZWJ U+200D(emoji连字) 不在字符集(大规模误报移除)
        assert "P261" not in _rules(
            _lint("Family emoji: \U0001f468‍\U0001f469‍\U0001f467 (father, mother, daughter)").findings
        )

    def test_bom_no_hit(self):
        # 信源evasion_tests: BOM U+FEFF 不在字符集(UTF-8 合法编码标记)
        assert "P261" not in _rules(_lint("\ufeffnormal text after bom").findings)

    def test_lrm_rlm_no_hit(self):
        # 方向标记 U+200E/U+200F 不在字符集(信源未含, 不预支; 混排排版有合法用途)
        assert "P261" not in _rules(_lint("mixed \u200e direction \u200f marks").findings)


class TestR217KnownGapGuards:
    """已知缺口守卫: 组合变音符/软连字 = 信源明示 known gap, 观察探针不命中"""

    def test_atk79_combining_accent_no_hit(self):
        p = _probe("atk79_combining_accent")
        assert "P261" not in _rules(_lint(p["text"], p["name"]).findings)

    def test_atk80_soft_hyphen_no_hit(self):
        p = _probe("atk80_soft_hyphen")
        assert "P261" not in _rules(_lint(p["text"], p["name"]).findings)


class TestR217P260Boundary:
    """与 P260 子1(5+连续)辖区切分守卫"""

    def test_five_consecutive_both_hit(self):
        # 5+连续zw: P261(3+交错)与P260(5+连续)交叉命中 = 双报常态
        rules = _rules(_lint("data \u200b\u200b\u200b\u200b\u200b payload").findings)
        assert {"P260", "P261"} <= rules

    def test_atk62_cross_hit(self):
        # 存量 atk62(5+连续) 现双命中 P260+P261 — 交叉命中常态, 漏检门禁只计expected
        p = _probe("atk62_zw_5plus")
        rules = _rules(_lint(p["text"], p["name"]).findings)
        assert {"P260", "P261"} <= rules

    def test_p258_skip_not_regressed(self):
        # P258 的"5+连续zw跳过"逻辑不回归(R215-review HIGH 两段式, 辖区切分不变)
        rules = _rules(_lint("【系\u200b\u200b\u200b\u200b\u200b统】x").findings)
        assert "P258" not in rules
        assert "P260" in rules


class TestR217NoFpOnClean:
    def test_zero_on_clean(self):
        # 新规则在58干净样本上0命中(信源FP验证后字符集 + 5TN实证)
        for p in sorted(_CLEAN_DIR.iterdir()):
            if not p.is_file():
                continue
            assert "P261" not in _rules(_lint(p.read_text(encoding="utf-8"), p.name).findings), (
                f"{p.name} 新增 P261 误报"
            )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
