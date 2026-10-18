"""R322: 多模态语境词裸子串撞车根因修复 回归（P2-26 复活触发器达成, P138/139/140+P132）

根因（三条独立真实 FP 证据链）:
- `_MULTIMODAL_CTX` 英文裸词子串误匹配: ① vision 撞 provision/television
  (deepset 良性语料 ds8) ② photo 撞 photographer/photography (ds363)
  ③ video 撞 video game 介质复合词 (NotInject-145, R318 登记根因)
- 修复形态: 词边界 photos?\\b / \\bvisions?\\b + video game 族负向断言
- P132 `_IMAGE_CTX` 同根因同修
- 已知残留（诚实声明, 精度优先取舍）: "video game + 生成任务"复合语境
  （如 video game trailer poster）无其他模态词共现时不报 — 介质复合词
  非模态引用, 静态面不可判意图, 与 R318 裁定同向
"""

from __future__ import annotations

import json

from ai_prompt_toolkit.baselines import GOLDEN_FILE


def _lint(text: str, name: str = "t"):
    from ai_prompt_toolkit.linter import lint_template

    return lint_template(name, text, apply_waivers=False)


def _rules(findings) -> set[str]:
    return {f.rule_id for f in findings}


def _probe(name: str) -> dict:
    g = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    return next(p for p in g["probes"] if p["name"] == name)


_TARGETS = ("P132", "P138", "P139", "P140")


class TestR322MultimodalCtxSilence:
    def test_provision_vision_silent(self):
        # 'provision' 含 vision 子串 — 修复前 P138/139/140 误火
        p = _probe("r322_mm_tn01_provision_vision")
        assert not (_rules(_lint(p["text"], p["name"]).findings) & set(_TARGETS))

    def test_photographer_silent(self):
        # 'photographer' 含 photo 子串 — 修复前 P138/139/140 误火
        p = _probe("r322_mm_tn02_photographer")
        assert not (_rules(_lint(p["text"], p["name"]).findings) & set(_TARGETS))

    def test_video_game_silent(self):
        # 'video game' 介质复合词 — R318 登记根因
        p = _probe("r322_mm_tn03_video_game")
        assert not (_rules(_lint(p["text"], p["name"]).findings) & set(_TARGETS))


class TestR322MultimodalCtxRecall:
    def test_legit_modality_refs_still_fire(self):
        # 防过收窄: 独立模态引用词必须保持触发（词边界只排子串撞车）
        cases = {
            "image": "Analyze this image and describe what you see in detail.",
            "video": "Generate a video clip from the provided script.",
            "photo": "Enhance this photo to improve lighting and contrast.",
            "zh_image": "多模态助手根据用户输入的图片与文本生成营销文案。",
        }
        for name, text in cases.items():
            fired = _rules(_lint(text, f"legit_{name}").findings)
            assert any(r in fired for r in ("P131", "P135", "P136", "P137", "P138")), name

    def test_video_game_compound_boundary_silent(self):
        # 已知残留守卫: video game 复合词（trailer 语境）无其他模态词共现时
        # 沉默 = 有意收窄（防未来扩标回退, R261 S5 同纪律）
        text = "Create a cinematic video game trailer poster with dramatic lighting."
        assert not (_rules(_lint(text, "gap_guard").findings) & set(_TARGETS))


class TestR322MultimodalTpAnchors:
    def test_golden_tp_probes_still_fire(self):
        # 既有 TP 锚点（zh-Hans 模态词面）收窄后必须保持实火
        for name, rid in (
            ("r263_p138_tp_mm_no_chain_decl", "P138"),
            ("r264_p139_tp_mm_no_isolation", "P139"),
            ("r277_p140_tp_mm_no_audit", "P140"),
        ):
            p = _probe(name)
            assert rid in _rules(_lint(p["text"], p["name"]).findings), name
