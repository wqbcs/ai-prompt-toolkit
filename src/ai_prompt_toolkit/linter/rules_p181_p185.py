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


def check_p181(text: str) -> list[Finding]:
    findings = []
    if not _VERSION_PATTERN.search(text):
        has_production = bool(re.search(r"(?:生产|production|prod|deploy|发布)", text, re.IGNORECASE))
        severity = Severity.HIGH if has_production else Severity.MEDIUM
        findings.append(Finding("P181", severity, "Prompt缺少版本声明, 建议添加version字段", "1", "1"))
    return findings


def check_p182(text: str) -> list[Finding]:
    findings = []
    if not _DEP_PATTERN.search(text):
        has_api_call = bool(re.search(r"(?:API|接口|调用|endpoint|fetch|request|http)", text, re.IGNORECASE))
        if has_api_call:
            findings.append(Finding("P182", Severity.MEDIUM, "Prompt调用外部API但缺少依赖声明", "1", "1"))
    return findings


def check_p183(text: str) -> list[Finding]:
    findings = []
    has_env = _ENV_PATTERN.search(text)
    if not has_env:
        has_multi_config = bool(re.search(r"(?:开发|测试|生产|dev|test|prod|staging|uat|预发)", text, re.IGNORECASE))
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
