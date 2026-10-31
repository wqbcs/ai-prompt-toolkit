"""T1-2 (R356): 检测输入归一化——NFKC + 零宽/格式控制字符剥离。

T1-1 取证（P3-38, R355）：全角（NFKC 可归一）+ 零宽插入 U+200B = 2 独立
归一化面均静默 → 漏检红证据成立。本轮立规=检测 pipeline 入口归一化
（defender.defend / InjectionDetector.detect），范围=检测面, 不动 lint 侧规则面。
行计数不变性：NFKC 与零宽剥离均不引入/移除换行 → 行号天然正确
（test_r356_unicode_normalization.py TestNormalizationProperty 钉死）。
"""

from __future__ import annotations

import re
import unicodedata

# 零宽/格式控制字符：U+200B 零宽空格 / U+200C 零宽非连接符 / U+200D 零宽连接符
# / U+2060 词连接符 / U+FEFF 零宽不换行空格（BOM）
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")


def normalize_for_detection(text: str) -> str:
    """检测输入归一化：NFKC（全角→半角、兼容性分解）+ 零宽字符剥离。

    ASCII 短路：NFKC 对 ASCII 子集是恒等映射, 且全部零宽/格式控制字符
    均为非 ASCII → ASCII 文本直接返回原串（isascii 为 C 层 O(n) 扫描,
    1.8MB 级目标 <5ms）。无短路时 1.8MB NFKC 实测开销数秒, 负载下击穿
    lint 60s 单目标上限（R343-RE-1, R356 全量 pytest 实证回归）。
    非 ASCII 文本走 NFKC + 字符类 sub（均单趟 O(n)）。
    """
    if text.isascii():
        return text
    normalized = unicodedata.normalize("NFKC", text)
    return _ZERO_WIDTH_RE.sub("", normalized)
