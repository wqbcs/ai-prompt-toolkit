"""AI Prompt Toolkit统一异常体系

层次结构:
  PromptToolkitError (基类)
  ├── CompileError (编译相关)
  ├── LintError (Lint相关)
  ├── SecurityError (安全相关)
  ├── ABTestError (A/B测试相关)
  │   └── ProviderError (Provider连接)
  ├── RedTeamError (红队测试相关)
  └── MarketError (模板市场相关)
"""

from __future__ import annotations


class PromptToolkitError(Exception):
    error_code: str = "E000"
    user_message: str = "操作失败"
    debug_detail: str = ""

    def __init__(
        self, message: str = "", *, error_code: str = "", user_message: str = "", debug_detail: str = ""
    ) -> None:
        super().__init__(message)
        if error_code:
            self.error_code = error_code
        if user_message:
            self.user_message = user_message
        if debug_detail:
            self.debug_detail = debug_detail
        if message and not self.debug_detail:
            self.debug_detail = message

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.user_message}"

    def to_dict(self) -> dict[str, str]:
        return {
            "error_code": self.error_code,
            "user_message": self.user_message,
            "debug_detail": self.debug_detail,
        }


class CompileError(PromptToolkitError):
    error_code = "E100"
    user_message = "编译失败"

    def __init__(self, message: str = "", *, line: int = 0, directive: str = "", suggestion: str = "") -> None:
        detail = f"Line {line}: {directive}" if line else message
        user_msg = f"编译失败: {directive}" if directive else "编译失败"
        if suggestion:
            user_msg += f" — 建议: {suggestion}"
        super().__init__(message, error_code=self.error_code, user_message=user_msg, debug_detail=detail)


class LintError(PromptToolkitError):
    error_code = "E200"
    user_message = "Lint检查异常"


class SecurityError(PromptToolkitError):
    error_code = "E300"
    user_message = "安全扫描异常"


class ABTestError(PromptToolkitError):
    error_code = "E400"
    user_message = "A/B测试异常"


class ProviderError(ABTestError):
    error_code = "E410"
    user_message = "Provider连接失败"

    def __init__(self, message: str = "", *, provider: str = "", suggestion: str = "") -> None:
        user_msg = f"Provider {provider} 连接失败" if provider else "Provider连接失败"
        if suggestion:
            user_msg += f" — 建议: {suggestion}"
        super().__init__(message, error_code=self.error_code, user_message=user_msg)


class RedTeamError(PromptToolkitError):
    error_code = "E500"
    user_message = "红队测试异常"


class MarketError(PromptToolkitError):
    error_code = "E600"
    user_message = "模板市场异常"
