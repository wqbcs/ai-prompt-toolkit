"""P236-P240 LLM推理引擎安全Lint规则

LLM推理引擎(Inference Engine)安全最佳实践:
- P236: 模型量化安全(量化后模型精度降级导致对抗样本易感性增加)
- P237: 推理侧信道风险(时序/功耗/缓存侧信道泄露模型信息)
- P238: KV缓存污染(长上下文KV缓存注入/越界读写)
- P239: 推理资源耗尽(无速率限制/请求大小限制, DoS风险)
- P240: 模型权重完整性(推理加载权重未校验, 替换攻击风险)

覆盖OWASP LLM04(Unauthorized Actions) + LLM06(Sensitive Info Disclosure)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P236_P240 = [
    LintRule(
        "P236",
        "模型量化安全",
        "inference_security",
        Severity.MEDIUM,
        "模型量化(INT8/INT4)后精度降级, 对抗样本易感性增加, 安全边界缩小",
        "量化安全: 量化后重新评估对抗鲁棒性+精度-安全权衡+混合精度(关键层FP16), 如 eval_robustness(quantized_model, attack=PGD)",
        description_en="Model quantization (INT8/INT4) reduces precision, increasing adversarial susceptibility and shrinking security boundary",
        remediation_en="Quantization safety: re-evaluate adversarial robustness after quantization+mixed precision for critical layers",
        family="inference_quantization",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P237",
        "推理侧信道风险",
        "inference_security",
        Severity.HIGH,
        "推理时序/功耗/缓存侧信道可泄露模型结构和训练数据信息",
        "侧信道防护: 常量时间推理+功耗随机化+缓存隔离+TEE执行, 如 constant_time_infer(model, input) + cache_flush()",
        description_en="Inference timing/power/cache side channels can leak model structure and training data",
        remediation_en="Side-channel defense: constant-time inference+power randomization+cache isolation+TEE execution",
        family="inference_sidechannel",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P238",
        "KV缓存污染",
        "inference_security",
        Severity.HIGH,
        "长上下文KV缓存可被注入/越界读写, 导致输出操纵或信息泄露",
        "KV缓存安全: 边界检查+隔离上下文+限制缓存大小+定期清除, 如 kv_cache = bounded_cache(max_tokens=4096, isolation=True)",
        description_en="Long context KV cache can be injected/OOB read-write, causing output manipulation or info leakage",
        remediation_en="KV cache security: boundary check+context isolation+size limit+periodic flush",
        family="inference_kv_cache",
        owasp_refs=["LLM04"],
    ),
    LintRule(
        "P239",
        "推理资源耗尽",
        "inference_security",
        Severity.HIGH,
        "推理服务无速率限制/请求大小限制, 可被DoS攻击耗尽GPU/CPU资源",
        "资源防护: 速率限制(token/s)+最大请求长度+并发控制+资源监控, 如 rate_limit=100_req/min, max_tokens=4096, max_concurrent=10",
        description_en="Inference service lacks rate limiting/request size limits, vulnerable to DoS attacks exhausting GPU/CPU",
        remediation_en="Resource defense: rate limiting+max request length+concurrency control+resource monitoring",
        family="inference_dos",
        owasp_refs=["LLM04"],
    ),
    LintRule(
        "P240",
        "模型权重完整性",
        "inference_security",
        Severity.HIGH,
        "推理加载模型权重未校验完整性, 替换攻击可植入后门模型",
        "权重完整性: SHA256校验+签名验证+可信源下载+加载前校验, 如 verify_checksum(weights, expected='sha256:abc...') + verify_signature(weights, pub_key)",
        description_en="Inference loads model weights without integrity check, replacement attack can implant backdoored model",
        remediation_en="Weight integrity: SHA256 checksum+signature verification+trusted source+pre-load verification",
        family="inference_weight_integrity",
        owasp_refs=["LLM04"],
    ),
]

for r in _RULES_P236_P240:
    _RULE_MAP[r.rule_id] = r

_QUANT_PATTERN = re.compile(
    r"(?:quantiz|量化|INT8|INT4|FP8|FP4|GPTQ|AWQ|bitsandbytes|bnb|load_in_4bit|load_in_8bit)", re.IGNORECASE
)
_ROBUST_PATTERN = re.compile(
    r"(?:robust|鲁棒|adversarial|对抗|PGD|FGSM|eval_robustness|混合精度|mixed.precision)", re.IGNORECASE
)
_SIDECHANNEL_PATTERN = re.compile(
    r"(?:timing|时序|侧信道|side.channel|power|功耗|cache.attack|缓存攻击|spectre|meltdown)", re.IGNORECASE
)
_CONST_TIME_PATTERN = re.compile(
    r"(?:constant.time|常量时间|恒定时间|响应时间恒定|时间恒定|cache.flush|缓存隔离|cache.isolat|TEE|trusted.execution|功耗随机)",
    re.IGNORECASE,
)
# 思维链/逐步推理是Prompt行为描述, 不是推理服务部署 — 排除"逐步推理"类误报
_REASONING_BEHAVIOR_PATTERN = re.compile(
    r"(?:逐步推理|思维链|chain.of.thought|思考过程|推理过程|step.by.step|scratchpad)", re.IGNORECASE
)
_KV_CACHE_PATTERN = re.compile(
    r"(?:kv.cache|KV缓存|key.value.cache|past_key_values|cached_key|context.cache|长上下文)", re.IGNORECASE
)
_KV_SECURE_PATTERN = re.compile(
    r"(?:边界检查|boundary|isolat|隔离|bounded|限制缓存|max_tokens|flush|清除缓存)", re.IGNORECASE
)
_RATE_LIMIT_PATTERN = re.compile(
    r"(?:rate.limit|速率限制|限流|throttle|quota|concurrency|并发|max_concurrent|token.per.sec)", re.IGNORECASE
)
_RESOURCE_PATTERN = re.compile(
    r"(?:max_tokens|max_length|max_request|资源监控|resource.monitor|GPU.monitor|timeout)", re.IGNORECASE
)
# R320: P239 抑制面中文对称 — 英文 "timeout" 经 _RESOURCE_PATTERN 可静默, 中文
# "超时" 不可（非对称 FP 面: 含推理关键词 + 正向语境中文 "超时" 声明的干净 prompt
# 被 DoS 误报）。只抑制正向语境 "超时" 声明: 配置动词在 "超时" 前 10 字窗内, 或
# "超时+防护名词"; 否定形态（golden atk37 "没有超时控制" = 检测下限）不得静默,
# 否则丢 TP 锚点。
_TIMEOUT_GUARD_VERB_PATTERN = re.compile(
    r"(?:设置|配置|声明|指定|启用|设定|定义|约束|限制|要求)[^，。；！？\n]{0,10}?超时"
)
_TIMEOUT_GUARD_NOUN_PATTERN = re.compile(r"超时(?:限制|机制|处理|策略|时间|重试|上限|控制|默认)")
_TIMEOUT_NEGATION_CHARS = "没无未不别勿"
_TIMEOUT_NEGATION_WORDS = ("没有", "无法")
_WEIGHT_LOAD_PATTERN = re.compile(
    r"(?:load_model|from_pretrained|load_state_dict|加载权重|load_weights|safetensors|model.load)", re.IGNORECASE
)
_WEIGHT_VERIFY_PATTERN = re.compile(
    r"(?:checksum|校验|sha256|hash|签名|signature|verify|完整性|integrity|trusted.source|可信源)", re.IGNORECASE
)


def check_p236(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _QUANT_PATTERN.search(text) and not _ROBUST_PATTERN.search(text):
        findings.append(Finding("P236", Severity.MEDIUM, "模型量化后未重新评估对抗鲁棒性(精度-安全权衡)"))
    return findings


def check_p237(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _SIDECHANNEL_PATTERN.search(text) and not _CONST_TIME_PATTERN.search(text):
        findings.append(Finding("P237", Severity.HIGH, "推理存在侧信道风险(未做常量时间/缓存隔离防护)"))
    return findings


def check_p238(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _KV_CACHE_PATTERN.search(text) and not _KV_SECURE_PATTERN.search(text):
        findings.append(Finding("P238", Severity.HIGH, "KV缓存未做边界检查/隔离/大小限制(缓存污染风险)"))
    return findings


def _has_timeout_guard(text: str) -> bool:
    """R320: 正向语境中文"超时"声明检查（英文 timeout 抑制面中文对称）。"""
    for pattern in (_TIMEOUT_GUARD_VERB_PATTERN, _TIMEOUT_GUARD_NOUN_PATTERN):
        for m in pattern.finditer(text):
            pre = text[max(0, m.start() - 2) : m.start()]
            # 否定形态不得视为防护声明: 紧邻单字符否定(没/无/未/不/别/勿)或
            # 双字否定词(没有/无法, 否定字在窗口首位) — atk37 "没有超时控制" 锚点
            if pre and (pre[-1] in _TIMEOUT_NEGATION_CHARS or pre in _TIMEOUT_NEGATION_WORDS):
                continue
            return True
    return False


def check_p239(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _REASONING_BEHAVIOR_PATTERN.search(text):
        return findings
    if not _RATE_LIMIT_PATTERN.search(text) and not _RESOURCE_PATTERN.search(text) and not _has_timeout_guard(text):
        # 注: 不含裸"api" — "API文档"等非服务语境不应触发DoS告警
        has_infer = re.search(
            # R317-P2-26 批2: serve → \bserve\b — 裸子串误配 "Discord server"/
            # "web server"(平台名非服务语义, NotInject 2 条真实 FP); 词边界后
            # "serve requests" 式真服务语义保留, golden 2 TP 经 推理/api接口 触发
            # 不受影响。
            r"(?:infer|推理|predict|generate|completion|\bserve\b|endpoint|api端点|api接口|api服务|api网关)",
            text,
            re.IGNORECASE,
        )
        if has_infer:
            findings.append(
                Finding(
                    "P239",
                    Severity.HIGH,
                    "推理服务缺速率限制/请求大小限制(DoS风险)",
                    location=loc_from_match(text, has_infer),
                )
            )
    return findings


def check_p240(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if _WEIGHT_LOAD_PATTERN.search(text) and not _WEIGHT_VERIFY_PATTERN.search(text):
        findings.append(Finding("P240", Severity.HIGH, "加载模型权重未校验完整性(替换攻击风险)"))
    return findings
