"""Lint规则集扩展——P156-P160 Prompt运维安全规范

R74新增(Prompt运维安全实践):
- P156: Prompt版本管理缺失
- P157: Prompt灰度发布策略缺失
- P158: Prompt数据脱敏声明缺失
- P159: Prompt沙箱隔离声明缺失
- P160: Prompt回滚机制声明缺失

参考: OWASP LLM Top 10 LLM06/LLM08, promptfoo安全断言, gptcache语义缓存设计
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P156_P160: list[LintRule] = [
    LintRule(
        "P156",
        "Prompt版本管理缺失",
        "structure",
        Severity.MEDIUM,
        "Prompt未声明版本管理(语义版本/变更日志/兼容性标注)",
        "声明版本管理: 采用语义版本(如v1.2.3), 维护变更日志, 标注向前兼容性",
        description_en="Prompt missing version management declaration",
        remediation_en="Declare version management: Use semantic versioning (e.g. v1.2.3), maintain changelog, mark forward compatibility",
        family="version_management",
    ),
    LintRule(
        "P157",
        "Prompt灰度发布策略缺失",
        "structure",
        Severity.MEDIUM,
        "Prompt未声明灰度发布策略(流量百分比/AB测试/逐步放量)",
        "声明灰度策略: 初始5%流量观察, 异常率<0.1%逐步放量至100%, 支持秒级回滚",
        description_en="Prompt missing canary/grayscale deployment strategy declaration",
        remediation_en="Declare canary strategy: Start at 5% traffic, scale to 100% if error rate<0.1%, support instant rollback",
        family="canary_deployment",
    ),
    LintRule(
        "P158",
        "Prompt数据脱敏声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明数据脱敏策略(PII检测/字段掩码/日志脱敏)",
        "声明脱敏策略: 对PII(姓名/身份证/手机号/邮箱)进行掩码, 日志中禁止输出原始敏感字段",
        description_en="Prompt missing data masking/desensitization declaration",
        remediation_en="Declare masking: Mask PII (name/ID/phone/email), prohibit raw sensitive fields in logs",
        family="data_masking",
    ),
    LintRule(
        "P159",
        "Prompt沙箱隔离声明缺失",
        "security",
        Severity.HIGH,
        "Prompt未声明沙箱隔离(执行环境隔离/资源限制/网络白名单)",
        "声明沙箱隔离: 执行环境容器化, 内存限制512MB, CPU限制1核, 网络仅允许白名单域名",
        description_en="Prompt missing sandbox isolation declaration",
        remediation_en="Declare sandbox: Containerized execution, memory limit 512MB, CPU limit 1 core, network whitelist only",
        family="sandbox_isolation",
    ),
    LintRule(
        "P160",
        "Prompt回滚机制声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明回滚机制(版本回滚/快照恢复/自动回滚触发条件)",
        "声明回滚机制: 保留最近3个版本快照, 异常率>1%自动回滚至上一稳定版本, 回滚耗时<30秒",
        description_en="Prompt missing rollback mechanism declaration",
        remediation_en="Declare rollback: Keep last 3 version snapshots, auto-rollback if error rate>1%, rollback time<30s",
        family="rollback_mechanism",
    ),
]

for r in _RULES_P156_P160:
    _RULE_MAP[r.rule_id] = r

_VERSION_CTX = re.compile(
    r"(?:版本|version|发布|deploy|发布|release|迭代|iterat|更新|update|变更|chang|上线|rollout|CI|CD|pipeline|流水线)",
    re.IGNORECASE,
)

_VERSION_DECL = re.compile(
    r"(?:语义版本|semver|版本号|v\d+\.\d+|变更日志|changelog|兼容|compat|向前兼容|forward.*compat|版本管理|version.*manage|tag|标签)",
    re.IGNORECASE,
)

_CANARY_DECL = re.compile(
    r"(?:灰度|canary|金丝雀|灰度发布|canary.*deploy|流量.*百分比|traffic.*percent|AB.*测试|A/B.*test|逐步.*放量|gradual.*rollout|分流|traffic.*split|实验|experiment|feature.*flag|特性开关)",
    re.IGNORECASE,
)

# R206校准: 移除单字泛词(数据/信息/用户/输出/接口/存储/API/日志/字段/响应/记录/data/info/user/output/log/API/field) —
# 干净prompt的"输出格式/用户问题"等表述即误触发(100%误报率), 保留PII/批量/管道强语义词
_MASKING_CTX = re.compile(
    r"(?:PII|个人信息|个人数据|身份证|手机号|电话号码|银行卡|账户|凭据|凭证|密码|credential|password|批量.*数据|数据管道|data.?pipeline|etl|导出.*数据|数据.*导出|数据库.*写入|写入.*数据库)",
    re.IGNORECASE,
)

_MASKING_DECL = re.compile(
    r"(?:脱敏|desensitiz|掩码|mask|匿名|anonymi|PII|隐私|privacy|敏感.*字段|sensitive.*field|姓名.*掩码|name.*mask|身份证.*脱敏|ID.*mask|手机.*掩码|phone.*mask|邮箱.*脱敏|email.*mask|禁止.*原始|prohibit.*raw|星号|asterisk|\*{3,})",
    re.IGNORECASE,
)

# R168校准: 需"执行不可信代码/脚本"语义 — 裸"运行/调用/工具"过宽(写文档提到"代码块"也误触发)
_SANDBOX_CTX = re.compile(
    r"(?:(?:执行|运行|run|exec).{0,10}(?:代码|脚本|命令|code|script|command)|代码执行|脚本执行|动态执行|shell|命令行|用户提交.{0,10}(?:代码|脚本|内容)|插件执行|工具执行|untrusted|eval\()",
    re.IGNORECASE,
)

_SANDBOX_DECL = re.compile(
    r"(?:沙箱|sandbox|隔离|isolat|容器|container|Docker|docker|内存.*限制|memory.*limit|CPU.*限制|CPU.*limit|资源.*限制|resource.*limit|白名单|whitelist|网络.*策略|network.*policy|命名空间|namespace|cgroup|chroot|seccomp)",
    re.IGNORECASE,
)

_ROLLBACK_CTX = re.compile(
    r"(?:发布|deploy|上线|rollout|更新|update|版本|version|变更|chang|迁移|migrat|切换|switch|升级|upgrade)",
    re.IGNORECASE,
)

_ROLLBACK_DECL = re.compile(
    r"(?:回滚|rollback|回退|fallback|快照|snapshot|恢复|restor|版本.*回滚|version.*rollback|自动.*回滚|auto.*rollback|异常.*回滚|error.*rollback|回滚.*耗时|rollback.*time|回滚.*触发|rollback.*trigger|稳定版本|stable.*version|保留.*版本|keep.*version)",
    re.IGNORECASE,
)


def check_p156(text: str) -> Finding | None:
    rule = _RULE_MAP["P156"]
    if not _VERSION_CTX.search(text):
        return None
    if _VERSION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p157(text: str) -> Finding | None:
    rule = _RULE_MAP["P157"]
    if not _VERSION_CTX.search(text):
        return None
    if _CANARY_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p158(text: str) -> Finding | None:
    rule = _RULE_MAP["P158"]
    if not _MASKING_CTX.search(text):
        return None
    if _MASKING_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p159(text: str) -> Finding | None:
    rule = _RULE_MAP["P159"]
    if not _SANDBOX_CTX.search(text):
        return None
    if _SANDBOX_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p160(text: str) -> Finding | None:
    rule = _RULE_MAP["P160"]
    if not _ROLLBACK_CTX.search(text):
        return None
    if _ROLLBACK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
