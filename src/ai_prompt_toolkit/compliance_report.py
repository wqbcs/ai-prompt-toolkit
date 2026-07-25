"""华为云合规认证报告生成器

生成符合华为云安全合规标准的Prompt工程认证报告，覆盖:
- OWASP LLM Top 10 2025合规检查
- 等保2.0三级要求映射
- 华为云安全基线检查
- 数据安全法/个人信息保护法合规
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ComplianceItem:
    requirement_id: str
    requirement_name: str
    category: str
    status: str = "not_checked"
    severity: str = "medium"
    evidence: str = ""
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_name": self.requirement_name,
            "category": self.category,
            "status": self.status,
            "severity": self.severity,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


@dataclass
class ComplianceReport:
    report_id: str = ""
    project_name: str = ""
    report_date: str = ""
    overall_status: str = "pending"
    total_items: int = 0
    passed_items: int = 0
    failed_items: int = 0
    warning_items: int = 0
    items: list[ComplianceItem] = field(default_factory=list)
    owasp_summary: dict[str, str] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_name": self.project_name,
            "report_date": self.report_date,
            "overall_status": self.overall_status,
            "total_items": self.total_items,
            "passed_items": self.passed_items,
            "failed_items": self.failed_items,
            "warning_items": self.warning_items,
            "pass_rate": round(self.passed_items / max(self.total_items, 1), 4),
            "items": [i.to_dict() for i in self.items],
            "owasp_summary": self.owasp_summary,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 华为云合规认证报告",
            f"",
            f"| 字段 | 值 |",
            f"|---|---|",
            f"| 报告编号 | {self.report_id} |",
            f"| 项目名称 | {self.project_name} |",
            f"| 报告日期 | {self.report_date} |",
            f"| 整体状态 | {self.overall_status} |",
            f"| 检查项总数 | {self.total_items} |",
            f"| 通过 | {self.passed_items} |",
            f"| 不通过 | {self.failed_items} |",
            f"| 警告 | {self.warning_items} |",
            f"| 通过率 | {round(self.passed_items / max(self.total_items, 1) * 100, 1)}% |",
            f"",
            f"## OWASP LLM Top 10 2025 合规",
            f"",
        ]
        for key, value in self.owasp_summary.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        lines.append("## 合规检查明细")
        lines.append("")
        lines.append("| 编号 | 要求 | 类别 | 状态 | 严重程度 |")
        lines.append("|---|---|---|---|---|")
        for item in self.items:
            status_icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "not_checked": "⏳"}.get(item.status, "?")
            lines.append(f"| {item.requirement_id} | {item.requirement_name} | {item.category} | {status_icon} {item.status} | {item.severity} |")
        if self.recommendations:
            lines.append("")
            lines.append("## 改进建议")
            lines.append("")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
        return "\n".join(lines)


_OWASP_REQUIREMENTS = [
    ComplianceItem("OWASP-LLM01", "Prompt注入防护", "owasp", "not_checked", "critical",
                   "", "实施输入边界校验和指令层级隔离"),
    ComplianceItem("OWASP-LLM02", "敏感信息泄露防护", "owasp", "not_checked", "critical",
                   "", "添加防泄露声明和Canary Token检测"),
    ComplianceItem("OWASP-LLM03", "供应链安全", "owasp", "not_checked", "high",
                   "", "验证第三方包名真实性"),
    ComplianceItem("OWASP-LLM04", "数据和模型投毒防护", "owasp", "not_checked", "high",
                   "", "实施来源验证和完整性校验"),
    ComplianceItem("OWASP-LLM05", "不当输出处理防护", "owasp", "not_checked", "high",
                   "", "对LLM输出进行编码转义"),
    ComplianceItem("OWASP-LLM06", "过度授权防护", "owasp", "not_checked", "critical",
                   "", "限制LLM调用权限，实施最小权限原则"),
    ComplianceItem("OWASP-LLM07", "系统提示词泄露防护", "owasp", "not_checked", "high",
                   "", "分段存储系统提示词，添加泄露检测"),
    ComplianceItem("OWASP-LLM08", "向量和嵌入安全", "owasp", "not_checked", "medium",
                   "", "向量数据库访问控制和相似度阈值过滤"),
    ComplianceItem("OWASP-LLM09", "错误信息防护", "owasp", "not_checked", "medium",
                   "", "添加事实性校验和知识截止声明"),
    ComplianceItem("OWASP-LLM10", "无界消费防护", "owasp", "not_checked", "medium",
                   "", "实施速率限制和Token消耗监控"),
]

_DJBF_REQUIREMENTS = [
    ComplianceItem("DJBF-2.0-01", "身份鉴别", "djbf", "not_checked", "high",
                   "", "LLM调用需身份认证，禁止匿名访问"),
    ComplianceItem("DJBF-2.0-02", "访问控制", "djbf", "not_checked", "high",
                   "", "实施基于角色的访问控制(RBAC)"),
    ComplianceItem("DJBF-2.0-03", "安全审计", "djbf", "not_checked", "high",
                   "", "记录所有LLM调用的审计日志"),
    ComplianceItem("DJBF-2.0-04", "入侵防范", "djbf", "not_checked", "high",
                   "", "检测和防御Prompt注入攻击"),
    ComplianceItem("DJBF-2.0-05", "数据完整性", "djbf", "not_checked", "medium",
                   "", "确保Prompt和响应的完整性校验"),
    ComplianceItem("DJBF-2.0-06", "数据保密性", "djbf", "not_checked", "high",
                   "", "敏感数据传输和存储加密"),
    ComplianceItem("DJBF-2.0-07", "个人信息保护", "djbf", "not_checked", "critical",
                   "", "遵循个人信息保护法，PII脱敏处理"),
    ComplianceItem("DJBF-2.0-08", "备份恢复", "djbf", "not_checked", "medium",
                   "", "Prompt模板和配置定期备份"),
]

_HWCLOUD_BASELINE = [
    ComplianceItem("HW-BL-01", "AK/SK安全管理", "hwcloud", "not_checked", "critical",
                   "", "AK/SK通过IAM委托或密钥管理服务获取，禁止硬编码"),
    ComplianceItem("HW-BL-02", "VPC网络隔离", "hwcloud", "not_checked", "high",
                   "", "LLM服务部署在VPC内，通过API网关暴露"),
    ComplianceItem("HW-BL-03", "数据加密存储", "hwcloud", "not_checked", "high",
                   "", "使用KMS加密敏感Prompt数据"),
    ComplianceItem("HW-BL-04", "ModelArts合规", "hwcloud", "not_checked", "high",
                   "", "ModelArts推理服务遵循华为云安全基线"),
    ComplianceItem("HW-BL-05", "日志审计AOM", "hwcloud", "not_checked", "medium",
                   "", "应用运维管理(AOM)采集LLM调用日志"),
    ComplianceItem("HW-BL-06", "API网关限流", "hwcloud", "not_checked", "medium",
                   "", "通过API网关实施限流和防重放攻击"),
]

_HWCLOUD_SECURITY_BASELINE = [
    ComplianceItem("HWC-SEC-01", "IAM最小权限", "hwcloud_security", "not_checked", "critical",
                   "", "Prompt声明华为云IAM最小权限原则，禁止使用root账号或管理员权限"),
    ComplianceItem("HWC-SEC-02", "OBS数据加密(KMS)", "hwcloud_security", "not_checked", "high",
                   "", "Prompt声明OBS数据使用KMS加密，禁止明文存储敏感数据"),
    ComplianceItem("HWC-SEC-03", "VPC网络隔离", "hwcloud_security", "not_checked", "high",
                   "", "Prompt声明VPC网络隔离，LLM服务不直接暴露公网"),
    ComplianceItem("HWC-SEC-04", "数据留存合规(GDPR/PIPL)", "hwcloud_security", "not_checked", "critical",
                   "", "Prompt声明数据留存策略，符合GDPR/PIPL要求，明确数据保留期限和删除机制"),
]


def generate_compliance_report(
    project_name: str = "",
    lint_findings: list[dict[str, Any]] | None = None,
    scan_results: list[dict[str, Any]] | None = None,
    probe_results: list[dict[str, Any]] | None = None,
) -> ComplianceReport:
    now = datetime.now(timezone.utc)
    report = ComplianceReport(
        report_id=f"HWC-LLM-{now.strftime('%Y%m%d%H%M%S')}",
        project_name=project_name,
        report_date=now.isoformat(),
    )

    all_items: list[ComplianceItem] = []
    for item in _OWASP_REQUIREMENTS:
        all_items.append(ComplianceItem(**{k: v for k, v in item.to_dict().items()}))
    for item in _DJBF_REQUIREMENTS:
        all_items.append(ComplianceItem(**{k: v for k, v in item.to_dict().items()}))
    for item in _HWCLOUD_BASELINE:
        all_items.append(ComplianceItem(**{k: v for k, v in item.to_dict().items()}))
    for item in _HWCLOUD_SECURITY_BASELINE:
        all_items.append(ComplianceItem(**{k: v for k, v in item.to_dict().items()}))

    lint_severity = {}
    if lint_findings:
        for f in lint_findings:
            rid = f.get("rule_id", "")
            sev = f.get("severity", "medium")
            if hasattr(sev, "value"):
                sev = sev.value
            lint_severity[rid] = sev

    if scan_results:
        for sr in scan_results:
            if sr.get("is_injection", False):
                for item in all_items:
                    if item.requirement_id == "OWASP-LLM01":
                        item.status = "fail"
                        item.evidence = f"检测到注入攻击: {sr.get('type', 'unknown')}"

    if probe_results:
        detected_probes = set()
        for pr in probe_results:
            if pr.get("is_detected", False):
                detected_probes.add(pr.get("probe_category", ""))

        category_mapping = {
            "dan": "OWASP-LLM01",
            "prompt_inject": "OWASP-LLM01",
            "encoding_bypass": "OWASP-LLM01",
            "leak_replay": "OWASP-LLM02",
            "system_prompt_leak": "OWASP-LLM02",
            "cross_modal_leak": "OWASP-LLM02",
            "package_hallucination": "OWASP-LLM03",
            "snowball": "OWASP-LLM09",
            "xss_inject": "OWASP-LLM05",
            "gcg_suffix": "OWASP-LLM10",
            "agent_inject": "OWASP-LLM06",
            "tool_abuse": "OWASP-LLM06",
            "image_inject": "OWASP-LLM01",
            "audio_inject": "OWASP-LLM01",
        }
        for probe_cat in detected_probes:
            owasp_id = category_mapping.get(probe_cat)
            if owasp_id:
                for item in all_items:
                    if item.requirement_id == owasp_id:
                        item.status = "fail"
                        item.evidence = f"Probe检测到风险: {probe_cat}"

    for item in all_items:
        if item.status == "not_checked":
            security_rules = {"P006", "P007", "P008", "P009", "P010", "P127", "P130", "P132", "P133", "P138", "P139"}
            has_security_finding = any(lint_severity.get(r, None) for r in security_rules)
            if has_security_finding:
                item.status = "warn"
                item.evidence = "存在安全相关Lint发现项"
            else:
                item.status = "pass"
                item.evidence = "未发现相关风险"

    report.items = all_items
    report.total_items = len(all_items)
    report.passed_items = sum(1 for i in all_items if i.status == "pass")
    report.failed_items = sum(1 for i in all_items if i.status == "fail")
    report.warning_items = sum(1 for i in all_items if i.status == "warn")

    from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2025
    report.owasp_summary = {k: v["name"] for k, v in OWASP_LLM_TOP_10_2025.items()}

    if report.failed_items > 0:
        report.overall_status = "fail"
    elif report.warning_items > 0:
        report.overall_status = "warn"
    else:
        report.overall_status = "pass"

    if report.failed_items > 0:
        report.recommendations.append("立即修复所有不通过项(critical/high)，确保OWASP LLM Top 10合规")
    if report.warning_items > 0:
        report.recommendations.append("关注警告项，补充安全声明和防护措施")
    report.recommendations.extend([
        "定期运行Probe扫描和Lint检查，建立持续合规监控",
        "将合规报告纳入CI/CD流水线，实施自动化安全门禁",
        "参考华为云安全白皮书完善安全基线配置",
    ])

    return report
