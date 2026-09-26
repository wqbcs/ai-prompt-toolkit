"""Lint规则集扩展——P121-P130 鸿蒙HarmonyOS NEXT专项规则

R53新增(赛事贴合-鸿蒙HarmonyOS NEXT 5.0+):
- P121: ArkTS严格模式合规 — 检测鸿蒙开发Prompt是否声明ArkTS严格模式
- P122: Stage模型生命周期规范 — 检测是否声明Stage模型生命周期管理
- P123: Ability路由声明 — 检测鸿蒙Ability路由声明完整性
- P124: 权限最小化声明 — 检测鸿蒙权限声明是否遵循最小化原则
- P125: 多设备适配声明 — 检测鸿蒙多设备(手机/平板/手表)适配声明
- P126: 无障碍访问规范 — 检测鸿蒙应用的无障碍访问规范声明
- P127: 鸿蒙安全沙箱声明 — 检测鸿蒙安全沙箱/数据隔离声明
- P128: 分布式数据管理规范 — 检测鸿蒙分布式数据管理声明
- P129: 元服务卡片规范 — 检测鸿蒙元服务/卡片开发规范声明
- P130: 鸿蒙网络安全规范 — 检测鸿蒙网络安全/HTTPS/证书规范声明
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P121_P130: list[LintRule] = [
    LintRule(
        "P121",
        "ArkTS严格模式合规缺失",
        "quality",
        Severity.HIGH,
        "鸿蒙开发Prompt未声明ArkTS严格模式合规要求",
        "声明ArkTS严格模式: '遵循ArkTS严格模式, 禁用any类型, 使用类型安全API'",
        description_en="HarmonyOS development Prompt missing ArkTS strict mode compliance declaration",
        remediation_en="Declare ArkTS strict mode: 'Follow ArkTS strict mode, disable any type, use type-safe API'",
        family="arkts_strict",
    ),
    LintRule(
        "P122",
        "Stage模型生命周期规范缺失",
        "structure",
        Severity.HIGH,
        "鸿蒙开发Prompt未声明Stage模型生命周期管理规范",
        "声明生命周期: '遵循Stage模型生命周期, 正确实现onCreate/onDestroy/onForeground/onBackground'",
        description_en="HarmonyOS Prompt missing Stage model lifecycle management specification",
        remediation_en="Declare lifecycle: 'Follow Stage model lifecycle, properly implement onCreate/onDestroy/onForeground/onBackground'",
        family="stage_lifecycle",
    ),
    LintRule(
        "P123",
        "Ability路由声明缺失",
        "structure",
        Severity.MEDIUM,
        "鸿蒙开发Prompt涉及页面导航但未声明Ability路由规范",
        "声明路由规范: '使用Navigation组件管理路由, 声明router配置, 遵循路由参数规范'",
        description_en="HarmonyOS Prompt involves navigation but missing Ability routing specification",
        remediation_en="Declare routing: 'Use Navigation component for routing, declare router config, follow routing parameter spec'",
        family="ability_routing",
    ),
    LintRule(
        "P124",
        "权限最小化声明缺失",
        "security",
        Severity.HIGH,
        "鸿蒙开发Prompt涉及权限请求但未声明最小化原则",
        "声明权限最小化: '遵循最小权限原则, 仅申请必要权限, 使用ohos.permission.*规范声明'",
        description_en="HarmonyOS Prompt involves permissions but missing least-privilege declaration",
        remediation_en="Declare least privilege: 'Follow least privilege principle, only request necessary permissions, use ohos.permission.* spec'",
        family="permission_minimal",
    ),
    LintRule(
        "P125",
        "多设备适配声明缺失",
        "quality",
        Severity.MEDIUM,
        "鸿蒙开发Prompt未声明多设备(手机/平板/手表/2in1)适配策略",
        "声明多设备适配: '使用断点系统实现响应式布局, 适配phone/tablet/wearable/2in1设备'",
        description_en="HarmonyOS Prompt missing multi-device adaptation strategy declaration",
        remediation_en="Declare multi-device adaptation: 'Use breakpoint system for responsive layout, adapt to phone/tablet/wearable/2in1'",
        family="multi_device",
    ),
    LintRule(
        "P126",
        "无障碍访问规范缺失",
        "quality",
        Severity.MEDIUM,
        "鸿蒙开发Prompt未声明无障碍访问规范(屏幕阅读器/无障碍组件)",
        "声明无障碍: '遵循Web Accessibility规范, 使用无障碍组件, 提供contentDescription/ariaLabel'",
        description_en="HarmonyOS Prompt missing accessibility specification (screen reader/accessible components)",
        remediation_en="Declare accessibility: 'Follow accessibility spec, use accessible components, provide contentDescription/ariaLabel'",
        family="accessibility",
    ),
    LintRule(
        "P127",
        "鸿蒙安全沙箱声明缺失",
        "security",
        Severity.HIGH,
        "鸿蒙开发Prompt涉及数据存储/共享但未声明安全沙箱数据隔离",
        "声明安全沙箱: '应用运行在独立沙箱中, 数据隔离存储, 跨应用数据共享需通过DataShare'",
        description_en="HarmonyOS Prompt involves data storage/sharing but missing sandbox data isolation declaration",
        remediation_en="Declare sandbox: 'App runs in isolated sandbox, data stored separately, cross-app sharing via DataShare'",
        family="sandbox",
    ),
    LintRule(
        "P128",
        "分布式数据管理规范缺失",
        "structure",
        Severity.MEDIUM,
        "鸿蒙开发Prompt涉及分布式场景但未声明分布式数据管理规范",
        "声明分布式规范: '使用分布式数据管理, 遵循数据同步策略, 声明distributedData配置'",
        description_en="HarmonyOS Prompt involves distributed scenarios but missing distributed data management specification",
        remediation_en="Declare distributed spec: 'Use distributed data management, follow sync strategy, declare distributedData config'",
        family="distributed_data",
    ),
    LintRule(
        "P129",
        "元服务卡片规范缺失",
        "quality",
        Severity.MEDIUM,
        "鸿蒙开发Prompt涉及卡片/元服务但未声明FormExtension规范",
        "声明卡片规范: '遵循FormExtension规范, 声明卡片生命周期, 控制卡片更新频率≤1次/小时'",
        description_en="HarmonyOS Prompt involves widget/service but missing FormExtension specification",
        remediation_en="Declare widget spec: 'Follow FormExtension spec, declare widget lifecycle, control update frequency ≤1/hour'",
        family="form_extension",
    ),
    LintRule(
        "P130",
        "鸿蒙网络安全规范缺失",
        "security",
        Severity.HIGH,
        "鸿蒙开发Prompt涉及网络请求但未声明HTTPS/证书/网络安全规范",
        "声明网络安全: '强制使用HTTPS, 配置网络安全策略, 声明certificate pinning, 遵循ohos.net规范'",
        description_en="HarmonyOS Prompt involves network requests but missing HTTPS/certificate/network security specification",
        remediation_en="Declare network security: 'Enforce HTTPS, configure network security policy, declare certificate pinning, follow ohos.net spec'",
        family="network_security",
    ),
]

for r in _RULES_P121_P130:
    _RULE_MAP[r.rule_id] = r


_HARMONYOS_CTX = re.compile(
    r"(?:鸿蒙|HarmonyOS|harmonyos|Harmony|OHOS|ohos|OpenHarmony|openharmony|ArkTS|arkts|Stage模型|Ability|元服务|卡片)",
    re.IGNORECASE,
)


_ARKTS_STRICT = re.compile(
    r"(?:严格模式|strict.?mode|类型安全|type.?safe|禁止.*any|no.*any|ArkTS.*规范|arkts.*spec)", re.IGNORECASE
)


def check_p121(text: str) -> Finding | None:
    rule = _RULE_MAP["P121"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if _ARKTS_STRICT.search(text):
        return None
    _ARKTS_REF = re.compile(r"(?:ArkTS|arkts|TypeScript|typescript|ets|\.ets)", re.IGNORECASE)
    if not _ARKTS_REF.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_STAGE_LIFECYCLE = re.compile(
    r"(?:onCreate|onDestroy|onForeground|onBackground|生命周期|lifecycle|aboutToAppear|aboutToDisappear|onPageShow|onPageHide)",
    re.IGNORECASE,
)


def check_p122(text: str) -> Finding | None:
    rule = _RULE_MAP["P122"]
    if not _HARMONYOS_CTX.search(text):
        return None
    _ABILITY_REF = re.compile(r"(?:Ability|UIAbility|Stage|stage模型|页面|page)", re.IGNORECASE)
    if not _ABILITY_REF.search(text):
        return None
    if _STAGE_LIFECYCLE.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_ROUTING_PATTERN = re.compile(r"(?:路由|router|导航|navigation|跳转|redirect|页面.*切换|page.*switch)", re.IGNORECASE)
_ROUTING_DECL = re.compile(
    r"(?:Navigation|router.*配置|路由.*参数|router.*parameter|路由.*规范|router.*spec)", re.IGNORECASE
)


def check_p123(text: str) -> Finding | None:
    rule = _RULE_MAP["P123"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _ROUTING_PATTERN.search(text):
        return None
    if _ROUTING_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_PERMISSION_PATTERN = re.compile(
    r"(?:权限|permission|ohos\.permission|授权|authorize|requestPermission)", re.IGNORECASE
)
_PERMISSION_MINIMAL = re.compile(
    r"(?:最小.*权限|least.?privilege|必要.*权限|necessary.*permission|最小化|minimal|ohos\.permission\.\*)",
    re.IGNORECASE,
)


def check_p124(text: str) -> Finding | None:
    rule = _RULE_MAP["P124"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _PERMISSION_PATTERN.search(text):
        return None
    if _PERMISSION_MINIMAL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_MULTI_DEVICE = re.compile(
    r"(?:多设备|手机|平板|手表|wearable|tablet|phone|2in1|折叠|foldable|响应式|responsive|断点|breakpoint)",
    re.IGNORECASE,
)
_MULTI_DEVICE_DECL = re.compile(
    r"(?:断点.*系统|breakpoint.*system|响应式.*布局|responsive.*layout|多设备.*适配|multi.?device.*adapt|屏幕.*适配|screen.*adapt)",
    re.IGNORECASE,
)


def check_p125(text: str) -> Finding | None:
    rule = _RULE_MAP["P125"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _MULTI_DEVICE.search(text):
        return None
    if _MULTI_DEVICE_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_ACCESSIBILITY_PATTERN = re.compile(
    r"(?:无障碍|accessibility|屏幕阅读器|screen.?reader|辅助|assistive|障碍|障碍.*用户|视力|色盲|contentDescription|aria)",
    re.IGNORECASE,
)
_ACCESSIBILITY_DECL = re.compile(
    r"(?:无障碍.*规范|accessibility.*spec|无障碍.*组件|accessible.*component|contentDescription|ariaLabel|语义.*标签|semantic.*label)",
    re.IGNORECASE,
)


def check_p126(text: str) -> Finding | None:
    rule = _RULE_MAP["P126"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _ACCESSIBILITY_PATTERN.search(text):
        return None
    if _ACCESSIBILITY_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_DATA_PATTERN = re.compile(
    r"(?:数据.*存储|数据.*共享|文件.*存储|数据库|preference|DataShare|沙箱|sandbox|数据.*隔离)", re.IGNORECASE
)
_SANDBOX_DECL = re.compile(
    r"(?:沙箱|sandbox|数据.*隔离|data.*isolat|DataShare|独立.*沙箱|isolated.*sandbox|跨应用.*DataShare)", re.IGNORECASE
)


def check_p127(text: str) -> Finding | None:
    rule = _RULE_MAP["P127"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _DATA_PATTERN.search(text):
        return None
    if _SANDBOX_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_DISTRIBUTED_PATTERN = re.compile(
    r"(?:分布式|distributed|跨设备|cross.?device|同步|sync|设备.*迁移|device.*migrat|流转|流转.*数据)", re.IGNORECASE
)
_DISTRIBUTED_DECL = re.compile(
    r"(?:分布式.*数据|distributed.*data|数据.*同步.*策略|sync.*strategy|distributedData|数据.*管理.*规范|data.*management.*spec)",
    re.IGNORECASE,
)


def check_p128(text: str) -> Finding | None:
    rule = _RULE_MAP["P128"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _DISTRIBUTED_PATTERN.search(text):
        return None
    if _DISTRIBUTED_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_FORM_PATTERN = re.compile(r"(?:卡片|widget|元服务|atomic.?service|FormExtension|服务卡片|桌面卡片)", re.IGNORECASE)
_FORM_DECL = re.compile(
    r"(?:FormExtension|卡片.*生命周期|widget.*lifecycle|更新.*频率|update.*frequency|卡片.*规范|widget.*spec)",
    re.IGNORECASE,
)


def check_p129(text: str) -> Finding | None:
    rule = _RULE_MAP["P129"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _FORM_PATTERN.search(text):
        return None
    if _FORM_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_NETWORK_PATTERN = re.compile(
    r"(?:网络|HTTP|https|请求|request|API.*调用|接口|fetch|axios|ohos\.net|socket|websocket)", re.IGNORECASE
)
_NETWORK_DECL = re.compile(
    r"(?:HTTPS|证书.*固定|certificate.*pinning|网络安全.*策略|network.*security.*policy|ohos\.net|TLS|安全.*传输|secure.*transport)",
    re.IGNORECASE,
)


def check_p130(text: str) -> Finding | None:
    rule = _RULE_MAP["P130"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _NETWORK_PATTERN.search(text):
        return None
    if _NETWORK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def run_checks_p121_p130(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [
        check_p121,
        check_p122,
        check_p123,
        check_p124,
        check_p125,
        check_p126,
        check_p127,
        check_p128,
        check_p129,
        check_p130,
    ]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
