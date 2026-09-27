"""P231-P235 联邦学习安全Lint规则

联邦学习(Federated Learning)安全最佳实践:
- P231: 梯度泄露风险(梯度反转攻击可还原训练数据)
- P232: 差分隐私缺失(联邦聚合未添加差分隐私噪声)
- P233: 模型投毒防护缺失(恶意客户端上传篡改模型更新)
- P234: 安全聚合协议缺失(梯度聚合未使用加密/安全聚合)
- P235: 客户端身份验证缺失(参与方未做身份认证, 伪装攻击风险)

覆盖OWASP LLM03(Supply Chain) + LLM06(Sensitive Info Disclosure)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P231_P235 = [
    LintRule(
        "P231",
        "梯度泄露风险",
        "federated_security",
        Severity.HIGH,
        "联邦学习梯度传输可被反转攻击还原原始训练数据, 隐私泄露风险",
        "梯度保护: 差分隐私(DP-SGD)+梯度裁剪+安全聚合, 如 dp_gradient = gradient + laplace_noise(epsilon=1.0), clip_gradient(norm=1.0)",
        description_en="Federated learning gradients can be inverted to reconstruct training data via gradient inversion attacks",
        remediation_en="Gradient protection: differential privacy(DP-SGD)+gradient clipping+secure aggregation",
        family="fed_gradient_leak",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P232",
        "差分隐私缺失",
        "federated_security",
        Severity.HIGH,
        "联邦聚合未添加差分隐私噪声, 无法提供数学可证明的隐私保证",
        "差分隐私: 聚合添加 calibrated noise, 设置epsilon/budget, 如 FedAvg + DP(epsilon=3.0, delta=1e-5), 隐私预算追踪",
        description_en="Federated aggregation lacks differential privacy noise, cannot provide mathematically provable privacy guarantees",
        remediation_en="Differential privacy: add calibrated noise to aggregation, set epsilon/budget, track privacy budget",
        family="fed_differential_privacy",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P233",
        "模型投毒防护缺失",
        "federated_security",
        Severity.HIGH,
        "恶意客户端可上传篡改模型更新, 污染全局模型(后门植入/性能降级)",
        "投毒防护: 异常检测(Krum/multi-krum)+鲁棒聚合(Robust LR)+贡献度验证, 如 filtered_updates = krum_select(updates, f=0.2)",
        description_en="Malicious clients can upload poisoned model updates to contaminate global model (backdoor/performance degradation)",
        remediation_en="Poisoning defense: anomaly detection(Krum)+robust aggregation+contribution validation",
        family="fed_model_poisoning",
        owasp_refs=["LLM03"],
    ),
    LintRule(
        "P234",
        "安全聚合协议缺失",
        "federated_security",
        Severity.MEDIUM,
        "梯度聚合未使用加密或安全聚合协议, 服务器可窥探客户端原始梯度",
        "安全聚合: Secret Sharing+Homomorphic Encryption+TEE, 如 SecureAgg = pairwise_masking + secret_sharing, 或使用Federated_TLS",
        description_en="Gradient aggregation lacks encryption or secure aggregation protocol, server can observe raw client gradients",
        remediation_en="Secure aggregation: Secret Sharing+Homomorphic Encryption+TEE, or Federated TLS",
        family="fed_secure_aggregation",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P235",
        "客户端身份验证缺失",
        "federated_security",
        Severity.HIGH,
        "参与方未做身份认证, 伪装攻击(Sybil)可创建多个虚假客户端操纵聚合结果",
        "客户端认证: PKI证书+Token验证+贡献度追踪+Sybil检测, 如 verify_client(cert, token) + detect_sybil(contribution_history)",
        description_en="Participants lack identity authentication, Sybil attack can create fake clients to manipulate aggregation",
        remediation_en="Client authentication: PKI certificate+Token verification+contribution tracking+Sybil detection",
        family="fed_client_auth",
        owasp_refs=["LLM03"],
    ),
]

for r in _RULES_P231_P235:
    _RULE_MAP[r.rule_id] = r

_GRADIENT_PATTERN = re.compile(r"(?:gradient|梯度|grad_|backward|反向传播|param.update|model.update)", re.IGNORECASE)
_DP_PATTERN = re.compile(
    r"(?:differential.privacy|差分隐私|dp.sgd|laplace|gaussian.noise|epsilon|privacy.budget|隐私预算|noise.scale)",
    re.IGNORECASE,
)
_GRADIENT_CLIP_PATTERN = re.compile(r"(?:clip|裁剪|norm|梯度裁剪|gradient.clip|max_norm)", re.IGNORECASE)
_POISON_PATTERN = re.compile(
    r"(?:poison|投毒|byzantine|拜占庭|malicious|恶意|backdoor|后门|tainted|篡改)", re.IGNORECASE
)
_ROBUST_AGG_PATTERN = re.compile(
    r"(?:krum|multi.krum|robust|鲁棒|trim|trimmed.mean|median|中位数|filtered|异常检测|anomaly.detect)", re.IGNORECASE
)
_FED_AGG_PATTERN = re.compile(
    r"(?:FedAvg|fed.avg|federated|联邦|aggregate|聚合|server.update|global.model)", re.IGNORECASE
)
_SECURE_AGG_PATTERN = re.compile(
    r"(?:secure.agg|安全聚合|secret.shar|homomorphic|同态|encrypt|加密|TEE|trusted.execution|pairwise.mask)",
    re.IGNORECASE,
)
_CLIENT_PATTERN = re.compile(r"(?:client|客户端|participant|参与方|worker|node)", re.IGNORECASE)
_AUTH_PATTERN = re.compile(r"(?:auth|认证|cert|证书|token|PKI|verify|验证|sybil.detect|身份)", re.IGNORECASE)


def check_p231(text: str) -> list[Finding]:
    findings = []
    if _GRADIENT_PATTERN.search(text) and not _DP_PATTERN.search(text) and not _GRADIENT_CLIP_PATTERN.search(text):
        findings.append(Finding("P231", Severity.HIGH, "梯度传输未添加差分隐私或裁剪(梯度泄露风险)", "1", "1"))
    return findings


def check_p232(text: str) -> list[Finding]:
    findings = []
    if _FED_AGG_PATTERN.search(text) and not _DP_PATTERN.search(text):
        findings.append(Finding("P232", Severity.HIGH, "联邦聚合未添加差分隐私噪声(无数学隐私保证)", "1", "1"))
    return findings


def check_p233(text: str) -> list[Finding]:
    findings = []
    if _FED_AGG_PATTERN.search(text) and not _ROBUST_AGG_PATTERN.search(text):
        findings.append(Finding("P233", Severity.HIGH, "联邦聚合缺模型投毒防护(无Krum/鲁棒聚合/异常检测)", "1", "1"))
    return findings


def check_p234(text: str) -> list[Finding]:
    findings = []
    if _FED_AGG_PATTERN.search(text) and not _SECURE_AGG_PATTERN.search(text):
        findings.append(Finding("P234", Severity.MEDIUM, "梯度聚合未使用安全聚合协议(服务器可窥探原始梯度)", "1", "1"))
    return findings


def check_p235(text: str) -> list[Finding]:
    findings = []
    if _CLIENT_PATTERN.search(text) and _FED_AGG_PATTERN.search(text) and not _AUTH_PATTERN.search(text):
        findings.append(Finding("P235", Severity.HIGH, "联邦参与方未做身份认证(Sybil伪装攻击风险)", "1", "1"))
    return findings
