"""Prompt断言/期望系统 — 参考promptfoo assert机制

8种断言类型:
- contains: 响应包含指定文本
- not-contains: 响应不包含指定文本
- regex: 响应匹配正则表达式
- json_schema: 响应符合JSON Schema
- similarity: 响应与期望文本相似度(Levenshtein)
- llm-rubric: LLM评判响应质量
- latency: 响应延迟在阈值内
- cost: 响应成本在预算内

安全防护:
- 禁止exec/eval
- 正则超时200ms(ReDoS防护)
- JSON Schema白名单类型
"""
from ai_prompt_toolkit.assertion.types import (
    AssertType,
    AssertionConfig,
    AssertionResult,
)
from ai_prompt_toolkit.assertion.engine import AssertionEngine

__all__ = ["AssertType", "AssertionConfig", "AssertionResult", "AssertionEngine"]
