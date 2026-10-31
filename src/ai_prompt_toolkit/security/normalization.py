"""T1-2 (R356) + R357 完成：检测输入归一化。

T1-1 取证（P3-38, R355）：全角（NFKC 可归一）+ 零宽插入 U+200B = 2 独立
归一化面均静默 → 漏检红证据成立。R356 立规=检测 pipeline 入口归一化
（defender.defend / InjectionDetector.detect），范围=检测面, 不动 lint 侧规则面。

R357 对抗性审查完成（R356 首版 5 字符集=武断子集, 攻击者以同块字符替代即逃逸）：
按 Unicode 语义分类, 非自选集——
  ① NFKC：全角→半角、兼容性组合
  ② Unicode tag 解码（U+E0000-E007F → ASCII 1:1）：tag 块有编码语义,
     剥离=销毁证据=新漏检面（malskanner unicode-tag-smuggling 首条规则面）;
     解码=DECODED 层同范式（与 base64/URL/hex 一致：还原原文再走既有规则）
  ③ Cf (Format) 类完整剥离（Unicode 属性类, 排除 tag 块）：零宽/双向控制
     （Trojan Source 面）/软连字符/词连接符等全部不可见格式字符
行计数不变性：三阶均不引入/移除换行 → 行号天然正确
（test_r356_unicode_normalization.py + test_r357_normalization_cf.py 钉死）。
"""

from __future__ import annotations

import re
import unicodedata

# ② Unicode tag 块（U+E0000-E007F）：序列以 U+E0000（tag first）开头,
#    每个 tag 字符 U+E0000+b ↔ 字节 b（1:1, malskanner unicode-tag-smuggling 面）;
#    U+E007F（tag last）为序列终止符。无效序列（无 U+E0000 头）按不可见垃圾剥离。
_TAG_RE = re.compile("[\U000e0000-\U000e007f]+")


def _decode_tags(text: str) -> str:
    """Unicode tag 序列解码（有编码语义, 不可剥离）：还原为 ASCII 再走规则层。"""

    def _sub(m: re.Match[str]) -> str:
        # Unicode tag 标准语义：tag last（U+E007F）分隔序列, 其后的
        # tag first 开启新序列 → 按 E007F 分段, 每段独立解码;
        # 无 tag first 头的段=无效, 按不可见垃圾剥离。
        out = []
        for part in m.group(0).split("\U000e007f"):
            if part.startswith("\U000e0000"):
                out.append("".join(chr(ord(ch) - 0xE0000) for ch in part[1:]))
        return "".join(out)

    return _TAG_RE.sub(_sub, text)


# ③ Cf (Format) 完整字符类——从 Unicode 数据库生成（2026-10-30, Cf 共 170 码点
#    21 区间, 已排除 tag 块 U+E0000-E007F：tag 有编码语义, 归 ② 解码类）。
#    一致性由 test_r357_normalization_cf.py::test_cf_charclass_matches_unicode 钉死
#    （类内每码点=Cf 且 0x30000 以下每 Cf 码点入类; Unicode 升级新增 Cf=测试红=重生成）。
_CF_RE = re.compile(
    "[\u00ad\u0600-\u0605\u061c\u06dd\u070f\u0890-\u0891\u08e2"
    "\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u206f"
    "\ufeff\ufff9-\ufffb"
    "\U000110bd\U000110cd\U00013430-\U0001343f"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a]"
)


def normalize_for_detection(text: str) -> str:
    """检测输入归一化：NFKC + Unicode tag 解码 + Cf 完整剥离。

    ASCII 短路：NFKC 对 ASCII 子集恒等, 且 tag/Cf 全部非 ASCII → ASCII
    文本直接返回原串（isascii 为 C 层 O(n) 扫描, 1.8MB 级目标 <5ms）。
    无短路时 1.8MB NFKC 实测开销数秒, 负载下击穿 lint 60s 单目标上限
    （R343-RE-1, R356 全量 pytest 实证回归）。
    非 ASCII 文本走三阶（均单趟 O(n)）。
    """
    if text.isascii():
        return text
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _decode_tags(normalized)
    return _CF_RE.sub("", normalized)
