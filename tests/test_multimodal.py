"""多模态Prompt Lint模块测试"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.multimodal import (
    MultimodalMessage,
    check_multimodal_prompt,
    estimate_image_tokens,
    parse_multimodal_messages,
)
from ai_prompt_toolkit.types import Finding, Severity


class TestMultimodalMessage:
    def test_to_dict_truncates_long_fields(self):
        msg = MultimodalMessage(
            role="user", content_type="image",
            text="x" * 200, image_url="http://" + "a" * 200,
            image_format="png", alt_text="y" * 100,
            detail="auto", provider_format="openai",
        )
        d = msg.to_dict()
        assert len(d["text"]) == 100
        assert len(d["image_url"]) == 100
        assert len(d["alt_text"]) == 50

    def test_to_dict_empty_fields(self):
        msg = MultimodalMessage(role="user", content_type="image")
        d = msg.to_dict()
        assert d["text"] == ""
        assert d["image_url"] == ""
        assert d["alt_text"] == ""


class TestParseMultimodalMessages:
    def test_parse_markdown_image(self):
        text = "看看这张图片 ![描述](https://example.com/photo.png) 怎么样"
        msgs = parse_multimodal_messages(text)
        assert len(msgs) >= 1
        md_msgs = [m for m in msgs if m.provider_format == "markdown"]
        assert len(md_msgs) == 1
        assert md_msgs[0].alt_text == "描述"
        assert md_msgs[0].image_format == "png"
        assert md_msgs[0].image_url == "https://example.com/photo.png"

    def test_parse_openai_image_url(self):
        text = '''
        {
          "role": "user",
          "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg", "detail": "high"}}
          ]
        }
        '''
        msgs = parse_multimodal_messages(text)
        openai_msgs = [m for m in msgs if m.provider_format == "openai"]
        assert len(openai_msgs) == 1
        assert openai_msgs[0].image_format == "jpg"
        assert openai_msgs[0].detail == "high"

    def test_parse_claude_base64_image(self):
        text = '''
        {
          "type": "image",
          "source": {"type": "base64", "media_type": "image/png", "data": "iVBOR..."}
        }
        '''
        msgs = parse_multimodal_messages(text)
        claude_msgs = [m for m in msgs if m.provider_format == "claude"]
        assert len(claude_msgs) == 1
        assert claude_msgs[0].image_format == "base64"

    def test_parse_gemini_inline_data(self):
        text = '''
        {"inline_data": {"mime_type": "image/jpeg", "data": "/9j/4AAQ..."}}
        '''
        msgs = parse_multimodal_messages(text)
        gemini_msgs = [m for m in msgs if m.provider_format == "gemini"]
        assert len(gemini_msgs) == 1
        assert gemini_msgs[0].image_format == "jpeg"

    def test_parse_local_file_reference(self):
        text = 'src="./images/photo.png"'
        msgs = parse_multimodal_messages(text)
        local_msgs = [m for m in msgs if m.provider_format == "local_file"]
        assert len(local_msgs) == 1
        assert local_msgs[0].image_format == "png"

    def test_parse_no_images(self):
        text = "这是一个纯文本提示词，没有任何图片"
        msgs = parse_multimodal_messages(text)
        assert len(msgs) == 0

    def test_parse_multiple_markdown_images(self):
        text = "![图1](a.png) 和 ![图2](b.jpg) 和 ![图3](c.webp)"
        msgs = parse_multimodal_messages(text)
        md_msgs = [m for m in msgs if m.provider_format == "markdown"]
        assert len(md_msgs) == 3

    def test_parse_unsupported_format_local_file(self):
        text = 'src="./data/file.tiff"'
        msgs = parse_multimodal_messages(text)
        local_msgs = [m for m in msgs if m.provider_format == "local_file"]
        assert len(local_msgs) == 0

    def test_parse_image_with_url_param(self):
        text = 'url="https://example.com/img.png"'
        msgs = parse_multimodal_messages(text)
        local_msgs = [m for m in msgs if m.provider_format == "local_file"]
        assert len(local_msgs) == 1


class TestEstimateImageTokens:
    def test_low_detail_returns_85(self):
        assert estimate_image_tokens(1920, 1080, "low") == 85

    def test_high_detail_small_image(self):
        tokens = estimate_image_tokens(256, 256, "high")
        assert tokens == 85 + 170 * 1 * 1

    def test_high_detail_large_image(self):
        tokens = estimate_image_tokens(2048, 2048, "high")
        tiles = 4 * 4
        assert tokens == 85 + 170 * tiles

    def test_auto_detail_small_image(self):
        tokens = estimate_image_tokens(300, 200, "auto")
        assert tokens == 85

    def test_auto_detail_large_image_scaled(self):
        tokens = estimate_image_tokens(4096, 4096, "auto")
        assert tokens > 85

    def test_auto_detail_medium_image(self):
        tokens = estimate_image_tokens(1024, 1024, "auto")
        expected_tiles = 2 * 2
        assert tokens == 85 + 170 * expected_tiles

    def test_auto_detail_tall_image(self):
        tokens = estimate_image_tokens(512, 1536, "auto")
        tiles_h = 3
        assert tokens == 85 + 170 * tiles_h


class TestCheckMultimodalPrompt:
    def test_no_images_returns_empty(self):
        findings = check_multimodal_prompt("纯文本提示词")
        assert len(findings) == 0

    def test_detects_images_info(self):
        text = "![描述](photo.png)"
        findings = check_multimodal_prompt(text)
        info_findings = [f for f in findings if f.rule_id == "MM-001"]
        assert len(info_findings) == 1
        assert "1" in info_findings[0].description

    def test_mm002_missing_alt_text(self):
        text = "![](photo.png)"
        findings = check_multimodal_prompt(text)
        mm002 = [f for f in findings if f.rule_id == "MM-002"]
        assert len(mm002) == 1
        assert mm002[0].severity == Severity.LOW

    def test_mm002_with_alt_text_passes(self):
        text = "![这是描述](photo.png)"
        findings = check_multimodal_prompt(text)
        mm002 = [f for f in findings if f.rule_id == "MM-002"]
        assert len(mm002) == 0

    def test_mm003_unsupported_format(self):
        text = "![图](photo.tiff)"
        findings = check_multimodal_prompt(text)
        mm003 = [f for f in findings if f.rule_id == "MM-003"]
        assert len(mm003) == 1
        assert mm003[0].severity == Severity.MEDIUM

    def test_mm004_http_url(self):
        text = '![图](http://example.com/photo.png)'
        findings = check_multimodal_prompt(text)
        mm004 = [f for f in findings if f.rule_id == "MM-004"]
        assert len(mm004) == 1
        assert mm004[0].severity == Severity.MEDIUM

    def test_mm005_local_file_reference(self):
        text = 'src="./images/photo.png"'
        findings = check_multimodal_prompt(text)
        mm005 = [f for f in findings if f.rule_id == "MM-005"]
        assert len(mm005) == 1
        assert mm005[0].severity == Severity.HIGH

    def test_mm006_too_many_images(self):
        parts = [f"![图{i}](img{i}.png)" for i in range(12)]
        text = " ".join(parts)
        findings = check_multimodal_prompt(text)
        mm006 = [f for f in findings if f.rule_id == "MM-006"]
        assert len(mm006) == 1
        assert "12" in mm006[0].description

    def test_mm007_missing_text_description(self):
        text = "![图](photo.png)"
        findings = check_multimodal_prompt(text)
        mm007 = [f for f in findings if f.rule_id == "MM-007"]
        assert len(mm007) == 1
        assert mm007[0].severity == Severity.MEDIUM

    def test_mm007_with_sufficient_text_passes(self):
        text = "请分析这张图片中的物体和场景，给出详细描述 ![图](photo.png)"
        findings = check_multimodal_prompt(text)
        mm007 = [f for f in findings if f.rule_id == "MM-007"]
        assert len(mm007) == 0

    def test_openai_format_detection(self):
        text = '{"url":"https://example.com/img.jpg"}'
        findings = check_multimodal_prompt(text, provider="openai")
        mm001 = [f for f in findings if f.rule_id == "MM-001"]
        assert len(mm001) == 1

    def test_combined_markdown_and_local_file(self):
        text = "![描述](https://example.com/photo.png) 和 src='./local/img.jpg'"
        findings = check_multimodal_prompt(text)
        mm005 = [f for f in findings if f.rule_id == "MM-005"]
        assert len(mm005) == 1
