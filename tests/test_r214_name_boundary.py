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
sys.path.insert(0, str(_ROOT / "src"))

from ai_prompt_toolkit.baselines import GOLDEN_FILE  # noqa: E402
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
        g = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
        return g["probes"]

    def test_all_probes_have_valid_lang(self):
        probes = self._probes()
        # R220: 113 | R230: +4(P265 TP×2/TN×2) +8(TN扩容) = 125 | R231: +6(OWASP 2026子面 TP×4/TN×2) = 131
        # R234: +12(P2-23 buried-injections 基准语料 TP×4/TN×8) = 143
        # R235: +7(P2-11 TN 侧 buried-injections 剩余面: json数组/终端/邮件/sql结果/yaml/base64日志/心跳) = 150
        # R238: +7(P2-11 TN 侧 buried-injections 剩余面: http日志/markdown报告/notebook/xml feed/git log/package.json/中文工单) = 157
        # R240: +12(P266 连接串/同形字面 TP×3/TN×9) | R241: +5(P267 AWS凭据ID面 TP×2/TN×3) = 174
        # R243-2: 直读真源 data/golden_attacks.json(原锁陈旧 fixture 快照 157, 漂移实锤)
        # R250: +16(P2-26 过防御首批探针 P226/P162/P008/P044 各 TP×2/TN×2) = 190
        # R251: +36(P2-26 第二批 9 规则 P163/P167/P009/P160/P206-P209/P257 各 TP×2/TN×2) = 226
        # R253: +4(H 簇华为云/鸿蒙探针: P071/P073 各 TP×1 zh-Hans + TN×1 en) = 230
        # R256: +2(OOD 泛化 TP: deepset #9/#12 ignore-previous 形态, en) = 232
        # R257: +3(T6 P163 forget 族: TP×2 deepset #97/#18 + TN×1 隐私复位护栏, en) = 235
        # R260: +6(P2-11 探针覆盖补欠: P223/P236/P240 各 1TP+1TN, 全 zh-Hans) = 241
        # R261: +20(P2-27 零探针补欠首批 10 规则 P016/P017/P021/P031/P033/P035/P038/P039/P041/P042
        #       各 1TP+1TN, 全 zh-Hans) = 261
        assert len(probes) == 261
        for p in probes:
            assert "lang" in p, f"{p['name']} 缺 lang 标签"
            assert _BCP47_RE.match(p["lang"]), f"{p['name']} lang 非 BCP-47: {p['lang']}"

    def test_current_language_distribution(self):
        probes = self._probes()
        langs = {p["name"]: p["lang"] for p in probes}
        assert langs["atk04_hardcoded_secret"] == "en"
        # R234: zh-Hans 99 | en 36 | R235: +2 zh-Hans(r235_tn09/tn11) +5 en(r235_tn10/12/13/14/15)
        # R235: zh-Hans 101 | en 41 | ja 6 | zh-Hant 2 (TP 面不变, 纯 TN 侧扩容)
        # R238: +2 zh-Hans(r238_tn17/tn22) +5 en(r238_tn16/18/19/20/21)
        # R238: zh-Hans 103 | en 46 | ja 6 | zh-Hant 2
        # R240: +7 zh-Hans | +10 en (P266 连接串/同形字面 12 探针)
        # R241: zh-Hans/en 面不变 (P267 AWS凭据ID 5 探针: TP×2/TN×3 均 en 面已计入上轮?)
        # R243-2: 直读真源后分布 = zh-Hans 110 | en 56 | ja 6 | zh-Hant 2
        # R250: +9 zh-Hans + 7 en (P2-26 16 探针) = zh-Hans 119 | en 63 | ja 6 | zh-Hant 2
        # R251: +7 zh-Hans (P167/P009/P160/P206/P208/P209/P257 各 1 条中文面) + 29 en
        #       = zh-Hans 126 | en 92 | ja 6 | zh-Hant 2
        # R253: +2 zh-Hans (r253_p071/p073 TP) + 2 en (TN)
        #       = zh-Hans 128 | en 94 | ja 6 | zh-Hant 2
        # R256: +2 en (OOD 泛化 TP) = zh-Hans 128 | en 96 | ja 6 | zh-Hant 2
        # R257: +3 en (T6 forget 族 3 探针) = zh-Hans 128 | en 99 | ja 6 | zh-Hant 2
        # R260: +6 zh-Hans (P223/P236/P240 各 1TP+1TN) = zh-Hans 134 | en 99 | ja 6 | zh-Hant 2
        # R261: +20 zh-Hans (P2-27 首批 10 规则各 1TP+1TN) = zh-Hans 154 | en 99 | ja 6 | zh-Hant 2
        assert sum(1 for v in langs.values() if v == "zh-Hans") == 154
        assert sum(1 for v in langs.values() if v == "ja") == 6
        assert sum(1 for v in langs.values() if v == "zh-Hant") == 2
        assert sum(1 for v in langs.values() if v == "en") == 99


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
