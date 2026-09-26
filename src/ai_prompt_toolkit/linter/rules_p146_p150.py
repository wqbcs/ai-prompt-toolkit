"""Lint规则集扩展——P146-P150 鸿蒙Stage模型深度检测
R71新增(鸿蒙Stage模型专项):
- P146: Stage模型UIAbility生命周期缺失 — 检测Stage模型Prompt是否声明UIAbility生命周期管理
- P147: Stage模型ExtensionAbility滥用 — 检测Stage模型Prompt是否声明ExtensionAbility使用边界
- P148: 鸿蒙分布式数据同步安全缺失 — 检测鸿蒙Prompt是否声明分布式数据同步安全策略
- P149: 鸿蒙ArkUI声明式范式违规 — 检测鸿蒙Prompt是否遵循ArkUI声明式开发范式
- P150: 鸿蒙卡片(Widget)更新策略缺失 — 检测鸿蒙元服务Prompt是否声明卡片更新策略
参考: HarmonyOS Stage Model Development Guide, ArkUI Best Practices
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_HARMONYOS_CTX = re.compile(
    r"(?:鸿蒙|HarmonyOS|harmonyos|Harmony|OHOS|ohos|OpenHarmony|openharmony|ArkTS|arkts|Stage模型|Ability|元服务|卡片)",
    re.IGNORECASE,
)

_STAGE_MODEL_CTX = re.compile(
    r"(?:Stage模型|UIAbility|ExtensionAbility|ServiceExtension|DataShareExtension|FormExtension|Stage|AbilityStage|Want|Caller|Callee)",
    re.IGNORECASE,
)

_DISTRIBUTED_CTX = re.compile(
    r"(?:分布式|distributed|跨设备|cross.device|数据同步|data.sync|软总线|SoftBus|设备发现|device.discovery)",
    re.IGNORECASE,
)

_ARKUI_CTX = re.compile(
    r"(?:ArkUI|arkui|声明式|declarative|@Component|@Builder|@State|@Prop|@Link|@Watch|@Provide|@Consume|@StorageLink|自定义组件)",
    re.IGNORECASE,
)

_WIDGET_CTX = re.compile(
    r"(?:卡片|Widget|widget|FormAbility|formExtension|元服务|AtomicService|桌面卡片|desktop.card|信息服务卡片)",
    re.IGNORECASE,
)

_LIFECYCLE_DECL = re.compile(
    r"(?:生命周期|lifecycle|onCreate|onDestroy|onForeground|onBackground|onWindowStageCreate|onWindowStageDestroy|Ability生命周期|状态管理)",
    re.IGNORECASE,
)

_EXTENSION_BOUNDARY = re.compile(
    r"(?:Extension.*边界|Extension.*限制|ServiceExtension.*用途|DataShare.*范围|FormExtension.*约束|最小权限|least.privilege|仅.*场景)",
    re.IGNORECASE,
)

_DISTRIBUTED_SAFETY = re.compile(
    r"(?:数据加密|data.encryption|端到端加密|E2EE|可信执行|TEE|安全通道|secure.channel|数据分级|data.classification|同步策略|sync.policy|冲突解决|conflict.resolution)",
    re.IGNORECASE,
)

_DECLARATIVE_PARADIGM = re.compile(
    r"(?:声明式|declarative|数据驱动|data.driven|单向数据流|unidirectional|状态不可变|immutable.state|无副作用|side.effect.free|@State.*驱动|响应式|reactive)",
    re.IGNORECASE,
)

_WIDGET_UPDATE_DECL = re.compile(
    r"(?:更新策略|update.policy|刷新频率|refresh.rate|定时更新|scheduled.update|按需更新|on.demand.update|数据源|data.source|form_provider|卡片更新|widget.refresh)",
    re.IGNORECASE,
)

_RULES_P146_P150: list[LintRule] = [
    LintRule(
        "P146",
        "Stage模型UIAbility生命周期缺失",
        "harmonyos",
        Severity.HIGH,
        "Stage模型Prompt未声明UIAbility生命周期管理(onCreate/onForeground/onBackground/onDestroy)",
        "声明生命周期: '在onCreate中初始化资源, onForeground恢复交互, onBackground暂停耗时操作, onDestroy释放资源'",
        description_en="Stage model Prompt missing UIAbility lifecycle management declaration",
        remediation_en="Declare lifecycle: 'Initialize resources in onCreate, resume interaction in onForeground, pause in onBackground, release in onDestroy'",
        family="harmonyos_stage",
    ),
    LintRule(
        "P147",
        "Stage模型ExtensionAbility滥用",
        "harmonyos",
        Severity.MEDIUM,
        "Stage模型Prompt未声明ExtensionAbility使用边界(ServiceExtension/DataShareExtension/FormExtension用途限制)",
        "声明Extension边界: 'ServiceExtension仅用于后台服务, DataShareExtension仅共享必要数据, FormExtension仅提供卡片能力'",
        description_en="Stage model Prompt missing ExtensionAbility usage boundary constraints",
        remediation_en="Declare Extension boundaries: 'ServiceExtension for background services only, DataShareExtension for necessary data sharing only, FormExtension for widget capabilities only'",
        family="harmonyos_stage",
    ),
    LintRule(
        "P148",
        "鸿蒙分布式数据同步安全缺失",
        "harmonyos",
        Severity.HIGH,
        "涉及分布式数据同步的鸿蒙Prompt未声明安全策略(数据加密/端到端加密/可信执行环境/数据分级/冲突解决)",
        "声明分布式安全: '敏感数据使用E2EE加密, 通过TEE可信通道传输, 数据分级存储, 冲突采用last-write-wins或用户选择策略'",
        description_en="HarmonyOS distributed data sync Prompt missing security policy declaration",
        remediation_en="Declare distributed security: 'Sensitive data uses E2EE, TEE trusted channel for transmission, data classification for storage, last-write-wins or user-choice for conflict resolution'",
        family="harmonyos_distributed",
    ),
    LintRule(
        "P149",
        "鸿蒙ArkUI声明式范式违规",
        "harmonyos",
        Severity.MEDIUM,
        "鸿蒙ArkUI Prompt未遵循声明式开发范式(数据驱动/单向数据流/状态不可变/无副作用)",
        "遵循声明式范式: '使用@State/@Prop/@Link驱动UI更新, 保持单向数据流, 状态修改通过回调, 避免命令式操作DOM'",
        description_en="HarmonyOS ArkUI Prompt not following declarative development paradigm",
        remediation_en="Follow declarative paradigm: 'Use @State/@Prop/@Link to drive UI updates, maintain unidirectional data flow, modify state via callbacks, avoid imperative DOM operations'",
        family="harmonyos_arkui",
    ),
    LintRule(
        "P150",
        "鸿蒙卡片(Widget)更新策略缺失",
        "harmonyos",
        Severity.MEDIUM,
        "鸿蒙元服务Prompt未声明卡片更新策略(刷新频率/定时更新/按需更新/数据源声明)",
        "声明卡片更新策略: '定时更新间隔>=30分钟, 按需更新仅在数据变化时触发, 声明form_provider数据源格式'",
        description_en="HarmonyOS widget Prompt missing update strategy declaration",
        remediation_en="Declare widget update strategy: 'Scheduled update interval >= 30min, on-demand update only on data changes, declare form_provider data source format'",
        family="harmonyos_widget",
    ),
]


def check_p146(text: str) -> Finding | None:
    rule = _RULE_MAP["P146"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _STAGE_MODEL_CTX.search(text):
        return None
    if _LIFECYCLE_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p147(text: str) -> Finding | None:
    rule = _RULE_MAP["P147"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _STAGE_MODEL_CTX.search(text):
        return None
    if _EXTENSION_BOUNDARY.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p148(text: str) -> Finding | None:
    rule = _RULE_MAP["P148"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _DISTRIBUTED_CTX.search(text):
        return None
    if _DISTRIBUTED_SAFETY.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p149(text: str) -> Finding | None:
    rule = _RULE_MAP["P149"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _ARKUI_CTX.search(text):
        return None
    if _DECLARATIVE_PARADIGM.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p150(text: str) -> Finding | None:
    rule = _RULE_MAP["P150"]
    if not _HARMONYOS_CTX.search(text):
        return None
    if not _WIDGET_CTX.search(text):
        return None
    if _WIDGET_UPDATE_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


for r in _RULES_P146_P150:
    _RULE_MAP[r.rule_id] = r
