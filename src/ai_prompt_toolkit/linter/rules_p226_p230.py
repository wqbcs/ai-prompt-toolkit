"""P226-P230 ArkTS安全Lint规则

鸿蒙HarmonyOS ArkTS专属安全检查:
- P226: ArkTS动态类型滥用(@ts-ignore/any类型绕过类型安全)
- P227: ArkUI状态管理风险(@State/@Link/@Prop不当使用导致数据泄露)
- P228: 鸿蒙权限声明缺失(abilities未声明所需权限, 可能运行时崩溃)
- P229: ArkTS跨组件通信风险(router/Emitter/分布式数据未做安全校验)
- P230: 鸿蒙沙箱隔离违规(文件/网络/设备访问越界沙箱范围)

覆盖OWASP LLM06(Sensitive Information Disclosure) + LLM04(Unauthorized Actions)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P226_P230 = [
    LintRule(
        "P226",
        "ArkTS动态类型滥用",
        "arkts_security",
        Severity.HIGH,
        "使用@ts-ignore/any类型绕过类型安全, 可能引入运行时类型错误和安全漏洞",
        "严格类型检查: 移除@ts-ignore, 用具体类型替代any, 启用strictNullChecks+noImplicitAny",
        description_en="Using @ts-ignore/any to bypass type safety, may introduce runtime type errors and security vulnerabilities",
        remediation_en="Strict type checking: remove @ts-ignore, replace any with concrete types, enable strictNullChecks+noImplicitAny",
        family="arkts_type_safety",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P227",
        "ArkUI状态管理风险",
        "arkts_security",
        Severity.HIGH,
        "@State/@Link/@Prop状态管理不当使用可能导致数据泄露或状态劫持",
        "状态管理安全: @State标记敏感数据需加密, @Link/@Prop单向绑定防止反向注入, @StorageLink需访问控制",
        description_en="Improper @State/@Link/@Prop usage may cause data leakage or state hijacking",
        remediation_en="State security: encrypt sensitive @State data, use one-way binding for @Link/@Prop, add access control for @StorageLink",
        family="arkui_state_security",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P228",
        "鸿蒙权限声明缺失",
        "arkts_security",
        Severity.HIGH,
        "abilities未声明所需权限(ohos.permission.*), 运行时可能崩溃或静默失败",
        "权限声明: module.json5中requestPermissions声明所需权限+权限理由+用户授权时机, 如 ohos.permission.INTERNET",
        description_en="Abilities lack required permission declarations (ohos.permission.*), may crash or silently fail at runtime",
        remediation_en="Permission declaration: declare requestPermissions in module.json5 + permission rationale + user authorization timing",
        family="harmony_permission",
        owasp_refs=["LLM04"],
    ),
    LintRule(
        "P229",
        "ArkTS跨组件通信风险",
        "arkts_security",
        Severity.MEDIUM,
        "router/Emitter/分布式数据传输未做安全校验, 可能被恶意组件拦截或篡改",
        "通信安全: router参数加密+签名验证, Emitter事件过滤+来源校验, 分布式数据加密传输+端对端认证",
        description_en="router/Emitter/distributed data transfer lacks security validation, may be intercepted or tampered by malicious components",
        remediation_en="Communication security: encrypt+sign router params, filter+validate Emitter events, encrypt distributed data+end-to-end auth",
        family="arkts_communication",
        owasp_refs=["LLM04", "LLM06"],
    ),
    LintRule(
        "P230",
        "鸿蒙沙箱隔离违规",
        "arkts_security",
        Severity.HIGH,
        "文件/网络/设备访问超出应用沙箱范围, 违反鸿蒙安全模型",
        "沙箱合规: 限制文件访问到应用沙箱目录, 网络请求仅限声明域名, 设备API需权限校验, 严禁硬编码系统路径(如/data/local/tmp)",
        description_en="File/network/device access exceeds app sandbox scope, violating HarmonyOS security model",
        remediation_en="Sandbox compliance: restrict file access to app sandbox dir, network only declared domains, device API requires permission, no hardcoded system paths",
        family="harmony_sandbox",
        owasp_refs=["LLM04"],
    ),
]

for r in _RULES_P226_P230:
    _RULE_MAP[r.rule_id] = r

_TS_IGNORE_PATTERN = re.compile(r"@ts-ignore|@ts-expect-error|//\s*eslint-disable", re.IGNORECASE)
_ANY_TYPE_PATTERN = re.compile(r"\bany\b", re.IGNORECASE)
_STRICT_NULL_PATTERN = re.compile(r"strictNullChecks|noImplicitAny|strict", re.IGNORECASE)
_STATE_PATTERN = re.compile(r"@(?:State|Link|Prop|Provide|Consume|StorageLink|StorageProp|Watch)\b", re.IGNORECASE)
_SENSITIVE_STATE_PATTERN = re.compile(r"(?:password|secret|token|key|credential|隐私|敏感|密钥|密码)", re.IGNORECASE)
_ENCRYPT_PATTERN = re.compile(r"(?:encrypt|加密|cipher|CryptoFramework|secure|安全存储|SecurityHelper)", re.IGNORECASE)
_PERMISSION_PATTERN = re.compile(
    r"(?:ohos\.permission|requestPermission|权限|permission|acl|accessControl)", re.IGNORECASE
)
_ABILITY_PATTERN = re.compile(
    r"(?:ability|Ability|UIAbility|ExtensionAbility|StageAbility|EntryAbility)", re.IGNORECASE
)
_ROUTER_PATTERN = re.compile(r"(?:router\.(?:push|replace|back|getParams)|UIRouter|Router)", re.IGNORECASE)
_EMITTER_PATTERN = re.compile(r"(?:Emitter|emitter\.(?:on|emit)|CommonEvent|EventHub)", re.IGNORECASE)
_DISTRIBUTED_PATTERN = re.compile(r"(?:distributed|分布式|DistributedDB|DeviceManager|remote|跨设备)", re.IGNORECASE)
_COMM_SECURE_PATTERN = re.compile(r"(?:签名|signature|验证|verify|加密|encrypt|认证|auth|校验|validate)", re.IGNORECASE)
_SANDBOX_VIOLATION_PATTERN = re.compile(
    r"(?:/data/local/tmp|/system/|/vendor/|/dev/|沙箱违规|sandbox.violation|getContext.*files.*\.\.)", re.IGNORECASE
)
_NETWORK_NO_DOMAIN_PATTERN = re.compile(r"(?:httpRequest|fetch|HttpClient|net\.http|request\()", re.IGNORECASE)
_DOMAIN_DECLARED_PATTERN = re.compile(r"(?:domain|域名|baseUrl|BASE_URL|allowedDomain|securityDomain)", re.IGNORECASE)


def check_p226(text: str) -> list[Finding]:
    findings = []
    has_ts_ignore = _TS_IGNORE_PATTERN.search(text)
    has_any = _ANY_TYPE_PATTERN.search(text)
    has_strict = _STRICT_NULL_PATTERN.search(text)
    if has_ts_ignore:
        findings.append(Finding("P226", Severity.HIGH, "使用@ts-ignore/eslint-disable绕过类型检查(安全风险)"))
    if has_any and not has_strict:
        findings.append(Finding("P226", Severity.HIGH, "使用any类型且未启用strictNullChecks/noImplicitAny"))
    return findings


def check_p227(text: str) -> list[Finding]:
    findings = []
    state_matches = _STATE_PATTERN.findall(text)
    if state_matches and _SENSITIVE_STATE_PATTERN.search(text) and not _ENCRYPT_PATTERN.search(text):
        findings.append(Finding("P227", Severity.HIGH, "敏感数据使用@State/@Link等装饰器但未加密(数据泄露风险)"))
    return findings


def check_p228(text: str) -> list[Finding]:
    findings = []
    if _ABILITY_PATTERN.search(text) and not _PERMISSION_PATTERN.search(text):
        findings.append(Finding("P228", Severity.HIGH, "Ability声明缺少ohos.permission权限声明(运行时崩溃风险)"))
    return findings


def check_p229(text: str) -> list[Finding]:
    findings = []
    has_router = _ROUTER_PATTERN.search(text)
    has_emitter = _EMITTER_PATTERN.search(text)
    has_distributed = _DISTRIBUTED_PATTERN.search(text)
    has_comm_secure = _COMM_SECURE_PATTERN.search(text)
    if has_router and not has_comm_secure:
        findings.append(Finding("P229", Severity.MEDIUM, "router参数传输未做安全校验(签名/加密/验证)"))
    if has_emitter and not has_comm_secure:
        findings.append(Finding("P229", Severity.MEDIUM, "Emitter事件通信未做安全校验(来源验证/事件过滤)"))
    if has_distributed and not has_comm_secure:
        findings.append(Finding("P229", Severity.MEDIUM, "分布式数据传输未做安全校验(加密/端对端认证)"))
    return findings


def check_p230(text: str) -> list[Finding]:
    findings = []
    if _SANDBOX_VIOLATION_PATTERN.search(text):
        findings.append(Finding("P230", Severity.HIGH, "访问超出应用沙箱范围的路径(违反鸿蒙安全模型)"))
    if _NETWORK_NO_DOMAIN_PATTERN.search(text) and not _DOMAIN_DECLARED_PATTERN.search(text):
        findings.append(Finding("P230", Severity.HIGH, "网络请求未限制声明域名(沙箱隔离违规)"))
    return findings
