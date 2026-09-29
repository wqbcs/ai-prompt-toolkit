"""Lint规则集扩展——P063-P070 Agent安全+Prompt模板版本+链式调用+多轮对话+知识更新+幻觉预防+格式一致+Token阈值

参考: OWASP LLM Top10 2025 + promptfoo + garak + DeepEval
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P063_P070: list[LintRule] = [
    LintRule(
        "P063",
        "Agent系统Prompt泄露风险",
        "security",
        Severity.HIGH,
        "Agent型Prompt中系统指令可能被用户输入覆盖或泄露",
        "添加防泄露指令(禁止重复/忽略上级指令), 使用Canary Token检测",
        description_en="Agent system Prompt instructions may be overridden or leaked by user input",
        remediation_en="Add anti-leakage instructions (prohibit repeating/ignoring prior instructions), use Canary Token detection",
        family="system_prompt_leak",
    ),
    LintRule(
        "P064",
        "Prompt模板版本迁移提示缺失",
        "quality",
        Severity.LOW,
        "模板使用旧版frontmatter格式但未声明兼容迁移信息",
        "在frontmatter中添加version字段, 使用upgrade-fm命令自动升级",
        description_en="Template uses legacy frontmatter format but does not declare compatibility migration info",
        remediation_en="Add version field in frontmatter, use upgrade-fm command for automatic upgrade",
        family="version_migration",
    ),
    LintRule(
        "P065",
        "链式调用缺失错误隔离",
        "quality",
        Severity.HIGH,
        "多步骤链式指令中缺少单步失败时的隔离和恢复机制",
        "每个步骤添加'如果失败则...'的降级或跳过指令",
        description_en="Multi-step chain instructions lack isolation and recovery mechanism for individual step failures",
        remediation_en="Add 'If failed then...' degradation or skip instruction for each step",
        family="chain_error_isolation",
    ),
    LintRule(
        "P066",
        "多轮对话上下文窗口溢出风险",
        "performance",
        Severity.MEDIUM,
        "多轮对话Prompt未设定上下文截断或摘要策略",
        "添加上下文窗口限制(如'仅参考最近N轮对话')或摘要指令",
        description_en="Multi-turn dialog Prompt does not set context truncation or summarization strategy",
        remediation_en="Add context window limit (e.g., 'Only reference the last N turns') or summarization instructions",
        family="context_window",
    ),
    LintRule(
        "P067",
        "知识截止日期缺失",
        "quality",
        Severity.MEDIUM,
        "涉及事实性知识的Prompt未声明知识截止日期",
        "在Prompt中添加'知识截止: YYYY-MM'或'基于截至XX的信息'",
        description_en="Factual knowledge Prompt does not declare knowledge cutoff date",
        remediation_en="Add 'Knowledge cutoff: YYYY-MM' or 'Based on information as of XX' in Prompt",
        family="knowledge_cutoff",
    ),
    LintRule(
        "P068",
        "幻觉预防指令缺失",
        "quality",
        Severity.MEDIUM,
        "事实性Prompt中缺少防止模型编造信息的约束",
        "添加'如果不确定请明确说明, 不要编造信息'约束",
        description_en="Factual Prompt lacks constraints preventing model from fabricating information",
        remediation_en="Add constraint 'If uncertain, please state explicitly, do not fabricate information'",
        family="hallucination_prevention",
    ),
    LintRule(
        "P069",
        "输出格式与示例不一致",
        "quality",
        Severity.MEDIUM,
        "Prompt中声明的输出格式与Few-shot示例的实际格式不匹配",
        "确保输出格式描述与示例格式一致, 修正冲突",
        description_en="Prompt declared output format does not match Few-shot example actual format",
        remediation_en="Ensure output format description matches example format, fix conflicts",
        family="format_example_mismatch",
    ),
    LintRule(
        "P070",
        "Token预算超限风险",
        "performance",
        Severity.MEDIUM,
        "Prompt文本过长可能导致Token预算超限(>4000 tokens)",
        "精简Prompt或分段处理, 使用token命令检查Token消耗",
        description_en="Prompt text too long may cause token budget overrun (>4000 tokens)",
        remediation_en="Simplify Prompt or process in segments, use token command to check token consumption",
        family="token_budget",
    ),
]

for r in _RULES_P063_P070:
    _RULE_MAP[r.rule_id] = r


_AGENT_PATTERN = re.compile(r"(?:agent|代理|智能体|assistant|助手)", re.IGNORECASE)
_SYSTEM_LEAK_PATTERN = re.compile(
    r"(?:忽略|ignore|forget|disregard|覆盖|override|上面|above|之前的指令|previous instructions)", re.IGNORECASE
)
_ANTI_LEAK_PATTERN = re.compile(r"(?:禁止重复|不得泄露|do not repeat|never reveal|canary|安全检查)", re.IGNORECASE)

_LEGACY_FRONTMATTER = re.compile(r"^---\s*\n(?!.*version)", re.MULTILINE)

_CHAIN_PATTERN = re.compile(r"(?:首先|第一步|step\s*1|然后|接着|第二步|step\s*2|最后|第三步|step\s*3)", re.IGNORECASE)
_CHAIN_ERROR_ISOLATION = re.compile(r"(?:如果.*失败|失败则|出错则|if.*fail|fallback|降级|跳过|skip)", re.IGNORECASE)

_MULTI_TURN_PATTERN = re.compile(
    r"(?:多轮|对话历史|上下文|会话|conversation|multi.?turn|context|session)", re.IGNORECASE
)
_CONTEXT_LIMIT = re.compile(r"(?:最近.*轮|仅参考|截断|摘要|summar|truncat|last\s+\d+\s+turn)", re.IGNORECASE)

# R208校准: 事实性判定收紧 — 原pattern含"数据"泛词, 任何数据处理prompt
# 恒触发(8/32干净样本误报); "fact"子串误配"refactor"(无词边界)。
_FACTUAL_PATTERN = re.compile(
    r"(?:事实|统计|年份|知识|\bfact\w*|\bstatistic\w*)", re.IGNORECASE
)
_CUTOFF_PATTERN = re.compile(
    r"(?:截止|截至|cutoff|knowledge\s+cut|截至.*月|更新至|as\s+of|仅依据|仅基于|only\s+based\s+on)", re.IGNORECASE
)

# R208校准: 防编造约束仅对真实幻觉风险面(引用/来源/事实性)有意义 —
# 原pattern含"数据"泛词恒触发(9/32干净样本误报), "fact"子串误配refactor。
# R210: "引用"须后接来源类词 — "引用测试输出行"是引用行为而非事实性风险面
# (R210 clean42暴露); "data"裸词是角色名/泛指(R210 clean35暴露)
_HALLUCINATION_RISK = re.compile(
    r"(?:事实|来源|\bfact\w*|\bcite\w*|\bsource\b|\breferenc\w*|引用.{0,10}(?:来源|出处|文献|权威|资料))",
    re.IGNORECASE,
)
_ANTI_HALLUCINATION = re.compile(
    r"(?:不确定|不要编造|如实回答|如不确定|do not fabricate|do not make up|不确定.*说明|honest|如实"
    r"|do\s+not\s+invent|don'?t\s+invent|不虚构|不臆造|不杜撰"
    r"|仅依据|仅基于|only\s+based\s+on|不补充.*之外|不得.*超出.*范围)",
    re.IGNORECASE,
)

_OUTPUT_FORMAT = re.compile(
    r"(?:输出(?:格式|为)|格式如下|JSON|Markdown|列表|表格|format|output\s+as|return\s+(?:a|the))", re.IGNORECASE
)
_EXAMPLE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)

_TOKEN_WARN_THRESHOLD = 4000


def check_p063(text: str) -> Finding | None:
    rule = _RULE_MAP["P063"]
    is_agent = bool(_AGENT_PATTERN.search(text))
    if not is_agent:
        return None
    has_leak_risk = bool(_SYSTEM_LEAK_PATTERN.search(text))
    has_anti_leak = bool(_ANTI_LEAK_PATTERN.search(text))
    if has_anti_leak:
        return None
    if not has_leak_risk:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p064(text: str) -> Finding | None:
    rule = _RULE_MAP["P064"]
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    frontmatter = text[3:end]
    if re.search(r"version", frontmatter, re.IGNORECASE):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p065(text: str) -> Finding | None:
    rule = _RULE_MAP["P065"]
    chain_steps = _CHAIN_PATTERN.findall(text)
    if len(chain_steps) < 2:
        return None
    has_isolation = bool(_CHAIN_ERROR_ISOLATION.search(text))
    if has_isolation:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=f"{rule.description} (检测到{len(chain_steps)}个链式步骤但无错误隔离)",
        remediation=rule.remediation,
        details={"chain_steps": len(chain_steps)},
    )


def check_p066(text: str) -> Finding | None:
    rule = _RULE_MAP["P066"]
    is_multi_turn = bool(_MULTI_TURN_PATTERN.search(text))
    if not is_multi_turn:
        return None
    has_limit = bool(_CONTEXT_LIMIT.search(text))
    if has_limit:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p067(text: str) -> Finding | None:
    rule = _RULE_MAP["P067"]
    is_factual = bool(_FACTUAL_PATTERN.search(text))
    if not is_factual:
        return None
    has_cutoff = bool(_CUTOFF_PATTERN.search(text))
    if has_cutoff:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p068(text: str) -> Finding | None:
    rule = _RULE_MAP["P068"]
    is_risk = bool(_HALLUCINATION_RISK.search(text))
    if not is_risk:
        return None
    has_anti = bool(_ANTI_HALLUCINATION.search(text))
    if has_anti:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def check_p069(text: str) -> Finding | None:
    rule = _RULE_MAP["P069"]
    has_format = bool(_OUTPUT_FORMAT.search(text))
    if not has_format:
        return None
    examples = _EXAMPLE_BLOCK.findall(text)
    if not examples:
        return None
    has_json_format = bool(re.search(r"JSON|json", text, re.IGNORECASE))
    has_json_example = any("{" in ex or "[" in ex for ex in examples)
    has_markdown_format = bool(re.search(r"Markdown|表格|列表", text, re.IGNORECASE))
    has_markdown_example = any("|" in ex or "- " in ex or "# " in ex for ex in examples)
    if has_json_format and not has_json_example and not has_markdown_example:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=f"{rule.description} (声明JSON格式但示例非JSON)",
            remediation=rule.remediation,
            details={"format_declared": "JSON", "example_format": "unknown"},
        )
    if has_markdown_format and not has_markdown_example and not has_json_example:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=f"{rule.description} (声明Markdown格式但示例非Markdown)",
            remediation=rule.remediation,
            details={"format_declared": "Markdown", "example_format": "unknown"},
        )
    return None


def check_p070(text: str) -> Finding | None:
    rule = _RULE_MAP["P070"]
    char_count = len(text)
    estimated_tokens = int(char_count * 0.6)
    if estimated_tokens <= _TOKEN_WARN_THRESHOLD:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=f"{rule.description} (估算{estimated_tokens} tokens, 阈值{_TOKEN_WARN_THRESHOLD})",
        remediation=rule.remediation,
        details={"estimated_tokens": estimated_tokens, "char_count": char_count, "threshold": _TOKEN_WARN_THRESHOLD},
    )


def run_checks_p063_p070(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [check_p063, check_p064, check_p065, check_p066, check_p067, check_p068, check_p069, check_p070]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
