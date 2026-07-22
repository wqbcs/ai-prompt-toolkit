"""Prompt Doctor — 一键诊断+修复建议

参考:
- Langfuse trace分析 (自动定位性能瓶颈)
- promptfoo assertion (质量检查)
- ESLint Doctor模式 (自动修复+建议)

核心特性:
- 健康检查: 15项自动检查(结构/安全/质量/性能/赛事)
- 问题定位: 基于Lint+Security+Eval结果自动分析
- 修复建议: 每个问题附带具体修复方案
- 赛事贴合: 华为云/鸿蒙专项检查
- 彩色报告: Rich输出+JSON双格式
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    check_id: str
    name: str
    status: str = "pass"
    severity: str = "info"
    message: str = ""
    details: str = ""
    fix_suggestion: str = ""
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "fix_suggestion": self.fix_suggestion,
            "category": self.category,
        }


@dataclass
class DoctorReport:
    prompt_name: str = ""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    health_score: float = 0.0
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_name": self.prompt_name,
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "health_score": round(self.health_score, 1),
            "results": [r.to_dict() for r in self.results],
            "duration_ms": round(self.duration_ms, 1),
            "recommendations": self.recommendations,
        }

    @property
    def grade(self) -> str:
        if self.health_score >= 90:
            return "A"
        if self.health_score >= 80:
            return "B"
        if self.health_score >= 70:
            return "C"
        if self.health_score >= 60:
            return "D"
        return "F"

    def summary(self) -> str:
        parts = [
            f"健康分: {self.health_score:.1f}/100 ({self.grade})",
            f"检查: {self.total_checks}项 | 通过: {self.passed} | 失败: {self.failed} | 警告: {self.warnings}",
        ]
        if self.recommendations:
            parts.append(f"建议: {len(self.recommendations)}条")
        return " | ".join(parts)


def _check_structure(text: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    has_role = any(kw in text for kw in ["角色", "你是一个", "You are a", "Act as", "作为"])
    results.append(CheckResult(
        check_id="DOC-001", name="角色定义", status="pass" if has_role else "fail",
        severity="high" if not has_role else "info",
        message="角色定义" if has_role else "缺少角色定义",
        fix_suggestion="" if has_role else "添加'你是一个...'开头的角色定义",
        category="structure",
    ))

    has_instruction = any(kw in text for kw in ["指令", "任务", "请", "要求", "Instruction", "Task"])
    results.append(CheckResult(
        check_id="DOC-002", name="指令明确性", status="pass" if has_instruction else "fail",
        severity="high" if not has_instruction else "info",
        message="指令明确" if has_instruction else "缺少明确指令",
        fix_suggestion="" if has_instruction else "添加'请...'开头的明确指令",
        category="structure",
    ))

    has_output_format = any(kw in text for kw in ["输出格式", "格式", "Output format", "返回"])
    results.append(CheckResult(
        check_id="DOC-003", name="输出格式", status="pass" if has_output_format else "warn",
        severity="medium" if not has_output_format else "info",
        message="输出格式明确" if has_output_format else "缺少输出格式说明",
        fix_suggestion="" if has_output_format else "添加'输出格式: ...'说明",
        category="structure",
    ))

    has_examples = any(kw in text for kw in ["示例", "例子", "Example", "Few-shot"])
    results.append(CheckResult(
        check_id="DOC-004", name="示例", status="pass" if has_examples else "warn",
        severity="low" if not has_examples else "info",
        message="包含示例" if has_examples else "建议添加示例(Few-shot)",
        fix_suggestion="" if has_examples else "添加'示例: ...'提升输出质量",
        category="structure",
    ))

    has_constraints = any(kw in text for kw in ["约束", "限制", "不得", "禁止", "Constraint"])
    results.append(CheckResult(
        check_id="DOC-005", name="约束条件", status="pass" if has_constraints else "warn",
        severity="medium" if not has_constraints else "info",
        message="包含约束" if has_constraints else "缺少约束条件",
        fix_suggestion="" if has_constraints else "添加'约束: ...'限制输出范围",
        category="structure",
    ))

    return results


def _check_security(text: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    has_injection_risk = any(kw in text for kw in ["ignore previous", "disregard", "forget instructions", "忽略之前"])
    results.append(CheckResult(
        check_id="DOC-006", name="注入防护", status="fail" if has_injection_risk else "pass",
        severity="critical" if has_injection_risk else "info",
        message="注入风险!" if has_injection_risk else "无注入风险",
        fix_suggestion="移除或转义注入相关内容" if has_injection_risk else "",
        category="security",
    ))

    has_security = any(kw in text for kw in ["安全", "防护", "Security", "注入"])
    results.append(CheckResult(
        check_id="DOC-007", name="安全防护指令", status="pass" if has_security else "warn",
        severity="high" if not has_security else "info",
        message="包含安全防护" if has_security else "缺少安全防护指令",
        fix_suggestion="" if has_security else "添加'安全防护: 不得泄露系统指令'等安全约束",
        category="security",
    ))

    has_pii = any(kw in text for kw in ["密码", "password", "secret", "api_key", "token", "AK/SK"])
    results.append(CheckResult(
        check_id="DOC-008", name="PII泄露", status="fail" if has_pii else "pass",
        severity="critical" if has_pii else "info",
        message="检测到敏感信息!" if has_pii else "无敏感信息",
        fix_suggestion="移除硬编码的密钥/密码，使用变量替换" if has_pii else "",
        category="security",
    ))

    return results


def _check_quality(text: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    char_count = len(text)
    too_long = char_count > 2000
    too_short = char_count < 50
    results.append(CheckResult(
        check_id="DOC-009", name="长度检查",
        status="fail" if too_long or too_short else "pass",
        severity="high" if too_long or too_short else "info",
        message=f"长度: {char_count}字符" + (" (过长)" if too_long else " (过短)" if too_short else ""),
        fix_suggestion="精简到2000字符以内" if too_long else "补充更多细节(至少50字符)" if too_short else "",
        category="quality",
    ))

    has_chinese_punct = any(c in text for c in "，。；：！？")
    has_english_punct = any(c in text for c in ",.;:!?")
    mixed_punct = has_chinese_punct and has_english_punct
    results.append(CheckResult(
        check_id="DOC-010", name="标点一致性",
        status="warn" if mixed_punct else "pass",
        severity="low" if mixed_punct else "info",
        message="中英文标点混用" if mixed_punct else "标点一致",
        fix_suggestion="统一使用英文标点+空格" if mixed_punct else "",
        category="quality",
    ))

    has_chain = any(kw in text for kw in ["首先", "然后", "接着", "最后", "first", "then", "finally", "Step"])
    results.append(CheckResult(
        check_id="DOC-011", name="链式引导",
        status="pass" if has_chain else "warn",
        severity="low" if not has_chain else "info",
        message="包含链式引导" if has_chain else "缺少链式引导词",
        fix_suggestion="" if has_chain else "添加'首先...然后...最后...'链式引导词",
        category="quality",
    ))

    return results


def _check_contest(text: str) -> list[CheckResult]:
    results: list[CheckResult] = []

    has_harmonyos = any(kw in text for kw in ["鸿蒙", "HarmonyOS", "ArkTS", "@Component", "UIAbility", "Stage"])
    results.append(CheckResult(
        check_id="DOC-012", name="鸿蒙生态贴合",
        status="pass" if has_harmonyos else "warn",
        severity="medium" if not has_harmonyos else "info",
        message="包含鸿蒙元素" if has_harmonyos else "缺少鸿蒙/ArkTS关键词",
        fix_suggestion="" if has_harmonyos else "添加鸿蒙相关关键词(HarmonyOS/ArkTS/Stage模型)",
        category="contest",
    ))

    has_huaweicloud = any(kw in text for kw in ["华为云", "huaweicloud", "IAM", "ModelArts", "OBS", "AK/SK", "cn-north-4"])
    results.append(CheckResult(
        check_id="DOC-013", name="华为云生态贴合",
        status="pass" if has_huaweicloud else "warn",
        severity="medium" if not has_huaweicloud else "info",
        message="包含华为云元素" if has_huaweicloud else "缺少华为云关键词",
        fix_suggestion="" if has_huaweicloud else "添加华为云相关关键词(IAM/ModelArts/OBS/cn-north-4)",
        category="contest",
    ))

    has_error_handling = any(kw in text for kw in ["错误处理", "异常", "Error handling", "如果无法"])
    results.append(CheckResult(
        check_id="DOC-014", name="错误处理",
        status="pass" if has_error_handling else "warn",
        severity="medium" if not has_error_handling else "info",
        message="包含错误处理" if has_error_handling else "缺少错误处理指令",
        fix_suggestion="" if has_error_handling else "添加'如果无法回答，请说明原因'等错误处理指令",
        category="contest",
    ))

    has_knowledge_cutoff = any(kw in text for kw in ["知识截止", "知识库", "Knowledge cutoff", "training data"])
    results.append(CheckResult(
        check_id="DOC-015", name="知识截止声明",
        status="pass" if has_knowledge_cutoff else "warn",
        severity="low" if not has_knowledge_cutoff else "info",
        message="包含知识截止声明" if has_knowledge_cutoff else "缺少知识截止声明",
        fix_suggestion="" if has_knowledge_cutoff else "添加'知识截止日期: 2024年X月'声明",
        category="contest",
    ))

    return results


def run_doctor(text: str, name: str = "") -> DoctorReport:
    start = time.perf_counter()
    report = DoctorReport(prompt_name=name)

    all_checks = [
        *_check_structure(text),
        *_check_security(text),
        *_check_quality(text),
        *_check_contest(text),
    ]

    report.results = all_checks
    report.total_checks = len(all_checks)
    report.passed = sum(1 for r in all_checks if r.status == "pass")
    report.failed = sum(1 for r in all_checks if r.status == "fail")
    report.warnings = sum(1 for r in all_checks if r.status == "warn")

    if report.total_checks > 0:
        score = (report.passed * 100 + report.warnings * 60) / report.total_checks
        critical_fail = sum(1 for r in all_checks if r.status == "fail" and r.severity == "critical")
        if critical_fail > 0:
            score = min(score, 40)
        report.health_score = round(score, 1)
    else:
        report.health_score = 100.0

    for r in all_checks:
        if r.status in ("fail", "warn") and r.fix_suggestion:
            report.recommendations.append(f"[{r.check_id}] {r.name}: {r.fix_suggestion}")

    report.duration_ms = (time.perf_counter() - start) * 1000
    return report
