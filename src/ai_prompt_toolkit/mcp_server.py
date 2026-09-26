"""MCP Server — 将ai-prompt-toolkit核心能力暴露为MCP协议(53个Tools)

参考:
- MCP官方规范 (https://modelcontextprotocol.io)
- claude-prompts MCP Server (https://github.com/minipuft/claude-prompts)
- mcp-server-langfuse (https://github.com/langfuse/mcp-server-langfuse)

暴露的MCP Tools (53个):
- Lint/Scan: prompt_lint(130规则), prompt_scan, prompt_judge, prompt_canary_inject/check
- 评估: prompt_evaluate(80维度), prompt_scorecard, prompt_dataset_run, eval_matrix
- 安全引擎: prompt_engine(5层融合), prompt_badge, prompt_token_analyze
- 红队/Probe: prompt_redteam, probe_run/detect/list/owasp_report/detector_run/owasp_summary/ethics_scan(15 Probes, 8 Detectors)
- 编译/优化: prompt_compile, prompt_gepa_optimize, prompt_auto_optimize, prompt_sanitize
- 版本/缓存: prompt_version_save/list, prompt_cache_stats/lookup/invalidate
- 报告: prompt_junit_report, prompt_sarif_report, prompt_diff, prompt_merge, prompt_semantic_diff
- 华为云: huaweicloud_modelarts_deploy/infer, huaweicloud_obs_upload/ecs_info/iam_auth, huaweicloud_compliance
- 盘古: pangu_compat_check, pangu_safety_audit
- 其他: prompt_template_render, prompt_doctor, prompt_trace_export, prompt_contest_eval...

暴露的MCP Resources:
1. prompt://templates — 场景模板列表(18个内置)
2. prompt://rules — Lint规则列表(P001-P130)
3. prompt://datasets — 数据集列表

使用方式:
1. 直接运行: python -m ai_prompt_toolkit.mcp_server
2. Cursor/Claude配置: {"mcpServers": {"prompt-toolkit": {"command": "python", "args": ["-m", "ai_prompt_toolkit.mcp_server"]}}}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_prompt_toolkit.types import Finding

_MCP_VERSION = "2024-11-05"
_SERVER_NAME = "ai-prompt-toolkit"
_SERVER_VERSION = "42.0.0"


def _make_response(id_val: Any, result: dict[str, Any]) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": id_val,
            "result": result,
        }
    )


def _make_error(id_val: Any, code: int, message: str) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": id_val,
            "error": {"code": code, "message": message},
        }
    )


def _handle_initialize(id_val: Any, params: dict[str, Any]) -> str:
    return _make_response(
        id_val,
        {
            "protocolVersion": _MCP_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {
                "name": _SERVER_NAME,
                "version": _SERVER_VERSION,
            },
        },
    )


def _handle_tools_list(id_val: Any) -> str:
    tools = [
        {
            "name": "prompt_lint",
            "description": "对Prompt文件执行Lint质量检查，返回255条规则(P001-P255)的检测结果和评分",
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
                    "mode": {
                        "type": "string",
                        "enum": ["absolute", "pairwise"],
                        "description": "评估模式",
                        "default": "absolute",
                    },
                    "dimensions": {
                        "type": "string",
                        "description": "评估维度(逗号分隔)",
                        "default": "relevance,accuracy,fluency,completeness,safety,helpfulness",
                    },
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
            "description": "对Prompt执行80维度(D01-D80)质量评估，返回综合评分和各维度得分",
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
                    "run_type": {
                        "type": "string",
                        "description": "运行类型: all/lint/scan/evaluate",
                        "enum": ["all", "lint", "scan", "evaluate"],
                    },
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
                    "session_id": {
                        "type": "string",
                        "description": "会话ID(启用炎症级联, 跨轮对话累积风险)",
                        "default": "",
                    },
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
                    "model": {
                        "type": "string",
                        "description": "目标模型(如gpt-4o/deepseek/qwen/pangu)",
                        "default": "default",
                    },
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
                    "metric": {
                        "type": "string",
                        "enum": [
                            "exact_match",
                            "contains_match",
                            "regex_match",
                            "lint_score",
                            "llm_judge",
                            "pangu_judge",
                        ],
                        "description": "Feedback metric类型",
                        "default": "lint_score",
                    },
                    "auto": {
                        "type": "string",
                        "enum": ["light", "medium", "heavy"],
                        "description": "优化预算(light=6/medium=12/heavy=18候选)",
                        "default": "light",
                    },
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
                    "flow_name": {
                        "type": "string",
                        "enum": ["lint-scan-flow", "gepa-optimize-flow"],
                        "description": "预设Flow名称",
                    },
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
                    "webhook_type": {
                        "type": "string",
                        "description": "通知类型(dingtalk/feishu/slack/webhook)",
                        "default": "webhook",
                    },
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
                    "result_type": {
                        "type": "string",
                        "enum": ["lint", "scan", "eval"],
                        "description": "结果类型",
                        "default": "lint",
                    },
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
                    "strategy": {
                        "type": "string",
                        "enum": ["prefer_newer", "prefer_longer", "union"],
                        "description": "合并策略",
                        "default": "prefer_newer",
                    },
                },
                "required": ["ours_text", "theirs_text"],
            },
        },
        {
            "name": "prompt_template_render",
            "description": "Prompt模板变量渲染: 安全变量插值+默认值, 防模板注入",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "模板文本(含{{var}}变量)"},
                    "variables": {"type": "string", "description": "JSON格式变量键值对"},
                    "strict": {"type": "boolean", "description": "严格模式(缺少变量报错)", "default": False},
                },
                "required": ["template"],
            },
        },
        {
            "name": "prompt_doctor",
            "description": "Prompt一键诊断: 15项健康检查(结构/安全/质量/赛事)+修复建议+健康分",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "prompt_trace_export",
            "description": "导出OTLP格式Tracing数据(兼容Jaeger/华为云AOM)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出OTLP JSON文件路径"},
                    "format": {
                        "type": "string",
                        "enum": ["otlp", "json", "tree"],
                        "description": "导出格式",
                        "default": "otlp",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "prompt_cache_stats",
            "description": "查看Prompt缓存统计: 容量/命中率/TTL/条目数",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "prompt_cache_lookup",
            "description": "查询Prompt缓存: 根据文本内容查找缓存结果",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "prompt_cache_invalidate",
            "description": "清除Prompt缓存: 按键清除或全部清除",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "all": {"type": "boolean", "description": "清除全部缓存", "default": True},
                    "key": {"type": "string", "description": "指定缓存键清除(设all=false时必填)"},
                },
                "required": [],
            },
        },
        {
            "name": "attack_vault_check",
            "description": "攻击签名检测: 检查文本是否匹配已知攻击模式(向量相似度)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "attack_vault_learn",
            "description": "攻击签名学习: 将检测到的攻击添加到签名库",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "攻击文本"},
                    "attack_type": {
                        "type": "string",
                        "description": "攻击类型(如injection/sql_injection)",
                        "enum": [
                            "injection",
                            "sql_injection",
                            "xss",
                            "ssrf",
                            "command_injection",
                            "path_traversal",
                            "other",
                        ],
                    },
                },
                "required": ["text", "attack_type"],
            },
        },
        {
            "name": "pangu_compat_check",
            "description": "盘古模型兼容性检查: 检测Prompt是否适配华为云盘古大模型(P096-P100规则)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检查的Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "pangu_safety_audit",
            "description": "盘古安全审计: 对盘古模型Prompt执行安全护栏和内容审核合规检查",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待审计的Prompt文本"},
                    "threshold": {"type": "number", "description": "安全评分阈值(默认0.8)", "default": 0.8},
                },
                "required": ["text"],
            },
        },
        {
            "name": "prompt_sanitize",
            "description": "Prompt消毒: 检测并清理编码混淆/模板注入/敏感信息/指令注入",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待消毒的Prompt文本"},
                    "level": {
                        "type": "string",
                        "description": "消毒级别(none/standard/strict)",
                        "enum": ["none", "standard", "strict"],
                        "default": "standard",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "prompt_auto_optimize",
            "description": "Prompt自动优化: 基于Lint评分迭代优化Prompt质量",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待优化的Prompt文本"},
                    "max_iterations": {"type": "integer", "description": "最大优化迭代次数(默认3)", "default": 3},
                },
                "required": ["text"],
            },
        },
        {
            "name": "eval_matrix",
            "description": "评估矩阵: 多Prompt评估对比矩阵",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompts": {"type": "string", "description": "JSON格式的Prompt字典 {name: content}"},
                },
                "required": ["prompts"],
            },
        },
        {
            "name": "huaweicloud_modelarts_deploy",
            "description": "华为云ModelArts部署: 生成ModelArts模型部署配置和脚本",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model_type": {
                        "type": "string",
                        "description": "模型类型(pangu/chatglm/qwen等)",
                        "default": "pangu",
                    },
                    "instance_type": {
                        "type": "string",
                        "description": "部署规格(如Ascend910/V100)",
                        "default": "Ascend910",
                    },
                    "region": {"type": "string", "description": "区域(如cn-north-4)", "default": "cn-north-4"},
                },
                "required": [],
            },
        },
        {
            "name": "huaweicloud_modelarts_infer",
            "description": "华为云ModelArts推理: 生成ModelArts在线推理调用示例",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "description": "推理端点URL"},
                    "prompt": {"type": "string", "description": "推理Prompt文本"},
                },
                "required": ["endpoint", "prompt"],
            },
        },
        {
            "name": "huaweicloud_obs_upload",
            "description": "华为云OBS上传: 生成OBS数据上传脚本和配置",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "bucket": {"type": "string", "description": "OBS桶名"},
                    "local_path": {"type": "string", "description": "本地文件路径"},
                    "region": {"type": "string", "description": "区域(如cn-north-4)", "default": "cn-north-4"},
                },
                "required": ["bucket", "local_path"],
            },
        },
        {
            "name": "huaweicloud_ecs_info",
            "description": "华为云ECS信息: 查询ECS实例规格和推荐配置",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "usage": {"type": "string", "description": "用途(AI训练/AI推理/Web服务)", "default": "AI推理"},
                    "region": {"type": "string", "description": "区域(如cn-north-4)", "default": "cn-north-4"},
                },
                "required": [],
            },
        },
        {
            "name": "huaweicloud_iam_auth",
            "description": "华为云IAM认证: 生成IAM认证配置和AK/SK使用示例",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "auth_method": {"type": "string", "description": "认证方式(aksk/token/agency)", "default": "aksk"},
                    "region": {"type": "string", "description": "区域(如cn-north-4)", "default": "cn-north-4"},
                },
                "required": [],
            },
        },
        {
            "name": "probe_run",
            "description": "运行Red Team探针扫描: 12大探针类别(garak风格,OWASP LLM Top 10 2025)自动检测Prompt安全漏洞",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测的Prompt文本"},
                    "probes": {"type": "string", "description": "指定探针(逗号分隔，空=全部)", "default": ""},
                },
                "required": ["text"],
            },
        },
        {
            "name": "probe_list",
            "description": "列出所有可用的Red Team探针和检测器",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "probe_detect",
            "description": "使用检测器分析文本中的安全风险模式",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测文本"},
                    "detectors": {"type": "string", "description": "指定检测器(逗号分隔，空=全部)", "default": ""},
                },
                "required": ["text"],
            },
        },
        {
            "name": "probe_owasp_report",
            "description": "生成OWASP LLM Top 10 2025合规报告",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测的Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "probe_detector_run",
            "description": "独立运行指定检测器(Detector): 精确运行单个或多个检测器分析文本，支持ethics_alignment/bias_fairness等6个检测器",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测文本"},
                    "detectors": {"type": "string", "description": "检测器名称(逗号分隔，留空=全部6个)", "default": ""},
                    "verbose": {"type": "boolean", "description": "详细模式(返回完整检测详情)", "default": False},
                },
                "required": ["text"],
            },
        },
        {
            "name": "probe_owasp_summary",
            "description": "OWASP LLM Top 10合规摘要: 精简版OWASP报告，仅返回风险等级/受影响类别数/Top3高危发现",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测的Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "probe_ethics_scan",
            "description": "伦理对齐专项扫描: 伦理对齐+偏见公平性双Detector深度扫描，返回合规评分和修复建议",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待扫描的Prompt文本"},
                    "threshold": {"type": "number", "description": "合规评分阈值(默认0.7)", "default": 0.7},
                },
                "required": ["text"],
            },
        },
        {
            "name": "huaweicloud_compliance",
            "description": "华为云安全合规报告: 7域(数据隐私/模型安全/访问控制/内容安全/运维/供应链/认证)加权评分, 含OWASP LLM Top 10映射, 生成等保2.0合规报告",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待检测的Prompt文本"},
                    "template_id": {"type": "string", "description": "模板ID(可选)", "default": ""},
                    "owasp_compliance_pct": {"type": "number", "description": "OWASP合规百分比(可选)", "default": 0.0},
                },
                "required": ["text"],
            },
        },
        {
            "name": "prompt_semantic_diff",
            "description": "Prompt语义差异对比: 按段(角色/约束/安全/示例)独立比较, 安全策略变更=critical, 支持结构化变更摘要",
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
            "name": "multimodal_token_estimate",
            "description": "多模态Token估算: 估算文本/图像/音频/视频的Token消耗和预算",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "文本内容"},
                    "image_width": {"type": "integer", "description": "图像宽度(像素)", "default": 0},
                    "image_height": {"type": "integer", "description": "图像高度(像素)", "default": 0},
                    "image_detail": {
                        "type": "string",
                        "enum": ["auto", "low", "high"],
                        "description": "图像细节级别",
                        "default": "auto",
                    },
                    "audio_duration": {"type": "number", "description": "音频时长(秒)", "default": 0},
                    "video_duration": {"type": "number", "description": "视频时长(秒)", "default": 0},
                    "video_fps": {"type": "integer", "description": "视频帧率", "default": 1},
                    "max_total": {"type": "integer", "description": "Token预算上限", "default": 8192},
                },
                "required": ["text"],
            },
        },
        {
            "name": "config_hot_reload_status",
            "description": "配置热加载状态: 查询ConfigWatcher监控状态、监控文件列表、上次加载时间",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "badge_generate_themed",
            "description": "主题Badge生成: 生成指定主题(light/dark/huawei)的安全评分SVG徽章",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "description": "安全评分(0-100)", "default": 80},
                    "grade": {
                        "type": "string",
                        "enum": ["A", "B", "C", "D", "F"],
                        "description": "安全等级",
                        "default": "B",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "huawei"],
                        "description": "主题",
                        "default": "light",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "harmonyos_arkui_check",
            "description": "鸿蒙ArkUI检查: 检测Prompt是否涉及ArkUI组件推荐和用法最佳实践",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "harmonyos_stage_model_check",
            "description": "鸿蒙Stage模型检查: 检测Prompt是否声明Stage模型生命周期和Ability交互",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "harmonyos_distributed_check",
            "description": "鸿蒙分布式检查: 检测Prompt是否声明分布式能力(设备发现/数据迁移/冲突解决)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Prompt文本"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "harmonyos_template_generate",
            "description": "鸿蒙ArkTS代码模板生成: 根据规则ID和场景生成鸿蒙ArkTS/ArkUI代码片段(覆盖P121/P122/P124/P146-P150)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "rule_id": {
                        "type": "string",
                        "description": "Lint规则ID(如P121/P146等)",
                        "enum": ["P121", "P122", "P124", "P146", "P147", "P148", "P149", "P150"],
                    },
                    "scene": {
                        "type": "string",
                        "description": "应用场景(如chatbot/card/extension)",
                        "default": "general",
                    },
                },
                "required": ["rule_id"],
            },
        },
        {
            "name": "prompt_lint_json_schema",
            "description": "输出Lint规则集JSON Schema: 生成所有Lint规则的JSON Schema定义, 可用于配置验证和IDE自动补全",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "按类别过滤(如security/structure/performance)",
                        "default": "",
                    },
                    "include_owasp": {"type": "boolean", "description": "包含OWASP映射", "default": True},
                },
                "required": [],
            },
        },
        {
            "name": "output_scan",
            "description": "输出安全扫描: 对LLM输出执行6类安全扫描(NoRefusal/Bias/Toxicity/Relevance/FactualConsistency/Citation), 参考llm-guard输出扫描器架构",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "LLM输出文本"},
                    "context": {"type": "string", "description": "原始输入(用于相关性检测)", "default": ""},
                    "scanners": {
                        "type": "string",
                        "description": "启用扫描器(逗号分隔): no_refusal,bias,toxicity,relevance,factual_consistency,citation",
                        "default": "",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "deveco_config",
            "description": "鸿蒙DevEco Studio配置生成: 生成prompt-toolkit集成配置+构建钩子+CI工作流, 用于HarmonyOS项目安全集成",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称", "default": "MyHarmonyApp"},
                    "bundle_name": {"type": "string", "description": "Bundle ID", "default": "com.example.myapp"},
                    "min_api": {"type": "integer", "description": "最低API版本", "default": 12},
                    "target_api": {"type": "integer", "description": "目标API版本", "default": 14},
                    "enable_lint": {"type": "boolean", "description": "启用Prompt Lint", "default": True},
                    "enable_scan": {"type": "boolean", "description": "启用安全扫描", "default": True},
                    "enable_output_scan": {"type": "boolean", "description": "启用输出扫描", "default": True},
                    "enable_redteam": {"type": "boolean", "description": "启用红队测试", "default": False},
                },
                "required": [],
            },
        },
        {
            "name": "rollback_safety_check",
            "description": "Prompt回滚安全检查: 对比两个版本检测安全降级(安全声明删除/约束丢失/评分下降)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "old_text": {"type": "string", "description": "旧版本Prompt文本"},
                    "new_text": {"type": "string", "description": "新版本Prompt文本"},
                },
                "required": ["old_text", "new_text"],
            },
        },
        {
            "name": "html_report_generate",
            "description": "生成交互式HTML报告: 带折叠/主题切换/搜索过滤的独立HTML",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "findings": {"type": "array", "description": "Lint结果列表", "items": {"type": "object"}},
                    "target": {"type": "string", "description": "目标名称", "default": "unknown"},
                },
                "required": ["findings"],
            },
        },
        {
            "name": "weight_preset_list",
            "description": "列出评估维度权重预设: 7个行业场景(security-heavy/quality-balanced/performance-first/harmonyos-strict/redteam-ready/cost-efficient)",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "fg_template_list",
            "description": "列出华为云FunctionGraph Prompt模板: 4种类型(ai_inference/conversation/embedding/content_moderation)",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "fg_template_generate",
            "description": "生成华为云FunctionGraph函数代码模板(Serverless AI函数)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "enum": ["ai_inference", "conversation", "embedding", "content_moderation"],
                        "description": "模板类型",
                    },
                    "name": {"type": "string", "description": "函数名称", "default": ""},
                    "description": {"type": "string", "description": "函数描述", "default": ""},
                },
                "required": ["template_type"],
            },
        },
        {
            "name": "prompt_version_create",
            "description": "创建Prompt版本记录(版本链管理+语义变更检测)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "模板ID"},
                    "content": {"type": "string", "description": "Prompt内容"},
                    "author": {"type": "string", "description": "作者", "default": ""},
                    "score": {"type": "number", "description": "评分", "default": 0},
                    "grade": {"type": "string", "description": "等级", "default": ""},
                },
                "required": ["template_id", "content"],
            },
        },
        {
            "name": "prompt_version_history",
            "description": "列出Prompt版本历史(版本链追踪)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "模板ID"},
                },
                "required": ["template_id"],
            },
        },
        {
            "name": "prompt_version_diff",
            "description": "对比两个Prompt版本的差异(语义+结构)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "模板ID"},
                    "version_id_1": {"type": "string", "description": "版本1 ID"},
                    "version_id_2": {"type": "string", "description": "版本2 ID"},
                },
                "required": ["template_id", "version_id_1", "version_id_2"],
            },
        },
        {
            "name": "mcp_reload",
            "description": "MCP热重载: 重新加载指定模块(默认rules)并刷新dispatch表",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "module": {
                        "type": "string",
                        "description": "模块名(默认ai_prompt_toolkit.linter.rules)",
                        "default": "ai_prompt_toolkit.linter.rules",
                    },
                },
            },
        },
        {
            "name": "test_suite_run",
            "description": "执行声明式测试套件(YAML配置驱动的Lint+Eval测试)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "suite_path": {"type": "string", "description": "测试套件YAML文件路径"},
                    "base_dir": {"type": "string", "description": "基础目录(默认当前目录)", "default": "."},
                },
                "required": ["suite_path"],
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
            "description": "170条Lint规则(P001-P170)和40+安全检测规则(INJ/PII/STRUCT/ANOMALY/INJ-ZH)",
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
        scenarios_dir = Path(__file__).parent.parent.parent / "_scenarios"
        templates = []
        if scenarios_dir.exists():
            for tpl in sorted(scenarios_dir.rglob("*.md")):
                templates.append({"name": tpl.stem, "path": str(tpl), "category": tpl.parent.name})
        return _make_response(
            id_val,
            {
                "contents": [
                    {"uri": uri, "mimeType": "application/json", "text": json.dumps(templates, ensure_ascii=False)}
                ]
            },
        )
    elif uri == "prompt://rules":
        rules = []
        for i in range(1, 131):
            rules.append({"rule_id": f"P{i:03d}", "category": "lint"})
        for i in range(1, 16):
            rules.append({"rule_id": f"INJ-{i:03d}", "category": "security"})
            rules.append({"rule_id": f"INJ-ZH-{i:03d}", "category": "security_zh"})
        for r in ["UNI-001", "UNI-002", "UNI-003", "CANARY-001", "CANARY-002", "CANARY-003"]:
            rules.append({"rule_id": r, "category": "unicode_canary"})
        return _make_response(
            id_val,
            {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(rules, ensure_ascii=False)}]},
        )
    elif uri == "prompt://datasets":
        from ai_prompt_toolkit.dataset import DatasetStore

        try:
            store = DatasetStore()
            datasets, _total = store.list_datasets()
            data = [{"id": d.dataset_id, "name": d.name, "cases": d.case_count} for d in datasets]
            store.close()
        except Exception:
            data = []
        return _make_response(
            id_val,
            {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({"total": len(data), "datasets": data}, ensure_ascii=False),
                    }
                ]
            },
        )
    return _make_error(id_val, -32602, f"Unknown resource URI: {uri}")


_TOOL_DISPATCH: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None


def _get_tool_dispatch() -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    global _TOOL_DISPATCH
    if _TOOL_DISPATCH is None:
        _TOOL_DISPATCH = {
            "prompt_lint": _tool_lint,
            "prompt_scan": _tool_scan,
            "prompt_judge": _tool_judge,
            "prompt_canary_inject": _tool_canary_inject,
            "prompt_canary_check": _tool_canary_check,
            "prompt_evaluate": _tool_evaluate,
            "prompt_dataset_run": _tool_dataset_run,
            "prompt_scorecard": _tool_scorecard,
            "prompt_engine": _tool_engine,
            "prompt_badge": _tool_badge,
            "prompt_token_analyze": _tool_token_analyze,
            "prompt_redteam": _tool_redteam,
            "prompt_compile": _tool_compile,
            "prompt_gepa_optimize": _tool_gepa_optimize,
            "prompt_version_save": _tool_prompt_version_save,
            "prompt_contest_eval": _tool_contest_eval,
            "prompt_flow_run": _tool_flow_run,
            "prompt_data_load": _tool_data_load,
            "prompt_eval_matrix": _tool_eval_matrix,
            "prompt_version_list": _tool_version_list,
            "prompt_junit_report": _tool_junit_report,
            "prompt_notify": _tool_notify,
            "prompt_plugin_list": _tool_plugin_list,
            "prompt_sarif_report": _tool_sarif_report,
            "prompt_diff": _tool_prompt_diff,
            "prompt_merge": _tool_prompt_merge,
            "prompt_template_render": _tool_template_render,
            "prompt_doctor": _tool_prompt_doctor,
            "prompt_trace_export": _tool_trace_export,
            "prompt_cache_stats": _tool_cache_stats,
            "prompt_cache_lookup": _tool_cache_lookup,
            "prompt_cache_invalidate": _tool_cache_invalidate,
            "attack_vault_check": _tool_attack_vault_check,
            "attack_vault_learn": _tool_attack_vault_learn,
            "pangu_compat_check": _tool_pangu_compat_check,
            "pangu_safety_audit": _tool_pangu_safety_audit,
            "prompt_sanitize": _tool_prompt_sanitize,
            "prompt_auto_optimize": _tool_prompt_auto_optimize,
            "eval_matrix": _tool_eval_matrix_compare,
            "huaweicloud_modelarts_deploy": _tool_huaweicloud_modelarts_deploy,
            "huaweicloud_modelarts_infer": _tool_huaweicloud_modelarts_infer,
            "huaweicloud_obs_upload": _tool_huaweicloud_obs_upload,
            "huaweicloud_ecs_info": _tool_huaweicloud_ecs_info,
            "huaweicloud_iam_auth": _tool_huaweicloud_iam_auth,
            "probe_run": _tool_probe_run,
            "probe_list": _tool_probe_list,
            "probe_detect": _tool_probe_detect,
            "probe_owasp_report": _tool_probe_owasp_report,
            "probe_detector_run": _tool_probe_detector_run,
            "probe_owasp_summary": _tool_probe_owasp_summary,
            "probe_ethics_scan": _tool_probe_ethics_scan,
            "huaweicloud_compliance": _tool_huaweicloud_compliance,
            "prompt_semantic_diff": _tool_prompt_semantic_diff,
            "multimodal_token_estimate": _tool_multimodal_token_estimate,
            "config_hot_reload_status": _tool_config_hot_reload_status,
            "badge_generate_themed": _tool_badge_generate_themed,
            "harmonyos_arkui_check": _tool_harmonyos_arkui_check,
            "harmonyos_stage_model_check": _tool_harmonyos_stage_model_check,
            "harmonyos_distributed_check": _tool_harmonyos_distributed_check,
            "harmonyos_template_generate": _tool_harmonyos_template_generate,
            "prompt_lint_json_schema": _tool_prompt_lint_json_schema,
            "output_scan": _tool_output_scan,
            "deveco_config": _tool_deveco_config,
            "rollback_safety_check": _tool_rollback_safety_check,
            "html_report_generate": _tool_html_report_generate,
            "weight_preset_list": _tool_weight_preset_list,
            "fg_template_list": _tool_fg_template_list,
            "fg_template_generate": _tool_fg_template_generate,
            "prompt_version_create": _tool_prompt_version_create,
            "prompt_version_history": _tool_prompt_version_list,
            "prompt_version_diff": _tool_prompt_version_diff,
            "mcp_reload": _tool_mcp_reload,
            "test_suite_run": _tool_test_suite_run,
        }
    return _TOOL_DISPATCH


def _check_auth(params: dict[str, Any]) -> str | None:
    import os

    expected_key = os.getenv("PROMPT_MCP_API_KEY", "")
    if not expected_key:
        return None
    provided = params.get("_meta", {}).get("apiKey", "")
    if not provided:
        for item in params.get("_meta", {}).get("progressToken", "").split("|"):
            if item.startswith("key:"):
                provided = item[4:]
    if provided != expected_key:
        return "Unauthorized: invalid API key"
    return None


def _handle_tool_call(id_val: Any, params: dict[str, Any]) -> str:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        auth_error = _check_auth(params)
        if auth_error:
            return _make_error(id_val, -32001, auth_error)
        handler = _get_tool_dispatch().get(tool_name)
        if handler is None:
            return _make_error(id_val, -32601, f"Unknown tool: {tool_name}")
        result = handler(arguments)

        return _make_response(
            id_val, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
        )
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
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "description": f.description,
            }
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
    from ai_prompt_toolkit.security.defender import PromptDefender
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.unicode_guard import scan_unicode_and_canary
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES

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
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "description": f.description,
            }
            for f in findings[:20]
        ],
    }


def _tool_judge(args: dict[str, Any]) -> dict[str, Any]:
    import asyncio

    from ai_prompt_toolkit.ab_test.judge import create_judge

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
            )
            if results
            else 0,
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
    from ai_prompt_toolkit.security.unicode_guard import CanaryToken, check_canary_leakage

    output = args["output"]
    tokens_data = json.loads(args["tokens"]) if isinstance(args["tokens"], str) else args["tokens"]
    tokens = [CanaryToken(token_id=t.get("token_id", ""), token_string=t.get("token_string", "")) for t in tokens_data]

    findings = check_canary_leakage(output, tokens)
    return {
        "is_leaked": len(findings) > 0,
        "findings": [f.to_dict() for f in findings],
    }


def _validate_tools_dispatch_sync() -> None:
    dispatch = _get_tool_dispatch()
    tools_list_str = str(_handle_tools_list(0))
    for tool_name in dispatch:
        if tool_name not in tools_list_str:
            import logging as _l

            _l.getLogger(__name__).warning(f"MCP工具dispatch与tools_list不同步: {tool_name}在dispatch但不在tools_list")


def run_server() -> None:
    _validate_tools_dispatch_sync()
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
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES

    template = args.get("template", "")
    if not template.strip():
        return {"error": "模板为空"}

    linter = PromptLinter()
    lint_result = linter.lint("mcp", template)
    lint_findings = lint_result.findings if hasattr(lint_result, "findings") else []

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
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, "score") else None)
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
    from ai_prompt_toolkit.security.badge import generate_scorecard_badge
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.prompt_scorecard import compute_scorecard
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.zh_injection_rules import ZH_INJECTION_RULES

    template = args.get("template", "")
    compact = args.get("compact", False)
    theme = args.get("theme", "light")
    if not template.strip():
        return {"error": "模板为空"}

    linter = PromptLinter()
    lint_result = linter.lint("mcp", template)
    lint_findings = lint_result.findings if hasattr(lint_result, "findings") else []

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
    scorecard = compute_scorecard(all_findings, lint_score=lint_result.score if hasattr(lint_result, "score") else None)

    svg = generate_scorecard_badge(scorecard, compact=compact, theme=theme)
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
    from ai_prompt_toolkit.redteam.detector import ComplianceDetector, LeakageDetector, RefusalDetector
    from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator
    from ai_prompt_toolkit.redteam.probe import create_probe, get_available_probes, get_probes_by_owasp

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
    from ai_prompt_toolkit.compiler import CompileContext, compile_template

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
        prompt,
        metric=metric,
        auto=auto,
        predictor_names=predictor_names,
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
    from ai_prompt_toolkit.flow_dag import FlowExecutor, create_gepa_optimize_flow, create_lint_scan_flow

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
    from ai_prompt_toolkit.sarif_report import eval_results_to_sarif, lint_results_to_sarif, scan_results_to_sarif

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
    from ai_prompt_toolkit.prompt_diff import prompt_hash
    from ai_prompt_toolkit.prompt_diff import prompt_merge as do_merge

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


def _tool_template_render(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_template import extract_variables, render_template

    template = args.get("template", "")
    variables_json = args.get("variables", "{}")
    strict = args.get("strict", False)

    if not template:
        return {"error": "Template text is required"}

    try:
        variables = json.loads(variables_json) if isinstance(variables_json, str) else variables_json
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in variables"}

    extracted = extract_variables(template)
    try:
        rendered = render_template(template, variables, strict=strict)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "rendered": rendered,
        "variables_found": [v.to_dict() for v in extracted],
        "variables_provided": list(variables.keys()),
    }


def _tool_prompt_doctor(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_doctor import run_doctor

    text = args.get("text", "")
    if not text:
        return {"error": "Prompt text is required"}

    report = run_doctor(text)
    return report.to_dict()


def _tool_trace_export(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.tracing import Tracer, print_trace_tree

    output_path = args.get("output_path", "")
    fmt = args.get("format", "otlp")

    tracer = Tracer.get_instance()
    summary = tracer.get_summary()

    if summary.get("total_traces", 0) == 0:
        return {"status": "no_data", "message": "No trace data available"}

    if fmt == "otlp" and output_path:
        path = tracer.save_otlp(output_path)
        return {"status": "exported", "path": str(path), "total_spans": summary.get("total_spans", 0)}
    elif fmt == "tree":
        return {"status": "ok", "tree": print_trace_tree(tracer)}
    else:
        otlp = tracer.export_otlp_json()
        return {"status": "ok", "format": "otlp_json", "data": json.loads(otlp)}


def _tool_cache_stats(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_cache import get_cache

    cache = get_cache()
    return cache.stats()


def _tool_cache_lookup(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_cache import PromptCache, get_cache

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    cache = get_cache()
    key = PromptCache.make_key(text)
    value = cache.get(key)
    if value is None:
        return {"status": "miss", "key": key}
    return {"status": "hit", "key": key, "value": value}


def _tool_cache_invalidate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_cache import get_cache

    cache = get_cache()
    if args.get("all", False):
        cache.clear()
        return {"status": "cleared", "message": "All cache entries cleared"}
    key = args.get("key", "")
    if key:
        removed = cache.invalidate(key)
        return {"status": "invalidated" if removed else "not_found", "key": key}
    return {"error": "Specify 'all' or 'key' parameter"}


def _tool_attack_vault_check(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.attack_vault import get_attack_vault

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    vault = get_attack_vault()
    is_match, score, sig = vault.check(text)
    result: dict[str, Any] = {
        "is_match": is_match,
        "similarity": round(score, 4),
        "vault_size": vault.size,
    }
    if sig:
        result["matched_attack_type"] = sig.attack_type
        result["matched_text_preview"] = sig.text[:100]
    return result


def _tool_attack_vault_learn(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.attack_vault import get_attack_vault

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    attack_type = args.get("attack_type", "unknown")
    vault = get_attack_vault()
    vault.learn(text, attack_type=attack_type)
    return {"status": "learned", "attack_type": attack_type, "vault_size": vault.size}


def _tool_pangu_compat_check(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.rules import _RULE_MAP
    from ai_prompt_toolkit.linter.rules_p096_p100 import run_checks_p096_p100

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    findings = run_checks_p096_p100(text)
    pangu_rules = {rid: _RULE_MAP[rid].to_dict() for rid in ["P096", "P097", "P098", "P099", "P100"]}
    return {
        "compatible": len(findings) == 0,
        "issues_found": len(findings),
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "description": f.description,
                "remediation": f.remediation,
                "details": f.details,
            }
            for f in findings
        ],
        "rules_checked": pangu_rules,
    }


def _tool_pangu_safety_audit(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.rules_p096_p100 import _PANGU_CTX, check_p100

    text = args.get("text", "")
    threshold = args.get("threshold", 0.8)
    if not text:
        return {"error": "text is required"}
    is_pangu = bool(_PANGU_CTX.search(text))
    finding = check_p100(text)
    safety_score = 1.0 if finding is None else 0.5
    has_safety_decl = finding is None
    audit_items = []
    if not is_pangu:
        audit_items.append({"item": "pangu_context", "status": "skip", "detail": "非盘古模型Prompt"})
    elif has_safety_decl:
        audit_items.append({"item": "safety_guardrail", "status": "pass", "detail": "安全护栏已声明"})
    else:
        audit_items.append({"item": "safety_guardrail", "status": "fail", "detail": "安全护栏未声明"})
    audit_items.append(
        {
            "item": "safety_score",
            "status": "pass" if safety_score >= threshold else "fail",
            "detail": f"安全评分{safety_score}(阈值{threshold})",
        }
    )
    return {
        "is_pangu_prompt": is_pangu,
        "safety_score": safety_score,
        "threshold": threshold,
        "passed": safety_score >= threshold,
        "audit_items": audit_items,
        "finding": {
            "rule_id": finding.rule_id,
            "description": finding.description,
            "remediation": finding.remediation,
        }
        if finding
        else None,
    }


def _tool_prompt_sanitize(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_sanitizer import sanitize_prompt

    text = args.get("text", "")
    level = args.get("level", "standard")
    if not text:
        return {"error": "text is required"}
    result = sanitize_prompt(text, level=level)
    return {
        "sanitized_text": result.sanitized_text,
        "risk_level": result.risk_level,
        "is_safe": result.is_safe,
        "actions": result.actions,
        "action_count": result.action_count,
    }


def _tool_prompt_auto_optimize(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_optimizer import optimize_prompt

    text = args.get("text", "")
    max_iter = args.get("max_iterations", 3)
    if not text:
        return {"error": "text is required"}
    result = optimize_prompt(text, max_iterations=max_iter)
    return result.to_dict()


def _tool_eval_matrix_compare(args: dict[str, Any]) -> dict[str, Any]:
    prompts_json = args.get("prompts", "")
    if not prompts_json:
        return {"error": "prompts is required"}
    try:
        prompts = json.loads(prompts_json)
    except json.JSONDecodeError:
        return {"error": "prompts must be valid JSON {name: content}"}
    if not isinstance(prompts, dict) or not prompts:
        return {"error": "prompts must be a non-empty JSON object"}
    from ai_prompt_toolkit.linter.linter import PromptLinter

    linter = PromptLinter()
    cells = []
    for name, content in prompts.items():
        result = linter.lint(f"{name}.prompt", content)
        cells.append({"name": name, "score": result.score, "findings": len(result.findings)})
    return {"prompts": list(prompts.keys()), "results": cells, "total": len(cells)}


def _tool_huaweicloud_modelarts_deploy(args: dict[str, Any]) -> dict[str, Any]:
    model_type = args.get("model_type", "pangu")
    instance_type = args.get("instance_type", "Ascend910")
    region = args.get("region", "cn-north-4")
    deploy_config = {
        "api_version": "v2",
        "kind": "Deployment",
        "metadata": {"name": f"{model_type}-deployment", "region": region},
        "spec": {
            "model_type": model_type,
            "instance_type": instance_type,
            "replicas": 1,
            "resource": {"flavor": instance_type},
            "envs": {"MODEL_NAME": model_type, "REGION": region},
        },
    }
    startup_script = f"""#!/bin/bash
# Huawei Cloud ModelArts Deployment Script
# Model: {model_type}, Instance: {instance_type}, Region: {region}

pip install modelarts
python -c \"\"\"
from modelarts.session import Session
session = Session(region='{region}')
print('ModelArts session initialized for {model_type}')
\"\"\"
"""
    return {
        "deploy_config": deploy_config,
        "startup_script": startup_script,
        "model_type": model_type,
        "instance_type": instance_type,
        "region": region,
        "tips": [
            "请确保已开通华为云ModelArts服务",
            "AK/SK请通过环境变量或IAM认证传入，切勿硬编码",
            "Ascend910适合盘古大模型部署，V100适合通用GPU推理",
        ],
    }


def _tool_huaweicloud_modelarts_infer(args: dict[str, Any]) -> dict[str, Any]:
    endpoint = args.get("endpoint", "https://infer.cn-north-4.myhuaweicloud.com/v1")
    prompt = args.get("prompt", "")
    if not prompt:
        return {"error": "prompt is required"}
    infer_code = f"""import requests

url = "{endpoint}/chat/completions"
headers = {{
    "Content-Type": "application/json",
    "X-Auth-Token": "$TOKEN"  # 从IAM获取
}}
payload = {{
    "model": "pangu",
    "messages": [
        {{"role": "system", "content": "You are a helpful assistant."}},
        {{"role": "user", "content": {prompt!r}}}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}}
resp = requests.post(url, json=payload, headers=headers)
print(resp.json())
"""
    return {
        "infer_code": infer_code,
        "endpoint": endpoint,
        "prompt_preview": prompt[:200],
        "tips": [
            "推理端点URL在ModelArts控制台>在线服务中获取",
            "Token有效期24小时，建议使用AK/SK签名方式",
            "生产环境建议配置自动扩缩容策略",
        ],
    }


def _tool_huaweicloud_obs_upload(args: dict[str, Any]) -> dict[str, Any]:
    bucket = args.get("bucket", "")
    local_path = args.get("local_path", "")
    region = args.get("region", "cn-north-4")
    if not bucket or not local_path:
        return {"error": "bucket and local_path are required"}
    upload_script = f"""import os
from obs import ObsClient

obs_client = ObsClient(
    access_key_id=os.getenv('OBS_AK'),
    secret_access_key=os.getenv('OBS_SK'),
    server='obs.{region}.myhuaweicloud.com'
)

resp = obs_client.putFile('{bucket}', os.path.basename('{local_path}'), '{local_path}')
if resp.status >= 300:
    print(f"Upload failed: {{resp.reason}}")
else:
    print(f"Upload succeeded: obs://{bucket}/{{os.path.basename('{local_path}')}}")

obs_client.close()
"""
    return {
        "upload_script": upload_script,
        "bucket": bucket,
        "local_path": local_path,
        "region": region,
        "target_url": f"obs://{bucket}/{local_path.split('/')[-1] if '/' in local_path else local_path}",
        "tips": [
            "请确保OBS桶已创建且权限配置正确",
            "大文件建议使用分段上传(>5MB)",
            "训练数据上传到OBS后，ModelArts可直接挂载",
        ],
    }


def _tool_huaweicloud_ecs_info(args: dict[str, Any]) -> dict[str, Any]:
    usage = args.get("usage", "AI推理")
    region = args.get("region", "cn-north-4")
    RECOMMENDATIONS = {
        "AI训练": [
            {"flavor": "pi2.2xlarge", "vcpu": 8, "memory": "64GB", "gpu": "Ascend 910", "scenario": "大模型预训练"},
            {"flavor": "p3s.2xlarge", "vcpu": 8, "memory": "64GB", "gpu": "V100 32GB", "scenario": "通用GPU训练"},
            {"flavor": "p2s.2xlarge", "vcpu": 8, "memory": "32GB", "gpu": "V100 16GB", "scenario": "中小模型微调"},
        ],
        "AI推理": [
            {"flavor": "pi1.2xlarge", "vcpu": 8, "memory": "32GB", "gpu": "Ascend 310", "scenario": "盘古推理部署"},
            {"flavor": "p3.2xlarge", "vcpu": 8, "memory": "32GB", "gpu": "V100 16GB", "scenario": "通用GPU推理"},
            {"flavor": "c6.4xlarge", "vcpu": 16, "memory": "32GB", "gpu": "无", "scenario": "CPU轻量推理"},
        ],
        "Web服务": [
            {"flavor": "c6.2xlarge", "vcpu": 8, "memory": "16GB", "gpu": "无", "scenario": "API网关/中间件"},
            {"flavor": "c6.4xlarge", "vcpu": 16, "memory": "32GB", "gpu": "无", "scenario": "高并发Web服务"},
            {"flavor": "m6.2xlarge", "vcpu": 8, "memory": "32GB", "gpu": "无", "scenario": "内存密集型服务"},
        ],
    }
    recommendations = RECOMMENDATIONS.get(usage, RECOMMENDATIONS["AI推理"])
    return {
        "usage": usage,
        "region": region,
        "recommendations": recommendations,
        "tips": [
            "Ascend实例需要申请华为云AI加速资源配额",
            "推理服务建议搭配ELB做负载均衡",
            "按需计费适合开发测试，包周期适合生产环境",
        ],
    }


def _tool_huaweicloud_iam_auth(args: dict[str, Any]) -> dict[str, Any]:
    auth_method = args.get("auth_method", "aksk")
    region = args.get("region", "cn-north-4")
    AUTH_EXAMPLES = {
        "aksk": {
            "description": "AK/SK签名认证（推荐生产环境）",
            "code": f"""import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials

ak = os.getenv('HWCLOUD_AK')
sk = os.getenv('HWCLOUD_SK')

credentials = BasicCredentials(ak, sk, project_id='{region}')
print('AK/SK认证初始化完成')
""",
            "security": ["AK/SK务必存储在环境变量或密钥管理服务(DEW)中", "切勿将AK/SK硬编码或提交到代码仓库"],
        },
        "token": {
            "description": "Token认证（推荐使用AK/SK+DEW替代密码方式）",
            "code": f"""import os
import requests

# 推荐方式: 使用AK/SK获取临时Token，而非密码
ak = os.getenv('HWCLOUD_AK')
sk = os.getenv('HWCLOUD_SK')

# 如必须使用密码认证，请通过DEW(数据加密服务)获取加密存储的密码
# 切勿在代码中明文存储密码
from huaweicloudsdkcore.auth.credentials import BasicCredentials
credentials = BasicCredentials(ak, sk, project_id='{region}')
print('认证初始化完成，建议使用AK/SK而非密码方式')
""",
            "security": [
                "不推荐密码认证方式，优先使用AK/SK",
                "如必须使用密码，请通过DEW(数据加密服务)获取",
                "Token有效期24小时，需定时刷新",
                "建议使用IAM代理而非主账号",
            ],
        },
        "agency": {
            "description": "委托认证（跨账号授权）",
            "code": """import os
from huaweicloudsdkcore.auth.credentials import GlobalCredentials

ak = os.getenv('HWCLOUD_AK')
sk = os.getenv('HWCLOUD_SK')
domain_id = os.getenv('HWCLOUD_DOMAIN_ID')

credentials = GlobalCredentials(ak, sk, domain_id=domain_id)
print('委托认证初始化完成，可通过agency方式跨账号访问')
""",
            "security": ["委托方式需要管理员预先配置信任委托", "建议最小权限原则配置委托策略"],
        },
    }
    example = AUTH_EXAMPLES.get(auth_method, AUTH_EXAMPLES["aksk"])
    return {
        "auth_method": auth_method,
        "region": region,
        "example": example,
        "available_methods": list(AUTH_EXAMPLES.keys()),
        "tips": [
            "生产环境强烈推荐AK/SK+DEW密钥管理",
            "定期轮换AK/SK，建议90天更换一次",
            "使用IAM子账号而非主账号操作",
        ],
    }


def _tool_probe_run(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import ProbeRunner

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    probes_str = args.get("probes", "")
    probe_names = [p.strip() for p in probes_str.split(",") if p.strip()] if probes_str else None
    runner = ProbeRunner(probe_names=probe_names)
    report = runner.run("mcp_probe", text)
    return report.to_dict()


def _tool_probe_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import list_detectors, list_probes

    return {"probes": list_probes(), "detectors": list_detectors()}


def _tool_probe_detect(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import _DETECTOR_REGISTRY

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    detectors_str = args.get("detectors", "")
    if detectors_str:
        detector_names = [d.strip() for d in detectors_str.split(",") if d.strip()]
        detectors = [_DETECTOR_REGISTRY[n]() for n in detector_names if n in _DETECTOR_REGISTRY]
    else:
        detectors = [_DETECTOR_REGISTRY[n]() for n in sorted(_DETECTOR_REGISTRY)]
    results = []
    for det in detectors:
        result = det.detect("", text)
        results.append({"detector": det.name, **result})
    return {"text_preview": text[:200], "detection_results": results}


def _tool_probe_owasp_report(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import ProbeRunner

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    runner = ProbeRunner()
    report = runner.run("owasp_report", text)
    return report.to_owasp_report()


def _tool_probe_detector_run(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import _DETECTOR_REGISTRY

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    detectors_str = args.get("detectors", "")
    verbose = args.get("verbose", False)
    if detectors_str:
        detector_names = [d.strip() for d in detectors_str.split(",") if d.strip()]
        invalid = [n for n in detector_names if n not in _DETECTOR_REGISTRY]
        if invalid:
            return {"error": f"Unknown detectors: {', '.join(invalid)}", "available": sorted(_DETECTOR_REGISTRY.keys())}
        detectors = [_DETECTOR_REGISTRY[n]() for n in detector_names]
    else:
        detectors = [_DETECTOR_REGISTRY[n]() for n in sorted(_DETECTOR_REGISTRY)]
    results = []
    total_detected = 0
    for det in detectors:
        result = det.detect("", text)
        entry = {
            "detector": det.name,
            "is_detected": result.get("is_detected", False),
            "confidence": result.get("confidence", 0.0),
        }
        if verbose:
            entry["details"] = result
        if result.get("is_detected"):
            total_detected += 1
        results.append(entry)
    compliance_score = round(1.0 - (total_detected / len(detectors) if detectors else 0), 4)
    return {
        "text_preview": text[:200],
        "detectors_run": len(detectors),
        "total_detected": total_detected,
        "compliance_score": compliance_score,
        "results": results,
    }


def _tool_probe_owasp_summary(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import ProbeRunner

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    runner = ProbeRunner()
    report = runner.run("owasp_summary", text)
    full_owasp = report.to_owasp_report()
    risk_score = full_owasp.get("risk_score", 0.0)
    if risk_score >= 7.0:
        risk_level = "CRITICAL"
    elif risk_score >= 4.0:
        risk_level = "HIGH"
    elif risk_score >= 2.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    affected = full_owasp.get("total_categories_affected", 0)
    top_findings = []
    for ref, info in full_owasp.get("owasp_findings", {}).items():
        if info.get("total_findings", 0) > 0:
            for finding in info.get("findings", [])[:1]:
                top_findings.append(
                    {"owasp_ref": ref, "name": info.get("name", ""), "severity": finding.get("severity", "unknown")}
                )
    top_findings = sorted(
        top_findings,
        key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("severity", "medium"), 2),
    )[:3]
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "total_categories_affected": affected,
        "total_categories": 10,
        "compliance_pct": round((10 - affected) / 10 * 100, 1),
        "top_3_findings": top_findings,
        "recommendation": "全面加固"
        if risk_level in ("CRITICAL", "HIGH")
        else "针对性修复"
        if risk_level == "MEDIUM"
        else "持续监控",
    }


def _tool_probe_ethics_scan(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.probe_framework import _DETECTOR_REGISTRY

    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    threshold = args.get("threshold", 0.7)
    ethics_det = _DETECTOR_REGISTRY.get("ethics_alignment")
    bias_det = _DETECTOR_REGISTRY.get("bias_fairness")
    if not ethics_det or not bias_det:
        return {"error": "ethics_alignment or bias_fairness detector not found"}
    ethics_result = ethics_det().detect("", text)
    bias_result = bias_det().detect("", text)
    ethics_score = 1.0 - ethics_result.get("confidence", 0.0)
    bias_score = 1.0 - bias_result.get("confidence", 0.0)
    overall_score = round((ethics_score + bias_score) / 2, 4)
    is_compliant = overall_score >= threshold
    recommendations = []
    if ethics_result.get("is_detected"):
        recommendations.append(
            f"[伦理对齐] 检测到有害内容关键词: {', '.join(ethics_result.get('harm_keywords_found', [])[:3])}"
        )
        recommendations.append("建议添加安全护栏声明，明确禁止生成有害/违法/不道德内容")
    if bias_result.get("is_detected"):
        recommendations.append(f"[偏见公平] 检测到偏见表述模式({bias_result.get('bias_matches_count', 0)}处)")
        recommendations.append("建议使用中性表述，添加包容性/公平性声明")
    if is_compliant:
        recommendations.append("[合规] 伦理对齐评分达标，建议持续监控")
    else:
        recommendations.append(f"[不合规] 伦理对齐评分({overall_score})低于阈值({threshold})，需立即修复")
    return {
        "text_preview": text[:200],
        "ethics_alignment": {
            "is_detected": ethics_result.get("is_detected", False),
            "score": round(ethics_score, 4),
            "details": ethics_result,
        },
        "bias_fairness": {
            "is_detected": bias_result.get("is_detected", False),
            "score": round(bias_score, 4),
            "details": bias_result,
        },
        "overall_ethics_score": overall_score,
        "threshold": threshold,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


def _tool_huaweicloud_compliance(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.huaweicloud_compliance import compute_huaweicloud_compliance

    text = args.get("text", "")
    template_id = args.get("template_id", "")
    owasp_pct = args.get("owasp_compliance_pct", 0.0)
    if not text:
        return {"error": "text is required"}
    from ai_prompt_toolkit.security.injection_detector import InjectionDetector
    from ai_prompt_toolkit.security.pii_detector import PIIDetector
    from ai_prompt_toolkit.security.structural_analyzer import check_structural
    from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

    all_findings: list[Finding] = list(InjectionDetector().detect(text))
    pii_f = PIIDetector().check(text)
    if pii_f:
        all_findings.append(pii_f)
    sc_f = SupplyChainDetector().check(text)
    if sc_f:
        all_findings.append(sc_f)
    struct_f = check_structural(text)
    if struct_f:
        all_findings.append(struct_f)
    report = compute_huaweicloud_compliance(all_findings, template_id=template_id, owasp_compliance_pct=owasp_pct)
    return report.to_dict()


def _tool_prompt_semantic_diff(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_diff import semantic_diff

    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    if not old_text or not new_text:
        return {"error": "old_text and new_text are required"}
    report = semantic_diff(old_text, new_text)
    return report.to_dict()


def _tool_multimodal_token_estimate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.multimodal_token_counter import MultimodalTokenCounter

    text = args.get("text", "")
    image_width = args.get("image_width", 0)
    image_height = args.get("image_height", 0)
    image_detail = args.get("image_detail", "auto")
    audio_duration = args.get("audio_duration", 0.0)
    video_duration = args.get("video_duration", 0.0)
    video_fps = args.get("video_fps", 1)
    max_total = args.get("max_total", 8192)
    counter = MultimodalTokenCounter(max_total=max_total)
    if text:
        counter.count_text(text)
    if image_width and image_height:
        counter.count_image(int(image_width), int(image_height), image_detail)
    if audio_duration:
        counter.count_audio(float(audio_duration))
    if video_duration:
        counter.count_video(float(video_duration), int(video_fps))
    return counter.get_budget().to_dict()


def _tool_config_hot_reload_status(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.config import get_watcher

    watcher = get_watcher()
    watches = [
        {"path": str(ws.path), "mtime": ws.mtime, "content_hash": ws.content_hash[:8]} for ws in watcher._watches
    ]
    return {
        "running": watcher._running,
        "watch_count": len(watcher._watches),
        "watches": watches,
        "poll_interval": watcher._poll_interval,
        "debounce_seconds": watcher._debounce_seconds,
    }


def _tool_badge_generate_themed(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.badge import generate_score_svg
    from ai_prompt_toolkit.security.prompt_scorecard import Grade

    score = args.get("score", 80)
    grade_str = args.get("grade", "B")
    theme = args.get("theme", "light")
    if theme not in ("light", "dark", "huawei"):
        theme = "light"
    try:
        grade = Grade(grade_str)
    except ValueError:
        grade = Grade.B
    svg = generate_score_svg(int(score), grade, theme=theme)
    return {"svg": svg, "score": score, "grade": grade_str, "theme": theme}


def _tool_harmonyos_arkui_check(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    import re

    arkui_keywords = re.compile(
        r"(?:ArkUI|ArkTS|Component|@Component|@Entry|@Builder|Row|Column|Text|Image|List|Grid|Tabs|Navigation|Swiper|@State|@Prop|@Link|@Watch|@Provide|@Consume)",
        re.IGNORECASE,
    )
    best_practice = re.compile(
        r"(?:组件.*推荐|component.*recommend|自定义组件|custom.*component|@Builder.*封装|@Extend|样式.*复用|style.*reuse|懒加载|lazy.*load|复用.*策略|reuse.*strategy)",
        re.IGNORECASE,
    )
    has_arkui = bool(arkui_keywords.search(text))
    has_best_practice = bool(best_practice.search(text))
    checks = []
    if has_arkui and not has_best_practice:
        checks.append(
            {
                "check": "ArkUI最佳实践缺失",
                "severity": "warn",
                "suggestion": "声明组件复用策略、懒加载、自定义组件封装等ArkUI最佳实践",
            }
        )
    if not re.search(r"@Component|@Entry", text) and has_arkui:
        checks.append(
            {"check": "ArkUI组件装饰器缺失", "severity": "warn", "suggestion": "使用@Component/@Entry装饰器声明组件"}
        )
    return {"pass": len(checks) == 0, "has_arkui_context": has_arkui, "checks": checks}


def _tool_harmonyos_stage_model_check(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    import re

    stage_keywords = re.compile(
        r"(?:Stage|Ability|UIAbility|ExtensionAbility|onCreate|onDestroy|onWindowStageCreate|onForeground|onBackground|AbilityStage|Context|HAP|HSP)",
        re.IGNORECASE,
    )
    lifecycle_decl = re.compile(
        r"(?:生命周期|lifecycle|onCreate|onDestroy|onForeground|onBackground|onWindowStageCreate|状态.*管理|state.*manage)",
        re.IGNORECASE,
    )
    has_stage = bool(stage_keywords.search(text))
    has_lifecycle = bool(lifecycle_decl.search(text))
    checks = []
    if has_stage and not has_lifecycle:
        checks.append(
            {
                "check": "Stage模型生命周期声明缺失",
                "severity": "warn",
                "suggestion": "声明UIAbility生命周期回调(onCreate/onDestroy/onForeground/onBackground)",
            }
        )
    if has_stage and not re.search(r"Context|want|AbilityResult", text, re.IGNORECASE):
        checks.append(
            {
                "check": "Stage模型Ability交互声明缺失",
                "severity": "info",
                "suggestion": "声明Ability间交互方式(Context/want/AbilityResult)",
            }
        )
    return {"pass": len(checks) == 0, "has_stage_context": has_stage, "checks": checks}


def _tool_harmonyos_distributed_check(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text", "")
    if not text:
        return {"error": "text is required"}
    import re

    dist_keywords = re.compile(
        r"(?:分布式|distributed|设备.*发现|device.*discover|数据.*迁移|data.*migrat|跨设备|cross.?device|流转|flow|协同|collaborat|Continuation|RemoteObject|DistributedData|DeviceManager)",
        re.IGNORECASE,
    )
    conflict_decl = re.compile(
        r"(?:冲突.*解决|conflict.*resolut|数据.*同步|data.*sync|一致性|consistency|锁|lock|互斥|mutex|仲裁|arbitrat|超时|timeout)",
        re.IGNORECASE,
    )
    has_dist = bool(dist_keywords.search(text))
    has_conflict = bool(conflict_decl.search(text))
    checks = []
    if has_dist and not has_conflict:
        checks.append(
            {
                "check": "分布式冲突解决策略缺失",
                "severity": "warn",
                "suggestion": "声明数据同步策略、冲突解决机制、锁/互斥机制、超时处理",
            }
        )
    if has_dist and not re.search(r"Continuation|RemoteObject|DistributedData|DeviceManager", text, re.IGNORECASE):
        checks.append(
            {
                "check": "分布式API声明缺失",
                "severity": "info",
                "suggestion": "声明使用的分布式API(Continuation/RemoteObject/DistributedData/DeviceManager)",
            }
        )
    return {"pass": len(checks) == 0, "has_distributed_context": has_dist, "checks": checks}


def _tool_harmonyos_template_generate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.harmonyos_templates import get_template

    rule_id = args.get("rule_id", "")
    scene = args.get("scene", "general")
    if not rule_id:
        return {"error": "rule_id is required"}
    template = get_template(rule_id)
    if template is None:
        return {
            "error": f"No template found for rule {rule_id}",
            "available_rules": ["P121", "P122", "P124", "P146", "P147", "P148", "P149", "P150"],
        }
    return {"rule_id": rule_id, "scene": scene, "template": template, "language": "ArkTS"}


def _tool_prompt_lint_json_schema(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
    from ai_prompt_toolkit.linter.rules import get_all_rules

    category = args.get("category", "")
    include_owasp = args.get("include_owasp", True)
    rules = get_all_rules()
    if category:
        rules = [r for r in rules if r.category == category]
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ai-prompt-toolkit Lint Rule Set",
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "string", "pattern": "^P\\d{3}$"},
                        "name": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "structure",
                                "security",
                                "performance",
                                "quality",
                                "compliance",
                                "agent",
                                "rag",
                                "harmonyos",
                                "multimodal",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                        "description": {"type": "string"},
                        "remediation": {"type": "string"},
                        "auto_fixable": {"type": "boolean"},
                    },
                    "required": ["rule_id", "name", "category", "severity"],
                },
            },
        },
    }
    if include_owasp:
        schema["properties"]["rules"]["items"]["properties"]["owasp_refs"] = {
            "type": "array",
            "items": {"type": "string", "pattern": "^LLM\\d{2}$"},
        }
    rules_data = []
    for r in rules:
        entry = r.to_dict()
        entry["auto_fixable"] = r.rule_id in AUTO_FIXABLE_RULES
        rules_data.append(entry)
    return {
        "schema": schema,
        "rules": rules_data,
        "total_count": len(rules_data),
        "auto_fixable_count": sum(1 for r in rules if r.rule_id in AUTO_FIXABLE_RULES),
    }


def _tool_output_scan(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.security.output_scanners import OutputScanEngine

    text = args.get("text", "")
    context = args.get("context", "")
    scanners = args.get("scanners", "")
    if not text:
        return {"error": "text is required"}
    scanner_kwargs = {}
    if scanners:
        scanner_list = [s.strip() for s in scanners.split(",")]
        scanner_kwargs = {
            "enable_no_refusal": "no_refusal" in scanner_list,
            "enable_bias": "bias" in scanner_list,
            "enable_toxicity": "toxicity" in scanner_list,
            "enable_relevance": "relevance" in scanner_list,
            "enable_factual": "factual_consistency" in scanner_list,
            "enable_citation": "citation" in scanner_list,
        }
    engine = OutputScanEngine(**scanner_kwargs) if scanner_kwargs else OutputScanEngine()
    report = engine.scan(text, context=context)
    return report.to_dict()


def _tool_deveco_config(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.harmonyos_templates import (
        generate_deveco_build_hook,
        generate_deveco_config,
        generate_deveco_workflow_yaml,
    )

    project_name = args.get("project_name", "MyHarmonyApp")
    bundle_name = args.get("bundle_name", "com.example.myapp")
    min_api = int(args.get("min_api", 12))
    target_api = int(args.get("target_api", 14))
    config = generate_deveco_config(
        project_name=project_name,
        bundle_name=bundle_name,
        min_api=min_api,
        target_api=target_api,
        enable_prompt_lint=args.get("enable_lint", True),
        enable_security_scan=args.get("enable_scan", True),
        enable_output_scan=args.get("enable_output_scan", True),
        enable_redteam=args.get("enable_redteam", False),
    )
    build_hook = generate_deveco_build_hook()
    workflow_yaml = generate_deveco_workflow_yaml()
    return {
        "config": config,
        "build_hook_lines": len(build_hook.splitlines()),
        "workflow_yaml_lines": len(workflow_yaml.splitlines()),
    }


def _tool_rollback_safety_check(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.prompt_diff import rollback_safety_check

    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    result = rollback_safety_check(old_text, new_text)
    return result.to_dict()


def _tool_html_report_generate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.html_report import generate_html_report

    findings = args.get("findings", [])
    target = args.get("target", "unknown")
    html = generate_html_report(findings, target)
    return {"html_length": len(html), "target": target}


def _tool_weight_preset_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.evaluator import list_weight_presets

    presets = list_weight_presets()
    return {"presets": presets, "count": len(presets)}


def _tool_fg_template_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.huawei_cloud.fg_template import list_fg_templates

    templates = list_fg_templates()
    return {"templates": templates, "count": len(templates)}


def _tool_fg_template_generate(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.huawei_cloud.fg_template import get_fg_template

    template_type = args.get("template_type", "ai_inference")
    name = args.get("name", "")
    description = args.get("description", "")
    template = get_fg_template(template_type, name=name, description=description)
    return {
        "name": template.name,
        "type": template.template_type.value,
        "description": template.description,
        "code": template.code,
        "env_vars": template.env_vars,
        "prompt_variables": template.prompt_variables,
        "version": template.version,
    }


def _tool_prompt_version_create(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager

    vm = PromptVersionManager()
    template_id = args.get("template_id", "")
    content = args.get("content", "")
    author = args.get("author", "")
    score = args.get("score", 0.0)
    grade = args.get("grade", "")
    pv = vm.create_version(template_id, content, author=author, score=score, grade=grade)
    return {
        "version_id": pv.version_id,
        "template_id": template_id,
        "change_type": pv.change_type,
        "parent_version": pv.parent_version,
    }


def _tool_prompt_version_list(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager

    vm = PromptVersionManager()
    template_id = args.get("template_id", "")
    versions = vm.get_versions(template_id)
    return {
        "template_id": template_id,
        "versions": [
            {
                "version_id": v.version_id,
                "change_type": v.change_type,
                "score": v.score,
                "grade": v.grade,
                "timestamp": v.timestamp,
            }
            for v in versions
        ],
        "count": len(versions),
    }


def _tool_prompt_version_diff(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.prompt_version import PromptVersionManager

    vm = PromptVersionManager()
    template_id = args.get("template_id", "")
    v1 = args.get("version_id_1", "")
    v2 = args.get("version_id_2", "")
    diff_result = vm.diff_versions(template_id, v1, v2)
    if not diff_result:
        return {"error": f"版本不存在: {v1} 或 {v2}"}
    return {"template_id": template_id, "from": v1, "to": v2, "diff": diff_result}


def _tool_mcp_reload(args: dict[str, Any]) -> dict[str, Any]:
    global _TOOL_DISPATCH
    import importlib
    import sys

    # 类身份保护: linter.rules 定义 LintRule/Finding 等核心类, in-process reload 会重建
    # 类对象, 导致 rule_loader/引擎等持有旧类引用的模块 isinstance 跨重载边界失效
    # (自定义规则被静默丢弃、RuleLoader 返回类型校验失败)。核心类模块不做 reload,
    # 仅热重载数据型扩展模块(rules_p*/owasp_mapping)——它们以 rule_id 为键把规则
    # 重新注册进现有 _RULE_MAP, 幂等且规则数稳定 255。核心类本身的变更需重启进程。
    _CORE_IDENTITY_MODULES = frozenset(
        {
            "ai_prompt_toolkit.linter.rules",
            "ai_prompt_toolkit.types",
        }
    )
    module_name = args.get("module", "ai_prompt_toolkit.linter.rules")
    try:
        is_core = module_name in _CORE_IDENTITY_MODULES
        if not is_core:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
        if module_name == "ai_prompt_toolkit.linter.rules":
            for mname in sorted(sys.modules):
                base = mname.rsplit(".", 1)[-1]
                if base.startswith("rules_p") and mname.rsplit(".", 1)[0] == "ai_prompt_toolkit.linter":
                    importlib.reload(sys.modules[mname])
            # owasp 映射引用 _RULE_MAP, 一并 reload 以同步(幂等)
            owasp_mod = sys.modules.get("ai_prompt_toolkit.linter.owasp_mapping")
            if owasp_mod is not None:
                importlib.reload(owasp_mod)
        _TOOL_DISPATCH = None
        from ai_prompt_toolkit.linter.rules import get_all_rules

        rule_count = len(get_all_rules())
        result: dict[str, Any] = {"status": "reloaded", "module": module_name, "rule_count": rule_count}
        if is_core:
            result["note"] = "核心类模块保持类身份稳定(未重建类), 已热重载规则数据模块; 核心类变更需重启进程"
        return result
    except Exception as e:
        return {"status": "error", "module": module_name, "error": str(e)}


def _tool_test_suite_run(args: dict[str, Any]) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.test_suite import load_test_suite, run_test_suite

    suite_path = args.get("suite_path", "")
    base_dir = args.get("base_dir", ".")
    if not suite_path:
        return {"error": "suite_path is required"}
    try:
        suite = load_test_suite(suite_path)
        result = run_test_suite(suite, base_dir=base_dir)
        return result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    run_server()
