"""条件编译Playground Web UI — FastAPI后端

参考: Handlebars Playground 左右分栏实时预览模式
- POST /api/compile: 条件编译接口
- GET /api/context-schema: 上下文JSON Schema
- POST /api/lint: Prompt Lint接口
- POST /api/scan: 安全扫描接口
- POST /api/evaluate: 评估接口
- GET /api/templates: 场景模板列表
- GET /api/version: 版本信息
- WebSocket /ws/compile: 实时编译
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from ai_prompt_toolkit.compiler import compile_template, CompileContext
from ai_prompt_toolkit.compiler.types import CompileReport
from ai_prompt_toolkit import __version__

logger = logging.getLogger(__name__)

_PLAYGROUND_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

app = FastAPI(title="AI Prompt Toolkit Playground", version=__version__)

try:
    from ai_prompt_toolkit.market.api import router as market_router
    app.include_router(market_router)
except Exception:
    logger.warning("Market API router failed to load")

try:
    from ai_prompt_toolkit.dataset_api import router as dataset_router
    app.include_router(dataset_router)
except Exception:
    logger.warning("Dataset API router failed to load")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_PLAYGROUND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_context(ctx_data: dict[str, Any]) -> CompileContext:
    model = ctx_data.get("model", "")
    language = ctx_data.get("language", "")
    industry = ctx_data.get("industry", "")
    flags = {k: v for k, v in ctx_data.items() if k not in ("model", "language", "industry") and isinstance(v, bool)}
    return CompileContext(model=model, language=language, industry=industry, flags=flags)


class CompileRequest:
    def __init__(self, template: str, context: dict[str, Any]):
        self.template = template
        self.context = context


@app.post("/api/compile")
async def api_compile(body: dict[str, Any]) -> dict[str, Any]:
    template = body.get("template", "")
    ctx_data = body.get("context", {})

    try:
        ctx = _build_context(ctx_data)
        result = compile_template(template, ctx)
        return {
            "status": "success",
            "compiled_text": result.compiled_text,
            "report": result.report.to_dict(),
        }
    except Exception:
        logger.exception("compile error")
        return {"status": "error", "error": "编译失败，请检查模板语法"}


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


@app.get("/api/version")
async def api_version() -> dict[str, str]:
    return {"version": __version__}


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


@app.post("/api/scan")
async def api_scan(body: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    template = body.get("template", "")
    detector = InjectionDetector()
    findings = detector.detect(template, template_id="playground")
    return {
        "status": "success",
        "total_findings": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


@app.post("/api/evaluate")
async def api_evaluate(body: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.evaluator import evaluate_template
    template = body.get("template", "")
    template_type = body.get("template_type", "prompt")
    dimensions = body.get("dimensions", [])
    try:
        result = evaluate_template("playground", template, dimensions=dimensions or None)
        dim_scores = {}
        for dim in result.scores:
            dim_scores[dim.name] = round(dim.score, 2)
        return {
            "status": "success",
            "overall_score": round(result.overall_score, 2),
            "dimension_scores": dim_scores,
            "summary": result.summary if hasattr(result, "summary") else "",
        }
    except Exception:
        logger.exception("evaluate error")
        return {"status": "error", "error": "评估失败，请检查输入内容"}


@app.get("/api/traces")
async def api_traces(limit: int = 50) -> dict[str, Any]:
    from ai_prompt_toolkit.tracing import Tracer
    try:
        tracer = Tracer.get_instance()
        traces = tracer.get_traces(limit=limit)
        return {"status": "success", "traces": [t.to_dict() for t in traces], "summary": tracer.get_summary()}
    except Exception:
        return {"status": "success", "traces": [], "summary": {"total_traces": 0}}


@app.get("/api/traces/summary")
async def api_traces_summary() -> dict[str, Any]:
    from ai_prompt_toolkit.tracing import Tracer
    try:
        tracer = Tracer.get_instance()
        return {"status": "success", "summary": tracer.get_summary()}
    except Exception:
        return {"status": "success", "summary": {"total_traces": 0}}


@app.post("/api/traces/export")
async def api_traces_export() -> dict[str, Any]:
    from ai_prompt_toolkit.tracing import Tracer
    try:
        tracer = Tracer.get_instance()
        count = tracer.save_traces()
        return {"status": "success", "exported": count}
    except Exception:
        return {"status": "error", "error": "导出失败"}


@app.post("/api/eval-matrix")
async def api_eval_matrix(body: dict[str, Any]) -> dict[str, Any]:
    templates = body.get("templates", [])
    if not templates:
        return {"status": "error", "error": "请提供templates数组"}
    from ai_prompt_toolkit.evaluator import evaluate_template
    matrix: list[dict[str, Any]] = []
    for tpl in templates:
        text = tpl.get("text", "")
        tid = tpl.get("id", "unknown")
        try:
            result = evaluate_template(tid, text)
            dim_map = {}
            for s in result.scores:
                dim_map[s.dimension_id] = round(s.score, 2)
            matrix.append({
                "id": tid,
                "overall_score": round(result.overall_score, 2),
                "category_scores": {k: round(v, 4) for k, v in result.category_scores.items()},
                "dimension_scores": dim_map,
                "status": "success",
            })
        except Exception:
            matrix.append({"id": tid, "status": "error", "overall_score": 0, "category_scores": {}, "dimension_scores": {}})
    return {"status": "success", "matrix": matrix}


@app.get("/api/eval-history")
async def api_eval_history(template_id: str = "", limit: int = 10) -> dict[str, Any]:
    from ai_prompt_toolkit.eval_store import EvalStore
    try:
        store = EvalStore()
        if template_id:
            snapshots = store.get_snapshots(template_id, limit=limit)
            trend = store.get_trend(template_id, limit=30)
            alerts = store.get_alerts(template_id, limit=10)
            return {
                "status": "success",
                "snapshots": [s.to_dict() for s in snapshots],
                "trend": [t.to_dict() for t in trend],
                "alerts": [a.to_dict() for a in alerts],
            }
        return {"status": "success", "snapshots": [], "trend": [], "alerts": []}
    except Exception:
        return {"status": "success", "snapshots": [], "trend": [], "alerts": []}


@app.get("/api/eval-compare")
async def api_eval_compare(a: int = 0, b: int = 0) -> dict[str, Any]:
    from ai_prompt_toolkit.eval_store import EvalStore
    if not a or not b:
        return {"status": "error", "error": "请提供snapshot_id参数a和b"}
    try:
        store = EvalStore()
        result = store.compare(a, b)
        return {"status": "success", "comparison": result}
    except Exception:
        return {"status": "error", "error": "对比失败"}


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
                ctx = _build_context(ctx_data)
                result = compile_template(template, ctx)
                await websocket.send_json({
                    "status": "success",
                    "compiled_text": result.compiled_text,
                    "report": result.report.to_dict(),
                })
            except json.JSONDecodeError:
                await websocket.send_json({"status": "error", "error": "Invalid JSON"})
            except Exception:
                logger.exception("ws compile error")
                await websocket.send_json({"status": "error", "error": "编译失败，请检查模板语法"})
    except WebSocketDisconnect:
        pass


_STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index() -> FileResponse:
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return FileResponse(str(_STATIC_DIR.parent / "index.html")) if (_STATIC_DIR.parent / "index.html").exists() else {"message": "Playground UI not built yet. Run: npm run build"}
