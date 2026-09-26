"""多模态Token计数器 — 参考OpenAI multimodal token pricing

支持的模态:
- 文本Token: tiktoken/字符估算
- 图像Token: 基于分辨率计算(低/中/高细节)
- 音频Token: 基于时长计算(Whisper格式)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenBudget:
    text_tokens: int = 0
    image_tokens: int = 0
    audio_tokens: int = 0
    video_tokens: int = 0
    max_total: int = 8192

    @property
    def total(self) -> int:
        return self.text_tokens + self.image_tokens + self.audio_tokens + self.video_tokens

    @property
    def remaining(self) -> int:
        return max(0, self.max_total - self.total)

    @property
    def usage_ratio(self) -> float:
        return self.total / self.max_total if self.max_total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_tokens": self.text_tokens,
            "image_tokens": self.image_tokens,
            "audio_tokens": self.audio_tokens,
            "video_tokens": self.video_tokens,
            "total_tokens": self.total,
            "max_total": self.max_total,
            "remaining": self.remaining,
            "usage_ratio": round(self.usage_ratio, 4),
        }


def estimate_text_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        import tiktoken

        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def estimate_image_tokens(width: int, height: int, detail: str = "auto") -> int:
    if detail == "low":
        return 85
    max_dim = 2048
    min_dim = 768
    w = min(width, max_dim)
    h = min(height, max_dim)
    if detail == "high":
        scale = min_dim / max(w, h) if max(w, h) > min_dim else 1.0
        scaled_w = int(w * scale)
        scaled_h = int(h * scale)
        tiles_w = (scaled_w + 511) // 512
        tiles_h = (scaled_h + 511) // 512
        return 85 + tiles_w * tiles_h * 170
    return 85


def estimate_audio_tokens(duration_seconds: float) -> int:
    return int(duration_seconds * 150)


def estimate_video_tokens(duration_seconds: float, fps: int = 1) -> int:
    frames = int(duration_seconds * fps)
    return frames * 85


class MultimodalTokenCounter:
    def __init__(self, max_total: int = 8192) -> None:
        self.budget = TokenBudget(max_total=max_total)

    def count_text(self, text: str, model: str = "gpt-4") -> int:
        tokens = estimate_text_tokens(text, model)
        self.budget.text_tokens += tokens
        return tokens

    def count_image(self, width: int, height: int, detail: str = "auto") -> int:
        tokens = estimate_image_tokens(width, height, detail)
        self.budget.image_tokens += tokens
        return tokens

    def count_audio(self, duration_seconds: float) -> int:
        tokens = estimate_audio_tokens(duration_seconds)
        self.budget.audio_tokens += tokens
        return tokens

    def count_video(self, duration_seconds: float, fps: int = 1) -> int:
        tokens = estimate_video_tokens(duration_seconds, fps)
        self.budget.video_tokens += tokens
        return tokens

    def get_budget(self) -> TokenBudget:
        return self.budget

    def reset(self) -> None:
        max_total = self.budget.max_total
        self.budget = TokenBudget(max_total=max_total)

    def check_within_budget(self) -> bool:
        return self.budget.total <= self.budget.max_total
