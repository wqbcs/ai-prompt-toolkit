"""多模态Prompt Lint模块

市场空白: 图片+文本混合Prompt目前缺乏专门的lint工具
参考: agentic_security(图片模态扫描), prompt-optimizer(T2I/I2I优化)

核心能力:
1. 多模态消息结构校验: OpenAI/Claude/Gemini格式
2. 图片URL/文件引用验证: 检测无效引用
3. 图片尺寸/格式约束检查
4. 多模态Token估算: 图片token消耗计算
5. Alt文本/描述完整性检查
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity

_OPENAI_IMAGE_URL_PATTERN = re.compile(r'"url"\s*:\s*"https?://[^\"]+\.(png|jpg|jpeg|gif|webp|bmp)', re.IGNORECASE)
_OPENAI_IMAGE_DETAIL_PATTERN = re.compile(r'"detail"\s*:\s*"(auto|low|high)"', re.IGNORECASE)
_CLAUDE_IMAGE_PATTERN = re.compile(r'"type"\s*:\s*"image".*?"source"\s*:\s*\{.*?"type"\s*:\s*"base64"', re.DOTALL)
_GEMINI_INLINE_DATA_PATTERN = re.compile(r'"inline_data"\s*:\s*\{.*?"mime_type"\s*:\s*"(image/\w+)"', re.DOTALL)
_LOCAL_FILE_PATTERN = re.compile(
    r'(src|href|url|path|file)\s*[=:]\s*["\']?([^\s"\']+\.(png|jpg|jpeg|gif|webp|svg|bmp))["\']?',
    re.IGNORECASE,
)
_MARKDOWN_IMAGE_PATTERN = re.compile(
    r"!\[([^\]]*)\]\(([^)]+)\)",
)
_IMAGE_SIZE_CONSTRAINTS = {
    "openai": {"min_px": 1, "max_px": 20_971_520},
    "claude": {"min_px": 1, "max_px": 8_000_000},
    "gemini": {"min_px": 1, "max_px": 10_485_760},
}
_SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"}


@dataclass
class MultimodalMessage:
    role: str
    content_type: str
    text: str = ""
    image_url: str = ""
    image_format: str = ""
    alt_text: str = ""
    detail: str = "auto"
    provider_format: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content_type": self.content_type,
            "text": self.text[:100] if self.text else "",
            "image_url": self.image_url[:100] if self.image_url else "",
            "image_format": self.image_format,
            "alt_text": self.alt_text[:50] if self.alt_text else "",
            "detail": self.detail,
            "provider_format": self.provider_format,
        }


def parse_multimodal_messages(text: str) -> list[MultimodalMessage]:
    messages: list[MultimodalMessage] = []
    md_images = _MARKDOWN_IMAGE_PATTERN.findall(text)
    for alt, url in md_images:
        fmt = url.rsplit(".", 1)[-1].lower() if "." in url else "unknown"
        messages.append(
            MultimodalMessage(
                role="user",
                content_type="image",
                image_url=url,
                image_format=fmt,
                alt_text=alt,
                provider_format="markdown",
            )
        )

    for match in _OPENAI_IMAGE_URL_PATTERN.finditer(text):
        url_start = max(0, match.start() - 200)
        context = text[url_start : match.end() + 50]
        detail_match = _OPENAI_IMAGE_DETAIL_PATTERN.search(context)
        detail = detail_match.group(1) if detail_match else "auto"
        messages.append(
            MultimodalMessage(
                role="user",
                content_type="image",
                image_url=match.group(0),
                image_format=match.group(1).lower(),
                detail=detail,
                provider_format="openai",
            )
        )

    for _match in _CLAUDE_IMAGE_PATTERN.finditer(text):
        messages.append(
            MultimodalMessage(
                role="user",
                content_type="image",
                image_format="base64",
                provider_format="claude",
            )
        )

    for match in _GEMINI_INLINE_DATA_PATTERN.finditer(text):
        mime = match.group(1)
        fmt = mime.split("/")[-1] if "/" in mime else "unknown"
        messages.append(
            MultimodalMessage(
                role="user",
                content_type="image",
                image_format=fmt,
                provider_format="gemini",
            )
        )

    for match in _LOCAL_FILE_PATTERN.finditer(text):
        fmt = match.group(3).lower()
        if fmt in _SUPPORTED_FORMATS:
            messages.append(
                MultimodalMessage(
                    role="user",
                    content_type="image",
                    image_url=match.group(2),
                    image_format=fmt,
                    provider_format="local_file",
                )
            )

    return messages


def estimate_image_tokens(width: int, height: int, detail: str = "auto") -> int:
    if detail == "low":
        return 85
    if detail == "high":
        tiles_w = max(1, (width + 511) // 512)
        tiles_h = max(1, (height + 511) // 512)
        return 85 + 170 * tiles_w * tiles_h
    if width > 2048 or height > 2048:
        scale = 2048 / max(width, height)
        width, height = int(width * scale), int(height * scale)
    if width <= 512 and height <= 512:
        return 85
    tiles_w = max(1, (width + 511) // 512)
    tiles_h = max(1, (height + 511) // 512)
    return 85 + 170 * tiles_w * tiles_h


def check_multimodal_prompt(text: str, provider: str = "openai") -> list[Finding]:
    findings: list[Finding] = []
    messages = parse_multimodal_messages(text)

    if not messages:
        return findings

    findings.append(
        Finding(
            rule_id="MM-001",
            severity=Severity.INFO,
            description=f"检测到{len(messages)}个多模态元素(图片)",
        )
    )

    for i, msg in enumerate(messages):
        if msg.content_type == "image":
            if msg.alt_text == "" and msg.provider_format == "markdown":
                findings.append(
                    Finding(
                        rule_id="MM-002",
                        severity=Severity.LOW,
                        description=f"图片#{i + 1}: 缺少Alt文本描述，影响可访问性和模型理解",
                    )
                )

            if msg.image_format not in _SUPPORTED_FORMATS and msg.image_format != "base64":
                findings.append(
                    Finding(
                        rule_id="MM-003",
                        severity=Severity.MEDIUM,
                        description=f"图片#{i + 1}: 不支持的图片格式'{msg.image_format}'，推荐png/jpg/webp",
                    )
                )

            if msg.image_url and msg.image_url.startswith("http://"):
                findings.append(
                    Finding(
                        rule_id="MM-004",
                        severity=Severity.MEDIUM,
                        description=f"图片#{i + 1}: 使用HTTP而非HTTPS，可能存在安全风险",
                    )
                )

            if msg.provider_format == "local_file":
                findings.append(
                    Finding(
                        rule_id="MM-005",
                        severity=Severity.HIGH,
                        description=f"图片#{i + 1}: 引用本地文件'{msg.image_url[:50]}'，API调用时无法访问",
                    )
                )

    text_only_len = len(re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text))
    image_count = len([m for m in messages if m.content_type == "image"])
    if image_count > 10:
        findings.append(
            Finding(
                rule_id="MM-006",
                severity=Severity.MEDIUM,
                description=f"图片数量过多({image_count}张)，建议<=10张以控制成本和延迟",
            )
        )

    if text_only_len < 20 and image_count > 0:
        findings.append(
            Finding(
                rule_id="MM-007",
                severity=Severity.MEDIUM,
                description="多模态Prompt缺少文字描述，图片需配文字说明以提升模型理解",
            )
        )

    return findings
