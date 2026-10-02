"""P246-P250 Prompt治理与运营安全Lint规则

Prompt治理(Governance)与运营安全最佳实践:
- P246: Prompt版本审计缺失(无版本控制/变更审批/回滚能力)
- P247: A/B测试安全风险(实验分流泄露用户数据/不公平歧视)
- P248: Prompt漂移检测(生产Prompt与基准偏离, 行为不一致)
- P249: 级联Prompt风险(Prompt链式调用错误传播/无限循环)
- P250: Prompt缓存中毒(共享缓存污染导致恶意输出注入)

覆盖OWASP LLM06(Excessive Agency) + LLM04(Unauthorized Actions)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P246_P250 = [
    LintRule(
        "P246",
        "Prompt版本审计缺失",
        "prompt_governance",
        Severity.HIGH,
        "Prompt无版本控制/变更审批/回滚能力, 无法追溯变更历史",
        "版本审计: Git管理+变更审批(CR)+自动diff+回滚预案, 如 prompt_version=v2.3.1, approve_change(author, reviewers=['sec', 'qa'])",
        description_en="Prompt lacks version control/change approval/rollback, cannot trace change history",
        remediation_en="Version audit: Git management+change approval(CR)+auto diff+rollback plan",
        family="governance_version_audit",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P247",
        "A/B测试安全风险",
        "prompt_governance",
        Severity.MEDIUM,
        "A/B实验分流可能泄露用户数据或不公平歧视(如按种族/性别分流)",
        "A/B安全: 匿名分流+公平性验证+数据隔离+最小暴露, 如 ab_test(group=hash(user_id)%2, exclude_pii=True, fairness_check=True)",
        description_en="A/B experiment routing may leak user data or cause unfair discrimination",
        remediation_en="A/B safety: anonymous routing+fairness validation+data isolation+minimal exposure",
        family="governance_ab_safety",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P248",
        "Prompt漂移检测",
        "prompt_governance",
        Severity.HIGH,
        "生产Prompt与基准版本偏离, 行为不一致或质量降级",
        "漂移检测: 语义diff+行为回归测试+自动告警+基线对比, 如 semantic_diff(current, baseline) + regression_test(output_compare)",
        description_en="Production Prompt deviates from baseline, causing inconsistent behavior or quality degradation",
        remediation_en="Drift detection: semantic diff+behavior regression test+auto alert+baseline comparison",
        family="governance_drift_detection",
        owasp_refs=["LLM06"],
    ),
    LintRule(
        "P249",
        "级联Prompt风险",
        "prompt_governance",
        Severity.HIGH,
        "Prompt链式调用存在错误传播/无限循环/资源耗尽风险",
        "级联防护: 最大深度限制+超时控制+错误隔离+断路器, 如 max_depth=5, timeout=30s, circuit_breaker(failure_rate=0.3), error_isolation=True",
        description_en="Prompt chain calls have error propagation/infinite loop/resource exhaustion risks",
        remediation_en="Cascade defense: max depth+timeout+error isolation+circuit breaker",
        family="governance_cascade",
        owasp_refs=["LLM04"],
    ),
    LintRule(
        "P250",
        "Prompt缓存中毒",
        "prompt_governance",
        Severity.HIGH,
        "共享Prompt缓存可被污染, 导致恶意输出注入到其他用户响应",
        "缓存安全: 命名空间隔离+签名验证+TTL+缓存清洗, 如 cache_ns=user_id, verify_signature(cached), ttl=300s, sanitize(cache_entry)",
        description_en="Shared Prompt cache can be poisoned, injecting malicious output into other users' responses",
        remediation_en="Cache security: namespace isolation+signature verification+TTL+cache sanitization",
        family="governance_cache_poison",
        owasp_refs=["LLM04"],
    ),
]

for r in _RULES_P246_P250:
    _RULE_MAP[r.rule_id] = r

# 注: 裸版本号(frontmatter "version: 1.0.0")不触发 — 有版本化流程证据(changelog/release/变更记录)才要求配套治理
_VERSION_PATTERN = re.compile(
    r"(?:changelog|变更日志|变更记录|release|发布记录|版本发布|版本.{0,6}更新|更新.{0,6}版本)", re.IGNORECASE
)
_AUDIT_PATTERN = re.compile(r"(?:audit|审计|审批|approve|review|CR|code.review|变更审批|rollback|回滚)", re.IGNORECASE)
_AB_TEST_PATTERN = re.compile(r"(?:A/B|ab.test|experiment|实验|分流|variant|control.group|treatment)", re.IGNORECASE)
_AB_SECURE_PATTERN = re.compile(
    r"(?:匿名|anonym|fairness|公平|隔离|isolat|exclude_pii|最小暴露|minimal)", re.IGNORECASE
)
_DRIFT_PATTERN = re.compile(r"(?:drift|漂移|偏离|baseline|基准|regression|回归|diff|差异|行为不一致)", re.IGNORECASE)
_DRIFT_SECURE_PATTERN = re.compile(
    r"(?:semantic.diff|语义diff|regression.test|回归测试|auto.alert|自动告警|baseline.compare|基线对比)", re.IGNORECASE
)
_CHAIN_PATTERN = re.compile(
    r"(?:chain|链式|cascade|级联|pipeline|管道|sequential|顺序调用|递归|recursi|loop|循环)", re.IGNORECASE
)
_CHAIN_SECURE_PATTERN = re.compile(
    r"(?:max.depth|最大深度|timeout|超时|circuit.breaker|断路器|error.isolat|错误隔离)", re.IGNORECASE
)
_CACHE_PATTERN = re.compile(r"(?:cache|缓存|memoize|memo|cached|shared.cache|共享缓存|redis|memcache)", re.IGNORECASE)
_CACHE_SECURE_PATTERN = re.compile(
    r"(?:namespace|命名空间|isolat|隔离|signature|签名|verify|验证|TTL|ttl|sanitiz|清洗)", re.IGNORECASE
)


def check_p246(text: str) -> list[Finding]:
    findings = []
    if _VERSION_PATTERN.search(text) and not _AUDIT_PATTERN.search(text):
        findings.append(Finding("P246", Severity.HIGH, "Prompt有版本但缺变更审批/审计/回滚"))
    return findings


def check_p247(text: str) -> list[Finding]:
    findings = []
    if _AB_TEST_PATTERN.search(text) and not _AB_SECURE_PATTERN.search(text):
        findings.append(Finding("P247", Severity.MEDIUM, "A/B实验缺安全防护(匿名/公平性/数据隔离)"))
    return findings


def check_p248(text: str) -> list[Finding]:
    findings = []
    if _DRIFT_PATTERN.search(text) and not _DRIFT_SECURE_PATTERN.search(text):
        findings.append(Finding("P248", Severity.HIGH, "Prompt漂移检测缺安全措施(语义diff/回归测试/告警)"))
    return findings


def check_p249(text: str) -> list[Finding]:
    findings = []
    if _CHAIN_PATTERN.search(text) and not _CHAIN_SECURE_PATTERN.search(text):
        findings.append(Finding("P249", Severity.HIGH, "级联Prompt缺防护(最大深度/超时/断路器/错误隔离)"))
    return findings


def check_p250(text: str) -> list[Finding]:
    findings = []
    if _CACHE_PATTERN.search(text) and not _CACHE_SECURE_PATTERN.search(text):
        findings.append(Finding("P250", Severity.HIGH, "Prompt缓存缺安全防护(命名空间隔离/签名/TTL/清洗)"))
    return findings
