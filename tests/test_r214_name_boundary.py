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
        # R262: +20(P2-27 零探针补欠第二批 10 规则 P047/P059/P062/P063/P065/P079/P087/P089/P094/P096
        #       各 1TP+1TN, 全 zh-Hans) = 281
        # R263: +20(P2-27 零探针补欠第三批 10 规则 P097/P100/P103/P121/P122/P124/P127/P131/P133/P138
        #       各 1TP+1TN, 全 zh-Hans) = 301
        # R264: +20(P2-27 零探针补欠第四批 10 规则 P139/P141/P146/P148/P171/P172/P174/P175/P179/P181
        #       各 1TP+1TN, 18 zh-Hans + 2 en〔P179 格式劫持面仅英文 respond only in JSON 形态〕) = 321
        # R265: +20(P2-27 零探针补欠第五批 10 规则 P186/P187/P190/P191/P192/P194/P196/P197/P200/P202
        #       各 1TP+1TN, 全 zh-Hans) = 341
        # R266: +20(P2-27 零探针补欠第六批 10 规则 P205/P211/P213/P215/P217/P218/P220/P227/P228/P230
        #       各 1TP+1TN, 全 zh-Hans) = 361
        # R267: +20(P2-27 零探针补欠第七批 10 规则 P231/P232/P233/P235/P237/P238/P246/P248/P249/P251
        #       各 1TP+1TN, 全 zh-Hans) = 381
        # R268: +4(P2-27 收尾批 2 规则 P256/P130 各 1TP+1TN, 全 zh-Hans; P130=websocket
        #       独立触发形态实证不依赖同义组抑制) = 385 → HIGH 72+10 清零收官
        # R271: +20(P2-27 MEDIUM 首批 10 规则 P003/P010/P012/P013/P014/P018/P020/P023/P024/P026
        #       各 1TP+1TN, 全 zh-Hans; MEDIUM 队列 107 条启动) = 405
        # R272: +20(P2-27 MEDIUM 第二批 10 规则 P028/P029/P032/P034/P036/P037/P040/P043/P045/P046
        #       各 1TP+1TN, 全 zh-Hans) = 425
        # R273: +20(P2-27 MEDIUM 第三批 10 规则 P049/P052/P054/P057/P058/P060/P066/P067/P068/P069
        #       各 1TP+1TN, 全 zh-Hans) = 445
        # R274: +20(P2-27 MEDIUM 第四批 10 规则 P070/P072/P074/P076/P078/P081/P084/P085/P086/P088
        #       各 1TP+1TN, 全 zh-Hans; 含 6 条鸿蒙/华为云生态族) = 465
        assert len(probes) == 465
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
        # R262: +20 zh-Hans (P2-27 第二批 10 规则各 1TP+1TN) = zh-Hans 174 | en 99 | ja 6 | zh-Hant 2
        # R263: +20 zh-Hans (P2-27 第三批 10 规则各 1TP+1TN) = zh-Hans 194 | en 99 | ja 6 | zh-Hant 2
        # R264: +18 zh-Hans + 2 en (P2-27 第四批, P179 面仅英文触发) = zh-Hans 212 | en 101 | ja 6 | zh-Hant 2
        # R265: +20 zh-Hans (P2-27 第五批 10 规则各 1TP+1TN) = zh-Hans 232 | en 101 | ja 6 | zh-Hant 2
        # R266: +20 zh-Hans (P2-27 第六批 10 规则各 1TP+1TN) = zh-Hans 252 | en 101 | ja 6 | zh-Hant 2
        # R267: +20 zh-Hans (P2-27 第七批 10 规则各 1TP+1TN) = zh-Hans 272 | en 101 | ja 6 | zh-Hant 2
        # R268: +4 zh-Hans (P2-27 收尾批 P256/P130 各 1TP+1TN) = zh-Hans 276 | en 101 | ja 6 | zh-Hant 2
        # R271: +20 zh-Hans (P2-27 MEDIUM 首批 10 规则各 1TP+1TN) = zh-Hans 296 | en 101 | ja 6 | zh-Hant 2
        # R272: +20 zh-Hans (P2-27 MEDIUM 第二批 10 规则各 1TP+1TN) = zh-Hans 316 | en 101 | ja 6 | zh-Hant 2
        # R273: +20 zh-Hans (P2-27 MEDIUM 第三批 10 规则各 1TP+1TN) = zh-Hans 336 | en 101 | ja 6 | zh-Hant 2
        # R274: +20 zh-Hans (P2-27 MEDIUM 第四批 10 规则各 1TP+1TN) = zh-Hans 356 | en 101 | ja 6 | zh-Hant 2
        assert sum(1 for v in langs.values() if v == "zh-Hans") == 356
        assert sum(1 for v in langs.values() if v == "ja") == 6
        assert sum(1 for v in langs.values() if v == "zh-Hant") == 2
        # R264: +2 en (P179 探针) = 101
        assert sum(1 for v in langs.values() if v == "en") == 101


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
