"""prompt-cli统一入口（兼容层，实际实现已迁移至cli_core）"""
from ai_prompt_toolkit.cli_core import main  # noqa: F401

__all__ = ["main"]
