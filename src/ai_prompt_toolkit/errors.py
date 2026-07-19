"""统一异常体系

设计原则:
1. 分层异常: ToolkitError(基类) → 领域异常(LintError/SecurityError/...) → 具体异常
2. 可区分: 每个模块有独立异常类，调用方可按类型捕获
3. CLI友好: error_code属性映射到退出码，CLI层统一处理
4. 可追溯: 保留原始异常链(__cause__)
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    LINT = "lint"
    SECURITY = "security"
    COMPILER = "compiler"
    AB_TEST = "ab_test"
    CONFIG = "config"
    MARKET = "market"
    VERSION = "version"
    REDTEAM = "redteam"
    MCP = "mcp"
    RUNTIME = "runtime"


class ToolkitError(Exception):
    """所有ai-prompt-toolkit异常的基类"""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory = ErrorCategory.RUNTIME,
        error_code: int = 1,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        prefix = f"[{self.category.value}]"
        base = f"{prefix} {self.args[0]}" if self.args else prefix
        if self.details:
            items = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({items})"
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "category": self.category.value,
            "message": self.args[0] if self.args else "",
            "error_code": self.error_code,
            "details": self.details,
        }


class LintError(ToolkitError):
    """Lint相关错误"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, category=ErrorCategory.LINT, error_code=1, details=details)


class SecurityError(ToolkitError):
    """安全相关错误"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, category=ErrorCategory.SECURITY, error_code=1, details=details)


class CompilerError(ToolkitError):
    """编译器相关错误"""

    def __init__(self, message: str, *, line: int | None = None, col: int | None = None) -> None:
        details: dict[str, Any] = {}
        if line is not None:
            details["line"] = line
        if col is not None:
            details["col"] = col
        super().__init__(message, category=ErrorCategory.COMPILER, error_code=3, details=details)
        self.line = line
        self.col = col


class AbTestError(ToolkitError):
    """A/B测试相关错误"""

    def __init__(self, message: str, *, provider: str | None = None, details: dict[str, Any] | None = None) -> None:
        d = details or {}
        if provider:
            d["provider"] = provider
        super().__init__(message, category=ErrorCategory.AB_TEST, error_code=1, details=d)


class ConfigError(ToolkitError):
    """配置相关错误"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, category=ErrorCategory.CONFIG, error_code=2, details=details)


class MarketError(ToolkitError):
    """市场/模板库相关错误"""

    def __init__(self, message: str, *, template_id: str | None = None, details: dict[str, Any] | None = None) -> None:
        d = details or {}
        if template_id:
            d["template_id"] = template_id
        super().__init__(message, category=ErrorCategory.MARKET, error_code=1, details=d)


class VersionError(ToolkitError):
    """版本管理相关错误"""

    def __init__(self, message: str, *, template_id: str | None = None, version: str | None = None, details: dict[str, Any] | None = None) -> None:
        d = details or {}
        if template_id:
            d["template_id"] = template_id
        if version:
            d["version"] = version
        super().__init__(message, category=ErrorCategory.VERSION, error_code=1, details=d)


class RedteamError(ToolkitError):
    """红队测试相关错误"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, category=ErrorCategory.REDTEAM, error_code=1, details=details)


class McpError(ToolkitError):
    """MCP Server相关错误"""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, category=ErrorCategory.MCP, error_code=1, details=details)


class ValidationError(ToolkitError):
    """输入验证错误"""

    def __init__(self, message: str, *, field: str | None = None, details: dict[str, Any] | None = None) -> None:
        d = details or {}
        if field:
            d["field"] = field
        super().__init__(message, category=ErrorCategory.RUNTIME, error_code=2, details=d)


def toolkit_exit_code(exc: ToolkitError) -> int:
    """将ToolkitError映射到CLI退出码"""
    return exc.error_code


_REMEDIATION_HINTS: dict[str, str] = {
    ErrorCategory.LINT: "运行 'prompt-cli lint --fix -t <file>' 自动修复",
    ErrorCategory.SECURITY: "运行 'prompt-cli scan -t <file>' 查看详细安全报告",
    ErrorCategory.COMPILER: "检查 {{#if}}...{{else}}...{{/if}} 语法是否正确",
    ErrorCategory.CONFIG: "检查 .prompt-cli.toml 配置文件格式",
    ErrorCategory.AB_TEST: "运行 'prompt-cli doctor' 检查Provider配置",
    ErrorCategory.VERSION: "运行 'prompt-cli version list' 查看历史版本",
    ErrorCategory.REDTEAM: "运行 'prompt-cli redteam -s <file>' 执行红队测试",
    ErrorCategory.MCP: "检查MCP Server配置和连接",
    ErrorCategory.MARKET: "运行 'prompt-cli market search' 查找模板",
}


def format_error_for_cli(exc: ToolkitError) -> str:
    """将ToolkitError格式化为CLI友好的错误信息"""
    base = str(exc)
    hint = _REMEDIATION_HINTS.get(exc.category)
    if hint:
        base = f"{base}\n  提示: {hint}"
    return base
