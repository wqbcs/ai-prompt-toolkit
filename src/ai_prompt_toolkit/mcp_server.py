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
        {
            "name": "prompt_token_analyze",
            "description": "Token计数与成本估算: 估算Prompt在各模型(GPT-4o/Claude/DeepSeek/Qwen/Pangu等)的Token消耗和API调用成本，并提供压缩优化建议",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                    "model": {"type": "string", "description": "目标模型(如gpt-4o/deepseek/qwen/pangu)", "default": "default"},
                    "compare": {"type": "boolean", "description": "多模型成本对比模式", "default": False},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_redteam",
            "description": "红队对抗性安全测试: 对Prompt执行OWASP LLM Top 10覆盖的Probe探测，支持离线模式",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本(离线模式)"},
                    "probes": {"type": "string", "description": "探测类型(逗号分隔，留空全部)"},
                    "owasp": {"type": "string", "description": "按OWASP分类过滤(如LLM01,LLM06)"},
                    "top_n": {"type": "integer", "description": "仅运行前N个Probe", "default": 10},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_compile",
            "description": "条件编译: 按模型/语言/行业条件编译提示词模板，支持{{#if}}/{{#elif}}/{{#else}}分支",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Prompt模板文本"},
                    "model": {"type": "string", "description": "目标模型(gpt-4/claude-3/deepseek等)"},
                    "language": {"type": "string", "description": "目标语言(zh/en/ja等)"},
                    "industry": {"type": "string", "description": "目标行业(fintech/healthcare等)"},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_gepa_optimize",
            "description": "GEPA反射式Prompt进化优化: 基于DSPy GEPA算法的迭代进化优化(反射提议+Pareto前沿+合并)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "待优化的Prompt文本"},
                    "metric": {"type": "string", "enum": ["exact_match", "contains_match", "regex_match", "lint_score", "llm_judge", "pangu_judge"], "description": "Feedback metric类型", "default": "lint_score"},
                    "auto": {"type": "string", "enum": ["light", "medium", "heavy"], "description": "优化预算(light=6/medium=12/heavy=18候选)", "default": "light"},
                    "predictors": {"type": "string", "description": "预测器名称(逗号分隔)", "default": "main"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "prompt_version_save",
            "description": "保存Prompt版本到版本管理引擎(版本树/diff/回滚/A-B对比)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Prompt名称"},
                    "content": {"type": "string", "description": "Prompt内容"},
                    "score": {"type": "number", "description": "Lint分数", "default": 0},
                    "source": {"type": "string", "description": "来源(manual/gepa/optimize)", "default": "manual"},
                    "tags": {"type": "string", "description": "标签(逗号分隔)"},
                },
                "required": ["name", "content"],
            },
        },
        {
            "name": "prompt_contest_eval",
            "description": "华为云+鸿蒙赛事贴合度评估(5鸿蒙Agent维度+5华为云维度+赛事就绪度)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "prompt_flow_run",
            "description": "执行Flow DAG工作流(lint-scan-flow/gepa-optimize-flow等预设或自定义YAML)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "flow_name": {"type": "string", "enum": ["lint-scan-flow", "gepa-optimize-flow"], "description": "预设Flow名称"},
                    "text": {"type": "string", "description": "输入文本"},
                },
                "required": ["flow_name", "text"],
            },
        },
        {
            "name": "prompt_data_load",
            "description": "数据连接器: 从文件系统(.md/.txt/.yaml/.json)或数据库加载Prompt数据",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "reader_type": {"type": "string", "enum": ["filesystem", "database"], "description": "连接器类型"},
                    "path": {"type": "string", "description": "文件系统路径或数据库连接字符串"},
                    "query": {"type": "string", "description": "数据库查询SQL(database类型)"},
                    "recursive": {"type": "boolean", "description": "是否递归扫描(默认true)", "default": True},
                },
                "required": ["reader_type", "path"],
            },
        },
        {
            "name": "prompt_eval_matrix",
            "description": "评估矩阵: 对Prompt执行多评估器评估并返回矩阵结果",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Prompt文本"},
                    "evaluators": {"type": "string", "description": "评估器(逗号分隔, 默认全部)"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "prompt_version_list",
            "description": "查询Prompt版本列表",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Prompt名称过滤"},
                    "limit": {"type": "integer", "description": "返回条数(默认20)", "default": 20},
                },
                "required": [],
            },
        },
        {
            "name": "prompt_junit_report",
            "description": "生成JUnit XML格式报告(兼容CI/CD平台)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "results": {"type": "string", "description": "JSON格式的lint/scan/eval结果"},
                    "suite_name": {"type": "string", "description": "测试套件名称", "default": "promptkit"},
                    "output_path": {"type": "string", "description": "输出文件路径"},
                },
                "required": ["results"],
            },
        },
        {
            "name": "prompt_notify",
            "description": "发送通知到DingTalk/Feishu/Slack/Webhook",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event": {"type": "string", "description": "事件类型(lint_failed/eval_passed/gepa_improved等)"},
                    "variables": {"type": "string", "description": "JSON格式的模板变量"},
                    "webhook_type": {"type": "string", "description": "通知类型(dingtalk/feishu/slack/webhook)", "default": "webhook"},
                    "webhook_url": {"type": "string", "description": "Webhook URL"},
                    "secret": {"type": "string", "description": "签名密钥(可选)"},
                },
                "required": ["event", "variables", "webhook_url"],
            },
        },
        {
            "name": "prompt_plugin_list",
            "description": "列出已注册的Plugin和Hook信息",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "prompt_sarif_report",
            "description": "生成SARIF v2.1.0格式报告(GitHub Code Scanning兼容)，支持lint/scan/eval结果转换",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "results": {"type": "string", "description": "JSON格式的lint/scan/eval结果"},
                    "result_type": {"type": "string", "enum": ["lint", "scan", "eval"], "description": "结果类型", "default": "lint"},
                    "output_path": {"type": "string", "description": "输出SARIF文件路径"},
                },
                "required": ["results"],
            },
        },
        {
            "name": "prompt_diff",
            "description": "Prompt结构化Diff对比: 段级差异分析+语义相似度+合并策略(prefer_newer/prefer_longer/union)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "old_text": {"type": "string", "description": "旧版Prompt文本"},
                    "new_text": {"type": "string", "description": "新版Prompt文本"},
                },
                "required": ["old_text", "new_text"],
            },
        },
        {
            "name": "prompt_merge",
            "description": "Prompt结构感知合并: 基于7段解析的智能合并(prefer_newer/prefer_longer/union三种策略)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ours_text": {"type": "string", "description": "我方Prompt文本"},
                    "theirs_text": {"type": "string", "description": "他方Prompt文本"},
                    "strategy": {"type": "string", "enum": ["prefer_newer", "prefer_longer", "union"], "description": "合并策略", "default": "prefer_newer"},
                },
                "required": ["ours_text", "theirs_text"],
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
        elif tool_name == "prompt_token_analyze":
            result = _tool_token_analyze(arguments)
        elif tool_name == "prompt_redteam":
            result = _tool_redteam(arguments)
        elif tool_name == "prompt_compile":
            result = _tool_compile(arguments)
        elif tool_name == "prompt_gepa_optimize":
            result = _tool_gepa_optimize(arguments)
        elif tool_name == "prompt_version_save":
            result = _tool_prompt_version_save(arguments)
        elif tool_name == "prompt_contest_eval":
            result = _tool_contest_eval(arguments)
        elif tool_name == "prompt_flow_run":
            result = _tool_flow_run(arguments)
        elif tool_name == "prompt_data_load":
            result = _tool_data_load(arguments)
        elif tool_name == "prompt_eval_matrix":
            result = _tool_eval_matrix(arguments)
        elif tool_name == "prompt_version_list":
            result = _tool_version_list(arguments)
        elif tool_name == "prompt_junit_report":
            result = _tool_junit_report(arguments)
        elif tool_name == "prompt_notify":
            result = _tool_notify(arguments)
        elif tool_name == "prompt_plugin_list":
            result = _tool_plugin_list(arguments)
        elif tool_name == "prompt_sarif_report":
            result = _tool_sarif_report(arguments)
        elif tool_name == "prompt_diff":
            result = _tool_prompt_diff(arguments)
        elif tool_name == "prompt_merge":
            result = _tool_prompt_merge(arguments)
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


def _tool_token_analyze(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens, compare_models

    template = args["template"]
    model = args.get("model", "default")
    do_compare = args.get("compare", False)

    if do_compare:
        comp = compare_models(template)
        return {
            "text_length": comp.text_length,
            "estimates": [e.to_dict() for e in comp.estimates],
            "cheapest_model": comp.cheapest_model,
            "most_efficient_model": comp.most_efficient_model,
        }

    result = analyze_prompt_tokens(template, model)
    return result.to_dict()


def _tool_redteam(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.redteam.probe import create_probe, get_available_probes, get_probes_by_owasp
    from ai_prompt_toolkit.redteam.detector import LeakageDetector, ComplianceDetector, RefusalDetector
    from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator

    template = args["template"]
    probes_str = args.get("probes", "")
    owasp = args.get("owasp", "")
    top_n = args.get("top_n", 10)

    available = get_available_probes()
    if owasp:
        owasp_refs = [ref.strip() for ref in owasp.split(",")]
        owasp_probes: list[str] = []
        for ref in owasp_refs:
            owasp_probes.extend(get_probes_by_owasp(ref))
        available = [p for p in available if p in owasp_probes]

    selected = probes_str.split(",") if probes_str else available
    if top_n > 0:
        selected = selected[:top_n]

    probe_instances = []
    for name in selected:
        try:
            probe_instances.append(create_probe(name.strip()))
        except ValueError:
            pass

    if not probe_instances:
        return {"error": "No valid probes selected", "available_probes": available}

    detectors = [LeakageDetector(), ComplianceDetector(), RefusalDetector()]
    orchestrator = ExplorationOrchestrator(probes=probe_instances, detectors=detectors)
    report = orchestrator.run_offline(template)

    return report.to_dict()


def _tool_compile(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.compiler import compile_template, CompileContext

    template = args["template"]
    model = args.get("model", "")
    language = args.get("language", "")
    industry = args.get("industry", "")

    ctx = CompileContext(model=model, language=language, industry=industry)
    result = compile_template(template, ctx)

    return {
        "compiled_text": result.compiled_text,
        "activated_branches": result.report.activated_branches,
        "ignored_branches": result.report.ignored_branches,
        "warnings": result.report.warnings,
    }


def _tool_gepa_optimize(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.gepa import gepa_optimize

    prompt = args["prompt"]
    metric = args.get("metric", "lint_score")
    auto = args.get("auto", "light")
    predictors_str = args.get("predictors", "main")
    predictor_names = [p.strip() for p in predictors_str.split(",")]

    result = gepa_optimize(
        prompt, metric=metric, auto=auto, predictor_names=predictor_names,
    )
    return result.to_dict()


def _tool_prompt_version_save(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_version import PromptVersionStore

    name = args["name"]
    content = args["content"]
    score = args.get("score", 0.0)
    source = args.get("source", "manual")
    tags_str = args.get("tags", "")
    tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

    store = PromptVersionStore()
    try:
        v = store.save(name, content, score=score, source=source, tags=tags)
        return v.to_dict()
    finally:
        store.close()


def _tool_contest_eval(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.huawei_eval import evaluate_contest_readiness
    return evaluate_contest_readiness(args["prompt"])


def _tool_flow_run(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.flow_dag import FlowExecutor, create_lint_scan_flow, create_gepa_optimize_flow

    flow_name = args["flow_name"]
    text = args["text"]

    presets = {"lint-scan-flow": create_lint_scan_flow, "gepa-optimize-flow": create_gepa_optimize_flow}
    dag = presets.get(flow_name, create_lint_scan_flow)()
    executor = FlowExecutor(dag)
    result = executor.execute(initial_inputs={"text": text})
    return result.to_dict()


def _tool_data_load(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.data_reader import DataReaderFactory

    reader_type = args["reader_type"]
    path = args["path"]

    kwargs: dict[str, Any] = {}
    if reader_type == "filesystem":
        kwargs = {"input_dir": path, "recursive": args.get("recursive", True)}
    elif reader_type == "database":
        kwargs = {"connection_string": path, "query": args.get("query", "")}

    reader = DataReaderFactory.create(reader_type, **kwargs)
    docs = reader.load_data()
    return {"document_count": len(docs), "documents": [d.to_dict() for d in docs[:20]]}


def _tool_eval_matrix(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.eval_matrix import build_matrix_from_evaluator_results

    prompt = args["prompt"]
    evaluators_str = args.get("evaluators", "")
    ev_list = [e.strip() for e in evaluators_str.split(",")] if evaluators_str else None

    report = build_matrix_from_evaluator_results("mcp-eval", prompt, evaluator_names=ev_list)
    return report.to_dict()


def _tool_version_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_version import PromptVersionStore

    name = args.get("name")
    limit = args.get("limit", 20)

    store = PromptVersionStore()
    try:
        versions = store.list_versions(name, limit=limit)
        return {"count": len(versions), "versions": [v.to_dict() for v in versions]}
    finally:
        store.close()


def _tool_junit_report(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.ci_integration import JUnitReporter, extract_ci_tags

    results_json = args.get("results", "[]")
    suite_name = args.get("suite_name", "promptkit")
    output_path = args.get("output_path", "")

    try:
        results = json.loads(results_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in results"}

    ci_tags = extract_ci_tags()
    reporter = JUnitReporter(suite_name=suite_name, ci_tags=ci_tags)

    for item in results:
        item_type = item.get("type", "lint")
        if item_type == "lint":
            reporter.add_lint_result(
                file_path=item.get("file_path", "unknown"),
                findings=item.get("findings", []),
                elapsed_ms=item.get("elapsed_ms", 0),
            )
        elif item_type == "scan":
            reporter.add_scan_result(
                file_path=item.get("file_path", "unknown"),
                findings=item.get("findings", []),
                elapsed_ms=item.get("elapsed_ms", 0),
            )
        elif item_type == "eval":
            reporter.add_eval_result(
                file_path=item.get("file_path", "unknown"),
                score=item.get("score", 0),
                passed=item.get("passed", False),
                details=item.get("details", ""),
                elapsed_ms=item.get("elapsed_ms", 0),
            )
        elif item_type == "gepa":
            reporter.add_gepa_result(
                prompt_name=item.get("prompt_name", "unknown"),
                best_score=item.get("best_score", 0),
                improvement=item.get("improvement", 0),
                elapsed_ms=item.get("elapsed_ms", 0),
            )
        elif item_type == "redteam":
            reporter.add_redteam_result(
                target=item.get("target", "unknown"),
                vulnerabilities=item.get("vulnerabilities", 0),
                passed=item.get("passed", False),
                elapsed_ms=item.get("elapsed_ms", 0),
            )

    response = {
        "total": reporter.suite.total,
        "failures": reporter.suite.failures,
        "errors": reporter.suite.errors,
        "has_failures": reporter.has_failures,
    }

    if output_path:
        path = reporter.write(output_path)
        response["output_path"] = str(path)
    else:
        response["xml_preview"] = reporter.to_xml_string()[:500]

    return response


def _tool_notify(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.notification import (
        NotificationConfig,
        NotificationManager,
    )

    event = args.get("event", "")
    variables_json = args.get("variables", "{}")
    webhook_type = args.get("webhook_type", "webhook")
    webhook_url = args.get("webhook_url", "")
    secret = args.get("secret", "")

    try:
        variables = json.loads(variables_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in variables"}

    config = NotificationConfig(
        type=webhook_type,
        webhook=webhook_url,
        secret=secret,
    )
    manager = NotificationManager(configs=[config])
    results = manager.notify(event, variables)

    return {"event": event, "results": results}


def _tool_plugin_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.plugin import PluginManager

    pm = PluginManager.get_instance()
    return pm.get_summary()


def _tool_sarif_report(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.sarif_report import lint_results_to_sarif, scan_results_to_sarif, eval_results_to_sarif

    results_json = args.get("results", "[]")
    result_type = args.get("result_type", "lint")
    output_path = args.get("output_path", "")

    try:
        findings = json.loads(results_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in results"}

    if result_type == "scan":
        report = scan_results_to_sarif(findings)
    elif result_type == "eval":
        report = eval_results_to_sarif(findings)
    else:
        report = lint_results_to_sarif(findings)

    response = {
        "total_results": report.total_results,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "runs": len(report.runs),
    }

    if output_path:
        path = report.write(output_path)
        response["output_path"] = str(path)
    else:
        response["sarif_json"] = report.to_dict()

    return response


def _tool_prompt_diff(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_diff import prompt_diff as do_diff

    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")

    if not old_text or not new_text:
        return {"error": "Both old_text and new_text are required"}

    report = do_diff(old_text, new_text)
    return report.to_dict()


def _tool_prompt_merge(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_diff import prompt_merge as do_merge, prompt_hash

    ours_text = args.get("ours_text", "")
    theirs_text = args.get("theirs_text", "")
    strategy = args.get("strategy", "prefer_newer")

    if not ours_text or not theirs_text:
        return {"error": "Both ours_text and theirs_text are required"}

    merged = do_merge("", ours_text, theirs_text, strategy=strategy)
    return {
        "merged_text": merged,
        "merged_hash": prompt_hash(merged),
        "strategy": strategy,
        "merged_length": len(merged),
    }


if __name__ == "__main__":
    run_server()
