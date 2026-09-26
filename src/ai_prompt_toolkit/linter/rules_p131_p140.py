"""Lint规则集扩展——P131-P140 多模态Prompt专项规则

R67新增(多模态Prompt安全与质量):
- P131: 多模态输入声明缺失 — 检测多模态Prompt是否声明输入模态类型
- P132: 图像安全校验缺失 — 检测涉及图像输入的Prompt是否声明图像安全校验
- P133: 音频内容过滤缺失 — 检测涉及音频输入的Prompt是否声明内容过滤
- P134: 跨模态一致性声明缺失 — 检测多模态Prompt是否声明跨模态输出一致性
- P135: 多模态Token预算缺失 — 检测多模态Prompt是否声明Token/资源预算限制
- P136: 多模态降级策略缺失 — 检测多模态Prompt是否声明模态降级/回退策略
- P137: 多模态输出格式规范缺失 — 检测多模态Prompt是否声明输出格式规范
- P138: 多模态链式攻击防护缺失 — 检测多模态Prompt是否声明跨模态组合攻击防护
- P139: 多模态数据隔离缺失 — 检测多模态Prompt是否声明模态间数据隔离
- P140: 多模态审计追踪缺失 — 检测多模态Prompt是否声明多模态审计追踪
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P131_P140: list[LintRule] = [
    LintRule(
        "P131",
        "多模态输入声明缺失",
        "structure",
        Severity.HIGH,
        "多模态Prompt未声明输入模态类型(文本/图像/音频/视频)",
        "声明输入模态: '接受文本和图像输入, 图像格式支持PNG/JPEG/WebP, 最大10MB'",
        description_en="Multimodal Prompt missing input modality type declaration",
        remediation_en="Declare input modalities: 'Accept text and image input, image format PNG/JPEG/WebP, max 10MB'",
        family="multimodal_input",
    ),
    LintRule(
        "P132",
        "图像安全校验缺失",
        "security",
        Severity.HIGH,
        "涉及图像输入的Prompt未声明图像安全校验(NSFW/恶意内容/隐写检测)",
        "声明图像安全: '对输入图像进行NSFW检测、恶意内容扫描、隐写术检测、EXIF元数据清理'",
        description_en="Image-input Prompt missing image safety validation (NSFW/malicious/steganography detection)",
        remediation_en="Declare image safety: 'Perform NSFW detection, malicious content scanning, steganography detection, EXIF metadata cleaning on input images'",
        family="image_safety",
    ),
    LintRule(
        "P133",
        "音频内容过滤缺失",
        "security",
        Severity.HIGH,
        "涉及音频输入的Prompt未声明音频内容过滤(隐藏指令/超声频段/语音注入)",
        "声明音频过滤: '对音频输入进行ASR转录审核、超声频段检测、隐藏指令识别、语音注入防护'",
        description_en="Audio-input Prompt missing audio content filtering (hidden instructions/ultrasonic/voice injection)",
        remediation_en="Declare audio filtering: 'Perform ASR transcription audit, ultrasonic frequency detection, hidden instruction identification, voice injection prevention'",
        family="audio_safety",
    ),
    LintRule(
        "P134",
        "跨模态一致性声明缺失",
        "quality",
        Severity.MEDIUM,
        "多模态Prompt未声明跨模态输出一致性校验(图像描述与文本描述是否一致)",
        "声明一致性校验: '确保图像描述与文本描述语义一致, 跨模态信息不矛盾, 实施一致性验证'",
        description_en="Multimodal Prompt missing cross-modal output consistency validation",
        remediation_en="Declare consistency: 'Ensure image description aligns with text description semantically, no cross-modal contradictions, implement consistency verification'",
        family="cross_modal_consistency",
    ),
    LintRule(
        "P135",
        "多模态Token预算缺失",
        "performance",
        Severity.MEDIUM,
        "多模态Prompt未声明Token/资源预算限制(图像Token消耗/音频处理时间)",
        "声明Token预算: '图像Token上限4096, 音频时长上限60秒, 总Token预算8192, 超出截断处理'",
        description_en="Multimodal Prompt missing token/resource budget limits",
        remediation_en="Declare token budget: 'Image token limit 4096, audio duration limit 60s, total token budget 8192, truncate if exceeded'",
        family="multimodal_budget",
    ),
    LintRule(
        "P136",
        "多模态降级策略缺失",
        "structure",
        Severity.MEDIUM,
        "多模态Prompt未声明模态降级/回退策略(图像不可用时的文本回退)",
        "声明降级策略: '图像不可用时回退到文本描述, 音频处理失败时使用字幕, 模态缺失时明确告知用户'",
        description_en="Multimodal Prompt missing modal degradation/fallback strategy",
        remediation_en="Declare fallback: 'Fall back to text description when image unavailable, use subtitles when audio processing fails, notify user when modality is missing'",
        family="modal_fallback",
    ),
    LintRule(
        "P137",
        "多模态输出格式规范缺失",
        "structure",
        Severity.MEDIUM,
        "多模态Prompt未声明输出格式规范(图像输出尺寸/格式/质量/音频输出参数)",
        "声明输出格式: '图像输出PNG格式最大2048x2048, 音频输出WAV/16kHz, 文本输出Markdown结构化'",
        description_en="Multimodal Prompt missing output format specification",
        remediation_en="Declare output format: 'Image output PNG max 2048x2048, audio output WAV/16kHz, text output structured Markdown'",
        family="multimodal_output_format",
    ),
    LintRule(
        "P138",
        "多模态链式攻击防护缺失",
        "security",
        Severity.HIGH,
        "多模态Prompt未声明跨模态组合攻击防护(图像注入+文本泄露/音频注入+越狱)",
        "声明链式防护: '检测跨模态组合攻击, 图像嵌入文本需审核, 音频隐藏指令需过滤, 防止编码绕过'",
        description_en="Multimodal Prompt missing cross-modal chain attack prevention",
        remediation_en="Declare chain prevention: 'Detect cross-modal combined attacks, audit embedded text in images, filter hidden audio instructions, prevent encoding bypass'",
        family="chain_attack_prevention",
    ),
    LintRule(
        "P139",
        "多模态数据隔离缺失",
        "security",
        Severity.HIGH,
        "多模态Prompt未声明模态间数据隔离(防止跨模态信息泄露/敏感数据通过图像外泄)",
        "声明数据隔离: '模态间数据隔离处理, 禁止将文本敏感信息编码到图像/音频, 防止跨模态数据泄露'",
        description_en="Multimodal Prompt missing cross-modal data isolation",
        remediation_en="Declare data isolation: 'Process data with modal isolation, prohibit encoding text sensitive info into image/audio, prevent cross-modal data leakage'",
        family="modal_data_isolation",
    ),
    LintRule(
        "P140",
        "多模态审计追踪缺失",
        "security",
        Severity.MEDIUM,
        "多模态Prompt未声明多模态审计追踪(记录各模态输入/输出/决策过程)",
        "声明审计追踪: '记录各模态输入哈希、输出摘要、模态转换决策, 支持多模态审计回溯'",
        description_en="Multimodal Prompt missing multimodal audit trail",
        remediation_en="Declare audit trail: 'Record input hash per modality, output summary, modality conversion decisions, support multimodal audit traceability'",
        family="multimodal_audit",
    ),
]

for r in _RULES_P131_P140:
    _RULE_MAP[r.rule_id] = r


_MULTIMODAL_CTX = re.compile(
    r"(?:多模态|multimodal|图像|image|图片|photo|音频|audio|语音|voice|视频|video|视觉|vision|跨模态|cross.?modal)",
    re.IGNORECASE,
)

_INPUT_MODALITY_DECL = re.compile(
    r"(?:输入.*模态|input.*modality|接受.*图像|accept.*image|支持.*音频|support.*audio|输入.*格式|input.*format|模态.*类型|modality.*type)",
    re.IGNORECASE,
)


def check_p131(text: str) -> Finding | None:
    rule = _RULE_MAP["P131"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _INPUT_MODALITY_DECL.search(text):
        return None
    _SPECIFIC_MODALITY = re.compile(
        r"(?:图像|image|图片|photo|音频|audio|语音|voice|视频|video|视觉|vision)", re.IGNORECASE
    )
    if not _SPECIFIC_MODALITY.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_IMAGE_SAFETY_DECL = re.compile(
    r"(?:NSFW|安全.*校验|safety.*check|恶意.*检测|malicious.*detect|隐写|steganograph|EXIF|元数据.*清理|metadata.*clean|内容.*审核|content.*moderat)",
    re.IGNORECASE,
)


def check_p132(text: str) -> Finding | None:
    rule = _RULE_MAP["P132"]
    _IMAGE_CTX = re.compile(r"(?:图像|image|图片|photo|视觉|vision|截图|screenshot)", re.IGNORECASE)
    if not _IMAGE_CTX.search(text):
        return None
    if _IMAGE_SAFETY_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_AUDIO_SAFETY_DECL = re.compile(
    r"(?:ASR|转录.*审核|transcription.*audit|超声|ultrasonic|隐藏.*指令|hidden.*instruction|语音.*注入|voice.*inject|音频.*过滤|audio.*filter)",
    re.IGNORECASE,
)


def check_p133(text: str) -> Finding | None:
    rule = _RULE_MAP["P133"]
    _AUDIO_CTX = re.compile(
        r"(?:音频|audio|语音|voice|声音|声纹|声学|超声|次声|sound|录音|recording|ASR|转录|transcri)", re.IGNORECASE
    )
    if not _AUDIO_CTX.search(text):
        return None
    if _AUDIO_SAFETY_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_CONSISTENCY_DECL = re.compile(
    r"(?:一致性|consistency|校验.*一致|verify.*consist|跨模态.*一致|cross.?modal.*consist|不矛盾|no.*contradict|语义.*对齐|semantic.*align)",
    re.IGNORECASE,
)


def check_p134(text: str) -> Finding | None:
    rule = _RULE_MAP["P134"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _CONSISTENCY_DECL.search(text):
        return None
    _MULTI_OUTPUT = re.compile(
        r"(?:输出.*图像|output.*image|生成.*图片|generate.*image|描述.*图片|describe.*image|图像.*描述|image.*description)",
        re.IGNORECASE,
    )
    if not _MULTI_OUTPUT.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_BUDGET_DECL = re.compile(
    r"(?:Token.*上限|token.*limit|Token.*预算|token.*budget|资源.*限制|resource.*limit|图像.*Token|image.*token|音频.*时长|audio.*duration|截断|truncat)",
    re.IGNORECASE,
)


def check_p135(text: str) -> Finding | None:
    rule = _RULE_MAP["P135"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _BUDGET_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_FALLBACK_DECL = re.compile(
    r"(?:降级|degradat|回退|fallback|不可用|unavail|失败.*回退|fail.*fallback|替代|alternat|模态.*缺失|modality.*missing)",
    re.IGNORECASE,
)


def check_p136(text: str) -> Finding | None:
    rule = _RULE_MAP["P136"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _FALLBACK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_OUTPUT_FORMAT_DECL = re.compile(
    r"(?:输出.*格式|output.*format|图像.*输出|image.*output|音频.*输出|audio.*output|PNG|JPEG|WAV|MP3|分辨率|resolution|采样率|sample.?rate)",
    re.IGNORECASE,
)


def check_p137(text: str) -> Finding | None:
    rule = _RULE_MAP["P137"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _OUTPUT_FORMAT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_CHAIN_ATTACK_DECL = re.compile(
    r"(?:链式.*攻击|chain.*attack|组合.*攻击|combined.*attack|跨模态.*注入|cross.?modal.*inject|嵌入.*文本|embed.*text|隐藏.*指令|hidden.*instruction|编码.*绕过|encoding.*bypass)",
    re.IGNORECASE,
)


def check_p138(text: str) -> Finding | None:
    rule = _RULE_MAP["P138"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _CHAIN_ATTACK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_DATA_ISOLATION_DECL = re.compile(
    r"(?:数据.*隔离|data.*isolat|模态.*隔离|modality.*isolat|禁止.*编码|prohibit.*encode|跨模态.*泄露|cross.?modal.*leak|敏感.*编码|sensitive.*encode)",
    re.IGNORECASE,
)


def check_p139(text: str) -> Finding | None:
    rule = _RULE_MAP["P139"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _DATA_ISOLATION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_AUDIT_DECL = re.compile(
    r"(?:审计|audit|追踪|trace|回溯|traceab|输入.*哈希|input.*hash|输出.*摘要|output.*summary|模态.*转换|modality.*convert|决策.*记录|decision.*log)",
    re.IGNORECASE,
)


def check_p140(text: str) -> Finding | None:
    rule = _RULE_MAP["P140"]
    if not _MULTIMODAL_CTX.search(text):
        return None
    if _AUDIT_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )
