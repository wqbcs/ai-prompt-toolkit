"""R323: 多模态输入门 _MULTIMODAL_INPUT_PATTERNS 根因修复 回归（P038/P039/P040）

根因（真实语料证据链）:
- 裸 `\\bmedia\\b` 撞 "social media" 常态良性面（deepset 独立语料 4 独立
  真实 FP: 26/171/358/384, 含连字符形态 Social-Media-Marketing）
- `\\bvideo\\b` 撞 "video game" 介质复合词（NotInject-145, 与 R322
  _MULTIMODAL_CTX 修复同根因的兄弟面）
- 修复形态: 移除裸 media（R212-6 移除裸 文件/attach、R253 H 簇裸词撞车
  移除同判据）+ video game 族负向断言
- 已知取舍: 仅以 "media" 表多模态输入的英文 prompt 不再触发（无其他
  模态词/上传词共现时）— 4 条实证 FP 面 > 假设召回面, 与 R318 精度优先同向
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


_TARGETS = ("P038", "P039", "P040")


class TestR323SocialMediaSilence:
    def test_social_media_en_silent(self):
        # 真实 benign 营销咨询 prompt（deepset 索引358）
        p = _probe("r323_mm_tn01_social_media")
        assert not (_rules(_lint(p["text"], p["name"]).findings) & set(_TARGETS))

    def test_social_media_hyphen_silent(self):
        # 连字符形态 Social-Media-Marketing（deepset 索引384, 德语文本）
        text = (
            "Ich habe bereits eine eigene Website und betreibe "
            "Social-Media-Marketing, aber ich möchte gerne noch mehr "
            "Reichweite erzielen."
        )
        assert not (_rules(_lint(text, "hyphen_guard").findings) & set(_TARGETS))

    def test_social_media_salad_silent(self):
        # 词沙拉形态（deepset 索引26）
        assert not (_rules(_lint("Data protection social media Europa", "salad").findings) & set(_TARGETS))


class TestR323VideoGameInputSilence:
    def test_video_game_input_gate_silent(self):
        # R322 探针 ni-145: 输入门修复后 P038/P040 亦必须沉默
        p = _probe("r322_mm_tn03_video_game")
        assert not (_rules(_lint(p["text"], p["name"]).findings) & set(_TARGETS))


class TestR323InputGateRecall:
    def test_legit_input_refs_still_fire(self):
        # 防过收窄: 真实模态输入引用必须保持触发（P038=无校验声明面）
        cases = {
            "image": "Analyze this image and describe what you see in detail.",
            "video": "Process this video clip and summarize the scenes.",
            "picture": "Here is a picture of my garden, what plants do you see?",
            "upload": "Upload this photo and enhance the lighting.",
            "zh": "用户上传的图片会直接用于内容识别并生成描述。",
        }
        for name, text in cases.items():
            fired = _rules(_lint(text, f"legit_{name}").findings)
            assert "P038" in fired, name


class TestR323TpAnchors:
    def test_golden_tp_probes_still_fire(self):
        # 既有 TP 锚点（zh-Hans 上传/图片面）收窄后必须保持实火
        for name, rid in (
            ("r261_p038_tp_image_no_validation", "P038"),
            ("r261_p039_tp_image_no_safety_filter", "P039"),
            ("r272_p040_tp_mm_no_fallback", "P040"),
        ):
            p = _probe(name)
            assert rid in _rules(_lint(p["text"], p["name"]).findings), name
