"""P171-P175鸿蒙NEXT API 14适配Lint规则

HarmonyOS NEXT (API 14) 新特性安全适配:
- P171: ArkUI装饰器@Builder安全校验
- P172: LazyForEach数据源变更检测
- P173: @Reusable装饰器复用安全
- P174: UIAbility生命周期状态管理
- P175: 分布式数据同步安全

覆盖OWASP LLM06(Excessive Agency)
"""
from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP
from ai_prompt_toolkit.types import Finding, Severity


_RULES_P171_P175 = [
    LintRule("P171", "ArkUI@Builder安全校验", "harmonyos", Severity.HIGH,
             "Prompt生成@Builder装饰器代码缺少参数类型校验, 可能导致运行时类型错误",
             "为@Builder函数添加参数类型声明和空值检查, 如@Builder myBuilder(param: string = '')",
             description_en="Prompt-generated @Builder decorator code lacks parameter type validation, may cause runtime type errors",
             remediation_en="Add parameter type declarations and null checks to @Builder functions",
             family="harmonyos_next_arkui", owasp_refs=["LLM06"]),
    LintRule("P172", "LazyForEach数据源安全", "harmonyos", Severity.HIGH,
             "Prompt使用LazyForEach但未实现IDataSource接口的变更通知方法, 数据更新不会触发UI刷新",
             "实现IDataSource接口的totalCount()/getData()/registerDataChangeListener()/unregisterDataChangeListener()",
             description_en="Prompt uses LazyForEach without implementing IDataSource change notification, data updates won't trigger UI refresh",
             remediation_en="Implement IDataSource interface with totalCount/getData/registerDataChangeListener/unregisterDataChangeListener",
             family="harmonyos_next_lazy", owasp_refs=["LLM06"]),
    LintRule("P173", "@Reusable复用安全", "harmonyos", Severity.MEDIUM,
             "Prompt使用@Reusable装饰器但未处理组件复用时状态重置, 可能导致脏数据残留",
             "在aboutToReuse生命周期中重置组件状态, 清理上一次实例的残留数据",
             description_en="Prompt uses @Reusable decorator without state reset on reuse, may cause stale data residue",
             remediation_en="Reset component state in aboutToReuse lifecycle, clean up previous instance data",
             family="harmonyos_next_reusable", owasp_refs=["LLM06"]),
    LintRule("P174", "UIAbility生命周期管理", "harmonyos", Severity.HIGH,
             "Prompt生成UIAbility代码缺少onForeground/onBackground状态处理, 应用切换可能丢失上下文",
             "实现onForeground/onBackground回调, 保存/恢复应用状态和Prompt上下文",
             description_en="Prompt-generated UIAbility code lacks onForeground/onBackground handling, context may be lost on app switch",
             remediation_en="Implement onForeground/onBackground callbacks, save/restore app state and Prompt context",
             family="harmonyos_next_lifecycle", owasp_refs=["LLM06"]),
    LintRule("P175", "分布式数据同步安全", "harmonyos", Severity.HIGH,
             "Prompt使用分布式数据但未配置数据权限和加密, 跨设备同步可能泄露敏感信息",
             "为分布式数据配置访问权限(access权限组)和加密策略, 禁止敏感Prompt明文同步",
             description_en="Prompt uses distributed data without permission and encryption config, cross-device sync may leak sensitive info",
             remediation_en="Configure access permissions and encryption for distributed data, prohibit plaintext Prompt sync",
             family="harmonyos_next_distributed", owasp_refs=["LLM06"]),
]

for r in _RULES_P171_P175:
    _RULE_MAP[r.rule_id] = r


_BUILDER_PATTERN = re.compile(r"@Builder\s+(\w+)\s*\(", re.I)
_LAZY_PATTERN = re.compile(r"LazyForEach", re.I)
_REUSABLE_PATTERN = re.compile(r"@Reusable", re.I)
_UIABILITY_PATTERN = re.compile(r"UIAbility", re.I)
_DISTRIBUTED_PATTERN = re.compile(r"分布式|distributed|DistributedData|DataSync", re.I)


def check_p171(text: str) -> Finding | None:
    if _BUILDER_PATTERN.search(text) and not re.search(r"param\s*:\s*\w+", text):
        return Finding(rule_id="P171", severity=Severity.HIGH,
                       description="@Builder函数缺少参数类型声明",
                       remediation="为@Builder添加参数类型: @Builder myBuilder(param: string = '')")
    return None


def check_p172(text: str) -> Finding | None:
    if _LAZY_PATTERN.search(text) and not re.search(r"IDataSource|registerDataChangeListener", text):
        return Finding(rule_id="P172", severity=Severity.HIGH,
                       description="LazyForEach未实现IDataSource变更通知接口",
                       remediation="实现IDataSource: totalCount/getData/registerDataChangeListener/unregisterDataChangeListener")
    return None


def check_p173(text: str) -> Finding | None:
    if _REUSABLE_PATTERN.search(text) and not re.search(r"aboutToReuse", text):
        return Finding(rule_id="P173", severity=Severity.MEDIUM,
                       description="@Reusable组件未处理aboutToReuse状态重置",
                       remediation="在aboutToReuse()中重置组件状态, 清理残留数据")
    return None


def check_p174(text: str) -> Finding | None:
    if _UIABILITY_PATTERN.search(text) and not re.search(r"onForeground|onBackground", text):
        return Finding(rule_id="P174", severity=Severity.HIGH,
                       description="UIAbility缺少onForeground/onBackground状态回调",
                       remediation="实现onForeground/onBackground回调, 保存/恢复应用状态")
    return None


def check_p175(text: str) -> Finding | None:
    if _DISTRIBUTED_PATTERN.search(text) and not re.search(r"权限|permission|加密|encrypt", text, re.I):
        return Finding(rule_id="P175", severity=Severity.HIGH,
                       description="分布式数据未配置权限和加密",
                       remediation="为分布式数据配置access权限组和加密策略")
    return None
