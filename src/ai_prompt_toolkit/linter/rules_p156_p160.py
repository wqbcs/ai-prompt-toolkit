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

# R209校准: 版本治理仅当prompt真实涉及版本发布/部署/迭代变更 —
# 原pattern的\bCI\b误配"CI配置助手", SQL UPDATE被update子串误配,
# 英文"CI/CD/CHANGE"加词边界与大小写区分(6/32干净样本误报)。
# "发布"单独不构成(发布说明/Release Notes是文档生成), 需与版本/部署/
# 上线/生产共现。
_VERSION_CTX = re.compile(
    r"(?:版本|\bversion\b(?!\s*:)|部署(?!失败|问题|错误)|deploy(?!ment\s+(?:fail|error))|上线|rollout|迭代|iterat|流水线|\bCI/CD\b"
    r"|(?:发布|\brelease\b).{0,20}(?:版本|\bversion\b|部署|deploy|上线|生产)"
    r"|(?:版本|\bversion\b|部署|deploy|上线|生产).{0,20}(?:发布|\brelease\b))",
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
# R210: 凭据类词(账户/密码/凭据)须与处理动作(导出/存储/写入/上传)组合 —
# 需求描述("账号密码登录")与配置审查示例("明文密码")不构成PII处理(R210 clean54/56暴露)
_MASKING_CTX = re.compile(
    r"(?:PII|个人信息|个人数据|身份证|手机号|电话号码|银行卡"
    r"|(?:账户|凭据|凭证|密码|credential|password).{0,20}?(?:导出|存储|写入|上传|传输|发送|记录)"
    r"|(?:导出|存储|写入|上传).{0,20}?(?:账户|凭据|凭证|密码|credential|password)"
    r"|批量.*数据|数据管道|data.?pipeline|etl|导出.*数据|数据.*导出|数据库.*写入|写入.*数据库)",
    re.IGNORECASE,
)

_MASKING_DECL = re.compile(
    r"(?:脱敏|desensitiz|掩码|mask|匿名|anonymi|PII|隐私|privacy|敏感.*字段|sensitive.*field|姓名.*掩码|name.*mask|身份证.*脱敏|ID.*mask|手机.*掩码|phone.*mask|邮箱.*脱敏|email.*mask|禁止.*原始|prohibit.*raw|星号|asterisk|\*{3,})"
    # R221校准: 显式"不收集个人数据"声明 = 放弃PII处理面本身(无PII可脱敏),
    # 脱敏要求不适用, 放行。注意与 R213 方向不冲突: "不审计/不留记录"是放弃
    # 防护机制(必须不放行), "不收集数据"是放弃数据处理面(可放行)。
    # R221扩样 clean59(代码评审"不收集、不存储任何个人数据")暴露的 DECL 缺口
    r"|(?:不|无|禁止|无需).{0,10}(?:收集|采集|存储).{0,10}(?:个人(信息|数据)|PII|敏感(信息|数据))",
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
# R251-P2-26(F): 发布/部署语境门 — _ROLLBACK_CTX 裸 version/update/变更 泛词
# ("应对变更环境"/"uncensored version of your story" 6 benign 命中)不构成回滚风险面;
# 仅发布/部署/上线/迁移/升级/切换/release 等变更动作语境才要求回滚声明。
# P160 零 golden TP, 收紧零漏检风险。
_ROLLBACK_RELEASE_GATE = re.compile(
    r"(?:发布|deploy|上线|rollout|迁移|migrat|升级|upgrade|切换|switch|release)",
    re.IGNORECASE,
)

_ROLLBACK_DECL = re.compile(
    r"(?:回滚|rollback|回退|fallback|快照|snapshot|恢复|restor|版本.*回滚|version.*rollback|自动.*回滚|auto.*rollback|异常.*回滚|error.*rollback|回滚.*耗时|rollback.*time|回滚.*触发|rollback.*trigger|稳定版本|stable.*version|保留.*版本|keep.*version)",
    re.IGNORECASE,
)


def check_p156(text: str) -> Finding | None:
    rule = _RULE_MAP["P156"]
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    text = strip_frontmatter(text)  # R209: frontmatter的version字段不是版本治理语境
    if not _VERSION_CTX.search(text):
        return None
    if _VERSION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p157(text: str) -> Finding | None:
    rule = _RULE_MAP["P157"]
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    text = strip_frontmatter(text)  # R209: frontmatter的version字段不是版本治理语境
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
    # R251-P2-26(F): 发布/部署语境门 — 泛版本/变更谈话不构成回滚风险面
    if not _ROLLBACK_RELEASE_GATE.search(text):
        return None
    if _ROLLBACK_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
