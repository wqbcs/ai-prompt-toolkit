r"""P268 全角字母注入 bypass 面（R293, P2-29 规则化: R286 ja 面缺口 + 4 独立真实 TP 取证）

痛点（R286 观察探针取证 + R293 互联网调查 4 独立真实 TP, 02 P2-29）:
「Ignore all instructions & rules」全角化（U+FF21-FF5A）在 267 规则零覆盖
（r286_ja_obs_fullwidth_bypass 实测仅质量规则实火）——全角字母是英文检测
工具的系统性盲点（zenn nexus_api_lab）, 日语特有攻击面（JSAI2026 pattern③
全角/半角混用）。R293 取证 4 独立真实 TP:
 1. tinyhumansai/openhuman PR #2067 (2026-05): 生产修复 — 全角
    `ｉｇｎｏｒｅ ａｌｌ ｐｒｅｖｉｏｕｓ ｉｎｓｔｒｕｃｔｉｏｎｓ` "passed all regex rules
    unmodified", 对策=fullwidth_to_ascii（U+FF01-FF5E 减 0xFEE0）
 2. ClawGuard 12 evasion techniques (2026-03, 引 arXiv 2602.00750):
    全角 Unicode 为 12 技术之 #7, 对策=_normalize_fullwidth（NFKC）
 3. arXiv 2504.11168 (2025-07): "Full Width Text" 对 6 家 guardrail 的
    规避矩阵实测（ASR 0-100% 因产品而异）
 4. arXiv 2508.14070 (2025-08): "fullwidth alternative attacks
    (U+FF00-U+FFEF)" 字符级对抗攻击面综述
行业共识对策=NFKC 归一化后再匹配（openhuman/ClawGuard/AWS/paultendo 四源
同型）— 本规则是该共识的确定性静态实现（零 LLM 楔子内, 无 NFKC 依赖,
unicodedata 标准库）。

辖区切分（与既有规则不重叠, 02 反清单纪律）:
- **与 P260 sub4（同形异码 西里尔/Greek 骨架）正交**: P260 sub4 管跨脚本
  视觉同形（U+0400-04FF/U+0370-03FF 混入 gn?re 骨架）, P268 管全角块
  （U+FF21-FF5A）字符替换 — 不同码区/不同信源（ATR 未覆盖全角面）/不同
  对策（NFKC 可逆归一化 vs 同形字表映射）。先例: 零宽族 P260(5+连续)/
  P261(3+交错) 同族不同形态分规则 — 本规则同族(encoding_evasion)不同
  形态独立编号
- **全角数字/假名不报**: 码区限定 U+FF21-FF5A（全角拉丁字母块）, 全角
  数字 U+FF10-FF19 与假名天然排除（r286_ja_tn_fullwidth_benign 锚）
- **ASCII 原文不报**: 本规则只匹配全角字符连续段 — 纯 ASCII 注入文本归
  既有 267 规则辖区（避免双报, FP 门禁面不扩）

精度设计（确定性+低误报是命根, 01 §2）:
- 形态=「全角拉丁字母连续段 → NFKC 解码 → 精确命中有限注入动词集」:
  良性全角拉丁（日语 ＯＫ/ＮＧ 惯例）解码后不命中动词集 → 沉默
  （r293_ja_tn_fullwidth_okng 锚）
- 动词集 6 词全有实证出处（不自调）: ignore/disregard/override/forget/
  bypass = P260 sub2 base64 片段集解码词表（ATR-2026-00001 L11 实证值）,
  jailbreak = P163 越狱族 — 裸名词（instructions/rules）不入集, 防良性
  全角英文词 FP
- **精确词匹配**（word == keyword）, 零长度容差: 长词内嵌（如 forgetful
  含 forget）与无空格连写（ignoreallprevious）均不报 — 取证 4/4 实证形态
  为空格分隔短语, 精度优先（P267 同纪律）
- 已知残留（诚实声明, 机制上限, 与 P260 诚实声明同型）:
  ① 关键词内全角/ASCII 混写（ｉｇnｏｒｅ）不报 — 连续段被 ASCII 打断;
  ② 动词集外的全角注入短语（如全角 "reveal system prompt"）不报 —
  有限集方案对未知形态必然漏检

ReDoS 线性: 单字符类+量词, 无嵌套量词/重叠星号（P3-05 审计形态）

OWASP: LLM01 Prompt Injection（与同族 P260/P261 一致, garak 编码探针族
tag owasp:llm01 印证）
ATLAS: AML.T0015 Evade AI Model（同映射表 P021/P177/P260/P261 行,
docs/mitre-atlas-mapping.md）
"""

from __future__ import annotations

import re
import unicodedata

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P268 = [
    LintRule(
        "P268",
        "全角字母注入bypass面",
        "security",
        Severity.HIGH,
        "Prompt含全角拉丁字母(U+FF21-FF5A)连续段且NFKC解码后精确命中注入动词"
        "(ignore/disregard/override/forget/bypass/jailbreak) — 全角化=有意"
        "规避英文检测(行业共识对策=NFKC归一化, 本规则为该对策的确定性静态实现)",
        "移除全角字母伪装: 全角注入内容仍按注入处置(改回半角不改变攻击性质); "
        "良性全角拉丁(如日语ＯＫ/ＮＧ)不受本规则影响",
        description_en=(
            "Prompt contains a run of fullwidth Latin letters (U+FF21-FF5A) "
            "that NFKC-decodes exactly to an injection verb (ignore/disregard/"
            "override/forget/bypass/jailbreak) — fullwidth substitution is "
            "deliberate evasion of English detection (the industry consensus "
            "countermeasure is NFKC normalization; this rule is its "
            "deterministic static implementation)"
        ),
        remediation_en=(
            "Remove the fullwidth-letter disguise: a fullwidth injection "
            "payload is still an injection (converting it back to halfwidth "
            "does not change its nature); legitimate fullwidth Latin "
            "(e.g. Japanese OK/NG) is not affected by this rule"
        ),
        family="encoding_evasion",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P268:
    _RULE_MAP[r.rule_id] = r

# 全角拉丁字母块: U+FF21-FF3A (A-Z) + U+FF41-FF5A (a-z)。全角数字
# U+FF10-FF19 / 全角符号 U+FF01-FF1F / 假名均不在内 — TN 天然安全
_FW_RUN_RE = re.compile(r"[\uFF21-\uFF3A\uFF41-\uFF5A]+")

# 注入动词有限集 — 全部实证出处（不自调）:
# ignore/disregard/override/forget/bypass = P260 sub2 base64 片段解码词表
# (ATR-2026-00001 L11); jailbreak = P163 越狱族
_FW_KEYWORDS = frozenset({"ignore", "disregard", "override", "forget", "bypass", "jailbreak"})


def check_p268(text: str) -> Finding | None:
    rule = _RULE_MAP["P268"]
    for m in _FW_RUN_RE.finditer(text):
        word = unicodedata.normalize("NFKC", m.group(0)).lower()
        if word in _FW_KEYWORDS:
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                # R218: location 契约单一入口（1-based line:col, 注入/编码最高价值面）
                location=loc_from_match(text, m),
                remediation=rule.remediation,
                details={"decoded": word, "match": m.group(0)[:40]},
            )
    return None
