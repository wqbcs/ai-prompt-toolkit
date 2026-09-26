"""华为云集成模块 — IAM/OBS/LTS深度集成 + FunctionGraph模板 + 鸿蒙生态

统一导出:
- iam: IAMCredential/sign_request/OBSConfig/LTSConfig/AuditLogEntry/HuaweiCloudService
- fg_template: FunctionGraph部署模板
- repo_check: 华为云仓库检查
"""

from __future__ import annotations

from ai_prompt_toolkit.huawei_cloud.fg_template import get_fg_template, list_fg_templates
from ai_prompt_toolkit.huawei_cloud.iam import (
    AuditLogEntry,
    HuaweiCloudService,
    IAMCredential,
    LTSConfig,
    OBSConfig,
    sign_request,
)
from ai_prompt_toolkit.huawei_cloud.repo_check import check_codearts_repo, generate_repo_yml_template

__all__ = [
    "AuditLogEntry",
    "HuaweiCloudService",
    "IAMCredential",
    "LTSConfig",
    "OBSConfig",
    "check_codearts_repo",
    "generate_repo_yml_template",
    "get_fg_template",
    "list_fg_templates",
    "sign_request",
]
