"""LSP服务端 — VS Code实时Lint集成

P2-01: 编辑Prompt时实时Lint+评分，debounce 300ms
- 基于pygls实现LSP协议
- textDocument/didChange 触发Lint
- textDocument/publishDiagnostics 发布诊断
- 自定义prompt/score 通知评分变更

参考: vscode-markdownlint / ESLint Server
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

try:
    from lsprotocol import types as lsp
    from pygls.server import LanguageServer
    _HAS_LSP = True
except ImportError:
    _HAS_LSP = False


_DEBOUNCE_MS = 300


def _lint_to_diagnostics(text: str) -> list[dict[str, Any]]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.types import Severity

    linter = PromptLinter()
    result = linter.lint("realtime", text)

    diagnostics = []
    sev_map = {
        Severity.CRITICAL: 1,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 3,
    }

    for finding in result.findings:
        line = 0
        char = 0
        loc = str(finding.location) if finding.location is not None else ""
        if loc:
            parts = loc.split(":")
            try:
                if len(parts) >= 1:
                    line = max(0, int(parts[0]) - 1)
                if len(parts) >= 2:
                    char = max(0, int(parts[1]) - 1)
            except (ValueError, IndexError):
                pass

        diagnostics.append({
            "range": {
                "start": {"line": line, "character": char},
                "end": {"line": line, "character": char + 20},
            },
            "severity": sev_map.get(finding.severity, 3),
            "code": finding.rule_id,
            "source": "prompt-linter",
            "message": finding.description,
        })

    return diagnostics


def _compute_score(text: str) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    linter = PromptLinter()
    result = linter.lint("realtime", text)
    return {
        "score": result.score,
        "total_rules": result.rule_count,
        "passed": result.passed_count,
        "failed": result.failed_count,
        "lint_time_ms": result.lint_time_ms,
    }


if _HAS_LSP:
    class PromptLanguageServer(LanguageServer):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._debounce_timers: dict[str, asyncio.TimerHandle] = {}
            self._documents: dict[str, str] = {}

        def _schedule_lint(self, uri: str, text: str) -> None:
            loop = asyncio.get_event_loop()
            if uri in self._debounce_timers:
                self._debounce_timers[uri].cancel()
            self._debounce_timers[uri] = loop.call_later(
                _DEBOUNCE_MS / 1000.0,
                lambda: asyncio.ensure_future(self._do_lint(uri, text))
            )

        async def _do_lint(self, uri: str, text: str) -> None:
            try:
                diagnostics = _lint_to_diagnostics(text)
                self.publish_diagnostics(uri, [
                    lsp.Diagnostic(
                        range=lsp.Range(
                            start=lsp.Position(line=d["range"]["start"]["line"],
                                                character=d["range"]["start"]["character"]),
                            end=lsp.Position(line=d["range"]["end"]["line"],
                                              character=d["range"]["end"]["character"]),
                        ),
                        message=d["message"],
                        severity=lsp.DiagnosticSeverity(d["severity"]),
                        code=d["code"],
                        source=d["source"],
                    )
                    for d in diagnostics
                ])

                score = _compute_score(text)
                self.send_notification(
                    lsp.NOTIFICATION_CUSTOM,
                    {"method": "prompt/score", "params": score}
                )
            except Exception:
                pass

    server = PromptLanguageServer("prompt-lsp", "v1.0.0")

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
        uri = params.text_document.uri
        text = params.text_document.text
        server._documents[uri] = text
        server._schedule_lint(uri, text)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
        uri = params.text_document.uri
        text = ""
        for change in params.content_changes:
            text = change.text
        server._documents[uri] = text
        server._schedule_lint(uri, text)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
    def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
        uri = params.text_document.uri
        server._documents.pop(uri, None)
        if uri in server._debounce_timers:
            server._debounce_timers[uri].cancel()
            del server._debounce_timers[uri]
        server.publish_diagnostics(uri, [])

    @server.feature(lsp.TEXT_DOCUMENT_HOVER)
    def hover(params: lsp.HoverParams) -> lsp.Hover | None:
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        uri = params.text_document.uri
        text = server._documents.get(uri, "")
        if not text:
            return None
        diagnostics = _lint_to_diagnostics(text)
        line = params.position.line
        for d in diagnostics:
            if d["range"]["start"]["line"] == line:
                rule_id = d["code"]
                rule = _RULE_MAP.get(rule_id)
                if rule:
                    content = f"**{rule_id}: {rule.name}**\n\n{rule.description}\n\n修复: {rule.remediation}"
                    if rule_id in AUTO_FIXABLE_RULES:
                        content += "\n\n⚡ 可自动修复(--fix)"
                    return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=content))
        return None

    @server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
    def code_action(params: lsp.CodeActionParams) -> list[lsp.CodeAction] | None:
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        actions = []
        for diag in params.context.diagnostics:
            rule_id = diag.code if isinstance(diag.code, str) else str(diag.code)
            rule = _RULE_MAP.get(rule_id)
            if rule and rule_id in AUTO_FIXABLE_RULES:
                actions.append(lsp.CodeAction(
                    title=f"修复 {rule_id}: {rule.name}",
                    kind=lsp.CodeActionKind.QuickFix,
                    diagnostics=[diag],
                    is_preferred=True,
                ))
            if rule:
                actions.append(lsp.CodeAction(
                    title=f"查看 {rule_id} 详情",
                    kind=lsp.CodeActionKind.QuickFix,
                    diagnostics=[diag],
                ))
        return actions if actions else None


def create_lsp_server() -> Any:
    if not _HAS_LSP:
        raise ImportError("LSP功能需要安装pygls: pip install pygls lsprotocol")
    return server


def run_lsp_stdio() -> None:
    lsp_server = create_lsp_server()
    lsp_server.start_io()


def run_lsp_tcp(host: str = "127.0.0.1", port: int = 2087) -> None:
    lsp_server = create_lsp_server()
    lsp_server.start_tcp(host, port)
