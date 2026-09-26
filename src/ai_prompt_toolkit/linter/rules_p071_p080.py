"""Lint规则集扩展——P071-P080 华为云生态专项规则

覆盖华为云/鸿蒙生态特有场景:
- 华为云API endpoint校验
- 昇腾NPU适配声明
- IAM认证方式指定
- 鸿蒙API版本兼容性
- 华为云区域指定
- ModelArts部署配置
- 服务配额限制提示
- 鸿蒙应用沙箱权限
- 数据合规跨境声明
- SLA降级策略
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P071_P080: list[LintRule] = [
    LintRule(
        "P071",
        "华为云API Endpoint缺失校验",
        "security",
        Severity.MEDIUM,
        "涉及华为云API调用的Prompt未声明具体的endpoint地址",
        "添加endpoint声明, 如 https://maas.cn-north-4.myhuaweicloud.com",
        description_en="Huawei Cloud API Prompt does not declare specific endpoint address",
        remediation_en="Add endpoint declaration, e.g., https://maas.cn-north-4.myhuaweicloud.com",
        family="huawei_endpoint",
    ),
    LintRule(
        "P072",
        "昇腾NPU适配声明缺失",
        "performance",
        Severity.MEDIUM,
        "涉及模型训练或推理的Prompt未声明昇腾NPU适配信息",
        "添加NPU适配说明, 如 '本任务适配华为昇腾NPU, 使用CANN算子库'",
        description_en="Model training/inference Prompt does not declare Ascend NPU adaptation info",
        remediation_en="Add NPU adaptation statement, e.g., 'This task is adapted for Huawei Ascend NPU, using CANN operator library'",
        family="ascend_npu",
    ),
    LintRule(
        "P073",
        "华为云IAM认证方式未指定",
        "security",
        Severity.HIGH,
        "涉及华为云服务调用的Prompt未指定IAM认证方式",
        "指定认证方式: AK/SK, IAM Token, 或Agency委托",
        description_en="Huawei Cloud service Prompt does not specify IAM authentication method",
        remediation_en="Specify authentication method: AK/SK, IAM Token, or Agency delegation",
        family="huawei_iam",
    ),
    LintRule(
        "P074",
        "鸿蒙API版本兼容性声明缺失",
        "quality",
        Severity.MEDIUM,
        "鸿蒙开发Prompt未声明目标API版本和最低兼容版本",
        "声明目标版本和最低兼容版本, 如 'HarmonyOS NEXT 5.0+, 最低兼容API 12'",
        description_en="HarmonyOS development Prompt does not declare target API version and minimum compatible version",
        remediation_en="Declare target version and minimum compatible version, e.g., 'HarmonyOS NEXT 5.0+, minimum compatible API 12'",
        family="harmony_api_version",
    ),
    LintRule(
        "P075",
        "华为云区域未指定",
        "quality",
        Severity.LOW,
        "涉及华为云部署的Prompt未指定目标部署区域",
        "指定部署区域, 如 cn-north-4(华北-北京四)",
        description_en="Huawei Cloud deployment Prompt does not specify target deployment region",
        remediation_en="Specify deployment region, e.g., cn-north-4 (North China-Beijing 4)",
        family="huawei_region",
    ),
    LintRule(
        "P076",
        "ModelArts模型部署配置缺失",
        "quality",
        Severity.MEDIUM,
        "涉及ModelArts的Prompt未声明模型部署规格和资源配置",
        "声明部署规格, 如 'GPU: V100 1卡, 内存: 32GB, 并发: 10'",
        description_en="ModelArts Prompt does not declare model deployment specifications and resource configuration",
        remediation_en="Declare deployment specs, e.g., 'GPU: V100 x1, Memory: 32GB, Concurrency: 10'",
        family="modelarts_deploy",
    ),
    LintRule(
        "P077",
        "华为云服务配额限制提示缺失",
        "quality",
        Severity.LOW,
        "涉及华为云资源使用的Prompt未提示服务配额和限流策略",
        "添加配额提示, 如 'API调用限流: 100次/分钟, 超限自动排队'",
        description_en="Huawei Cloud resource Prompt does not indicate service quota and rate limiting policy",
        remediation_en="Add quota notice, e.g., 'API rate limit: 100 calls/minute, auto-queuing when exceeded'",
        family="huawei_quota",
    ),
    LintRule(
        "P078",
        "鸿蒙应用沙箱权限声明缺失",
        "security",
        Severity.MEDIUM,
        "鸿蒙应用开发Prompt未声明应用沙箱和权限边界",
        "声明权限边界, 如 '仅申请网络和存储权限, 不申请位置和通讯录权限'",
        description_en="HarmonyOS app development Prompt does not declare app sandbox and permission boundaries",
        remediation_en="Declare permission boundaries, e.g., 'Only request network and storage permissions, not location and contacts'",
        family="harmony_sandbox",
    ),
    LintRule(
        "P079",
        "华为云数据合规跨境声明缺失",
        "compliance",
        Severity.HIGH,
        "涉及数据处理或存储的华为云Prompt未声明数据合规和跨境传输要求",
        "添加合规声明, 如 '数据存储于中国境内, 符合数据安全法和个保法要求'",
        description_en="Huawei Cloud data processing/storage Prompt does not declare data compliance and cross-border transfer requirements",
        remediation_en="Add compliance declaration, e.g., 'Data stored within China, compliant with Data Security Law and PIPL requirements'",
        family="compliance_gdpr",
    ),
    LintRule(
        "P080",
        "华为云SLA降级策略缺失",
        "quality",
        Severity.LOW,
        "涉及华为云服务依赖的Prompt未声明SLA降级和服务降级策略",
        "添加SLA声明, 如 '可用性: 99.95%, 降级策略: 自动切换备用区域'",
        description_en="Huawei Cloud service dependency Prompt does not declare SLA degradation and service degradation strategy",
        remediation_en="Add SLA declaration, e.g., 'Availability: 99.95%, degradation strategy: auto-switch to backup region'",
        family="compliance_audit",
    ),
]

for r in _RULES_P071_P080:
    _RULE_MAP[r.rule_id] = r


_HW_CLOUD_API_PATTERN = re.compile(
    r"(?:华为云|huawei.?cloud|api\.huaweicloud|maas\.cn|modelarts|ecs|obs|ris)", re.IGNORECASE
)
_ENDPOINT_PATTERN = re.compile(r"(?:endpoint|端点|接口地址|https://[a-z0-9.-]+\.myhuaweicloud\.com)", re.IGNORECASE)

_NPU_PATTERN = re.compile(r"(?:训练|推理|模型部署|train|inference|deploy|GPU|显卡|算力)", re.IGNORECASE)
_NPU_ADAPT_PATTERN = re.compile(r"(?:昇腾|NPU|CANN|Ascend|达芬奇|DaVinci)", re.IGNORECASE)

_IAM_PATTERN = re.compile(r"(?:华为云.*认证|huawei.*auth|IAM|ak/sk|密钥|secret|token|凭证)", re.IGNORECASE)
_IAM_METHOD_PATTERN = re.compile(r"(?:AK/SK|IAM Token|Agency|委托|永久安全凭证|临时安全凭证)", re.IGNORECASE)

_HARMONYOS_API_PATTERN = re.compile(r"(?:HarmonyOS|鸿蒙|ArkTS|ArkUI|Stage模型|Ability)", re.IGNORECASE)
_API_VERSION_PATTERN = re.compile(r"(?:API\s*\d+|SDK\s*\d+|HarmonyOS.*\d+\.\d+|NEXT\s*\d+|版本.*\d+)", re.IGNORECASE)

_REGION_PATTERN = re.compile(
    r"(?:cn-north|cn-east|cn-south|cn-southwest|ap-southeast|region|区域|部署区域|华北|华东|华南|亚太)", re.IGNORECASE
)

_MODELARTS_PATTERN = re.compile(r"(?:ModelArts|模型部署|在线服务|推理部署|训练作业)", re.IGNORECASE)
_DEPLOY_SPEC_PATTERN = re.compile(r"(?:GPU|V100|A300|Ascend|内存|并发|规格|flavor|instance)", re.IGNORECASE)

_QUOTA_PATTERN = re.compile(r"(?:配额|限流|QPS|QPM|rate.?limit|quota|throttl)", re.IGNORECASE)

_SANDBOX_PATTERN = re.compile(r"(?:沙箱|sandbox|权限声明|permission|ohos\.permission)", re.IGNORECASE)
_PERMISSION_PATTERN = re.compile(
    r"(?:网络|存储|位置|通讯录|相机|麦克风|internet|storage|location|contacts)", re.IGNORECASE
)

_DATA_COMPLIANCE_PATTERN = re.compile(
    r"(?:数据存储|数据处理|数据传输|跨境|数据安全|个人信息|隐私|data.?storage|data.?process|cross.?border)",
    re.IGNORECASE,
)
_COMPLIANCE_DECL_PATTERN = re.compile(
    r"(?:数据安全法|个保法|个人信息保护法|GDPR|境内存储|合规|compliance)", re.IGNORECASE
)

_SLA_PATTERN = re.compile(r"(?:SLA|可用性|降级|容灾|灾备|disaster.?recovery|failover|高可用)", re.IGNORECASE)
_SLA_DECL_PATTERN = re.compile(r"(?:99\.\d+%|降级策略|备用|切换|fallback)", re.IGNORECASE)


def check_p071(text: str) -> Finding | None:
    rule = _RULE_MAP["P071"]
    has_api = bool(_HW_CLOUD_API_PATTERN.search(text))
    if not has_api:
        return None
    has_endpoint = bool(_ENDPOINT_PATTERN.search(text))
    if has_endpoint:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p072(text: str) -> Finding | None:
    rule = _RULE_MAP["P072"]
    has_npu_context = bool(_NPU_PATTERN.search(text))
    if not has_npu_context:
        return None
    has_npu_adapt = bool(_NPU_ADAPT_PATTERN.search(text))
    if has_npu_adapt:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p073(text: str) -> Finding | None:
    rule = _RULE_MAP["P073"]
    has_iam = bool(_IAM_PATTERN.search(text))
    if not has_iam:
        return None
    has_method = bool(_IAM_METHOD_PATTERN.search(text))
    if has_method:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p074(text: str) -> Finding | None:
    rule = _RULE_MAP["P074"]
    is_harmonyos = bool(_HARMONYOS_API_PATTERN.search(text))
    if not is_harmonyos:
        return None
    has_version = bool(_API_VERSION_PATTERN.search(text))
    if has_version:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p075(text: str) -> Finding | None:
    rule = _RULE_MAP["P075"]
    has_deploy = bool(_HW_CLOUD_API_PATTERN.search(text))
    if not has_deploy:
        return None
    has_region = bool(_REGION_PATTERN.search(text))
    if has_region:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p076(text: str) -> Finding | None:
    rule = _RULE_MAP["P076"]
    has_modelarts = bool(_MODELARTS_PATTERN.search(text))
    if not has_modelarts:
        return None
    has_spec = bool(_DEPLOY_SPEC_PATTERN.search(text))
    if has_spec:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p077(text: str) -> Finding | None:
    rule = _RULE_MAP["P077"]
    has_hw_cloud = bool(_HW_CLOUD_API_PATTERN.search(text))
    if not has_hw_cloud:
        return None
    has_quota = bool(_QUOTA_PATTERN.search(text))
    if has_quota:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p078(text: str) -> Finding | None:
    rule = _RULE_MAP["P078"]
    is_harmonyos = bool(_HARMONYOS_API_PATTERN.search(text))
    if not is_harmonyos:
        return None
    has_sandbox = bool(_SANDBOX_PATTERN.search(text))
    has_permission = bool(_PERMISSION_PATTERN.search(text))
    if has_sandbox or has_permission:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p079(text: str) -> Finding | None:
    rule = _RULE_MAP["P079"]
    has_data = bool(_DATA_COMPLIANCE_PATTERN.search(text))
    if not has_data:
        return None
    has_compliance = bool(_COMPLIANCE_DECL_PATTERN.search(text))
    if has_compliance:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p080(text: str) -> Finding | None:
    rule = _RULE_MAP["P080"]
    has_sla = bool(_SLA_PATTERN.search(text))
    if not has_sla:
        return None
    has_sla_decl = bool(_SLA_DECL_PATTERN.search(text))
    if has_sla_decl:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def run_checks_p071_p080(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [
        check_p071,
        check_p072,
        check_p073,
        check_p074,
        check_p075,
        check_p076,
        check_p077,
        check_p078,
        check_p079,
        check_p080,
    ]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
