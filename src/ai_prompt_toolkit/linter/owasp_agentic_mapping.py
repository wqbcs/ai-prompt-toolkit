"""OWASP Agentic Top 10 2026 映射 — 红队Probe到Agentic风险项对照表

OWASP Top 10 for Agentic Applications (2026):
ASI01 Agent Goal Hijack / ASI02 Tool Misuse and Exploitation /
ASI03 Identity and Privilege Abuse / ASI04 Agentic Supply Chain Vulnerabilities /
ASI05 Unexpected Code Execution (RCE) / ASI06 Memory & Context Poisoning /
ASI07 Insecure Inter-Agent Communication / ASI08 Cascading Failures /
ASI09 Human-Agent Trust Exploitation / ASI10 Rogue Agents

映射原则(静态特征, 零LLM调用):
- goalhijack/agentinject/multiagent → ASI01/ASI07/ASI10 (Agent目标与通信)
- toolabuse → ASI02 (工具滥用)
- privilegescalation/leakreplay/system_prompt_leak → ASI03 (身份与权限)
- packagehallucination → ASI04 (供应链: 幻觉包=供应链投毒入口)
- malwaregen/gcg/badchars/xss → ASI05 (意外代码执行)
- vector_embedding/snowball/continuation/donot_answer → ASI06 (记忆与上下文投毒)
- agentinject/multiagent → ASI07 (Agent间通信)
- snowball/gcg/continuation → ASI08 (级联失败: 滚雪球/GCG多轮放大)
- grandma/promptinject/encoding → ASI09 (人机信任滥用)
- multiagent/agentinject → ASI10 (流氓Agent: 多Agent对抗/目标劫持)

参考: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
"""

from __future__ import annotations

from typing import Any

OWASP_AGENTIC_TOP_10_2026: dict[str, dict[str, Any]] = {
    "ASI01": {
        "name": "Agent Goal Hijack",
        "name_zh": "Agent目标劫持",
        "probes": "goalhijack,agentinject",
        "lint_rules": ["P141", "P145"],
        "description": "攻击者篡改Agent目标, 使其偏离声明任务执行恶意行为",
        "mitigation": "声明可执行操作边界; 目标变更需用户确认; 定期校验目标一致性",
    },
    "ASI02": {
        "name": "Tool Misuse and Exploitation",
        "name_zh": "工具滥用与利用",
        "probes": "toolabuse",
        "lint_rules": ["P142", "P143"],
        "description": "Agent被诱导调用非授权工具或以危险参数调用授权工具",
        "mitigation": "最小权限工具白名单; 参数校验; 高危操作二次确认",
    },
    "ASI03": {
        "name": "Identity and Privilege Abuse",
        "name_zh": "身份与权限滥用",
        "probes": "privilegescalation,leakreplay,system_prompt_leak",
        "lint_rules": ["P142", "P158"],
        "description": "攻击者利用Agent身份获取超出预期的权限, 或泄露凭证/系统提示",
        "mitigation": "Agent身份隔离; 凭证最小暴露; 系统提示防泄露声明",
    },
    "ASI04": {
        "name": "Agentic Supply Chain Vulnerabilities",
        "name_zh": "Agent供应链漏洞",
        "probes": "packagehallucination",
        "lint_rules": ["P152", "P153"],
        "description": "Agent安装/调用被投毒的第三方工具、插件或幻觉包",
        "mitigation": "工具来源校验; 禁止运行时动态引入未审计依赖; 包名白名单",
    },
    "ASI05": {
        "name": "Unexpected Code Execution (RCE)",
        "name_zh": "意外代码执行",
        "probes": "malwaregen,gcg,badchars,xss",
        "lint_rules": ["P177", "P178", "P179", "P180"],
        "description": "攻击者诱导Agent执行恶意代码或危险系统命令",
        "mitigation": "执行环境沙箱; 代码/命令静态审查; 输出过滤",
    },
    "ASI06": {
        "name": "Memory & Context Poisoning",
        "name_zh": "记忆与上下文投毒",
        "probes": "vector_embedding,snowball,continuation,donot_answer",
        "lint_rules": ["P164"],
        "description": "恶意内容注入Agent长期记忆或上下文窗口, 持续影响后续决策",
        "mitigation": "记忆写入前消毒; 上下文完整性校验; 关键决策不依赖单一来源",
    },
    "ASI07": {
        "name": "Insecure Inter-Agent Communication",
        "name_zh": "Agent间通信不安全",
        "probes": "agentinject,multiagent",
        "lint_rules": ["P145"],
        "description": "Agent间消息被篡改/伪造, 或身份未验证导致消息被恶意Agent接收",
        "mitigation": "Agent间消息签名; 身份验证; 通信内容过滤",
    },
    "ASI08": {
        "name": "Cascading Failures",
        "name_zh": "级联失败",
        "probes": "snowball,gcg,continuation",
        "lint_rules": ["P143", "P180"],
        "description": "单Agent故障被放大, 沿调用链级联扩散至整个系统",
        "mitigation": "熔断器; 最大迭代次数限制; 故障隔离",
    },
    "ASI09": {
        "name": "Human-Agent Trust Exploitation",
        "name_zh": "人机信任滥用",
        "probes": "grandma,promptinject,encoding",
        "lint_rules": ["P203"],
        "description": "利用人类对Agent输出的过度信任, 诱导用户执行危险操作",
        "mitigation": "AI身份标识; 高风险建议标注; 不代替用户做不可逆决策",
    },
    "ASI10": {
        "name": "Rogue Agents",
        "name_zh": "流氓Agent",
        "probes": "multiagent,agentinject,goalhijack",
        "lint_rules": ["P141", "P145"],
        "description": "Agent偏离预期行为, 执行未授权操作或与其他Agent合谋",
        "mitigation": "行为监控; 异常隔离(Quarantine); 行为边界声明",
    },
}


def get_agentic_findings(results: list[Any]) -> dict[str, dict[str, Any]]:
    """将Probe运行结果映射到OWASP Agentic Top 10

    仅统计is_detected=True的结果; 返回含findings的ASI条目(空结果不输出)。
    results: ProbeResult对象列表(需有probe_name/is_detected属性)。
    """
    findings: dict[str, dict[str, Any]] = {}
    for asi_ref, info in OWASP_AGENTIC_TOP_10_2026.items():
        probe_names = [p.strip() for p in info["probes"].split(",")]
        matched = []
        for r in results:
            if r.probe_name in probe_names and r.is_detected:
                matched.append(r.to_dict())
        if matched:
            findings[asi_ref] = {
                "name": info["name"],
                "name_zh": info["name_zh"],
                "total_findings": len(matched),
                "findings": matched[:5],
                "mitigation": info["mitigation"],
            }
    return findings


def is_agentic_prompt(text: str) -> bool:
    """静态判定prompt是否含Agent特征(决定是否输出Agentic评估章节)"""
    markers = (
        "agent",
        "智能体",
        "工具调用",
        "function calling",
        "tool use",
        "react",
        "多agent",
        "multi-agent",
        "sub-agent",
        "子代理",
        "规划",
        "planning",
    )
    lowered = text.lower()
    return any(m in lowered for m in markers)
