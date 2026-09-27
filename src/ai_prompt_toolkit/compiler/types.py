"""条件编译专用类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TokenKind(Enum):
    """词法单元类型。"""

    TEXT = "text"
    IF_OPEN = "if_open"
    IF_CLOSE = "if_close"
    ELSE = "else"
    ELSE_IF = "else_if"


@dataclass
class Token:
    """词法单元。"""

    kind: TokenKind
    value: str
    line: int
    col: int
    expr: str = ""

    def __repr__(self) -> str:
        expr_part = f", expr={self.expr!r}" if self.expr else ""
        return f"Token({self.kind.value!r}, {self.value!r}, L{self.line}:C{self.col}{expr_part})"


class NodeType(Enum):
    """AST 节点类型。"""

    TEXT = "text"
    CONDITIONAL = "conditional"
    BLOCK = "block"


@dataclass
class Condition:
    """条件表达式节点，支持逻辑运算符连接。"""

    dimension: str
    operator: str
    value: str | list[str]
    logical: str | None = None
    right: Condition | None = None

    def __repr__(self) -> str:
        base = f"Condition({self.dimension!r} {self.operator} {self.value!r})"
        if self.logical and self.right:
            base += f" {self.logical} {self.right!r}"
        return base


@dataclass
class ASTNode:
    """AST 节点。"""

    type: NodeType
    value: str = ""
    condition: Condition | None = None
    children: list[ASTNode] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0

    def __repr__(self) -> str:
        children_count = len(self.children)
        cond_part = f", cond={self.condition!r}" if self.condition else ""
        return f"ASTNode({self.type.value!r}, {self.value!r}{cond_part}, children={children_count})"


@dataclass
class CompileContext:
    """编译上下文，携带模型/语言/行业等维度信息。"""

    model: str = ""
    language: str = ""
    industry: str = ""
    flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """导出为字典（用于缓存键计算）。"""
        return {
            "model": self.model,
            "language": self.language,
            "industry": self.industry,
            "flags": self.flags,
        }


@dataclass
class BranchInfo:
    """分支信息，用于编译报告。"""

    condition: str
    line_start: int
    line_end: int
    nesting_level: int
    content_preview: str = ""

    def __repr__(self) -> str:
        preview = f", preview={self.content_preview!r}" if self.content_preview else ""
        return (
            f"BranchInfo({self.condition!r}, L{self.line_start}-{self.line_end}, depth={self.nesting_level}{preview})"
        )


@dataclass
class CompileReport:
    """编译报告，记录分支命中、忽略、警告等信息。"""

    template_id: str = ""
    timestamp: str = ""
    status: str = "success"
    activated_branches: list[BranchInfo] = field(default_factory=list)
    ignored_branches: list[BranchInfo] = field(default_factory=list)
    uncovered_conditions: list[str] = field(default_factory=list)
    has_fallback: bool = False
    result_is_empty: bool = False
    cache_hit: bool = False
    compilation_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_warning(self, msg: str) -> None:
        """追加警告。"""
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        """追加错误，并将状态置为 failed。"""
        self.errors.append(msg)
        self.status = "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "activated_branches": [b.to_dict() if hasattr(b, "to_dict") else str(b) for b in self.activated_branches],
            "ignored_branches": [b.to_dict() if hasattr(b, "to_dict") else str(b) for b in self.ignored_branches],
            "uncovered_conditions": self.uncovered_conditions,
            "has_fallback": self.has_fallback,
            "result_is_empty": self.result_is_empty,
            "cache_hit": self.cache_hit,
            "compilation_time_ms": self.compilation_time_ms,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class CompileResult:
    """编译结果。"""

    compiled_text: str
    report: CompileReport
    cache_hit: bool = False
