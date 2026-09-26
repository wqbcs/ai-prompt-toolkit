"""条件编译引擎。

提供模板条件编译的完整流程：
词法分析 → 语法分析 → 条件求值 → 渲染输出，外加 LRU 缓存。

典型用法::

    from ai_prompt_toolkit.compiler import compile_template, CompileContext

    source = "你好{{#if model == gpt-4}}GPT-4 用户{{else}}其他用户{{/if}}"
    result = compile_template(source, CompileContext(model="gpt-4"))
    print(result.compiled_text)  # "你好GPT-4 用户"
"""

from __future__ import annotations

from datetime import datetime, timezone

from ai_prompt_toolkit.compiler.cache import CompileCache
from ai_prompt_toolkit.compiler.evaluator import EvaluationError, Evaluator, evaluate
from ai_prompt_toolkit.compiler.lexer import Lexer, LexerError
from ai_prompt_toolkit.compiler.parser import NestingError, ParseError, Parser
from ai_prompt_toolkit.compiler.renderer import FallbackStrategy, Renderer
from ai_prompt_toolkit.compiler.types import (
    ASTNode,
    BranchInfo,
    CompileContext,
    CompileReport,
    CompileResult,
    Condition,
    NodeType,
    Token,
    TokenKind,
)

__all__ = [
    "ASTNode",
    "BranchInfo",
    "CompileCache",
    "CompileContext",
    "CompileReport",
    "CompileResult",
    "Condition",
    "EvaluationError",
    "Evaluator",
    "FallbackStrategy",
    "Lexer",
    "LexerError",
    "NestingError",
    "NodeType",
    "ParseError",
    "Parser",
    "Renderer",
    "Token",
    "TokenKind",
    "compile_template",
    "evaluate",
]

_global_cache = CompileCache()


def compile_template(
    source: str,
    context: CompileContext | None = None,
    *,
    fallback: FallbackStrategy = "warn",
    template_id: str = "",
    use_cache: bool = True,
) -> CompileResult:
    """SDK 入口函数：编译模板字符串。

    完整流程：词法分析 → 语法分析 → 条件求值 → 渲染 → 缓存。

    Args:
        source: 模板源码，包含 ``{{#if}}`` / ``{{else}}`` / ``{{/if}}`` 指令。
        context: 编译上下文，提供 model/language/industry 等维度值。
        fallback: 无匹配分支时的回退策略（``empty`` / ``skip`` / ``warn``）。
        template_id: 模板标识，用于编译报告追踪。
        use_cache: 是否启用 LRU 缓存。

    Returns:
        CompileResult，包含编译后文本和详细报告。

    Raises:
        LexerError: 词法分析错误。
        ParseError: 语法分析错误。
        NestingError: 嵌套深度超限。
        EvaluationError: 条件求值副作用检测。
    """
    if context is None:
        context = CompileContext()

    ctx_dict = context.to_dict()

    if use_cache:
        cached = _global_cache.get(source, ctx_dict)
        if cached is not None:
            return cached

    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    renderer = Renderer(context, fallback=fallback, template_id=template_id)
    result = renderer.render(ast)

    result.report.timestamp = datetime.now(timezone.utc).isoformat()
    result.report.template_id = template_id

    if use_cache:
        _global_cache.set(source, ctx_dict, result)

    return result
