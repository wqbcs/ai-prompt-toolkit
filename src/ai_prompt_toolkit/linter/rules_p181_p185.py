"""P181-P185 Prompt运维Lint规则

Prompt生产运维最佳实践(参考promptfoo versioning + Langfuse deployment):
- P181: Prompt版本声明缺失(生产环境必须有版本号)
- P182: Prompt依赖声明缺失(外部API/模型/工具依赖需显式声明)
- P183: Prompt环境隔离不足(生产/测试/开发环境配置隔离)
- P184: Prompt降级策略缺失(模型不可用时无降级方案)
- P185: Prompt灰度发布配置缺失(新版本灰度发布策略)

覆盖OWASP LLM06(Excessive Agency), LLM09(Overreliance)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P181_P185 = [
    LintRule(
        "P181",
        "版本声明缺失",
        "operations",
        Severity.HIGH,
        "Prompt缺少版本声明, 生产环境无法追踪变更和回滚",
        "在Prompt头部添加版本声明, 如 version: 1.2.3 或 v=1.2.3",
        description_en="Prompt lacks version declaration, production cannot track changes or rollback",
        remediation_en="Add version declaration in Prompt header, e.g. version: 1.2.3",
        family="prompt_versioning",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P182",
        "依赖声明缺失",
        "operations",
        Severity.MEDIUM,
        "Prompt缺少外部依赖声明(模型/API/工具), 变更时无法评估影响范围",
        "声明Prompt依赖的模型版本、API端点、工具列表, 如 dependencies: [gpt-4, weather-api]",
        description_en="Prompt lacks dependency declaration (model/API/tool), cannot assess impact on change",
        remediation_en="Declare model version, API endpoints, tool list in Prompt, e.g. dependencies: [gpt-4, weather-api]",
        family="prompt_dependencies",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P183",
        "环境隔离不足",
        "operations",
        Severity.MEDIUM,
        "Prompt缺少环境隔离配置, 生产/测试/开发环境可能混用导致意外行为",
        "为不同环境配置不同参数(模型/温度/约束), 使用环境变量或配置文件隔离",
        description_en="Prompt lacks environment isolation, prod/test/dev may mix causing unexpected behavior",
        remediation_en="Configure different parameters per environment (model/temperature/constraints), use env vars or config files",
        family="prompt_isolation",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P184",
        "降级策略缺失",
        "operations",
        Severity.MEDIUM,
        "Prompt缺少降级策略, 当主模型不可用时无备用方案, 服务可能中断",
        "声明降级策略: 主模型→备用模型→规则回复, 如 fallback: [gpt-3.5, template-response]",
        description_en="Prompt lacks degradation strategy, no fallback when primary model unavailable, service may break",
        remediation_en="Declare fallback: primary→secondary→rule-based, e.g. fallback: [gpt-3.5, template-response]",
        family="prompt_degradation",
        owasp_refs=["LLM09"],
    ),
    LintRule(
        "P185",
        "灰度发布配置缺失",
        "operations",
        Severity.MEDIUM,
        "Prompt缺少灰度发布配置, 新版本全量上线无法控制风险暴露面",
        "配置灰度策略: 流量百分比/用户分桶/A-B对比, 如 canary: 10% or ab_test: [v1, v2]",
        description_en="Prompt lacks canary deployment config, new version full rollout has uncontrolled risk exposure",
        remediation_en="Configure canary: traffic percentage/user bucketing/A-B test, e.g. canary: 10% or ab_test: [v1, v2]",
        family="prompt_canary",
        owasp_refs=["LLM06"],
    ),
]

for r in _RULES_P181_P185:
    _RULE_MAP[r.rule_id] = r

_VERSION_PATTERN = re.compile(
    # R179: 支持引号包裹的版本值(frontmatter里常见 version: "2.0")
    r"(?:version|v|ver)[\"']?\s*[:=]\s*[\"']?v?[\d.]+",
    re.IGNORECASE,
)
_DEP_PATTERN = re.compile(r"(?:依赖|depend|requires?|model|api|tool)\s*[:=]", re.IGNORECASE)
_ENV_PATTERN = re.compile(r"(?:env|environment|stage|profile|NODE_ENV|APP_ENV)\s*[:=]", re.IGNORECASE)
_FALLBACK_PATTERN = re.compile(r"(?:降级|fallback|degradation|备用|backup|secondary|retry)", re.IGNORECASE)
_CANARY_PATTERN = re.compile(r"(?:灰度|canary|gradual|rollout|ab.test|ab-test|bucket|分桶)", re.IGNORECASE)


# R207校准: 版本声明仅对生产环境prompt强制(生产无法追踪变更=HIGH语义成立) —
# 本地草稿/测试prompt要求版本属过度要求(R206前97%误报)。
# 与P055共用生产场景语义: 部署失败=排障场景, 发布说明=文档类,
# "不直接修改生产集群"=安全约束声明(非生产部署声明)。
_P181_PROD_CTX = re.compile(
    r"(?:生产(?!库)|production|部署(?!失败)|deploy(?!\s+fail)|上线|正式环境|(?<![A-Za-z0-9_/.-])prod(?![A-Za-z0-9_-])|发布(?!说明|notes|检查单|日期|前))",
    re.IGNORECASE,
)
_P181_PROD_NEGATION = re.compile(r"(?:不|禁止|避免|勿|无需|no|without|avoid)\s*\S{0,4}$", re.IGNORECASE)


def _has_prod_ctx(text: str) -> bool:
    for m in _P181_PROD_CTX.finditer(text):
        if _P181_PROD_NEGATION.search(text[max(0, m.start() - 8) : m.start()]):
            continue
        return True
    return False


def check_p181(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if not _VERSION_PATTERN.search(text):
        if not _has_prod_ctx(text):
            return findings
        findings.append(Finding("P181", Severity.HIGH, "Prompt缺少版本声明, 建议添加version字段", "1", "1"))
    return findings


def check_p182(text: str) -> list[Finding]:
    findings = []
    if not _DEP_PATTERN.search(text):
        # R211校准: 原has_api_call裸泛词(API|接口|调用|endpoint|fetch|request|http)
        # 使"工具调用/请求体/调用"等一切动词即触发, R210扩样暴露8/56误报。
        # 依赖声明真实面=API实体+调用类动作共现(调用weather API获取天气),
        # "写API文档/审查API设计/接口测试生成"本身不构成外部依赖调用。
        has_api_entity = bool(
            re.search(r"API|接口|endpoint|webhook|REST|gRPC|外部(服务|接口|API)|第三方(服务|接口)", text, re.IGNORECASE)
        )
        has_api_use = bool(
            re.search(
                r"(?:调用|invoke|invokes|invocation|fetch|integrat\w*|calls|requests|query|查询|集成)",
                text,
                re.IGNORECASE,
            )
        )
        if has_api_entity and has_api_use:
            findings.append(Finding("P182", Severity.MEDIUM, "Prompt调用外部API但缺少依赖声明", "1", "1"))
    return findings


def check_p183(text: str) -> list[Finding]:
    findings = []
    has_env = _ENV_PATTERN.search(text)
    if not has_env:
        # R211校准: 原裸多环境词(dev/test/prod/staging)命中单元测试/接口
        # 测试/发布说明等文档prompt(裸"测试"即触发), R210扩样暴露11/56误报。
        # 环境隔离真实触发面=≥2个不同环境名与"环境"共现(开发环境用X,
        # 测试环境用Y), 或 environment+config 英文组合。
        env_names = {
            m.group(1).lower()
            for m in re.finditer(r"(开发|测试|生产|预发|dev|staging|prod|uat)\s*环境", text, re.IGNORECASE)
        }
        has_multi_config = len(env_names) >= 2 or bool(
            re.search(r"environment.{0,12}(?:different|isolat|separat|config)", text, re.IGNORECASE)
        )
        if has_multi_config:
            findings.append(Finding("P183", Severity.MEDIUM, "提及多环境但缺少环境隔离配置", "1", "1"))
    return findings


def check_p184(text: str) -> list[Finding]:
    findings = []
    if not _FALLBACK_PATTERN.search(text):
        has_model = bool(re.search(r"(?:GPT|Claude|模型|model|LLM|大模型)", text, re.IGNORECASE))
        if has_model:
            findings.append(Finding("P184", Severity.MEDIUM, "Prompt依赖模型但缺少降级策略", "1", "1"))
    return findings


def check_p185(text: str) -> list[Finding]:
    findings = []
    if not _CANARY_PATTERN.search(text):
        has_deploy = bool(re.search(r"(?:部署|上线|发布|deploy|release|rollout)", text, re.IGNORECASE))
        if has_deploy:
            findings.append(Finding("P185", Severity.MEDIUM, "提及部署发布但缺少灰度配置", "1", "1"))
    return findings
