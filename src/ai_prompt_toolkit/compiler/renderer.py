"""条件编译渲染器，深度优先遍历 AST 并生成最终文本。"""

from __future__ import annotations

import time
from typing import Literal

from ai_prompt_toolkit.compiler.evaluator import evaluate
from ai_prompt_toolkit.compiler.types import (
    ASTNode,
    BranchInfo,
    CompileContext,
    CompileReport,
    CompileResult,
    Condition,
    NodeType,
)

FallbackStrategy = Literal["empty", "skip", "warn"]


class Renderer:
    """条件编译渲染器。

    深度优先遍历 AST，根据 CompileContext 对条件分支进行匹配，
    生成最终编译文本和 CompileReport。

    Args:
        context: 编译上下文。
        fallback: 无匹配分支时的回退策略。
            - ``empty``: 输出空字符串。
            - ``skip``: 跳过该条件块。
            - ``warn``: 跳过并添加警告。
        template_id: 模板标识，用于报告。
    """

    def __init__(
        self,
        context: CompileContext,
        fallback: FallbackStrategy = "warn",
        template_id: str = "",
    ) -> None:
        self._ctx = context
        self._fallback = fallback
        self._template_id = template_id
        self._report = CompileReport(template_id=template_id)
        self._output: list[str] = []

    def _branch_info(
        self,
        condition: Condition,
        line_start: int,
        line_end: int,
        nesting: int,
        preview: str = "",
    ) -> BranchInfo:
        """创建 BranchInfo。"""
        return BranchInfo(
            condition=str(condition),
            line_start=line_start,
            line_end=line_end,
            nesting_level=nesting,
            content_preview=preview[:80],
        )

    def _render_text(self, node: ASTNode) -> None:
        """渲染文本节点。"""
        self._output.append(node.value)

    def _render_conditional(self, node: ASTNode, nesting: int = 0) -> None:
        if node.condition is not None:
            self._render_single_conditional(node, nesting)
        else:
            self._render_multi_conditional(node, nesting)

    def _render_single_conditional(self, node: ASTNode, nesting: int) -> None:
        # R199: 局部变量收窄 — 调用方已保证condition非None, 显式守卫收窄类型
        cond = node.condition
        if cond is None:
            return
        result, warnings = evaluate(cond, self._ctx)
        for w in warnings:
            self._report.add_warning(w)

        bi = self._branch_info(
            cond,
            node.line_start,
            node.line_end,
            nesting,
            self._preview_children(node.children),
        )

        if_body: list[ASTNode] = []
        else_body: list[ASTNode] = []
        current = if_body

        for child in node.children:
            if child.type == NodeType.BLOCK and child.condition is None:
                current = else_body
                else_body.extend(child.children)
                continue
            current.append(child)

        if result:
            self._report.activated_branches.append(bi)
            self._render_children(if_body, nesting + 1)
            if else_body:
                else_bi = self._branch_info(
                    Condition(dimension="__else__", operator="==", value="true"),
                    node.line_start,
                    node.line_end,
                    nesting,
                    self._preview_children(else_body),
                )
                self._report.ignored_branches.append(else_bi)
        else:
            self._report.ignored_branches.append(bi)
            if else_body:
                self._report.has_fallback = True
                else_bi = self._branch_info(
                    Condition(dimension="__else__", operator="==", value="true"),
                    node.line_start,
                    node.line_end,
                    nesting,
                    self._preview_children(else_body),
                )
                self._report.activated_branches.append(else_bi)
                self._render_children(else_body, nesting + 1)
            else:
                self._handle_no_match(node, nesting)

    def _render_multi_conditional(self, node: ASTNode, nesting: int) -> None:
        """渲染条件节点。

        children 布局:
        [0..N-1] = 条件分支（if / else if）
        [N] = 可选 else 块（NodeType.BLOCK，无 condition）
        """
        matched = False
        condition_children: list[ASTNode] = []
        else_child: ASTNode | None = None

        for child in node.children:
            if child.type == NodeType.CONDITIONAL:
                condition_children.append(child)
            elif child.type == NodeType.BLOCK and child.condition is None:
                else_child = child

        for branch in condition_children:
            if branch.condition is None:
                continue
            result, warnings = evaluate(branch.condition, self._ctx)
            for w in warnings:
                self._report.add_warning(w)

            bi = self._branch_info(
                branch.condition,
                branch.line_start,
                branch.line_end,
                nesting,
                self._preview_children(branch.children),
            )

            if result and not matched:
                matched = True
                self._report.activated_branches.append(bi)
                self._render_children(branch.children, nesting + 1)
            else:
                self._report.ignored_branches.append(bi)

        if not matched and else_child is not None:
            self._report.has_fallback = True
            bi = self._branch_info(
                Condition(dimension="__else__", operator="==", value="true"),
                else_child.line_start,
                else_child.line_end if else_child.children else else_child.line_start,
                nesting,
                self._preview_children(else_child.children),
            )
            self._report.activated_branches.append(bi)
            self._render_children(else_child.children, nesting + 1)

        if not matched and else_child is None:
            self._handle_no_match(node, nesting)

    def _handle_no_match(self, node: ASTNode, nesting: int) -> None:
        """处理无匹配分支的情况。"""
        if self._fallback == "empty" or self._fallback == "skip":
            pass
        elif self._fallback == "warn":
            cond_str = str(node.condition) if node.condition else "<unknown>"
            self._report.add_warning(f"条件块无匹配分支且无 else 回退: {cond_str} (L{node.line_start}-{node.line_end})")
            self._report.uncovered_conditions.append(cond_str)

    @staticmethod
    def _preview_children(children: list[ASTNode], max_len: int = 80) -> str:
        """生成子节点内容预览。"""
        parts: list[str] = []
        total = 0
        for child in children:
            text = child.value if child.type == NodeType.TEXT else ""
            if text:
                if total + len(text) > max_len:
                    parts.append(text[: max_len - total])
                    break
                parts.append(text)
                total += len(text)
        return "".join(parts).strip()

    def _render_children(self, children: list[ASTNode], nesting: int = 0) -> None:
        """递归渲染子节点。"""
        for child in children:
            if child.type == NodeType.TEXT:
                self._render_text(child)
            elif child.type == NodeType.CONDITIONAL:
                self._render_conditional(child, nesting)
            elif child.type == NodeType.BLOCK:
                self._render_children(child.children, nesting)

    def render(self, ast: ASTNode) -> CompileResult:
        """渲染 AST，返回 CompileResult。

        Args:
            ast: 语法分析器输出的 AST 根节点。

        Returns:
            包含编译文本和报告的 CompileResult。
        """
        start_ms = time.perf_counter()
        self._output = []
        self._report = CompileReport(template_id=self._template_id)

        self._render_children(ast.children)

        compiled_text = "".join(self._output)
        elapsed_ms = (time.perf_counter() - start_ms) * 1000

        self._report.compilation_time_ms = round(elapsed_ms, 3)
        self._report.result_is_empty = len(compiled_text.strip()) == 0

        if self._report.status != "failed" and self._report.errors:
            self._report.status = "partial"
        elif self._report.status != "failed" and not self._report.warnings:
            self._report.status = "success"

        return CompileResult(
            compiled_text=compiled_text,
            report=self._report,
        )
