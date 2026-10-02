"""R224-P1-3: OWASP LLM Top 10 防御缺口报告 — 每文件×每风险的防御声明体检。

复用:
- probe_framework.OWASP_LLM_TOP_10_2025 (10风险定义+官方remediation, 不新造)
- linter.owasp_mapping.get_owasp_coverage / _OWASP_RULE_MAPPING (规则映射, 不新造)

口径(诚实声明, 与prompt-defense-audit同类工具对齐):
度量的是**防御声明/意图的存在性**(文本层静态可检测面), 不是防御的实际有效性。
运行时拦截/运行时防护不在本工具检测域, 见 README 适用域划分。

输出: JSON(供CI断言) + Markdown(供README/评审)。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.linter.owasp_mapping import get_owasp_coverage
from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2025, _OWASP_REMEDIATIONS

# 每风险的防御意图标记词表(文本层静态检测面)。
# 设计: 中英双语+关键语义, 宽口径(命中任一即视为"声明了该风险的防御意图")。
# 这是启发式: 词在≠防御有效, 词无≠防御不存在(可能在运行时层) — 报告口径声明见模块docstring。
_RISK_DEFENSE_MARKERS: dict[str, list[str]] = {
    "LLM01": [
        # Prompt Injection — 输入边界/指令隔离/转义/不执行用户指令
        "忽略.{0,6}(指令|命令).{0,12}(用户|外部|输入)",
        "不执行.{0,8}(用户|外部).{0,8}(指令|命令)",
        "输入.{0,6}(边界|转义|校验|过滤)",
        "指令层级|指令隔离|input boundary",
        "转义.{0,6}(用户|外部|输入)",
        "promptlint:ignore",  # 显式豁免=已有注入面意识
    ],
    "LLM02": [
        # Sensitive Information Disclosure — 防泄露声明/不输出敏感信息
        "不(输出|泄露|透露|展示).{0,12}(敏感|隐私|个人|内部|秘密)",
        "不(输出|泄露|透露).{0,8}(系统提示|提示词|system prompt)",
        "防泄露|防泄漏|禁止.{0,8}(泄露|透露)",
        "数据(脱敏|最小化|不保留)",
        "个人信息.{0,6}(保护|最小)",
    ],
    "LLM03": [
        # Supply Chain — 包来源/版本锁定/不安装未验证包
        "(官方|可信).{0,6}(源|渠道|包)",
        "版本(锁定|固定|pin)",
        "不(安装|引入|调用).{0,10}(未验证|未知|不明)",
        "供应链|supply.chain",
        "签名校验|完整性校验",
    ],
    "LLM04": [
        # Data & Model Poisoning — 数据来源验证/不采信外部数据
        "数据(来源|出处).{0,6}(验证|校验|标注)",
        "不(采信|信任|执行).{0,8}(外部|外部数据|未验证)",
        "数据(验证|校验|过滤).{0,8}(前|之前)",
        "投毒|poisoning",
    ],
    "LLM05": [
        # Improper Output Handling — 输出转义/防二次注入
        "输出.{0,8}(转义|编码|过滤|校验)",
        "防.{0,6}(XSS|注入|二次)",
        "HTML.{0,6}(转义|编码|escape)",
        "输出.{0,8}(不直接|经过).{0,6}(渲染|执行|插入)",
    ],
    "LLM06": [
        # Excessive Agency — 权限最小化/人工审批/不自主执行高危
        "最小权限|least.privilege",
        "人工审批|人工确认|human.in.the.loop",
        "不(自主|自行).{0,8}(执行|调用|修改|删除)",
        "高危操作.{0,8}(确认|审批|二次)",
        "权限(范围|最小|受限)",
    ],
    "LLM07": [
        # System Prompt Leakage — 系统提示保护/canary
        "系统提示.{0,8}(保密|不外泄|不泄露|保护|分段)",
        "canary|金丝雀",
        "不(复述|输出|展示).{0,8}(系统提示|system.prompt)",
        "system.prompt.{0,8}(protect|hidden)",
    ],
    "LLM08": [
        # Vector & Embedding Weaknesses — 检索访问控制/相似度阈值
        "向量(库|数据库).{0,8}(访问控制|权限|隔离)",
        "(相似度|阈值).{0,8}(过滤|阈值)",
        "检索.{0,8}(净化|过滤|验证|白名单)",
        "embedding.{0,8}(threshold|filter)",
    ],
    "LLM09": [
        # Misinformation — 事实校验/知识截止/不编造
        "不(编造|虚构|杜撰)|no.hallucination",
        "事实(校验|核对|溯源)|fact.check",
        "知识(截止|边界|时效)",
        "不确定.{0,6}(说明|告知|承认|标注)",
        "引用.{0,6}(来源|出处)",
    ],
    "LLM10": [
        # Unbounded Consumption — 资源限制/token预算/速率
        "token.{0,8}(预算|上限|限制|budget)",
        "(速率|频率)限制|rate.limit",
        "输出.{0,6}(不超|限制).{0,6}(字|token|长度)",
        "成本(监控|上限|限制)",
        "资源(限制|上限|配额)",
    ],
}

_SEVERITY_BY_GAP_COUNT = (
    (6, "critical"),  # 缺6+风险防御声明
    (4, "high"),
    (2, "medium"),
    (1, "low"),
)


def _compile_markers() -> dict[str, list[re.Pattern]]:
    return {ref: [re.compile(p, re.IGNORECASE) for p in pats] for ref, pats in _RISK_DEFENSE_MARKERS.items()}


_MARKERS = _compile_markers()


def assess_text(text: str) -> dict[str, bool]:
    """返回 {LLMxx: 是否声明了该风险的防御意图}。"""
    return {ref: any(p.search(text) for p in pats) for ref, pats in _MARKERS.items()}


def assess_files(files: dict[str, str]) -> dict[str, dict[str, Any]]:
    """每文件: 缺哪些风险防御 + gap率 + 分级。"""
    result: dict[str, dict[str, Any]] = {}
    for name, text in sorted(files.items()):
        covered = assess_text(text)
        gaps = sorted(ref for ref, ok in covered.items() if not ok)
        gap_rate = len(gaps) / len(covered)
        grade = "pass"
        for threshold, sev in _SEVERITY_BY_GAP_COUNT:
            if len(gaps) >= threshold:
                grade = sev
                break
        result[name] = {
            "covered": [ref for ref, ok in covered.items() if ok],
            "gaps": gaps,
            "gap_rate": round(gap_rate, 4),
            "grade": grade,
        }
    return result


def aggregate(files: dict[str, str]) -> dict[str, Any]:
    """聚合: 每风险缺防御的文件占比(社会证明数字) + 每文件分级 + 总缺口率。"""
    per_file = assess_files(files)
    n = len(files) or 1
    risk_gaps: dict[str, dict[str, Any]] = {}
    coverage = get_owasp_coverage()
    for ref, info in sorted(OWASP_LLM_TOP_10_2025.items()):
        lacking = [name for name, d in per_file.items() if ref in d["gaps"]]
        risk_gaps[ref] = {
            "name": info["name"],
            "lacking_count": len(lacking),
            "lacking_rate": round(len(lacking) / n, 4),
            "lacking_files": lacking,
            "remediation": _OWASP_REMEDIATIONS.get(ref, ""),
            "lint_rules": coverage.get(ref, {}).get("lint_rules", []),
        }
    grades = [d["grade"] for d in per_file.values()]
    return {
        "generated_at": datetime.now().isoformat(),
        "file_count": len(files),
        "risks": risk_gaps,
        "per_file": per_file,
        "summary": {
            "grade_distribution": {g: grades.count(g) for g in ("critical", "high", "medium", "low", "pass")},
            "avg_gap_rate": round(sum(d["gap_rate"] for d in per_file.values()) / n, 4),
            "worst_risk": max(risk_gaps.items(), key=lambda kv: kv[1]["lacking_rate"])[0] if risk_gaps else "",
        },
        "caveat": "度量防御声明/意图存在性(静态文本面), 非防御实际有效性; 运行时防护不在检测域",
    }


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OWASP LLM Top 10 防御缺口报告",
        "",
        f"生成: {report['generated_at']} · 文件数: {report['file_count']} · 平均缺口率: {report['summary']['avg_gap_rate']:.0%}",
        "",
        "> 口径: 度量**防御声明/意图存在性**(静态文本面), 非实际有效性; 运行时防护不在检测域。",
        "",
        "## 每风险防御缺口(缺声明的文件占比)",
        "",
        "| 风险 | 名称 | 缺声明文件 | 占比 | 映射Lint规则 |",
        "|---|---|---|---|---|",
    ]
    for ref, d in sorted(report["risks"].items()):
        rules = d["lint_rules"]
        rules_s = f"{len(rules)}条({', '.join(rules[:4])}{'…' if len(rules) > 4 else ''})" if rules else "—"
        lines.append(f"| {ref} | {d['name']} | {d['lacking_count']}/{report['file_count']} | {d['lacking_rate']:.0%} | {rules_s} |")
    worst = report["summary"]["worst_risk"]
    lines += [
        "",
        f"**最大缺口风险**: {worst} {report['risks'][worst]['name']} ({report['risks'][worst]['lacking_rate']:.0%} 文件缺防御声明)",
        "",
        "## 每文件分级",
        "",
        "| 文件 | 缺口 | 缺哪些风险 | 分级 |",
        "|---|---|---|---|",
    ]
    for name, d in sorted(report["per_file"].items(), key=lambda kv: -kv[1]["gap_rate"]):
        lines.append(f"| {name} | {len(d['gaps'])}/10 | {', '.join(d['gaps']) or '—'} | {d['grade']} |")
    lines += ["", "## 修复建议(按最大缺口风险)", ""]
    for ref, d in sorted(report["risks"].items(), key=lambda kv: -kv[1]["lacking_rate"])[:3]:
        if d["lacking_count"] == 0:
            break
        lines.append(f"- **{ref} {d['name']}** ({d['lacking_rate']:.0%} 文件缺): {d['remediation']}")
    return "\n".join(lines)


def write_report(report: dict[str, Any], output: str | Path) -> None:
    p = Path(output)
    if p.suffix.lower() in (".md", ".markdown"):
        p.write_text(format_markdown(report), encoding="utf-8")
    else:
        p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
