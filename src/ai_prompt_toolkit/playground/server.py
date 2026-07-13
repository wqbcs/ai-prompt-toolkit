"""条件编译Playground Web UI — FastAPI后端

参考: Handlebars Playground 左右分栏实时预览模式
- POST /api/compile: 条件编译接口
- GET /api/context-schema: 上下文JSON Schema
- WebSocket /ws/compile: 实时编译
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from ai_prompt_toolkit.compiler import compile_template, CompileContext
from ai_prompt_toolkit.compiler.types import CompileReport

app = FastAPI(title="AI Prompt Toolkit Playground", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompileRequest:
    def __init__(self, template: str, context: dict[str, Any]):
        self.template = template
        self.context = context


@app.post("/api/compile")
async def api_compile(body: dict[str, Any]) -> dict[str, Any]:
    template = body.get("template", "")
    ctx_data = body.get("context", {})
    model = ctx_data.get("model", "")
    language = ctx_data.get("language", "")
    industry = ctx_data.get("industry", "")
    flags = {k: v for k, v in ctx_data.items() if k not in ("model", "language", "industry") and isinstance(v, bool)}

    try:
        ctx = CompileContext(model=model, language=language, industry=industry, flags=flags)
        result = compile_template(template, ctx)
        return {
            "status": "success",
            "compiled_text": result.compiled_text,
            "report": result.report.to_dict(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/context-schema")
async def api_context_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "model": {"type": "string", "description": "模型名称", "examples": ["gpt-4o", "claude-3-sonnet", "qwen-max"]},
            "language": {"type": "string", "description": "目标语言", "examples": ["zh-CN", "en-US", "ja-JP"]},
            "industry": {"type": "string", "description": "行业领域", "examples": ["finance", "healthcare", "education"]},
        },
        "additionalProperties": {"type": "boolean"},
    }


@app.get("/api/templates")
async def api_templates() -> list[dict[str, Any]]:
    from ai_prompt_toolkit.frontmatter import parse_front_matter
    base = Path.cwd() / "_scenarios"
    if not base.exists():
        return []
    templates = []
    for p in sorted(base.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, _ = parse_front_matter(text)
        if fm:
            templates.append({
                "id": p.stem,
                "name": fm.get("author", p.stem),
                "tags": fm.get("tags", []),
                "template_type": fm.get("template_type", "prompt"),
                "lint_score": fm.get("lint_score", 0),
            })
    return templates


@app.post("/api/lint")
async def api_lint(body: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    template = body.get("template", "")
    template_type = body.get("template_type", "prompt")
    linter = PromptLinter()
    result = linter.lint("playground", template, template_type=template_type)
    return {
        "status": "success",
        "score": result.score,
        "findings": [f.to_dict() for f in result.findings],
    }


@app.websocket("/ws/compile")
async def ws_compile(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                body = json.loads(data)
                template = body.get("template", "")
                ctx_data = body.get("context", {})
                model = ctx_data.get("model", "")
                language = ctx_data.get("language", "")
                industry = ctx_data.get("industry", "")
                flags = {k: v for k, v in ctx_data.items() if k not in ("model", "language", "industry") and isinstance(v, bool)}
                ctx = CompileContext(model=model, language=language, industry=industry, flags=flags)
                result = compile_template(template, ctx)
                await websocket.send_json({
                    "status": "success",
                    "compiled_text": result.compiled_text,
                    "report": result.report.to_dict(),
                })
            except json.JSONDecodeError:
                await websocket.send_json({"status": "error", "error": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"status": "error", "error": str(e)})
    except WebSocketDisconnect:
        pass


_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index() -> FileResponse:
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return FileResponse(str(_STATIC_DIR.parent / "index.html")) if (_STATIC_DIR.parent / "index.html").exists() else {"message": "Playground UI not built yet. Run: npm run build"}
