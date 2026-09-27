"""P216-P220 多模态安全Lint规则

多模态LLM输入/输出安全最佳实践:
- P216: 图像注入风险(图像prompt包含隐藏指令/对抗样本)
- P217: 音频指令注入(语音输入嵌入不可听指令)
- P218: 跨模态信息泄露(多模态上下文中敏感信息跨模态泄露)
- P219: 模态降级安全(降级到纯文本时丢失安全约束)
- P220: 多模态输出验证(生成图像/音频未做内容审核)

覆盖OWASP LLM06(Excessive Agency) + LLM02(Sensitive Information Disclosure)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P216_P220 = [
    LintRule(
        "P216",
        "图像注入风险",
        "multimodal_security",
        Severity.HIGH,
        "图像输入可能包含隐藏指令/对抗样本, 多模态模型可能执行图像中嵌入的恶意指令",
        "图像预处理: 元数据剥离+对抗检测+内容审核, 如 exif_strip(image) + adversarial_check(image) + nsfw_scan(image)",
        description_en="Image input may contain hidden instructions/adversarial examples, multimodal model may execute embedded malicious commands",
        remediation_en="Image preprocessing: metadata strip+adversarial detection+content moderation",
        family="multimodal_image_injection",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P217",
        "音频指令注入",
        "multimodal_security",
        Severity.HIGH,
        "语音输入可能嵌入人类不可听但模型可解析的隐藏指令(超声波/低频注入)",
        "音频安全: 频谱分析+人类可听范围过滤+ASR置信度校验, 如 filter_freq(audio, 20, 20000) + asr_confidence_check(transcript)",
        description_en="Audio input may embed inaudible but model-parseable hidden instructions (ultrasonic/low-freq injection)",
        remediation_en="Audio safety: spectral analysis+audible range filter+ASR confidence validation",
        family="multimodal_audio_injection",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P218",
        "跨模态信息泄露",
        "multimodal_security",
        Severity.HIGH,
        "多模态上下文中, 一种模态的敏感信息可能通过另一种模态泄露(如图片中的文字被OCR提取)",
        "跨模态隔离: 模态间敏感标注+脱敏传递+访问控制, 如 tag_sensitive(image, 'PII') + redact_before_cross_modal(data)",
        description_en="Sensitive info in one modality may leak through another (e.g., text in image extracted by OCR)",
        remediation_en="Cross-modal isolation: sensitive tagging+redaction propagation+access control between modalities",
        family="multimodal_cross_leak",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P219",
        "模态降级安全",
        "multimodal_security",
        Severity.MEDIUM,
        "降级到纯文本模式时, 原多模态安全约束可能丢失(如图片审核约束在文本模式下不生效)",
        "降级安全: 保留核心约束+降级后重新评估+明确降级边界, 如 assert_constraints_preserved(mode='text', constraints=original)",
        description_en="Degrading to text-only mode may lose multimodal safety constraints",
        remediation_en="Degradation safety: preserve core constraints+re-evaluate after downgrade+explicit degradation boundary",
        family="multimodal_degradation",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P220",
        "多模态输出验证",
        "multimodal_security",
        Severity.HIGH,
        "模型生成图像/音频等输出未经内容审核, 可能包含不当内容/深度伪造",
        "输出审核: 生成内容NSFW检测+深度伪造检测+水印标记, 如 nsfw_check(output) + deepfake_detect(output) + watermark(output)",
        description_en="Model-generated image/audio output lacks content moderation, may contain inappropriate/deepfake content",
        remediation_en="Output moderation: NSFW detection+deepfake detection+watermark tagging on generated content",
        family="multimodal_output_validation",
        owasp_refs=["LLM02"],
    ),
]

for r in _RULES_P216_P220:
    _RULE_MAP[r.rule_id] = r

_IMAGE_PATTERN = re.compile(
    r"(?:image|img|图片|图像|vision|视觉|多模态|multimodal|base64.*image|data:image)", re.IGNORECASE
)
_IMAGE_CHECK_PATTERN = re.compile(
    r"(?:exif.*strip|adversarial.*check|nsfw.*scan|内容审核|content.*moderat|image.*valid|图片.*检测)", re.IGNORECASE
)
_AUDIO_PATTERN = re.compile(r"(?:audio|语音|voice|speech|whisper|asr|声音|录音|转录|transcri)", re.IGNORECASE)
_AUDIO_CHECK_PATTERN = re.compile(
    r"(?:频谱|spectral|可听范围|audible.*range|asr.*confid|音频.*过滤|audio.*filter)", re.IGNORECASE
)
_CROSS_MODAL_PATTERN = re.compile(
    r"(?:跨模态|cross.*modal|多模态.*上下文|multimodal.*context|ocr|OCR|图片.*文字|image.*text)", re.IGNORECASE
)
_CROSS_PROTECT_PATTERN = re.compile(
    r"(?:脱敏|redact|敏感标|sensitive.*tag|访问控制|access.*control|模态.*隔离)", re.IGNORECASE
)
_DEGRADE_PATTERN = re.compile(r"(?:降级|degrade|fallback.*text|纯文本|text.only|回退.*文本)", re.IGNORECASE)
_DEGRADE_CHECK_PATTERN = re.compile(
    r"(?:约束保留|constraint.*preserv|降级.*评估|degrade.*eval|降级边界|degrad.*boundary)", re.IGNORECASE
)
_OUTPUT_PATTERN = re.compile(
    r"(?:生成图|generate.*image|生成音|generate.*audio|输出图|output.*image|深度伪造|deepfake|tts|图像生成|image.*generat)",
    re.IGNORECASE,
)
_OUTPUT_CHECK_PATTERN = re.compile(
    r"(?:nsfw|深度伪造.*检测|deepfake.*detect|水印|watermark|输出.*审核|output.*moderat)", re.IGNORECASE
)


def check_p216(text: str) -> list[Finding]:
    findings = []
    if _IMAGE_PATTERN.search(text) and not _IMAGE_CHECK_PATTERN.search(text):
        findings.append(Finding("P216", Severity.HIGH, "图像输入未经安全预处理(元数据剥离/对抗检测/内容审核)", "1", "1"))
    return findings


def check_p217(text: str) -> list[Finding]:
    findings = []
    if _AUDIO_PATTERN.search(text) and not _AUDIO_CHECK_PATTERN.search(text):
        findings.append(
            Finding("P217", Severity.HIGH, "语音输入未经频谱分析和可听范围过滤, 存在隐藏指令注入风险", "1", "1")
        )
    return findings


def check_p218(text: str) -> list[Finding]:
    findings = []
    if _CROSS_MODAL_PATTERN.search(text) and not _CROSS_PROTECT_PATTERN.search(text):
        findings.append(Finding("P218", Severity.HIGH, "跨模态上下文未做敏感信息脱敏和隔离保护", "1", "1"))
    return findings


def check_p219(text: str) -> list[Finding]:
    findings = []
    if _DEGRADE_PATTERN.search(text) and not _DEGRADE_CHECK_PATTERN.search(text):
        findings.append(Finding("P219", Severity.MEDIUM, "模态降级后未保留/重新评估安全约束", "1", "1"))
    return findings


def check_p220(text: str) -> list[Finding]:
    findings = []
    if _OUTPUT_PATTERN.search(text) and not _OUTPUT_CHECK_PATTERN.search(text):
        findings.append(Finding("P220", Severity.HIGH, "多模态生成输出未经内容审核(NSFW/深度伪造检测)", "1", "1"))
    return findings
