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
        # R275: +20(P2-27 MEDIUM 第五批 10 规则 P092/P093/P095/P098/P099/P101/P102/P104/P105/P107
        #       各 1TP+1TN, 全 zh-Hans; 含 5 条鸿蒙/盘古生态族) = 485
        # R276: +20(P2-27 MEDIUM 第六批 10 规则 P109/P110/P111/P116/P117/P120/P123/P125/P126/P128
        #       各 1TP+1TN, 全 zh-Hans; 含 4 条鸿蒙生态族) = 505
        # R277: +20(P2-27 MEDIUM 第七批 10 规则 P129/P134/P135/P136/P137/P140/P144/P145/P147/P149
        #       各 1TP+1TN, 全 zh-Hans; 含 6 条多模态/Agent/鸿蒙族) = 525
        # R278: +20(P2-27 MEDIUM 第八批 10 规则 P150/P151/P152/P153/P154/P155/P156/P157/P158/P164
        #       各 1TP+1TN, 全 zh-Hans; 含 5 条生产安全编码族) = 545
        # R279: +20(P2-27 MEDIUM 第九批 10 规则 P165/P166/P168/P169/P173/P183/P184/P185/P188/P189
        #       各 1TP+1TN, 全 zh-Hans; 含 4 条安全编码族 + 3 条鸿蒙族 + 3 条运维族) = 565
        # R280: +20(P2-27 MEDIUM 第十批 10 规则 P193/P195/P198/P199/P203/P204/P210/P212/P214/P219
        #       各 1TP+1TN, 全 zh-Hans; agent_security×2+inference_security×2+compliance×2+
        #       rag_security×1+harmonyos_v16×2+multimodal_security×1) = 585
        # R281: +14(P2-27 MEDIUM 收官批 7 规则 P229/P234/P242/P243/P247/P262/P263
        #       各 1TP+1TN, 全 zh-Hans; MEDIUM 107 条清零收官) = 599
        # R282: +20(P2-27 LOW 首批 10 规则 P011/P015/P019/P025/P027/P030/P048/P050/P053/P055
        #       各 1TP+1TN, 全 zh-Hans; LOW 27 条 3 批推进首批) = 619
        # R285: +34(P2-27 LOW 次批 10 规则 P056/P061/P064/P075/P077/P080/P082/P083/P090/P091
        #       + 收官批 7 规则 P106/P108/P112/P115/P118/P119/P264 各 1TP+1TN, 全 zh-Hans;
        #       LOW 27 条清零, 探针覆盖 267/267=100% 收官) = 653
        # R286: +10 ja (P2-11 ja 面扩容: P261/P260/P266/P267 ja 语境 TP×4 +
        #       多义性/敬语/buried-injections/全角数字 TN×4 + 形态素/全角 bypass
        #       观察×2; 全角字母 bypass 缺口登记 02 总板) = 663
        # R288: +3 (P2-30 P178 逃生舱: ja 安全文档引用 FP + en advisory 引用
        #       FP + 「这是示例」型红线 TP pin) = 666
        # R293: +1 ja (P2-29 P268 全角字母规则化: r293_ja_tn_fullwidth_okng 良性
        #       全角拉丁 TN; R240 tn08/R286 obs 两条盲点观察探针翻转 TP 不增数) = 667
        # R312: +5 (P269 tag块 ASCII smuggling: 4TP+旗帜TN, 全 en) = 672
        # R315: +8 (P2-26 过防御批 TN: P009×2/P164×2/P170×2/P008×2, en 4+zh-Hans 4) = 680
        # R317: +4 (P2-26 批2 TN: P169×2/P239×2, 全 en) = 684
        # R319: +2 (深审探针: P269 混排 TP + P008 智 TN) + R320: +1 (P239 超时对称 TN)
        # + R321: +5 (指令文件 IPI 取证 ATR 源: 3 盲点观察 + 2 TN) = 692
        # R322: +4 (指令文件 IPI 规则化 P270: 2TP+2TN, 全 en) = 696
        # R322: +3 (多模态裸子串撞车根因修复 TN: provision/photographer/video game, 全 en) = 699
        # R323: +1 (多模态输入门 social media 根因 TN, en) = 700
        # R323: +3 (P271 规则化: 1TP+2TN, 全 en) = 703
        # R325: 探针总数断言改为动态读真源(上方台账为历史留痕, 防每轮 +N 手工漏改致红)
        assert len(probes) == self._source_probe_count()
        for p in probes:
            assert "lang" in p, f"{p['name']} 缺 lang 标签"
            assert _BCP47_RE.match(p["lang"]), f"{p['name']} lang 非 BCP-47: {p['lang']}"

    @staticmethod
    def _source_probe_count() -> int:
        # R325: 探针总数唯一真源 = data/golden_attacks.json(GOLDEN_FILE)["probes"], 动态计数防漂移
        g = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
        return len(g["probes"])

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
        # R275: +20 zh-Hans (P2-27 MEDIUM 第五批 10 规则各 1TP+1TN) = zh-Hans 376 | en 101 | ja 6 | zh-Hant 2
        # R276: +20 zh-Hans (P2-27 MEDIUM 第六批 10 规则各 1TP+1TN) = zh-Hans 396 | en 101 | ja 6 | zh-Hant 2
        # R277: +20 zh-Hans (P2-27 MEDIUM 第七批 10 规则各 1TP+1TN) = zh-Hans 416 | en 101 | ja 6 | zh-Hant 2
        # R278: +20 zh-Hans (P2-27 MEDIUM 第八批 10 规则各 1TP+1TN) = zh-Hans 436 | en 101 | ja 6 | zh-Hant 2
        # R279: +20 zh-Hans (P2-27 MEDIUM 第九批 10 规则各 1TP+1TN) = zh-Hans 456 | en 101 | ja 6 | zh-Hant 2
        # R280: +20 zh-Hans (P2-27 MEDIUM 第十批 10 规则各 1TP+1TN) = zh-Hans 476 | en 101 | ja 6 | zh-Hant 2
        # R281: +14 zh-Hans (P2-27 MEDIUM 收官批 7 规则各 1TP+1TN) = zh-Hans 490 | en 101 | ja 6 | zh-Hant 2
        # R282: +20 zh-Hans (P2-27 LOW 首批 10 规则各 1TP+1TN) = zh-Hans 510 | en 101 | ja 6 | zh-Hant 2
        # R285: +34 zh-Hans (P2-27 LOW 次批 10 + 收官批 7 各 1TP+1TN, LOW 清零收官)
        #       = zh-Hans 544 | en 101 | ja 6 | zh-Hant 2
        # R286: +10 ja (P2-11 ja 面扩容: TP×4/TN×4/观察×2)
        #       = zh-Hans 544 | en 101 | ja 16 | zh-Hant 2
        # R288: +1 ja (P2-30 TN) = zh-Hans 544 | en 103 | ja 17 | zh-Hant 2
        # R293: +1 ja (P2-29 P268 良性全角拉丁 TN) = zh-Hans 544 | en 103 | ja 18 | zh-Hant 2
        # R312: +5 en (P269 tag块探针 4TP+旗帜TN) = zh-Hans 544 | en 108 | ja 18 | zh-Hant 2
        # R315: +4 zh-Hans (P009 支付/P164 越狱游戏/P170 方法论/P008 才能) + 4 en
        #       (P009 文件清理/P164 越狱科普/P170 科研essay/P008 忽略脏话)
        #       = zh-Hans 548 | en 112 | ja 18 | zh-Hant 2
        # R317: +4 en (P2-26 批2: P169 社区公园/community运营 + P239 Discord/
        #       web server) = zh-Hans 548 | en 116 | ja 18 | zh-Hant 2
        # R320: +1 zh-Hans (P239 超时对称 TN); R321: +5 en (指令文件 IPI 取证)
        # = zh-Hans 551 | en 121 | ja 18 | zh-Hant 2
        # R322: +4 en (P270 规则化: 2TP+2TN) = zh-Hans 551 | en 125 | ja 18 | zh-Hant 2
        # R322: +3 en (多模态根因修复 TN) = zh-Hans 551 | en 128 | ja 18 | zh-Hant 2
        # R323: +1 en (多模态输入门 social media TN) = zh-Hans 551 | en 129 | ja 18 | zh-Hant 2
        # R323: +3 en (P271 规则化 1TP+2TN) = zh-Hans 551 | en 132 | ja 18 | zh-Hant 2
        # R334: +3 zh-Hans (P270 中文扩展 a_priv/b_cred 2TP+1TN) = zh-Hans 554 | en 132 | ja 18 | zh-Hant 2
        assert sum(1 for v in langs.values() if v == "zh-Hans") == 554
        assert sum(1 for v in langs.values() if v == "ja") == 18
        assert sum(1 for v in langs.values() if v == "zh-Hant") == 2
        # R264: +2 en (P179 探针) = 101; R288: +2 en (P2-30 探针) = 103; R312: +5 en (P269) = 108; R315: +4 en (P2-26 TN) = 112; R317: +4 en (批2 TN) = 116; R321: +5 en (指令文件 IPI 取证) = 121; R322: +4 en (P270 规则化 2TP+2TN) = 125; R322: +3 en (多模态根因修复 TN) = 128; R323: +1 en (多模态输入门 TN) = 129; R323: +3 en (P271 规则化 1TP+2TN) = 132
        assert sum(1 for v in langs.values() if v == "en") == 132


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
