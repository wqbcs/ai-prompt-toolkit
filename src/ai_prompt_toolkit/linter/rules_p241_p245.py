"""P241-P245 Prompt合规审计Lint规则

Prompt合规与审计(Compliance & Audit)最佳实践:
- P241: GDPR数据最小化违规(Prompt收集超出必要范围的个人数据)
- P242: AI Act透明度缺失(未声明AI生成内容/决策逻辑不透明)
- P243: 数据保留策略缺失(无明确数据保留期限和删除策略)
- P244: 审计日志不完整(关键操作未记录/日志不可追溯)
- P245: 跨境数据传输合规(数据跨境传输未做合规评估)

覆盖OWASP LLM02(Sensitive Information) + LLM07(Unauthorized Actions)
"""
from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP
from ai_prompt_toolkit.types import Finding, Severity


_RULES_P241_P245 = [
    LintRule("P241", "GDPR数据最小化违规", "compliance_audit", Severity.HIGH,
             "Prompt收集超出必要范围的个人数据(姓名/地址/身份证/健康), 违反GDPR数据最小化原则",
             "数据最小化: 仅收集任务必需数据+匿名化/假名化+定期审查, 如 collect(name='optional', email='required', address='excluded')",
             description_en="Prompt collects personal data beyond necessary scope (name/address/ID/health), violating GDPR data minimization",
             remediation_en="Data minimization: collect only task-essential data+anonymization+pseudonymization+regular review",
             family="compliance_gdpr_minimization", owasp_refs=["LLM02"]),
    LintRule("P242", "AI Act透明度缺失", "compliance_audit", Severity.MEDIUM,
             "未声明输出为AI生成内容或决策逻辑不透明, 违反EU AI Act透明度要求",
             "AI透明度: 显式声明AI生成+可解释性(XAI)+决策日志+人类监督, 如 add_disclaimer('AI生成内容') + explain_decision(model, input)",
             description_en="Output not declared as AI-generated or decision logic opaque, violating EU AI Act transparency requirements",
             remediation_en="AI transparency: explicit AI declaration+XAI+decision log+human oversight",
             family="compliance_ai_act_transparency", owasp_refs=["LLM07"]),
    LintRule("P243", "数据保留策略缺失", "compliance_audit", Severity.MEDIUM,
             "无明确数据保留期限和自动删除策略, 违反GDPR存储限制原则",
             "数据保留: 定义retention_period+自动删除+数据分类+合规审查, 如 set_retention(personal_data, period='30d', auto_delete=True)",
             description_en="No explicit data retention period or auto-deletion policy, violating GDPR storage limitation",
             remediation_en="Data retention: define retention_period+auto-deletion+data classification+compliance review",
             family="compliance_data_retention", owasp_refs=["LLM02"]),
    LintRule("P244", "审计日志不完整", "compliance_audit", Severity.HIGH,
             "关键操作(查询/修改/删除)未记录审计日志或日志不可追溯",
             "审计日志: 记录who/what/when/why+不可篡改(append-only)+定期审查+异常告警, 如 audit_log(user, action='query', resource=data, timestamp=now)",
             description_en="Critical operations lack audit logging or logs are not traceable",
             remediation_en="Audit logging: record who/what/when/why+append-only+regular review+anomaly alerting",
             family="compliance_audit_log", owasp_refs=["LLM07"]),
    LintRule("P245", "跨境数据传输合规", "compliance_audit", Severity.HIGH,
             "数据跨境传输未做合规评估(GDPR第44-49条/中国数据出境安全评估)",
             "跨境合规: 数据本地化+标准合同条款(SCC)+充分性认定+安全评估, 如 assess_cross_border(data, destination='EU', mechanism='SCC')",
             description_en="Cross-border data transfer lacks compliance assessment (GDPR Art.44-49/China Data Export Security Assessment)",
             remediation_en="Cross-border compliance: data localization+SCC+adequacy decision+security assessment",
             family="compliance_cross_border", owasp_refs=["LLM02"]),
]

for r in _RULES_P241_P245:
    _RULE_MAP[r.rule_id] = r

_PERSONAL_DATA_PATTERN = re.compile(r'(?:姓名|name|地址|address|身份证|ID.card|护照|passport|手机号|phone|邮箱|email|健康|health|医疗|medical|种族|race|宗教|religion|政治|politic|生物特征|biometric)', re.IGNORECASE)
_MINIMIZE_PATTERN = re.compile(r'(?:匿名|anonymiz|假名|pseudonym|最小化|minimiz|脱敏|desensitiz|仅收集|only.collect|必要|essential|required)', re.IGNORECASE)
_AI_GEN_PATTERN = re.compile(r'(?:AI生成|AI.generated|由AI|generated.by|模型输出|model.output|机器生成|machine.generated|自动生成|auto.generated)', re.IGNORECASE)
_TRANSPARENCY_PATTERN = re.compile(r'(?:透明|transparen|可解释|explainab|XAI|disclaimer|声明|声明AI|disclose|公开决策|人类监督|human.oversight)', re.IGNORECASE)
_RETENTION_PATTERN = re.compile(r'(?:保留|retention|存储期限|storage.period|删除策略|deletion.policy|auto.delete|自动删除|数据生命周期|data.lifecycle|保留期|retention.period)', re.IGNORECASE)
_AUDIT_PATTERN = re.compile(r'(?:审计|audit|日志|log|记录|record|trace|追溯|append.only|不可篡改|immutab)', re.IGNORECASE)
_CRITICAL_OP_PATTERN = re.compile(r'(?:删除|delete|修改|update|查询|query|访问|access|导出|export|下载|download|权限变更|permission.change)', re.IGNORECASE)
_CROSS_BORDER_PATTERN = re.compile(r'(?:跨境|cross.border|出境|export.*data|国际|international|海外|oversea|GDPR.*Art|数据出境|data.transfer.*border)', re.IGNORECASE)
_COMPLIANCE_PATTERN = re.compile(r'(?:合规|compliance|SCC|标准合同|充分性认定|adequacy|安全评估|security.assess|数据本地化|data.localiz)', re.IGNORECASE)


def check_p241(text: str) -> list[Finding]:
    findings = []
    if _PERSONAL_DATA_PATTERN.search(text) and not _MINIMIZE_PATTERN.search(text):
        findings.append(Finding("P241", Severity.HIGH, "收集个人数据超出必要范围(缺匿名化/数据最小化)", 1, 1))
    return findings


def check_p242(text: str) -> list[Finding]:
    findings = []
    has_model = re.search(r'(?:model|模型|AI|LLM|GPT|generate|生成)', text, re.IGNORECASE)
    if has_model and not _AI_GEN_PATTERN.search(text) and not _TRANSPARENCY_PATTERN.search(text):
        findings.append(Finding("P242", Severity.MEDIUM, "AI输出未声明透明度(缺AI声明/可解释性/人类监督)", 1, 1))
    return findings


def check_p243(text: str) -> list[Finding]:
    findings = []
    if _PERSONAL_DATA_PATTERN.search(text) and not _RETENTION_PATTERN.search(text):
        findings.append(Finding("P243", Severity.MEDIUM, "个人数据无保留策略(缺retention_period/自动删除)", 1, 1))
    return findings


def check_p244(text: str) -> list[Finding]:
    findings = []
    if _CRITICAL_OP_PATTERN.search(text) and not _AUDIT_PATTERN.search(text):
        findings.append(Finding("P244", Severity.HIGH, "关键操作未记录审计日志(缺who/what/when/why)", 1, 1))
    return findings


def check_p245(text: str) -> list[Finding]:
    findings = []
    if _CROSS_BORDER_PATTERN.search(text) and not _COMPLIANCE_PATTERN.search(text):
        findings.append(Finding("P245", Severity.HIGH, "跨境数据传输未做合规评估(缺SCC/安全评估/本地化)", 1, 1))
    return findings
