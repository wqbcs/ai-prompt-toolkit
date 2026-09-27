"""P211-P215 鸿蒙NEXT API 16 Lint规则

鸿蒙NEXT API 16新特性与安全最佳实践:
- P211: ArkUI懒加载缺失(长列表未用LazyForEach导致内存溢出)
- P212: @ObservedV2装饰器误用(状态管理V2使用不当导致更新异常)
- P213: 原生绑定安全(FFI/NAPI调用未做参数校验导致内存越界)
- P214: 元服务权限过度(元服务声明过多权限增加攻击面)
- P215: 分布式数据同步安全(分布式数据未加密/未校验导致泄露)

覆盖OWASP LLM06(Excessive Agency)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P211_P215 = [
    LintRule(
        "P211",
        "ArkUI懒加载缺失",
        "harmonyos_v16",
        Severity.HIGH,
        "鸿蒙NEXT长列表未使用LazyForEach懒加载, 可能导致内存溢出和渲染卡顿",
        "使用LazyForEach替代ForEach: LazyForEach(dataSource, item => ListItem, keyGenerator)",
        description_en="HarmonyOS NEXT long list lacks LazyForEach, may cause OOM and render lag",
        remediation_en="Use LazyForEach instead of ForEach: LazyForEach(dataSource, item => ListItem, keyGenerator)",
        family="harmonyos_lazy_load",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P212",
        "ObservedV2装饰器误用",
        "harmonyos_v16",
        Severity.MEDIUM,
        "@ObservedV2/@Trace装饰器使用不当, 状态更新可能无法正确触发UI刷新",
        "确保@ObservedV2类属性用@Trace装饰, 嵌套对象需递归装饰, 参考: @ObservedV2 class Model { @Trace value: number = 0 }",
        description_en="@ObservedV2/@Trace decorators misused, state updates may not trigger UI refresh",
        remediation_en="Ensure @ObservedV2 class properties use @Trace, nested objects need recursive decoration",
        family="harmonyos_observed_v2",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P213",
        "原生绑定安全",
        "harmonyos_v16",
        Severity.HIGH,
        "NAPI/FFI调用未做参数校验和边界检查, 可能导致内存越界/类型混淆",
        "NAPI安全: napi_value类型检查+长度校验+null检查, 如 napi_get_value_string_utf8 前先 napi_typeof 验证",
        description_en="NAPI/FFI calls lack parameter validation and bounds checking, may cause OOB/type confusion",
        remediation_en="NAPI safety: napi_value type check+length check+null check before access",
        family="harmonyos_napi_safety",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P214",
        "元服务权限过度",
        "harmonyos_v16",
        Severity.MEDIUM,
        "元服务声明过多系统权限, 增加攻击面和用户信任成本",
        "最小权限原则: 仅声明必要权限, 使用ohos.permission精简列表, 避免ohos.permission.ALL",
        description_en="Atomic service declares excessive permissions, increases attack surface and trust cost",
        remediation_en="Least privilege: only declare necessary ohos.permission, avoid ohos.permission.ALL",
        family="harmonyos_permission",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P215",
        "分布式数据同步安全",
        "harmonyos_v16",
        Severity.HIGH,
        "分布式数据同步未加密/未校验, 跨设备传输可能泄露敏感信息",
        "分布式安全: distributedDB加密+数据签名+设备认证, 如 distributedDB: {encrypt: true, algorithm: 'AES-256'}",
        description_en="Distributed data sync lacks encryption/validation, cross-device transfer may leak sensitive data",
        remediation_en="Distributed safety: distributedDB encryption+data signature+device authentication",
        family="harmonyos_distributed_security",
        owasp_refs=["LLM06"],
    ),
]

for r in _RULES_P211_P215:
    _RULE_MAP[r.rule_id] = r

_FOREACH_PATTERN = re.compile(r"(?:ForEach|foreach|列表渲染|list.render)", re.IGNORECASE)
_LAZY_PATTERN = re.compile(r"(?:LazyForEach|lazy.foreach|懒加载|lazy.load)", re.IGNORECASE)
_OBSERVED_V2_PATTERN = re.compile(r"(?:@ObservedV2|ObservedV2|observed.v2)", re.IGNORECASE)
_TRACE_PATTERN = re.compile(r"(?:@Trace|Trace装饰|trace.decorator)", re.IGNORECASE)
_NAPI_PATTERN = re.compile(r"(?:napi_|NAPI|node_api|ffi|dlopen|原生调用|native.call)", re.IGNORECASE)
_NAPI_CHECK_PATTERN = re.compile(r"(?:napi_typeof|napi_is_|typeof|类型检查|type.check|null.check)", re.IGNORECASE)
_PERMISSION_PATTERN = re.compile(r"(?:ohos\.permission|requestPermission|权限声明)", re.IGNORECASE)
_PERMISSION_ALL_PATTERN = re.compile(r"(?:ohos\.permission\.ALL|permission\.ANY|\*权限|全权限)", re.IGNORECASE)
_DISTRIBUTED_PATTERN = re.compile(r"(?:distributedDB|分布式数据|distributed.data|跨设备|cross.device)", re.IGNORECASE)
_ENCRYPT_PATTERN = re.compile(r"(?:encrypt|加密|AES|RSA|cipher|数据签名)", re.IGNORECASE)


def check_p211(text: str) -> list[Finding]:
    findings = []
    if _FOREACH_PATTERN.search(text) and not _LAZY_PATTERN.search(text):
        findings.append(Finding("P211", Severity.HIGH, "长列表未使用LazyForEach懒加载", "1", "1"))
    return findings


def check_p212(text: str) -> list[Finding]:
    findings = []
    if _OBSERVED_V2_PATTERN.search(text) and not _TRACE_PATTERN.search(text):
        findings.append(Finding("P212", Severity.MEDIUM, "@ObservedV2未配合@Trace装饰器", "1", "1"))
    return findings


def check_p213(text: str) -> list[Finding]:
    findings = []
    if _NAPI_PATTERN.search(text) and not _NAPI_CHECK_PATTERN.search(text):
        findings.append(Finding("P213", Severity.HIGH, "NAPI/FFI调用未做参数校验", "1", "1"))
    return findings


def check_p214(text: str) -> list[Finding]:
    findings = []
    if _PERMISSION_ALL_PATTERN.search(text):
        findings.append(Finding("P214", Severity.MEDIUM, "声明了过度权限(ALL/ANY)", "1", "1"))
    elif _PERMISSION_PATTERN.search(text):
        perm_count = len(re.findall(r"ohos\.permission\.\w+", text))
        if perm_count > 5:
            findings.append(Finding("P214", Severity.MEDIUM, f"声明了{perm_count}个权限, 建议精简", "1", "1"))
    return findings


def check_p215(text: str) -> list[Finding]:
    findings = []
    if _DISTRIBUTED_PATTERN.search(text) and not _ENCRYPT_PATTERN.search(text):
        findings.append(Finding("P215", Severity.HIGH, "分布式数据同步未加密", "1", "1"))
    return findings
