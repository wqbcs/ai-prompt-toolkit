"""R214-B3: 繁体中文 + CJK 空格插入语言面回归

诊断量化(先扩样后决策):
- zh-Hant 2/2=100% 漏检 (P113 系統提示 / P257 知識庫 — 词面仅简繁+日语)
- 空格插入 2 条漏检 (系统 提示 / 知 识库 — ATR evasion_tests 实证技术)
- 决策: 繁体→pattern 修复; 空格插入→方案B 有限\\s*容忍(仅 P113 + RAG门),
  不做全局空白归一化(影响257规则全局行为, 风险入L3)
"""

from __future__ import annotations

import json
import pathlib

import pytest

_FIXDIR = pathlib.Path(__file__).parent / "fixtures"
_CLEAN_DIR = _FIXDIR / "clean_prompts"


def _lint(text: str, name: str = "t"):
    from ai_prompt_toolkit.linter import lint_template

    return lint_template(name, text, apply_waivers=False)


def _rules(findings) -> set[str]:
    return {f.rule_id for f in findings}


def _probe(name: str) -> dict:
    g = json.loads((_FIXDIR / "golden_attacks.json").read_text(encoding="utf-8"))
    return next(p for p in g["probes"] if p["name"] == name)


class TestR214Zhhant:
    def test_zhhant_probes_exist(self):
        assert _probe("atk49_zhhant_system_prompt_leak")["lang"] == "zh-Hant"
        assert _probe("atk50_zhhant_rag_boundary")["lang"] == "zh-Hant"

    def test_atk49_zhhant_p113(self):
        p = _probe("atk49_zhhant_system_prompt_leak")
        assert "P113" in _rules(_lint(p["text"], p["name"]).findings)

    def test_atk50_zhhant_p257(self):
        p = _probe("atk50_zhhant_rag_boundary")
        assert "P257" in _rules(_lint(p["text"], p["name"]).findings)


class TestR214SplitKeyword:
    def test_split_probes_exist(self):
        assert _probe("atk51_split_keyword_system_prompt")["lang"] == "zh-Hans"
        assert _probe("atk52_split_keyword_rag")["lang"] == "zh-Hans"

    def test_atk51_split_p113(self):
        p = _probe("atk51_split_keyword_system_prompt")
        assert "P113" in _rules(_lint(p["text"], p["name"]).findings)

    def test_atk52_split_p257(self):
        p = _probe("atk52_split_keyword_rag")
        assert "P257" in _rules(_lint(p["text"], p["name"]).findings)


class TestR214SplitNoFp:
    _SPLIT_FORMS = ("系统 提示", "知 识库", "系统提示", "知识库")

    def test_clean_samples_no_new_hits(self):
        # \\s* 容忍扩面后: P113 命中集保持存量{clean26}, P257 保持 0
        p113_hits = set()
        for p in sorted(_CLEAN_DIR.iterdir()):
            if not p.is_file():
                continue
            got = _rules(_lint(p.read_text(encoding="utf-8"), p.name).findings)
            assert "P257" not in got, f"{p.name} 新增 P257 误报"
            if "P113" in got:
                p113_hits.add(p.name)
        assert p113_hits == {"clean26_提示词压缩.md"}  # 存量误报, 不得新增
