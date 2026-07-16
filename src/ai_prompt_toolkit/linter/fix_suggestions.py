"""Lint智能修复建议 — 按影响分数排序+自动修复+手动修复步骤

P2-02: 解决"修复哪个问题优先？"的决策疲劳
- 每个Finding计算score_impact(对总评分的影响权重)
- 支持自动修复的显示一键修复+预览
- 不支持自动修复的显示手动修复步骤
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity
from ai_prompt_toolkit.linter.linter import FixAction, PromptLinter


_SEVERITY_IMPACT = {
    Severity.CRITICAL: 15.0,
    Severity.HIGH: 10.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.5,
}

_CATEGORY_IMPACT = {
    "structure": 3.0,
    "clarity": 2.5,
    "security": 4.0,
    "consistency": 2.0,
    "completeness": 3.5,
    "performance": 1.5,
    "robustness": 3.0,
    "localization": 1.0,
}

_MANUAL_FIX_STEPS: dict[str, list[str]] = {
    "P001": ["检查Prompt是否有清晰的角色定义", "在开头添加'你是一个[角色]'", "明确指定专业领域和能力边界"],
    "P002": ["将任务分解为2-5个步骤", "使用编号列表明确执行顺序", "每步添加期望输出说明"],
    "P003": ["在Prompt末尾添加输出格式示例", "使用JSON/Markdown模板定义格式", "添加'请按以下格式输出'前缀"],
    "P004": ["添加约束条件(如'不超过500字')", "明确边界条件(如'如果无法回答请说明')", "添加负面约束(如'不要编造信息')"],
    "P007": ["将复杂指令拆分为多个子Prompt", "使用条件分支处理不同场景", "添加'如果...则...'逻辑结构"],
    "P008": ["添加'请用中文回答'语言指令", "避免混用中英文术语", "统一使用目标语言的专业术语"],
    "P009": ["添加长度限制(如'500字以内')", "使用分段标记控制输出结构", "添加'简洁回答'或'详细说明'指令"],
    "P010": ["在Prompt中提供2-3个示例", "使用'例如:'引导示例", "确保示例覆盖典型场景"],
    "P011": ["将核心指令放在开头和结尾", "避免在中间嵌入关键约束", "使用'重要:'标记关键指令"],
    "P012": ["添加'请逐步推理'指令", "要求模型先分析再回答", "添加中间步骤检查点"],
    "P013": ["在输出要求中指定评估标准", "添加'请自检以下条件'指令", "使用对比检查列表"],
    "P014": ["添加'如果不确定请说明'指令", "避免绝对化表述", "添加置信度输出要求"],
    "P015": ["使用更精确的词汇替换模糊词", "将'可能'改为'需要'、'大概'改为'具体'", "添加量化和时间约束"],
    "P017": ["在开头定义角色和语气", "添加'以[语气]风格回答'指令", "确保语气与目标受众匹配"],
    "P018": ["添加'请用中文回答'或'Please answer in English'", "避免中英混用导致歧义", "统一专业术语的翻译"],
    "P019": ["添加上下文传递指令(如'基于以上内容')", "在多轮对话中引用前文", "使用编号引用特定部分"],
    "P020": ["添加'请基于事实回答'指令", "要求标注信息来源", "添加'不要编造'约束"],
    "P021": ["确保变量使用{{variable}}格式", "检查所有变量是否在上下文中定义", "为变量添加默认值"],
    "P022": ["简化嵌套条件逻辑", "使用决策树替代多层if-else", "拆分为多个独立Prompt"],
    "P023": ["添加错误处理指令", "定义异常情况的回退策略", "添加'如果出错请...'指令"],
    "P024": ["添加'请使用UTF-8编码'指令", "避免特殊字符导致解析错误", "使用标准Unicode字符"],
    "P027": ["将长Prompt拆分为多段", "添加段落标记(##)", "使用编号分隔不同部分"],
    "P028": ["检查所有占位符是否有对应值", "为占位符提供默认值", "使用必需/可选标记"],
    "P030": ["添加输入验证指令", "指定输入格式和范围", "添加'如果输入无效请...'处理"],
}


@dataclass
class FixSuggestion:
    finding: Finding
    score_impact: float
    priority_rank: int
    auto_fixable: bool
    fix_action: FixAction | None = None
    manual_steps: list[str] = field(default_factory=list)
    preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.finding.rule_id,
            "severity": self.finding.severity.value,
            "description": self.finding.description,
            "score_impact": round(self.score_impact, 2),
            "priority_rank": self.priority_rank,
            "auto_fixable": self.auto_fixable,
            "fix_preview": self.preview,
            "manual_steps": self.manual_steps,
        }


def compute_score_impact(finding: Finding, total_rules: int = 40) -> float:
    sev_weight = _SEVERITY_IMPACT.get(finding.severity, 1.0)
    cat_weight = 2.0
    for cat, w in _CATEGORY_IMPACT.items():
        if cat in finding.description.lower() or cat in finding.rule_id.lower():
            cat_weight = w
            break
    base_impact = 100.0 / max(total_rules, 1)
    return base_impact * sev_weight * cat_weight / 5.0


def get_fix_suggestions(
    findings: list[Finding],
    text: str,
    linter: PromptLinter | None = None,
) -> list[FixSuggestion]:
    if linter is None:
        linter = PromptLinter()

    suggestions: list[FixSuggestion] = []
    for finding in findings:
        impact = compute_score_impact(finding)
        fix_action = linter._get_fix_action(finding, text)
        auto_fixable = fix_action is not None

        manual_steps = _MANUAL_FIX_STEPS.get(finding.rule_id, [
            f"参考规则{finding.rule_id}的修复建议",
            finding.remediation if finding.remediation else "手动调整Prompt内容",
        ])

        preview = ""
        if fix_action:
            preview = f"'{fix_action.original[:40]}' → '{fix_action.replacement[:40]}'"
            if len(fix_action.original) > 40 or len(fix_action.replacement) > 40:
                preview += "..."

        suggestions.append(FixSuggestion(
            finding=finding,
            score_impact=impact,
            priority_rank=0,
            auto_fixable=auto_fixable,
            fix_action=fix_action,
            manual_steps=manual_steps,
            preview=preview,
        ))

    suggestions.sort(key=lambda s: s.score_impact, reverse=True)
    for i, s in enumerate(suggestions, 1):
        s.priority_rank = i

    return suggestions


def format_suggestions(suggestions: list[FixSuggestion], *, verbose: bool = False) -> str:
    if not suggestions:
        return "没有需要修复的问题！你的Prompt质量很棒！"

    lines = [f"修复建议(按影响评分排序，共{len(suggestions)}项):\n"]

    for s in suggestions:
        marker = "AUTO" if s.auto_fixable else "MANUAL"
        lines.append(f"  {s.priority_rank}. [{marker}] {s.finding.rule_id} (影响: {s.score_impact:.1f}分)")
        lines.append(f"     {s.finding.description}")

        if s.auto_fixable and s.fix_action:
            lines.append(f"     一键修复: {s.preview}")
        else:
            for step in s.manual_steps[:3]:
                lines.append(f"     - {step}")

        if verbose:
            lines.append("")

    total_impact = sum(s.score_impact for s in suggestions)
    auto_count = sum(1 for s in suggestions if s.auto_fixable)
    lines.append(f"\n总影响: {total_impact:.1f}分 | 可自动修复: {auto_count}/{len(suggestions)}")

    return "\n".join(lines)
