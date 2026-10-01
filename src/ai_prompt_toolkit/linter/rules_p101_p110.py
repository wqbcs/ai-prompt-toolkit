"""Lint规则集扩展——P101-P110 高级语义与逻辑规则

R53新增:
- P101: 语义冗余检测 — 检测Prompt中的重复/冗余表述
- P102: 逻辑矛盾检测 — 检测Prompt中的自相矛盾指令
- P103: 指令冲突检测 — 检测相互矛盾的指令对
- P104: 角色一致性 — 检测角色定义与行为指令的不一致
- P105: 输出格式约束完整性 — 检测输出格式声明是否包含完整规范
- P106: 负面示例缺失 — 检测缺少反例/负面示例的情况
- P107: 条件分支覆盖 — 检测缺失的条件分支处理
- P108: 多语言一致性 — 检测中英混排时的一致性问题
- P109: RAG检索增强规范 — 检测RAG场景下的检索增强声明缺失
- P110: 工具调用Chain规范 — 检测多步骤工具调用链规范
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P101_P110: list[LintRule] = [
    LintRule(
        "P101",
        "语义冗余检测",
        "quality",
        Severity.MEDIUM,
        "Prompt中存在重复或冗余的表述，可能降低模型注意力效率",
        "合并重复表述，使用简洁精炼的指令替代",
        description_en="Redundant expressions detected in Prompt, may reduce model attention efficiency",
        remediation_en="Merge redundant expressions, use concise instructions instead",
        family="semantic_redundancy",
    ),
    LintRule(
        "P102",
        "逻辑矛盾检测",
        "quality",
        # R180: 伪语义检测(正则词对)精度天花板低, 与P016/P023同属MEDIUM advisory
        Severity.MEDIUM,
        "Prompt中存在自相矛盾的指令，可能导致模型行为混乱",
        "统一矛盾指令，确保所有要求方向一致",
        description_en="Contradictory instructions detected in Prompt, may confuse model behavior",
        remediation_en="Unify contradictory instructions, ensure all requirements are consistent",
        family="logical_consistency",
    ),
    LintRule(
        "P103",
        "指令冲突检测",
        "quality",
        Severity.HIGH,
        "Prompt中存在相互冲突的约束条件",
        "解决约束冲突，明确优先级或区分适用场景",
        description_en="Conflicting constraints detected in Prompt",
        remediation_en="Resolve constraint conflicts, clarify priorities or distinguish applicable scenarios",
        family="instruction_conflict",
    ),
    LintRule(
        "P104",
        "角色一致性问题",
        "quality",
        Severity.MEDIUM,
        "Prompt中的角色定义与行为指令不一致",
        "确保角色定义与后续指令在定位和能力上保持一致",
        description_en="Role definition inconsistent with behavioral instructions in Prompt",
        remediation_en="Ensure role definition aligns with subsequent instructions in positioning and capabilities",
        family="role_consistency",
    ),
    LintRule(
        "P105",
        "输出格式约束不完整",
        "structure",
        Severity.MEDIUM,
        "输出格式声明缺少完整规范(如缺少字段说明/示例/边界值)",
        "补充输出格式的完整规范: 字段定义、示例、边界值、默认值",
        description_en="Output format declaration lacks complete specification (e.g., missing field descriptions/examples/boundary values)",
        remediation_en="Add complete output format specification: field definitions, examples, boundary values, defaults",
        family="output_format_completeness",
    ),
    LintRule(
        "P106",
        "负面示例缺失",
        "quality",
        Severity.LOW,
        "Prompt仅提供正面示例而缺少反例/负面示例，模型可能无法识别错误模式",
        "添加1-2个反例展示不期望的输出格式或内容",
        description_en="Prompt only provides positive examples without negative examples, model may not recognize error patterns",
        remediation_en="Add 1-2 counter-examples showing undesired output format or content",
        family="negative_example",
    ),
    LintRule(
        "P107",
        "条件分支覆盖不足",
        "structure",
        Severity.MEDIUM,
        "Prompt缺少对边界条件/异常情况的分支处理",
        "添加if-else条件分支: 正常情况/边界情况/异常情况的处理逻辑",
        description_en="Prompt lacks branch handling for boundary conditions/edge cases",
        remediation_en="Add if-else conditional branches: handling for normal/boundary/exception cases",
        family="branch_coverage",
    ),
    LintRule(
        "P108",
        "多语言一致性问题",
        "quality",
        Severity.LOW,
        "Prompt中中英混排时存在术语不一致或表达风格切换问题",
        "统一术语翻译，保持表达风格一致，或使用i18n模板分离",
        description_en="Inconsistent terminology or style switching in bilingual Prompt",
        remediation_en="Unify terminology translation, maintain consistent style, or use i18n template separation",
        family="multilingual_consistency",
    ),
    LintRule(
        "P109",
        "RAG检索增强规范缺失",
        "quality",
        Severity.MEDIUM,
        "RAG场景Prompt缺少检索增强声明(上下文引用/置信度/来源标注)",
        "添加RAG规范: '基于提供的上下文回答, 如上下文不足请声明信息不足, 标注信息来源'",
        description_en="RAG Prompt missing retrieval-augmented declarations (context citation/confidence/source annotation)",
        remediation_en="Add RAG specification: 'Answer based on provided context, declare insufficient information when needed, annotate sources'",
        family="rag_specification",
    ),
    LintRule(
        "P110",
        "工具调用链规范缺失",
        "structure",
        Severity.MEDIUM,
        "多步骤工具调用场景缺少调用链声明(顺序/依赖/超时/错误恢复)",
        "声明工具调用链: 调用顺序、依赖关系、超时处理、错误恢复策略",
        description_en="Multi-step tool calling scenario missing chain declaration (sequence/dependency/timeout/error recovery)",
        remediation_en="Declare tool call chain: call sequence, dependencies, timeout handling, error recovery strategy",
        family="tool_chain",
    ),
]

for r in _RULES_P101_P110:
    _RULE_MAP[r.rule_id] = r


# R210: 阈值保持0.5(分词级下0.5已能区分"真近重复"与"同主题不同句") —
# 日志行/代码片段等高相似数据由下方代码围栏剥离解决, 不再靠抬阈值
_SIMILAR_SENTENCE_THRESHOLD = 0.5
_MAX_REDUNDANT_PAIRS = 50  # R175: 报告上限(超过后早退, description显示'N+')


def _extract_sentences(text: str) -> list[str]:
    # R210: 增加英文句号切分(". "后跟空白), 否则英文prompt整段为一句无法对比
    parts = re.split(r"[。！？\n]+|\.(?=\s)", text)
    out = []
    for s in parts:
        s = s.strip()
        if len(s) <= 5:
            continue
        # R210: 实义token(汉字+英文词)数 <3 的片段不构成可比句子
        # (代码标签如"</div>"、短标记等), 避免碎片互比误报
        cjk = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
        latin = len(re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", s))
        if cjk + latin < 3:
            continue
        out.append(s)
    return out


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def check_p101(text: str) -> Finding | None:
    rule = _RULE_MAP["P101"]
    # R210: 代码围栏(日志/代码)是数据非指令文本 — 日志行共享svc=order等字段
    # Jaccard达0.67, 代码片段(如"</div>")互比, 都是误报(R210 clean52/55暴露)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    sentences = _extract_sentences(text)
    if len(sentences) < 3:
        return None
    # R210: 字符级Jaccard对英文失真 — 英文短句字符集天然高度重叠
    # (字母表仅26, 任何两句英文Jaccard都>0.5, 新英文样本暴露14/56误报)。
    # 改为分词级: CJK按单字(与字符级等价), Latin按空格分词(语义单元)。
    def _tokens(s: str) -> frozenset[str]:
        cjk = {c for c in s if "\u4e00" <= c <= "\u9fff"}
        latin = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", s)}
        return frozenset(cjk | latin)

    token_sets = [_tokens(s) for s in sentences]
    sizes = [len(ts) for ts in token_sets]
    threshold = _SIMILAR_SENTENCE_THRESHOLD
    redundant_pairs: list[tuple[int, int]] = []
    truncated = False
    n = len(sentences)
    for i in range(n):
        sa = token_sets[i]
        if not sa:
            continue
        for j in range(i + 1, n):
            sb = token_sets[j]
            if not sb:
                continue
            # R175性能: 数学等价剪枝 — Jaccard <= min/max, min/max <= t时不可能超阈值
            hi, lo = (sizes[i], sizes[j]) if sizes[i] >= sizes[j] else (sizes[j], sizes[i])
            if lo / hi <= threshold:
                continue
            inter = len(sa & sb)
            union = sizes[i] + sizes[j] - inter
            if union and inter / union > threshold:
                redundant_pairs.append((i + 1, j + 1))
                if len(redundant_pairs) >= _MAX_REDUNDANT_PAIRS:
                    truncated = True
                    break
        if truncated:
            break
    if not redundant_pairs:
        return None
    count_text = f"{len(redundant_pairs)}+" if truncated else f"{len(redundant_pairs)}"
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=f"{rule.description} (检测到{count_text}组相似表述)",
        remediation=rule.remediation,
        details={"redundant_pairs": redundant_pairs[:5]},
    )


_CONTRADICTION_PATTERNS = [
    (re.compile(r"必须.*?禁止|禁止.*?必须", re.IGNORECASE), "必须/禁止矛盾"),
    # R180: 移除"请/不要矛盾" — "请做X, 不要Y"是正常指令形态, 此pattern大量误报
    (re.compile(r"always.*?never|never.*?always", re.IGNORECASE), "always/never矛盾"),
    (re.compile(r"必须.{0,20}(?:不要|禁止|不能)|不要.{0,20}必须", re.IGNORECASE), "必须/不要矛盾"),
]


def check_p102(text: str) -> Finding | None:
    rule = _RULE_MAP["P102"]
    for pattern, label in _CONTRADICTION_PATTERNS:
        if pattern.search(text):
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=f"{rule.description} ({label})",
                remediation=rule.remediation,
                details={"contradiction_type": label},
            )
    return None


_CONFLICT_PATTERNS = [
    (re.compile(r"简短.*?详细|详细.*?简短", re.IGNORECASE), "简短/详细冲突"),
    (re.compile(r"简洁.*?全面|全面.*?简洁", re.IGNORECASE), "简洁/全面冲突"),
    (re.compile(r"简短.*?完整|完整.*?简短", re.IGNORECASE), "简短/完整冲突"),
    (re.compile(r"严格.*?灵活|灵活.*?严格", re.IGNORECASE), "严格/灵活冲突"),
    (
        re.compile(
            r"(?:concise|brief).*?(?:detailed|comprehensive)|(?:detailed|comprehensive).*?(?:concise|brief)",
            re.IGNORECASE,
        ),
        "concise/detailed conflict",
    ),
]


def check_p103(text: str) -> Finding | None:
    rule = _RULE_MAP["P103"]
    for pattern, label in _CONFLICT_PATTERNS:
        if pattern.search(text):
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=f"{rule.description} ({label})",
                remediation=rule.remediation,
                details={"conflict_type": label},
            )
    return None


_ROLE_PATTERN = re.compile(r"你(?:是|作为|扮演|充当).{2,20}?[\。，,]", re.IGNORECASE)
_TECHNICAL_ACTION = re.compile(r"(?:编写|开发|实现|设计|构建|部署|调试|优化|分析|审查)", re.IGNORECASE)
_CREATIVE_ACTION = re.compile(r"(?:创作|写作|撰写|构思|想象|设计.*风格|创意)", re.IGNORECASE)


def check_p104(text: str) -> Finding | None:
    rule = _RULE_MAP["P104"]
    role_match = _ROLE_PATTERN.search(text)
    if not role_match:
        return None
    role_text = role_match.group()
    has_tech = _TECHNICAL_ACTION.search(role_text)
    has_creative = _CREATIVE_ACTION.search(role_text)
    body_has_tech = _TECHNICAL_ACTION.search(text[role_match.end() :])
    body_has_creative = _CREATIVE_ACTION.search(text[role_match.end() :])
    if has_tech and body_has_creative and not has_creative:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=f"{rule.description} (角色定义偏技术但指令偏创作)",
            remediation=rule.remediation,
        )
    if has_creative and body_has_tech and not has_tech:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=f"{rule.description} (角色定义偏创作但指令偏技术)",
            remediation=rule.remediation,
        )
    return None


_FORMAT_PATTERN = re.compile(r"(?:输出格式|输出为|返回格式|格式要求|output.*format|format.*output)", re.IGNORECASE)
# R210: 加"带引号的JSON键"(如 {"category": ...}) — 内联JSON示例本身即字段说明,
# 无需额外字段/边界值声明(R210 clean46暴露)
_FORMAT_COMPLETE = re.compile(
    r"(?:字段|示例|边界|默认值|field|example|boundary|default|\"[A-Za-z_]+\")", re.IGNORECASE
)
# R207校准: 格式规范完整度仅对结构化输出(JSON/YAML/CSV/表格/schema)有意义 —
# 普通自然语言输出无需字段/边界值说明(R206前81%误报)。
# R207二次收窄: 独立"schema"词误匹配数据库schema语境(迁移/变更类prompt),
# 仅保留输出格式显式声明式匹配。
_FORMAT_STRUCTURED_CTX = re.compile(
    r"(?:输出.{0,6}(?:JSON|YAML|CSV|XML|表格|schema)|JSON格式|YAML格式|CSV格式"
    r"|返回.{0,4}(?:JSON|YAML|CSV)|fields?\s*[:：]|结构化输出)",
    re.IGNORECASE,
)


def check_p105(text: str) -> Finding | None:
    rule = _RULE_MAP["P105"]
    if not _FORMAT_PATTERN.search(text):
        return None
    if not _FORMAT_STRUCTURED_CTX.search(text):
        return None
    if _FORMAT_COMPLETE.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_EXAMPLE_POSITIVE = re.compile(r"(?:示例|例子|例如|example|for instance|如:)", re.IGNORECASE)
_EXAMPLE_NEGATIVE = re.compile(
    r"(?:不要|避免|反面|错误示例|反例|不要这样|do not|avoid|bad example|wrong example|incorrect)", re.IGNORECASE
)


def check_p106(text: str) -> Finding | None:
    rule = _RULE_MAP["P106"]
    if not _EXAMPLE_POSITIVE.search(text):
        return None
    if _EXAMPLE_NEGATIVE.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


# R212-6: 条件触发收窄 — 原pattern含裸"当/条件/when/if"无词边界:
# "when multiple options exist"(SQL)/"diff"/"identify"子串误触发,
# "条件"是SQL领域词(触发条件/条件句式)。真条件分支=如果/假如/假设(非否定)/
# if|else|otherwise(独立词)。"假设"前4字含否定词(不/别/勿假设)是约束声明非分支。
_CONDITION_PATTERN = re.compile(
    r"(?:如果|假如|若|\bif\b|\belif\b|否则|\belse\b|\botherwise\b|(?<![不别勿])假设)", re.IGNORECASE
)
# R212-6: 异常处理声明扩面 — 真异常分支不只"失败/错误":
# "如果不确定→引导联系人工"(客服)/"if not contain→I don't know"(RAG)/
# "不假设未给出的表结构"(SQL保守声明) 都是边界处理逻辑。
_EXCEPTION_PATTERN = re.compile(
    r"(?:异常|错误|失败|超时|exception|error|fail|timeout|fallback|回退|兜底"
    r"|不确定|无法|未包含|不包含|未找到|不假设|不要假设"
    r"|联系|人工|not\s+cover|no\s+information|don'?t\s+know|I\s+don'?t\s+know|cannot)",
    re.IGNORECASE,
)


def check_p107(text: str) -> Finding | None:
    rule = _RULE_MAP["P107"]
    if not _CONDITION_PATTERN.search(text):
        return None
    if _EXCEPTION_PATTERN.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


_ZH_EN_MIX = re.compile(r"[\u4e00-\u9fff].*[a-zA-Z]|[a-zA-Z].*[\u4e00-\u9fff]")
_ZH_TERM = re.compile(r"([\u4e00-\u9fff]{2,8})\s*\(([a-zA-Z]{2,20})\)")
_EN_TERM = re.compile(r"([a-zA-Z]{2,20})\s*[\(（]([\u4e00-\u9fff]{2,8})[\)）]")


def check_p108(text: str) -> Finding | None:
    rule = _RULE_MAP["P108"]
    if not _ZH_EN_MIX.search(text):
        return None
    zh_terms = _ZH_TERM.findall(text)
    en_terms = _EN_TERM.findall(text)
    if not zh_terms and not en_terms:
        return None
    term_map: dict[str, str] = {}
    inconsistencies = []
    for zh, en in zh_terms:
        key = en.lower()
        if key in term_map and term_map[key] != zh:
            inconsistencies.append(f"{en}: {term_map[key]} vs {zh}")
        term_map[key] = zh
    for en, zh in en_terms:
        key = en.lower()
        if key in term_map and term_map[key] != zh:
            inconsistencies.append(f"{en}: {term_map[key]} vs {zh}")
        term_map[key] = zh
    if not inconsistencies:
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=f"{rule.description} (不一致术语: {', '.join(inconsistencies[:3])})",
        remediation=rule.remediation,
        details={"inconsistencies": inconsistencies[:5]},
    )


# R212-6: 移除裸"文档" — 技术文档/PRD/白皮书/翻译类prompt的"文档"即误触发
# (5样本)。真实RAG面=检索/上下文/知识库/向量等检索语义词, 与"写文档"无关。
_RAG_PATTERN = re.compile(
    r"(?:上下文|检索|知识库|context|retriev|knowledge.?base|RAG|rag|检索增强|向量|embedding)", re.IGNORECASE
)
_RAG_DECL = re.compile(
    r"(?:信息不足|来源.*标注|置信度|引用|citation|cite\b|confidence|source.*annotat|retriev.*augment)",
    re.IGNORECASE,
)


def check_p109(text: str) -> Finding | None:
    rule = _RULE_MAP["P109"]
    if not _RAG_PATTERN.search(text):
        return None
    if _RAG_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


# R212-6: 链式信号分强弱。强信号=显式步骤编排(首先…然后/依次/pipeline/chain/
# workflow)直指多步工具调用; 弱信号(步骤/流程/step)在数据分析/迁移/日志/
# 写作类prompt中是通用流程词(6样本零工具词误报), 须与工具语境组合才构成
# 工具链缺恢复的面。
_TOOL_CHAIN_STRONG = re.compile(
    r"(?:首先.*然后|依次|pipeline|chain|workflow|多步骤|multi.?step)", re.IGNORECASE
)
_TOOL_CHAIN_WEAK = re.compile(r"(?:步骤|流程|先.*后|step)", re.IGNORECASE)
# 工具语境: 显式工具/函数/API/MCP调用面(区别于通用流程词)
_TOOL_CTX = re.compile(
    r"(?:工具|函数|API|接口|插件|tool|function|plugin|MCP|调用.{0,4}(?:工具|API|函数|接口))", re.IGNORECASE
)
_TOOL_DECL = re.compile(
    r"(?:超时|timeout|错误恢复|error.?recovery|fallback|回退|依赖|dependency|调用顺序|call.?order"
    r"|重试|retry)",
    re.IGNORECASE
)


def check_p110(text: str) -> Finding | None:
    rule = _RULE_MAP["P110"]
    strong = _TOOL_CHAIN_STRONG.search(text)
    weak = _TOOL_CHAIN_WEAK.search(text)
    if not (strong or (weak and _TOOL_CTX.search(text))):
        return None
    if _TOOL_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        remediation=rule.remediation,
    )


def run_checks_p101_p110(text: str) -> list[Finding]:
    results: list[Finding] = []
    for fn in [
        check_p101,
        check_p102,
        check_p103,
        check_p104,
        check_p105,
        check_p106,
        check_p107,
        check_p108,
        check_p109,
        check_p110,
    ]:
        r = fn(text)
        if r is not None:
            results.append(r)
    return results
