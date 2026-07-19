"""Pydantic V2验证模型 — 核心类型的验证增强

参考: langfuse Pydantic模型模式
- FindingModel: 发现项验证
- BaseReportModel: 报告验证
- CompileContextModel: 编译上下文验证
- ScanSummaryModel: 扫描摘要验证
"""
from __future__ import annotations

from typing import Any

try:
    from pydantic import BaseModel, Field, field_validator

    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False


if _HAS_PYDANTIC:

    class FindingModel(BaseModel):
        rule_id: str = Field(min_length=1, description="规则ID")
        severity: str = Field(pattern="^(info|low|medium|high|critical)$", description="严重程度")
        description: str = Field(min_length=1, description="问题描述")
        location: str = Field(default="", description="位置")
        remediation: str = Field(default="", description="修复建议")
        details: dict[str, Any] = Field(default_factory=dict, description="详情")

        @field_validator("severity")
        @classmethod
        def validate_severity(cls, v: str) -> str:
            allowed = {"info", "low", "medium", "high", "critical"}
            if v not in allowed:
                raise ValueError(f"severity必须是{allowed}之一, 得到: {v}")
            return v

    class BaseReportModel(BaseModel):
        timestamp: str = Field(min_length=1, description="时间戳")
        template_id: str = Field(min_length=1, description="模板ID")
        status: str = Field(pattern="^(success|partial|failed|blocked|passed)$", description="状态")
        details: dict[str, Any] = Field(default_factory=dict)
        warnings: list[str] = Field(default_factory=list)
        findings: list[FindingModel] = Field(default_factory=list)

    class CompileContextModel(BaseModel):
        model: str = Field(default="", description="目标模型")
        language: str = Field(default="", description="语言代码")
        industry: str = Field(default="", description="行业")
        flags: dict[str, bool] = Field(default_factory=dict, description="布尔标志")

        @field_validator("language")
        @classmethod
        def validate_language(cls, v: str) -> str:
            if v and len(v) > 10:
                raise ValueError(f"language过长: {v}")
            return v

    class ScanSummaryModel(BaseModel):
        command: str = Field(default="", description="命令名")
        total_files: int = Field(ge=0, description="总文件数")
        total_findings: int = Field(ge=0, description="总发现项")
        critical: int = Field(ge=0, default=0)
        high: int = Field(ge=0, default=0)
        medium: int = Field(ge=0, default=0)
        low: int = Field(ge=0, default=0)
        info: int = Field(ge=0, default=0)
        elapsed_ms: float = Field(ge=0, default=0.0)
        extras: dict[str, Any] = Field(default_factory=dict)

    class MarketTemplateModel(BaseModel):
        id: str = Field(min_length=1, description="模板ID")
        name: str = Field(min_length=1, description="模板名称")
        version: str = Field(default="1.0", pattern=r"^\d+\.\d+$", description="版本号")
        status: str = Field(default="draft", pattern="^(draft|published|deprecated|review)$")
        author: str = Field(default="")
        description: str = Field(default="")
        tags: list[str] = Field(default_factory=list)
        category: str = Field(default="")

    class ABTestConfigModel(BaseModel):
        test_id: str = Field(min_length=1)
        significance_level: float = Field(ge=0.01, le=0.10, default=0.05)
        min_sample_size: int = Field(ge=5, default=30)
        timeout_seconds: float = Field(gt=0, default=30.0)
        max_retries: int = Field(ge=0, default=3)

else:

    class FindingModel:  # type: ignore[no-redef]
        pass

    class BaseReportModel:  # type: ignore[no-redef]
        pass

    class CompileContextModel:  # type: ignore[no-redef]
        pass

    class ScanSummaryModel:  # type: ignore[no-redef]
        pass

    class MarketTemplateModel:  # type: ignore[no-redef]
        pass

    class ABTestConfigModel:  # type: ignore[no-redef]
        pass


def validate_finding(data: dict[str, Any]) -> list[str]:
    if not _HAS_PYDANTIC:
        return _manual_validate_finding(data)
    try:
        FindingModel(**data)
        return []
    except Exception as e:
        return [str(e)]


def validate_report(data: dict[str, Any]) -> list[str]:
    if not _HAS_PYDANTIC:
        return _manual_validate_report(data)
    try:
        BaseReportModel(**data)
        return []
    except Exception as e:
        return [str(e)]


def validate_scan_summary(data: dict[str, Any]) -> list[str]:
    if not _HAS_PYDANTIC:
        return _manual_validate_scan_summary(data)
    try:
        ScanSummaryModel(**data)
        return []
    except Exception as e:
        return [str(e)]


def _manual_validate_finding(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("rule_id"):
        errors.append("rule_id不能为空")
    sev = data.get("severity", "")
    if sev not in ("info", "low", "medium", "high", "critical"):
        errors.append(f"severity无效: {sev}")
    if not data.get("description"):
        errors.append("description不能为空")
    return errors


def _manual_validate_report(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("timestamp"):
        errors.append("timestamp不能为空")
    if not data.get("template_id"):
        errors.append("template_id不能为空")
    status = data.get("status", "")
    if status not in ("success", "partial", "failed", "blocked", "passed"):
        errors.append(f"status无效: {status}")
    return errors


def _manual_validate_scan_summary(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in ("total_files", "total_findings", "critical", "high", "medium", "low", "info"):
        val = data.get(field_name, 0)
        if not isinstance(val, int) or val < 0:
            errors.append(f"{field_name}必须为非负整数")
    return errors
