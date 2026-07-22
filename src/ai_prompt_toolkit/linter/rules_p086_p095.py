"""Lint规则集扩展——P086-P095 鸿蒙HarmonyOS NEXT场景专项规则

R39新增(赛事贴合-鸿蒙生态):
- P086: ArkTS语法兼容性 — 检测非ArkTS兼容语法
- P087: Stage模型声明缺失 — 鸿蒙Stage模型需要Ability声明
- P088: Ability生命周期缺失 — 检测Ability生命周期回调
- P089: 鸿蒙权限声明缺失 — 检测ohos.permission权限声明
- P090: 鸿蒙UI组件兼容性 — 检测ArkUI组件版本兼容性
- P091: 鸿蒙资源引用规范 — 检测$r/$rawfile资源引用规范
- P092: 鸿蒙线程模型声明 — 检测TaskPool/Worker线程模型
- P093: 鸿蒙数据管理规范 — 检测关系型数据库/偏好数据使用规范
- P094: 鸿蒙网络安全规范 — 检测HTTP/HTTPS证书锁定/网络安全配置
- P095: 鸿蒙应用签名规范 — 检测应用签名和证书配置
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP


_RULES_P086_P095: list[LintRule] = [
    LintRule("P086", "ArkTS语法兼容性风险", "quality", Severity.MEDIUM,
             "鸿蒙Prompt中使用了非ArkTS兼容语法(TypeScript高级特性)",
             "仅使用ArkTS支持子集: 避免as const/satisfies/enum运行时/namespace",
             description_en="HarmonyOS prompt uses non-ArkTS compatible TypeScript features",
             remediation_en="Use only ArkTS subset: avoid as const/satisfies/runtime enum/namespace", family="arkts_compat"),
    LintRule("P087", "Stage模型Ability声明缺失", "structure", Severity.HIGH,
             "鸿蒙Stage模型Prompt缺少Ability声明和入口配置",
             "添加Ability声明: '入口Ability: EntryAbility, 类型: main'",
             description_en="HarmonyOS Stage model prompt missing Ability declaration",
             remediation_en="Add Ability declaration: 'Entry Ability: EntryAbility, type: main'", family="harmony_ability"),
    LintRule("P088", "Ability生命周期回调缺失", "quality", Severity.MEDIUM,
             "鸿蒙开发Prompt缺少Ability生命周期回调(onCreate/onDestroy等)",
             "声明生命周期回调: onCreate→onWindowStageCreate→onForeground→onBackground→onDestroy",
             description_en="HarmonyOS prompt missing Ability lifecycle callbacks",
             remediation_en="Declare lifecycle: onCreate→onWindowStageCreate→onForeground→onBackground→onDestroy", family="harmony_lifecycle"),
    LintRule("P089", "鸿蒙权限声明缺失", "security", Severity.HIGH,
             "鸿蒙应用Prompt未声明所需权限(ohos.permission.*)",
             "声明权限: ohos.permission.INTERNET等, 使用最小权限原则",
             description_en="HarmonyOS app prompt missing permission declarations (ohos.permission.*)",
             remediation_en="Declare permissions: ohos.permission.INTERNET etc., use least privilege", family="harmony_permission"),
    LintRule("P090", "鸿蒙UI组件版本兼容性", "quality", Severity.LOW,
             "鸿蒙Prompt使用了特定版本ArkUI组件但未声明最低API版本",
             "声明组件兼容性: '组件X需要API 12+, 降级方案: 使用基础组件替代'",
             description_en="HarmonyOS prompt uses version-specific ArkUI components without min API declaration",
             remediation_en="Declare compatibility: 'Component X requires API 12+, fallback: basic components'", family="harmony_ui_compat"),
    LintRule("P091", "鸿蒙资源引用规范缺失", "quality", Severity.LOW,
             "鸿蒙Prompt引用资源未使用$r/$rawfile标准引用方式",
             "使用标准资源引用: $r('app.string.key') 或 $rawfile('file.mp4')",
             description_en="HarmonyOS prompt uses non-standard resource references",
             remediation_en="Use standard references: $r('app.string.key') or $rawfile('file.mp4')", family="harmony_resource"),
    LintRule("P092", "鸿蒙线程模型声明缺失", "performance", Severity.MEDIUM,
             "鸿蒙耗时操作Prompt未声明TaskPool/Worker线程模型",
             "声明线程策略: '耗时操作使用TaskPool, UI更新回主线程'",
             description_en="HarmonyOS prompt with heavy operations missing TaskPool/Worker thread declaration",
             remediation_en="Declare threading: 'Use TaskPool for heavy ops, UI updates on main thread'", family="harmony_thread"),
    LintRule("P093", "鸿蒙数据管理规范缺失", "quality", Severity.MEDIUM,
             "鸿蒙数据存储Prompt未声明使用关系型数据库/偏好数据/分布式数据",
             "声明数据管理: '轻量用Preferences, 结构化用RDB, 跨设备用分布式DataShare'",
             description_en="HarmonyOS data storage prompt missing RDB/Preferences/DataShare declaration",
             remediation_en="Declare data mgmt: 'Lightweight: Preferences, Structured: RDB, Cross-device: DataShare'", family="harmony_data"),
    LintRule("P094", "鸿蒙网络安全规范缺失", "security", Severity.HIGH,
             "鸿蒙网络请求Prompt未声明HTTPS/证书锁定/网络安全配置",
             "声明网络安全: '强制HTTPS, 证书锁定(publicKeyPinning), 禁止明文传输'",
             description_en="HarmonyOS network prompt missing HTTPS/certificate pinning declaration",
             remediation_en="Declare security: 'Enforce HTTPS, certificate pinning, no cleartext traffic'", family="harmony_network"),
    LintRule("P095", "鸿蒙应用签名规范缺失", "compliance", Severity.MEDIUM,
             "鸿蒙应用发布Prompt未声明签名证书和Profile配置",
             "声明签名配置: '调试证书: .p12, Profile: .p7b, 发布证书: AGC分发'",
             description_en="HarmonyOS release prompt missing signing certificate and Profile config",
             remediation_en="Declare signing: 'Debug cert: .p12, Profile: .p7b, Release: AGC distribution'", family="harmony_signing"),
]

for r in _RULES_P086_P095:
    _RULE_MAP[r.rule_id] = r


_ARKTS_UNSUPPORTED = re.compile(
    r'(?:as\s+const|satisfies|enum\s+\w+\s*\{|namespace\s+\w+\s*\{)',
    re.IGNORECASE
)
_HARMONYOS_CTX = re.compile(
    r'(?:HarmonyOS|鸿蒙|ArkTS|ArkUI|Stage模型|Ability|ohos|@Entry|@Component)',
    re.IGNORECASE
)


def check_p086(text: str) -> Finding | None:
    rule = _RULE_MAP["P086"]
    if not _HARMONYOS_CTX.search(text):
        return None
    unsupported = _ARKTS_UNSUPPORTED.findall(text)
    if not unsupported:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (检测到: {', '.join(unsupported[:3])})",
        remediation=rule.remediation,
        details={"unsupported_syntax": unsupported[:3]},
    )


_STAGE_MODEL_PATTERN = re.compile(
    r'(?:Stage模型|Stage\s*Model|UIAbility|ExtensionAbility|HAP|HarmonyOS.*应用)',
    re.IGNORECASE
)
_ABILITY_DECL_PATTERN = re.compile(
    r'(?:EntryAbility|MainAbility|Ability.*声明|module\.json|Ability.*config)',
    re.IGNORECASE
)


def check_p087(text: str) -> Finding | None:
    rule = _RULE_MAP["P087"]
    if not _STAGE_MODEL_PATTERN.search(text):
        return None
    if _ABILITY_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_LIFECYCLE_PATTERN = re.compile(
    r'(?:Ability|生命周期|lifecycle|onCreate|onDestroy|onForeground|onBackground)',
    re.IGNORECASE
)
_LIFECYCLE_DECL_PATTERN = re.compile(
    r'(?:onCreate|onDestroy|onWindowStageCreate|onForeground|onBackground|生命周期回调)',
    re.IGNORECASE
)


def check_p088(text: str) -> Finding | None:
    rule = _RULE_MAP["P088"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _LIFECYCLE_PATTERN.search(text):
        return None
    if _LIFECYCLE_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_PERMISSION_PATTERN = re.compile(
    r'(?:权限|permission|ohos\.permission|授权|隐私|敏感)',
    re.IGNORECASE
)
_PERMISSION_DECL_PATTERN = re.compile(
    r'(?:ohos\.permission|requestPermissionsFromUser|acquirePermissions|权限声明)',
    re.IGNORECASE
)


def check_p089(text: str) -> Finding | None:
    rule = _RULE_MAP["P089"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _PERMISSION_PATTERN.search(text):
        return None
    if _PERMISSION_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_ARKUI_COMPONENT = re.compile(
    r'(?:List|Grid|WaterFlow|Swiper|Tabs|Navigator|Video|Web|Canvas|XComponent)',
    re.IGNORECASE
)
_API_VERSION_DECL = re.compile(
    r'(?:API\s*\d+|SDK\s*\d+|version.*\d+|最低.*API|兼容.*版本)',
    re.IGNORECASE
)


def check_p090(text: str) -> Finding | None:
    rule = _RULE_MAP["P090"]
    if not _HARMONYOS_CTX.search(text):
        return None
    components = _ARKUI_COMPONENT.findall(text)
    if not components:
        return None
    if _API_VERSION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=f"{rule.description} (组件: {', '.join(components[:5])})",
        remediation=rule.remediation,
        details={"components": components[:5]},
    )


_RESOURCE_REF_PATTERN = re.compile(
    r'(?:资源|图片|图标|字符串|媒体|resource|image|icon|string|media)',
    re.IGNORECASE
)
_STANDARD_REF_PATTERN = re.compile(
    r'(?:\$r\(|\$rawfile\(|app\.string|app\.media|app\.color)',
    re.IGNORECASE
)


def check_p091(text: str) -> Finding | None:
    rule = _RULE_MAP["P091"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _RESOURCE_REF_PATTERN.search(text):
        return None
    if _STANDARD_REF_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_THREAD_PATTERN = re.compile(
    r'(?:耗时|异步|并发|多线程|计算密集|CPU|后台任务|async|concurrent|worker|thread)',
    re.IGNORECASE
)
_THREAD_DECL_PATTERN = re.compile(
    r'(?:TaskPool|Worker|@Concurrent|线程模型|主线程|子线程|taskpool|worker线程)',
    re.IGNORECASE
)


def check_p092(text: str) -> Finding | None:
    rule = _RULE_MAP["P092"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _THREAD_PATTERN.search(text):
        return None
    if _THREAD_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_DATA_MGMT_PATTERN = re.compile(
    r'(?:数据存储|持久化|数据库|缓存|偏好设置|SQLite|RDB|Preferences|DataShare|relational)',
    re.IGNORECASE
)
_DATA_DECL_PATTERN = re.compile(
    r'(?:关系型数据库|RDB|Preferences|DataShare|分布式数据|@ohos\.data|数据管理策略)',
    re.IGNORECASE
)


def check_p093(text: str) -> Finding | None:
    rule = _RULE_MAP["P093"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _DATA_MGMT_PATTERN.search(text):
        return None
    if _DATA_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_NETWORK_PATTERN = re.compile(
    r'(?:HTTP|HTTPS|网络请求|接口调用|API.*请求|fetch|axios|xhr|rest|graphql)',
    re.IGNORECASE
)
_NETSEC_DECL_PATTERN = re.compile(
    r'(?:HTTPS|证书锁定|certificatePinning|publicKeyPinning|网络安全配置|securityConfig|SSL|TLS|禁止明文)',
    re.IGNORECASE
)


def check_p094(text: str) -> Finding | None:
    rule = _RULE_MAP["P094"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _NETWORK_PATTERN.search(text):
        return None
    if _NETSEC_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_SIGN_PATTERN = re.compile(
    r'(?:签名|发布|上架|应用市场|HAP.*构建|AppGallery|分发|provision|profile)',
    re.IGNORECASE
)
_SIGN_DECL_PATTERN = re.compile(
    r'(?:\.p12|\.p7b|\.cer|签名配置|调试签名|发布签名|AGC|AppGallery Connect|Provision.*Profile)',
    re.IGNORECASE
)


def check_p095(text: str) -> Finding | None:
    rule = _RULE_MAP["P095"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _SIGN_PATTERN.search(text):
        return None
    if _SIGN_DECL_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def run_checks_p086_p095(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p086, check_p087, check_p088, check_p089, check_p090,
               check_p091, check_p092, check_p093, check_p094, check_p095]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
