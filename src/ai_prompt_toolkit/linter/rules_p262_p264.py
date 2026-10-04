"""P262-P264 跨模型可移植性规则族（R229, P1-16, 对标 aiproof AIP016-018）

痛点（08 需求调研 + aiproof 竞品信号）：prompt 为某一模型定制后移植到
另一模型时静默劣化——身份绑错模型、确定性要求与随机性要求自相矛盾、
厂商专属对话格式硬编码。三条规则均为**静态可判定的可移植性缺陷**，
不依赖运行时、不依赖 LLM（楔子不变）。

精度设计（确定性+低误报是命根，01 §2）：
- P262 要求"身份标记词与品牌名近邻共现"（±40 字符窗口），不是全 prompt
  任意两处各出现一个——避免"你是数据分析师…(200字)….GPT-4 参考文档"误报
- P263 要求"确定性词集 ∩ 随机性词集同时非空"——单一方向不报
- P264 要求"厂商专属分隔符成对/成组出现"——单个 Human: 不报（普通正文）

category=portability（新类别，无白名单校验约束——rules.py 无 category 枚举门）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P262_P264 = [
    LintRule(
        "P262",
        "跨模型身份绑定",
        "portability",
        Severity.MEDIUM,
        "Prompt将自身身份绑定到特定模型品牌(你是ChatGPT/You are a GPT-4 assistant等) — "
        "移植到其他模型时身份声明失真, 且向模型植入未授权的身份",
        "删除模型品牌名的身份声明, 用能力/角色描述替代(如'你是一个专业代码审查助手'), "
        "模型选择由调用方在API参数指定而非写进prompt正文",
        description_en=(
            "Prompt binds its identity to a specific model brand (e.g. 'You are ChatGPT' / "
            "'You are a GPT-4 assistant') — identity declaration goes stale when ported to "
            "another model and injects an unauthorized identity"
        ),
        remediation_en=(
            "Remove the model-brand identity declaration; describe the role/capability instead "
            "(e.g. 'You are a professional code-review assistant'); select the model via API "
            "parameters, not prompt body"
        ),
        family="cross_model_portability",
    ),
    LintRule(
        "P263",
        "确定性与随机性声明矛盾",
        "portability",
        Severity.MEDIUM,
        "Prompt同时声明确定性/一致性要求(必须一致/可复现/deterministic)与随机性/创造性要求"
        "(随机/creative/多样性) — 两者互斥, 不同模型对矛盾约束的取舍不同, 移植时行为漂移",
        "二选一: 要可复现就删随机性要求并固定temperature=0; 要多样性就删确定性声明。"
        "明确声明预期行为边界, 不靠模型自行调和矛盾",
        description_en=(
            "Prompt declares both determinism/consistency requirements (must be identical / "
            "reproducible / deterministic) and randomness/creativity requirements (random / "
            "creative / diverse) — mutually exclusive; different models resolve the conflict "
            "differently, so behavior drifts when ported"
        ),
        remediation_en=(
            "Pick one: for reproducibility remove the randomness requirement and pin "
            "temperature=0; for diversity remove the determinism declaration. State the "
            "expected behavior boundary explicitly instead of letting the model reconcile"
        ),
        family="cross_model_portability",
    ),
    LintRule(
        "P264",
        "厂商专属对话格式硬编码",
        "portability",
        Severity.LOW,
        "Prompt硬编码厂商专属对话分隔符(Human:/Assistant:、### Instruction:/### Response:、"
        "<|system|>、[INST]等) — 该格式只对特定模型/框架有效, 移植后结构语义丢失",
        "改用调用方消息API的role字段(system/user/assistant)承载对话结构, prompt正文不硬编码厂商分隔符",
        description_en=(
            "Prompt hardcodes vendor-specific chat delimiters (Human:/Assistant:, "
            "'### Instruction:/'### Response:', <|system|>, [INST], etc.) — the format is only "
            "meaningful to one specific model/framework; structural semantics are lost when ported"
        ),
        remediation_en=(
            "Use the API's role fields (system/user/assistant) to carry conversation "
            "structure instead of hardcoding vendor delimiters in the prompt body"
        ),
        family="cross_model_portability",
    ),
]

for r in _RULES_P262_P264:
    _RULE_MAP[r.rule_id] = r

# ── P262: 跨模型身份绑定 ─────────────────────────────────────────────────
# 模型品牌名（大小写不敏感; 中文品牌无大小写问题）
_MODEL_BRANDS = [
    r"GPT-?4[oa]?",
    r"GPT-?3\.?5?",
    r"ChatGPT",
    r"Claude",
    r"Gemini",
    r"PaLM",
    r"LLaMA",
    r"Mistral",
    r"Mixtral",
    r"DeepSeek",
    r"通义",
    r"文心",
    r"ERNIE",
    r"豆包",
    r"Kimi",
    r"Moonshot",
    r"Grok",
]
_BRAND_RE = re.compile("|".join(f"(?:{b})" for b in _MODEL_BRANDS), re.IGNORECASE)
# 身份标记词（品牌名 ±40 字符窗口内出现即命中）
_IDENTITY_MARKER_RE = re.compile(
    r"(?:你是|你身为|作为|充当|扮演|假装是|自称|acting\s+as|pretend(?:ing)?\s+(?:to\s+be|you\s+are)|"
    r"you\s+are\s+(?:a\s+|an\s+|the\s+)?|i\s+am\s+(?:a\s+|an\s+|the\s+)?)",
    re.IGNORECASE,
)
_BRAND_WINDOW = 40


def check_p262(text: str) -> Finding | None:
    rule = _RULE_MAP["P262"]
    # R229: 函数内延迟导入 — rules.py 在 L1427 导入本模块时 strip_frontmatter
    # (L1628 定义)尚未执行到, 顶层导入触发循环导入; P100/P156/P221/P224 同惯例
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    # R229: frontmatter 是资产元数据(model_compatibility 声明)非正文 — 品牌名不
    # 在元数据里做绑定锚点(同 P100/P221/P224 R178 惯例, 复用 strip_frontmatter
    # 边界计算; 不整体剥离以保留原文 location 行号精确性)。修复: 20 个模板
    # C5 误报(元数据品牌名跨 `---` 边界落入正文身份句 ±40 窗口)
    fm_len = len(text) - len(strip_frontmatter(text))
    for bm in _BRAND_RE.finditer(text, fm_len):
        lo = max(0, bm.start() - _BRAND_WINDOW)
        hi = min(len(text), bm.end() + _BRAND_WINDOW)
        if _IDENTITY_MARKER_RE.search(text, lo, hi):
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                location=loc_from_match(text, bm),
                remediation=rule.remediation,
                details={"brand": bm.group(0)},
            )
    return None


# ── P263: 确定性与随机性声明矛盾 ─────────────────────────────────────────
_DETERMINISM_RE = re.compile(
    r"(?:确定性|必须一致|严格一致|完全一致|保持一致|输出一致|相同输出|同一输出|可复现|可重复|复现|"
    r"deterministic|reproducib\w+|consistent(?:\s+output)?|identical\s+output)",
    re.IGNORECASE,
)
_RANDOMNESS_RE = re.compile(
    r"(?:随机|creative(?:ly|s)?|creativity|创造性|创意(?!性?声明)|多样性|diverse\w*|"
    r"random\w*|发挥想象|天马行空|想象力)",
    re.IGNORECASE,
)


def check_p263(text: str) -> Finding | None:
    rule = _RULE_MAP["P263"]
    dm = _DETERMINISM_RE.search(text)
    rm = _RANDOMNESS_RE.search(text)
    if dm and rm:
        # location 取先出现者（矛盾的"第一现场"）
        anchor = dm if dm.start() < rm.start() else rm
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            location=loc_from_match(text, anchor),
            remediation=rule.remediation,
            details={
                "determinism_match": dm.group(0),
                "randomness_match": rm.group(0),
            },
        )
    return None


# ── P264: 厂商专属对话格式硬编码 ─────────────────────────────────────────
# 成对/成组才报（单个 Human: 可能是普通正文）
_VENDOR_FORMATS = (
    ("human_assistant", re.compile(r"Human:\s*\S[^\n]*\n+Assistant:\s*\S", re.IGNORECASE)),
    # R229 ReDoS: 行有界线性形态（每行 [^\n]*\n 确定性消费、外层 {0,40} 行有界，
    # 无嵌套量词/重叠备选 → 线性时间）；0-40 中间行覆盖真实对话格式段落
    (
        "hash_instruction_response",
        re.compile(r"###\s*Instruction:\s*\S[^\n]*\n(?:[^\n]*\n){0,40}###\s*(?:Response|Output):"),
    ),
    ("hash_input_response", re.compile(r"###\s*Input:\s*\S[^\n]*\n(?:[^\n]*\n){0,40}###\s*(?:Response|Output):")),
    ("llama_inst", re.compile(r"\[INST\][^\[\]]*\[/INST\]")),
    ("system_special_tok", re.compile(r"<\|system\|>.*?<\|/system\|>", re.DOTALL)),
    ("eot_bos", re.compile(r"<\|startofprompt\|>|<\|eot_id\|>")),
    ("im_start_end", re.compile(r"<\|im_start\|>.*?<\|im_end\|>", re.DOTALL)),
)


def check_p264(text: str) -> Finding | None:
    rule = _RULE_MAP["P264"]
    for name, pattern in _VENDOR_FORMATS:
        m = pattern.search(text)
        if m:
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                location=loc_from_match(text, m),
                remediation=rule.remediation,
                details={"format": name},
            )
    return None
