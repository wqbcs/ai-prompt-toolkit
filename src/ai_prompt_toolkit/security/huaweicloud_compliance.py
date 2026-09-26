"""华为云安全合规报告 — 面向华为云ModelArts/盘古大模型部署的安全合规检查

参考:
- 华为云安全白皮书 (等保2.0三级/GDPR/个人信息保护法)
- OWASP LLM Top 10 2025
- 华为云AI安全最佳实践 (模型部署/数据隐私/访问控制)

合规维度(7大域):
1. 数据隐私 — 个人信息保护法/GDPR合规(PII检测/数据脱敏/跨境传输)
2. 模型安全 — OWASP LLM Top 10 2025(注入/越狱/泄露/供应链)
3. 访问控制 — 最小权限原则/API鉴权/速率限制
4. 内容安全 — 内容审核/有害信息过滤/价值观对齐
5. 运维安全 — 日志审计/变更管理/应急响应
6. 供应链安全 — 依赖验证/模型来源/工具链完整性
7. 合规认证 — 等保2.0/ISO27001/CSA STAR映射

评分体系:
- 每域0-100分, 加权汇总为综合合规分
- 合规等级: A(90+)/B(75+)/C(60+)/D(40+)/F(<40)
- 决策: PASS/CONDITIONAL/FAIL
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


class ComplianceGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ComplianceDecision(str, Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"


@dataclass
class DomainResult:
    domain: str
    domain_name: str
    score: int
    max_score: int
    findings_count: int
    critical_count: int
    high_count: int
    checks_passed: int
    checks_total: int
    details: list[str] = field(default_factory=list)
    remediation: str = ""

    @property
    def ratio(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 1.0

    @property
    def pass_rate(self) -> float:
        return self.checks_passed / self.checks_total if self.checks_total > 0 else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "domain_name": self.domain_name,
            "score": self.score,
            "max_score": self.max_score,
            "ratio": round(self.ratio, 2),
            "findings_count": self.findings_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "pass_rate": round(self.pass_rate, 2),
            "details": self.details[:5],
            "remediation": self.remediation,
        }


_HUAWEICLOUD_DOMAIN_WEIGHTS = {
    "data_privacy": 0.20,
    "model_security": 0.20,
    "access_control": 0.15,
    "content_safety": 0.15,
    "ops_security": 0.10,
    "supply_chain": 0.10,
    "certification": 0.10,
}

_DOMAIN_NAMES = {
    "data_privacy": "数据隐私",
    "model_security": "模型安全",
    "access_control": "访问控制",
    "content_safety": "内容安全",
    "ops_security": "运维安全",
    "supply_chain": "供应链安全",
    "certification": "合规认证",
}

_SEVERITY_DEDUCTION = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFO: 0,
}

_PII_RULE_IDS = {"PII001", "PII002", "PII003"}
_INJECTION_PREFIXES = ("INJ-", "INJ-ZH-", "ANOMALY-")
_SUPPLY_CHAIN_PREFIXES = ("SC", "UNI", "CANARY")
_PROBE_PREFIX = "PROBE-"
_CONTENT_SAFETY_RULES = {"P106", "P107", "P108", "P109", "P110"}
_ACCESS_CONTROL_RULES = {"P087", "P088", "P089", "P095"}
_OPS_RULES = {"P092", "P097", "P098", "P099", "P100"}

_DOMAIN_REMEDIATIONS = {
    "data_privacy": "实施数据脱敏和分类分级，确保PII检测覆盖，遵守个人信息保护法第51条",
    "model_security": "加固Prompt注入防御，实施OWASP LLM Top 10修复建议，启用Probe扫描",
    "access_control": "实施最小权限原则，启用API鉴权和速率限制，定期审查权限配置",
    "content_safety": "部署内容审核过滤器，建立有害信息黑名单，确保价值观对齐",
    "ops_security": "启用华为云LTS日志审计，建立变更管理流程，制定应急响应预案",
    "supply_chain": "验证第三方依赖真实性，使用华为云SWR镜像签名，启用SBOM生成",
    "certification": "完成等保2.0三级测评，建立ISO27001体系，申请CSA STAR认证",
}


def _classify_to_domain(rule_id: str) -> str:
    if rule_id in _PII_RULE_IDS or "PII" in rule_id:
        return "data_privacy"
    if rule_id.startswith(_PROBE_PREFIX):
        return "model_security"
    if any(rule_id.startswith(p) for p in _INJECTION_PREFIXES):
        return "model_security"
    if any(rule_id.startswith(p) for p in _SUPPLY_CHAIN_PREFIXES):
        return "supply_chain"
    if rule_id in _CONTENT_SAFETY_RULES:
        return "content_safety"
    if rule_id in _ACCESS_CONTROL_RULES:
        return "access_control"
    if rule_id in _OPS_RULES:
        return "ops_security"
    if rule_id.startswith("STRUCT"):
        return "model_security"
    if rule_id.startswith("P"):
        return "content_safety"
    return "model_security"


def _compute_domain(
    domain_key: str,
    findings: list[Finding],
    max_score: int = 100,
) -> DomainResult:
    deduction = sum(_SEVERITY_DEDUCTION.get(f.severity, 0) for f in findings)
    score = max(0, max_score - deduction)
    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)
    checks_passed = max(1, 10 - len(findings))
    checks_total = 10
    details = [f"[{f.rule_id}] {f.description[:60]}" for f in findings[:5]]
    return DomainResult(
        domain=domain_key,
        domain_name=_DOMAIN_NAMES.get(domain_key, domain_key),
        score=score,
        max_score=max_score,
        findings_count=len(findings),
        critical_count=critical,
        high_count=high,
        checks_passed=checks_passed,
        checks_total=checks_total,
        details=details,
        remediation=_DOMAIN_REMEDIATIONS.get(domain_key, ""),
    )


@dataclass
class HuaweiCloudComplianceReport:
    report_id: str
    timestamp: str
    overall_score: int
    grade: ComplianceGrade
    decision: ComplianceDecision
    domains: list[DomainResult]
    total_findings: int
    critical_count: int
    high_count: int
    template_id: str = ""
    owasp_compliance_pct: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "platform": "华为云 ModelArts",
            "framework": "华为云AI安全合规 + OWASP LLM Top 10 2025",
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "decision": self.decision.value,
            "domains": [d.to_dict() for d in self.domains],
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "template_id": self.template_id,
            "owasp_compliance_pct": self.owasp_compliance_pct,
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = [
            "# 华为云安全合规报告",
            "",
            "| 字段 | 值 |",
            "|---|---|",
            f"| 报告ID | {self.report_id} |",
            f"| 时间 | {self.timestamp} |",
            "| 平台 | 华为云 ModelArts |",
            f"| 综合评分 | **{self.overall_score}/100** ({self.grade.value}) |",
            f"| 决策 | {self.decision.value} |",
            f"| OWASP合规率 | {self.owasp_compliance_pct}% |",
            f"| 发现总数 | {self.total_findings} (CRITICAL:{self.critical_count} HIGH:{self.high_count}) |",
            "",
            "## 合规域详情",
            "",
            "| 域 | 评分 | 通过率 | 发现 | CRITICAL | HIGH | 修复建议 |",
            "|---|---|---|---|---|---|---|",
        ]
        for d in self.domains:
            lines.append(
                f"| {d.domain_name} | {d.score}/{d.max_score} | {d.pass_rate:.0%} | "
                f"{d.findings_count} | {d.critical_count} | {d.high_count} | {d.remediation[:30]} |"
            )
        if self.summary:
            lines.extend(["", "## 总结", "", self.summary])
        return "\n".join(lines)


def compute_huaweicloud_compliance(
    findings: list[Finding],
    template_id: str = "",
    owasp_compliance_pct: float = 0.0,
) -> HuaweiCloudComplianceReport:
    buckets: dict[str, list[Finding]] = {k: [] for k in _HUAWEICLOUD_DOMAIN_WEIGHTS}
    for f in findings:
        domain = _classify_to_domain(f.rule_id)
        buckets[domain].append(f)

    domain_results: list[DomainResult] = []
    weighted_score = 0.0

    for domain_key, weight in _HUAWEICLOUD_DOMAIN_WEIGHTS.items():
        dr = _compute_domain(domain_key, buckets[domain_key])
        domain_results.append(dr)
        weighted_score += dr.ratio * weight * 100

    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    high = sum(1 for f in findings if f.severity == Severity.HIGH)

    overall = min(100, max(0, round(weighted_score)))
    if critical > 0:
        overall = min(overall, 35)
    elif high > 0:
        overall = min(overall, 65)

    if overall >= 90:
        grade = ComplianceGrade.A
    elif overall >= 75:
        grade = ComplianceGrade.B
    elif overall >= 60:
        grade = ComplianceGrade.C
    elif overall >= 40:
        grade = ComplianceGrade.D
    else:
        grade = ComplianceGrade.F

    if critical > 0:
        decision = ComplianceDecision.FAIL
    elif grade in (ComplianceGrade.A, ComplianceGrade.B):
        decision = ComplianceDecision.PASS
    elif grade == ComplianceGrade.C:
        decision = ComplianceDecision.CONDITIONAL
    else:
        decision = ComplianceDecision.FAIL

    total = len(findings)

    if critical > 0:
        summary = f"发现{critical}个严重风险，禁止上线，需立即修复"
    elif high > 0:
        summary = f"发现{high}个高风险，建议修复后再部署至华为云ModelArts"
    elif total > 0:
        summary = f"发现{total}个中低风险，可条件性部署，建议持续优化"
    else:
        summary = "安全合规检查全部通过，可安全部署至华为云ModelArts"

    report_id = f"HC-COMPLIANCE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.now(timezone.utc).isoformat()

    return HuaweiCloudComplianceReport(
        report_id=report_id,
        timestamp=timestamp,
        overall_score=overall,
        grade=grade,
        decision=decision,
        domains=domain_results,
        total_findings=total,
        critical_count=critical,
        high_count=high,
        template_id=template_id,
        owasp_compliance_pct=owasp_compliance_pct,
        summary=summary,
    )
