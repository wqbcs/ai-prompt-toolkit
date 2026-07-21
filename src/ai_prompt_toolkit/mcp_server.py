"""MCP Server — 将lint/scan/judge/canary能力暴露为MCP协议

参考:
- MCP官方规范 (https://modelcontextprotocol.io)
- claude-prompts MCP Server (https://github.com/minipuft/claude-prompts)
- mcp-server-langfuse (https://github.com/langfuse/mcp-server-langfuse)

暴露的MCP Tools:
1. prompt_lint — 对Prompt文件执行Lint检查
2. prompt_scan — 对Prompt文件执行安全扫描
3. prompt_judge — LLM-as-Judge评估
4. prompt_canary_inject — 注入Canary Token
5. prompt_canary_check — 检测Canary泄露
6. prompt_evaluate — 62维度质量评估
7. prompt_dataset_run — 批量数据集运行
8. prompt_scorecard — 安全评分卡(0-100分)
9. prompt_engine — 多层融合注入检测引擎(5层+元分类器融合)
10. prompt_badge — 安全评分徽章SVG生成

暴露的MCP Resources:
1. prompt://templates — 场景模板列表
2. prompt://rules — Lint规则列表

使用方式:
1. 直接运行: python -m ai_prompt_toolkit.mcp_server
2. Cursor/Claude配置: {"mcpServers": {"prompt-toolkit": {"command": "python", "args": ["-m", "ai_prompt_toolkit.mcp_server"]}}}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_MCP_VERSION = "2024-11-05"
_SERVER_NAME = "ai-prompt-toolkit"
_SERVER_VERSION = "42.0.0"


def _make_response(id_val: Any, result: dict[str, Any]) -> str:
    return json.dumps({
        "jsonrpc": "2.0",
        "id": id_val,
        "result": result,
    })


def _make_error(id_val: Any, code: int, message: str) -> str:
    return json.dumps({
        "jsonrpc": "2.0",
        "id": id_val,
        "error": {"code": code, "message": message},
    })


def _handle_initialize(id_val: Any, params: dict[str, Any]) -> str:
    return _make_response(id_val, {
        "protocolVersion": _MCP_VERSION,
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
        },
        "serverInfo": {
            "name": _SERVER_NAME,
            "version": _SERVER_VERSION,
        },
    })


def _handle_tools_list(id_val: Any) -> str:
    tools = [
        {
            "name": "prompt_lint",
            "description": "对Prompt文件执行Lint质量检查，返回55条规则的检测结果和评分",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Prompt文件路径(.md)"},
                    "gate": {"type": "boolean", "description": "是否启用Quality Gate", "default": False},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "prompt_scan",
            "description": "对Prompt文件执行安全扫描：注入检测+PII+供应链+Unicode威胁",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Prompt文件路径(.md)"},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "prompt_judge",
            "description": "LLM-as-Judge评估：用LLM裁判评估Prompt回答质量（6通用+4 RAG维度）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "评估问题"},
                    "response": {"type": "string", "description": "待评估的回答"},
                    "mode": {"type": "string", "enum": ["absolute", "pairwise"], "description": "评估模式", "default": "absolute"},
                    "dimensions": {"type": "string", "description": "评估维度(逗号分隔)", "default": "relevance,accuracy,fluency,completeness,safety,helpfulness"},
                },
                "required": ["question", "response"],
            },
        },
        {
            "name": "prompt_canary_inject",
            "description": "在系统Prompt中注入Canary Token追踪标记，用于检测Prompt泄露",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "要注入Canary Token的Prompt文本"},
                    "count": {"type": "integer", "description": "Token数量", "default": 3},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "prompt_canary_check",
            "description": "检测LLM输出中是否存在Canary Token泄露，判断系统Prompt是否被泄露",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "output": {"type": "string", "description": "LLM的输出文本"},
                    "tokens": {"type": "string", "description": "之前注入的Canary Token列表(JSON数组)"},
                },
                "required": ["output", "tokens"],
            },
        },
        {
            "name": "prompt_evaluate",
            "description": "对Prompt执行62维度质量评估，返回综合评分和各维度得分",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                    "dimensions": {"type": "string", "description": "指定评估维度(逗号分隔，留空则全部)"},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_dataset_run",
            "description": "对数据集批量执行lint/scan/evaluate，返回每个用例的结果",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "数据集ID"},
                    "run_type": {"type": "string", "description": "运行类型: all/lint/scan/evaluate", "enum": ["all", "lint", "scan", "evaluate"]},
                },
                "required": ["dataset_id"],
            },
        },
        {
            "name": "prompt_scorecard",
            "description": "对Prompt执行综合安全评分(0-100分,A-F等级,5维度评分,ALLOW/WARN/BLOCK决策)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_engine",
            "description": "多层融合注入检测引擎: 5层(L1正则+L2分类器+L3相似度+L4结构+L5异常)并行检测+元分类器融合+Isotonic校准+炎症级联",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                    "session_id": {"type": "string", "description": "会话ID(启用炎症级联, 跨轮对话累积风险)", "default": ""},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_badge",
            "description": "生成安全评分徽章SVG图片, 可嵌入README或CI报告(评分+等级+决策三段式)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                    "compact": {"type": "boolean", "description": "紧凑模式(仅评分+等级)", "default": False},
                },
                "required": ["template"],
            },
        },
    ]
    return _make_response(id_val, {"tools": tools})


def _handle_resources_list(id_val: Any) -> str:
    resources = [
        {
            "uri": "prompt://templates",
            "name": "场景模板列表",
            "description": "内置53个行业场景模板（鸿蒙/华为云/可观测性/混沌工程/GitOps等）",
            "mimeType": "application/json",
        },
        {
            "uri": "prompt://rules",
            "name": "Lint规则列表",
            "description": "55条Lint规则(P001-P055)和40+安全检测规则(INJ/PII/STRUCT/ANOMALY/INJ-ZH)",
            "mimeType": "application/json",
        },
        {
            "uri": "prompt://datasets",
            "name": "数据集列表",
            "description": "所有已创建的测试数据集",
            "mimeType": "application/json",
        },
    ]
    return _make_response(id_val, {"resources": resources})


def _handle_resources_read(id_val: Any, params: dict[str, Any]) -> str:
    uri = params.get("uri", "")
    if uri == "prompt://templates":
        from ai_prompt_toolkit.cli_helpers import discover_templates
        scenarios_dir = Path(__file__).parent.parent.parent / "_scenarios"
        templates = []
        if scenarios_dir.exists():
            for tpl in sorted(scenarios_dir.rglob("*.md")):
                templates.append({"name": tpl.stem, "path": str(tpl), "category": tpl.parent.name})
        return _make_response(id_val, {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(templates, ensure_ascii=False)}]
        })
    elif uri == "prompt://rules":
        rules = []
        for i in range(1, 56):
            rules.append({"rule_id": f"P{i:03d}", "category": "lint"})
        for i in range(1, 16):
            rules.append({"rule_id": f"INJ-{i:03d}", "category": "security"})
            rules.append({"rule_id": f"INJ-ZH-{i:03d}", "category": "security_zh"})
        for r in ["UNI-001", "UNI-002", "UNI-003", "CANARY-001", "CANARY-002", "CANARY-003"]:
            rules.append({"rule_id": r, "category": "unicode_canary"})
        return _make_response(id_val, {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(rules, ensure_ascii=False)}]
        })
    elif uri == "prompt://datasets":
        from ai_prompt_toolkit.dataset import DatasetStore
        try:
            store = DatasetStore()
            datasets, total = store.list_datasets()
            data = [{"id": d.dataset_id, "name": d.name, "cases": d.case_count} for d in datasets]
            store.close()
        except Exception:
            data = []
        return _make_response(id_val, {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps({"total": len(data), "datasets": data}, ensure_ascii=False)}]
        })
    return _make_error(id_val, -32602, f"Unknown resource URI: {uri}")


def _handle_tool_call(id_val: Any, params: dict[str, Any]) -> str:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "prompt_lint":
            result = _tool_lint(arguments)
        elif tool_name == "prompt_scan":
            result = _tool_scan(arguments)
        elif tool_name == "prompt_judge":
            result = _tool_judge(arguments)
        elif tool_name == "prompt_canary_inject":
            result = _tool_canary_inject(arguments)
        elif tool_name == "prompt_canary_check":
            result = _tool_canary_check(arguments)
        elif tool_name == "prompt_evaluate":
            result = _tool_evaluate(arguments)
        elif tool_name == "prompt_dataset_run":
            result = _tool_dataset_run(arguments)
        elif tool_name == "prompt_scorecard":
            result = _tool_scorecard(arguments)
        elif tool_name == "prompt_engine":
            result = _tool_engine(arguments)
        elif tool_name == "prompt_badge":
            result = _tool_badge(arguments)
        else:
            return _make_error(id_val, -32601, f"Unknown tool: {tool_name}")

        return _make_response(id_val, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
        })
    except Exception as e:
        return _make_error(id_val, -32603, f"Tool execution error: {e}")


def _tool_lint(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.linter.quality_gate import QualityGate

    file_path = Path(args["file_path"])
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    text = file_path.read_text(encoding="utf-8")
    linter = PromptLinter()
    result = linter.lint(file_path.name, text)

    response = {
        "file": str(file_path),
        "score": result.score,
        "findings_count": result.failed_count,
        "findings": [
            {"rule_id": f.rule_id, "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
             "description": f.description}
            for f in result.findings
        ],
    }

    if args.get("gate"):
        qg = QualityGate()
        gate_result = qg.evaluate(result.findings, score=result.score)
        response["quality_gate"] = {
            "verdict": gate_result.verdict.value,
            "summary": gate_result.summary,
        }

    return response


def _tool_scan(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.defender import PromptDefender
    from ai_prompt_toolkit.security.unicode_guard import scan_unicode_and_canary

    file_path = Path(args["file_path"])
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    text = file_path.read_text(encoding="utf-8")
    detector = InjectionDetector(extra_rules=ZH_INJECTION_RULES)
    findings = detector.detect(text)

    pii = PIIDetector()
    pii_finding = pii.check(text)
    if pii_finding:
        findings.append(pii_finding)

    defender = PromptDefender()
    defense = defender.defend(text)
    if defense.findings:
        findings.extend(defense.findings)

    unicode_findings = scan_unicode_and_canary(text)
    findings.extend(unicode_findings)

    return {
        "file": str(file_path),
        "is_safe": defense.is_safe,
        "risk_score": defense.risk_score,
        "findings_count": len(findings),
        "findings": [
            {"rule_id": f.rule_id, "severity": f.severity.value if hasattr(f.severity, 'value') else str(f.severity),
             "description": f.description}
            for f in findings[:20]
        ],
    }


def _tool_judge(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.ab_test.judge import create_judge
    import asyncio

    question = args["question"]
    response = args["response"]
    mode = args.get("mode", "absolute")
    dimensions = args.get("dimensions", "relevance,accuracy,fluency,completeness,safety,helpfulness")
    dim_list = [d.strip() for d in dimensions.split(",")]

    judge = create_judge(dimensions=dim_list, mode=mode)

    if mode == "pairwise":
        result = asyncio.run(judge.evaluate_pairwise(question, response, response))
        return result.to_dict()
    else:
        results = asyncio.run(judge.evaluate_absolute(question, response))
        return {
            "mode": mode,
            "results": [r.to_dict() for r in results],
            "overall_score": round(
                sum(r.score * r.dimension.weight for r in results) / max(sum(r.dimension.weight for r in results), 1), 2
            ) if results else 0,
        }


def _tool_canary_inject(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.unicode_guard import inject_canary_tokens

    prompt = args["prompt"]
    count = args.get("count", 3)
    injected, tokens = inject_canary_tokens(prompt, count)
    return {
        "injected_prompt": injected,
        "tokens": [t.to_dict() for t in tokens],
        "token_strings": [t.token_string for t in tokens],
    }


def _tool_canary_check(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.unicode_guard import check_canary_leakage, CanaryToken

    output = args["output"]
    tokens_data = json.loads(args["tokens"]) if isinstance(args["tokens"], str) else args["tokens"]
    tokens = [CanaryToken(token_id=t.get("token_id", ""), token_string=t.get("token_string", ""))
              for t in tokens_data]

    findings = check_canary_leakage(output, tokens)
    return {
        "is_leaked": len(findings) > 0,
        "findings": [f.to_dict() for f in findings],
    }


def run_server() -> None:
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            id_val = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})

            if method == "initialize":
                response = _handle_initialize(id_val, params)
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response = _handle_tools_list(id_val)
            elif method == "tools/call":
                response = _handle_tool_call(id_val, params)
            elif method == "resources/list":
                response = _handle_resources_list(id_val)
            elif method == "resources/read":
                response = _handle_resources_read(id_val, params)
            elif method == "ping":
                response = _make_response(id_val, {})
            else:
                response = _make_error(id_val, -32601, f"Method not found: {method}")

            print(response, flush=True)
        except Exception as e:
            error = _make_error(None, -32603, str(e))
            print(error, flush=True)


def _tool_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.evaluator import evaluate_template
    template = args.get("template", "")
    dimensions_str = args.get("dimensions", "")
    dimensions = [d.strip() for d in dimensions_str.split(",") if d.strip()] if dimensions_str else None
    result = evaluate_template("mcp", template, dimensions=dimensions)
    dim_scores = {s.name: round(s.score, 2) for s in result.scores}
    return {
        "overall_score": round(result.overall_score, 2),
        "dimension_scores": dim_scores,
        "category_scores": {k: round(v, 4) for k, v in result.category_scores.items()},
    }


def _tool_dataset_run(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.dataset import DatasetStore
    dataset_id = args.get("dataset_id", "")
    run_type = args.get("run_type", "all")
    store = DatasetStore()
    if not store.get_dataset(dataset_id):
        store.close()
        return {"error": f"Dataset not found: {dataset_id}"}
    results = store.run_dataset(dataset_id, run_type=run_type)
    store.close()
    return {
        "dataset_id": dataset_id,
        "run_type": run_type,
        "total_cases": len(results),
        "results": [r.to_dict() for r in results],
    }


def _tool_scorecard(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard

    template = args.get("template", "")
    if not template.strip():
        return {"error": "模板为空"}

    linter = PromptLinter()
    lint_result = linter.lint("mcp", template)
    lint_findings = lint_result.findings if hasattr(lint_result, 'findings') else []

    detector = InjectionDetector(extra_rules=ZH_INJECTION_RULES)
    sec_findings = detector.detect(template)

    pii = PIIDetector()
    pii_finding = pii.check(template)
    if pii_finding:
        sec_findings.append(pii_finding)

    struct_finding = check_structural(template)
    if struct_finding:
        sec_findings.append(struct_finding)

    all_findings = list(lint_findings) + sec_findings
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, 'score') else None)
    return scorecard.to_dict()


def _tool_engine(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.engine import FusionEngine

    template = args.get("template", "")
    session_id = args.get("session_id", "")
    if not template.strip():
        return {"error": "模板为空"}

    engine = FusionEngine(enable_inflammation=bool(session_id))
    result = engine.analyze(template, session_id=session_id)
    return result.to_dict()


def _tool_badge(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.linter import PromptLinter
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
    from ai_prompt_toolkit.security.badge import generate_scorecard_badge

    template = args.get("template", "")
    compact = args.get("compact", False)
    if not template.strip():
        return {"error": "模板为空"}

    linter = PromptLinter()
    lint_result = linter.lint("mcp", template)
    lint_findings = lint_result.findings if hasattr(lint_result, 'findings') else []

    detector = InjectionDetector(extra_rules=ZH_INJECTION_RULES)
    sec_findings = detector.detect(template)

    pii = PIIDetector()
    pii_finding = pii.check(template)
    if pii_finding:
        sec_findings.append(pii_finding)

    struct_finding = check_structural(template)
    if struct_finding:
        sec_findings.append(struct_finding)

    all_findings = list(lint_findings) + sec_findings
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, 'score') else None)

    svg = generate_scorecard_badge(scorecard, compact=compact)
    return {
        "score": scorecard.overall_score,
        "grade": scorecard.grade.value,
        "decision": scorecard.decision.value,
        "svg": svg,
    }


if __name__ == "__main__":
    run_server()
