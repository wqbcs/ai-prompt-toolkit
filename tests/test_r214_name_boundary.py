"""R214-B1: P241/P243 name 词边界修复 + golden 探针 lang schema

- P0-1: _PERSONAL_DATA_PATTERN 裸 "name" 子串误配 namespace/rename/filename
  (代码常见词) — 与 R213-B5 race→trace 同型子串盲区
- P2-5: golden_attacks.json 每条探针加 BCP-47 lang 标签, 漏检基线分语言
  统计机械派生(无新启发式)
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_FIXDIR = pathlib.Path(__file__).parent / "fixtures"
sys.path.insert(0, str(_ROOT / "src"))

from ai_prompt_toolkit.linter import lint_template  # noqa: E402

_BCP47_RE = re.compile(r"^[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*$")


def _p241_243(text: str) -> list:
    r = lint_template("t", text, apply_waivers=False)
    return [f for f in r.findings if f.rule_id in ("P241", "P243")]


class TestR214NameBoundary:
    def test_code_words_not_pii(self):
        # namespace/rename/filename 是代码词, 不得触发个人数据规则
        text = "Handle the namespace and rename operation in the config file."
        assert not _p241_243(text)

    def test_real_name_still_detected(self):
        # 真实姓名词仍须触发
        assert _p241_243("收集用户的姓名和地址用于画像")
        assert _p241_243("Collect the user's name and address for profiling.")


class TestR214LangSchema:
    def _probes(self) -> list[dict]:
        g = json.loads((_FIXDIR / "golden_attacks.json").read_text(encoding="utf-8"))
        return g["probes"]

    def test_all_probes_have_valid_lang(self):
        probes = self._probes()
        assert len(probes) == 73  # R215: 52 + 新面×16 + review观察×5（zw/空格×2/词法/同形异码）
        for p in probes:
            assert "lang" in p, f"{p['name']} 缺 lang 标签"
            assert _BCP47_RE.match(p["lang"]), f"{p['name']} lang 非 BCP-47: {p['lang']}"

    def test_current_language_distribution(self):
        probes = self._probes()
        langs = {p["name"]: p["lang"] for p in probes}
        assert langs["atk04_hardcoded_secret"] == "en"
        assert sum(1 for v in langs.values() if v == "zh-Hans") == 51  # R215-review: 48+3（atk69/70/71）
        assert sum(1 for v in langs.values() if v == "ja") == 6
        assert sum(1 for v in langs.values() if v == "zh-Hant") == 2


class TestR214PerLanguageReport:
    def test_per_language_derivation(self):
        # 分语言统计机械派生自 expected 单元, 总和必须等于全局口径
        spec = importlib.util.spec_from_file_location("check_miss_rate", _ROOT / "scripts" / "check_miss_rate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        report = mod.run()
        per_lang = report["per_language"]
        assert set(per_lang) == {"zh-Hans", "en", "ja", "zh-Hant"}
        assert sum(v["expected"] for v in per_lang.values()) == report["expected_total"]
        assert sum(v["missed"] for v in per_lang.values()) == report["total_missed"]
        assert report["global_rate"] == 0.0  # R214: 全语言 0 漏检
