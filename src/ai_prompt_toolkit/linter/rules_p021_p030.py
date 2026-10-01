"""Lint 规则集扩展——P021-P030 Prompt 质量检查规则 (R15新增)。"""

from __future__ import annotations

import re
from collections.abc import Callable

from ai_prompt_toolkit.types import Finding, Severity

_P021_PATTERNS = [
    # R180: 长串须含数字(真编码串数字频率高; 驼峰方法名列表无数字误报)
    re.compile(r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]{40,}={0,2}"),
    re.compile(r"\\u[0-9a-fA-F]{4}"),
    re.compile(r"\\x[0-9a-fA-F]{2}"),
    # R180: API名精确大小写(atob/fromCharCode), 排除大写开头的普通英文词"Decode"
    re.compile(r"(?:atob|fromCharCode|unhex)|\bdecode\b", re.IGNORECASE),
]

_P022_PATTERNS = [
    re.compile(r"\{\{[^#/}].*?\}\}"),
    re.compile(r"\$\{[^}]+\}"),
    re.compile(r"<%.*?%>"),
    re.compile(r"\{%.*?%\}"),
    re.compile(r"(?:import|include|require)\s+\{", re.IGNORECASE),
]

_P023_POSITIVE = re.compile(
    r"(?<!不)(?:要|必须|需要|请|should|must|need\s+to|please)\s*?(.{3,40}?)(?=[。.!！\n]|$)",
    re.IGNORECASE,
)
_P023_NEGATIVE = re.compile(
    r"(?:不要|不可|禁止|不能|must\s+not|do\s+not|never|avoid)\s*?(.{3,40}?)(?=[。.!！\n]|$)",
    re.IGNORECASE,
)

# R207校准: P025长文生成上下文门 — 仅报告/白皮书/说明书/文章类任务需要长度约束
_P025_LONGFORM_CTX = re.compile(
    r"(?:报告|白皮书|说明书|方案书|写[一做].{0,8}(?:文章|报告|文案|周报)"
    r"|draft|whitepaper|write\s+(?:an?\s+)?(?:article|essay|blog|report))",
    re.IGNORECASE,
)

_P025_LENGTH_PATTERNS = [
    re.compile(
        r"(?:字数|字符|[Tt]oken|段落|篇幅|长度|words?|characters?|tokens?|paragraphs?|length).*?(?:\d+|限制|范围|以内|不超过|至少)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:不超过|最多|至少|最少|min\s+\d+|max\s+\d+|no\s+more\s+than\s+\d+|at\s+least\s+\d+).*(?:字|词|[Tt]oken|段落|word|token|paragraph|character)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\d+)\s*(?:字|词|words?|characters?|tokens?|paragraphs?)",
        re.IGNORECASE,
    ),
]

_P026_FALLBACK_PATTERNS = [
    re.compile(
        r"如果.*(?:失败|出错|错误|异常|无法|不确定|不清楚)|if.*(?:fail|error|exception|unable|uncertain)", re.IGNORECASE
    ),
    re.compile(r"(?:回退|fallback|否则|otherwise|备选|替代|降级)", re.IGNORECASE),
    # R207: RAG/检索类回退表达 — "上下文未覆盖时明确说资料中没有相关信息"
    # 属于标准回退行为声明, 原pattern仅覆盖"如果失败/否则"式, 漏检此类
    re.compile(
        r"(?:未|没有|无法).{0,10}(?:覆盖|找到|提及|检索到|相关信息|匹配).{0,15}(?:说明|表示|说|回复|回答|声明)",
        re.IGNORECASE,
    ),
]

_P027_SENSITIVE_CULTURAL = [
    re.compile(r"(?:种族|民族|肤色|religion|宗教信仰|性别歧视|sexist|racist|歧视)", re.IGNORECASE),
    re.compile(r"(?:黑人|白人|黄种人|Negro|Oriental)", re.IGNORECASE),
]

_P028_MULTI_STEP = re.compile(
    r"(?:首先|然后|接着|最后|第一步|第二步|step\s+1|step\s+2|首先.*然后|first.*then)",
    re.IGNORECASE,
)
_P028_TASK_COMPLEXITY = re.compile(
    r"(?:分析|推理|比较|评估|判断|规划|设计|analyze|reason|compare|evaluate|judge|plan|design)",
    re.IGNORECASE,
)

_P029_USER_INPUT = [
    re.compile(r"\{\{.*?user.*?\}\}", re.IGNORECASE),
    re.compile(r"\{user_input\}", re.IGNORECASE),
    re.compile(r"\$\{.*?input.*?\}", re.IGNORECASE),
]
_P029_ESCAPE_PATTERNS = re.compile(
    r"(?:转义|escape|sanitize|校验|验证|validate|过滤|filter|清洗|clean)",
    re.IGNORECASE,
)

_P030_MODEL_DEPENDENCY = re.compile(
    r"(?:GPT-4|Claude|文心|通义|Gemini|PaLM|only\s+works?\s+with|requires?\s+(?:GPT|Claude))",
    re.IGNORECASE,
)
_P030_COMPATIBILITY = re.compile(
    r"(?:兼容|compatible|适配|fallback|备选模型|alternative\s+model)",
    re.IGNORECASE,
)


def check_p021(text: str) -> Finding | None:
    matches = []
    for pattern in _P021_PATTERNS:
        for m in pattern.finditer(text):
            matches.append(m.group(0)[:60])
    if not matches:
        return None
    return Finding(
        rule_id="P021",
        severity=Severity.HIGH,
        description=f"Prompt 中存在编码混淆内容 (发现 {len(matches)} 处)",
        remediation="移除或解码混淆内容，使用明文表达意图",
        details={"matches": matches[:5]},
    )


def check_p022(text: str) -> Finding | None:
    # R179: 剥离markdown代码块 — 教学代码示例(import {...}等)不是prompt注入标记
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    matches = []
    for pattern in _P022_PATTERNS:
        for m in pattern.finditer(text):
            matches.append(m.group(0)[:60])
    if not matches:
        return None
    return Finding(
        rule_id="P022",
        severity=Severity.CRITICAL,
        description=f"Prompt 中存在模板注入标记 (发现 {len(matches)} 处)",
        remediation="对模板变量进行校验和转义，避免注入攻击",
        details={"matches": matches[:5]},
    )


def check_p023(text: str) -> Finding | None:
    positives = _P023_POSITIVE.findall(text)
    negatives = _P023_NEGATIVE.findall(text)
    if not positives or not negatives:
        return None
    conflicts = []
    _NEG_WORDS = re.compile(r"(?:不得|不要|禁止|不能|避免|切勿|no|not|never)", re.IGNORECASE)
    for p in positives:
        # R180: positive短语本身含否定词(如"必须基于事实…不得编造")是防御声明, 非冲突
        if _NEG_WORDS.search(p):
            continue
        p_norm = re.sub(r"\s+", " ", p.lower().strip())
        for n in negatives:
            n_norm = re.sub(r"\s+", " ", n.lower().strip())
            if p_norm == n_norm or p_norm in n_norm or n_norm in p_norm:
                conflicts.append({"positive": p.strip(), "negative": n.strip()})
    if not conflicts:
        return None
    return Finding(
        rule_id="P023",
        severity=Severity.HIGH,
        description=f"Prompt 中存在指令冲突 (发现 {len(conflicts)} 处)",
        remediation="审查并统一矛盾的指令，确保逻辑一致",
        details={"conflicts": conflicts[:3]},
    )


def _extract_ngrams(text: str, n: int = 2) -> set[str]:
    cleaned = re.sub(r"[^\u4e00-\u9fffa-zA-Z0-9]", "", text)
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


def check_p024(text: str) -> Finding | None:
    example_blocks = re.findall(
        r"(?:示例|例子|example|e\.g\.)[:：\s]*(.*?)(?=\n\n|\n[^#\s]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not example_blocks:
        return None
    negative_actions = re.findall(
        r"(?:不要|不可|禁止|不能|must\s+not|do\s+not|never|avoid)\s*?(.{3,40}?)(?=[。.!！\n]|$)",
        text,
        re.IGNORECASE,
    )
    if not negative_actions:
        return None
    for block in example_blocks:
        positive_actions = re.findall(
            r"(?:可以|能|may|can|allowed)\s*?(.{3,40}?)(?=[。.!！\n]|$)",
            block,
            re.IGNORECASE,
        )
        for pos in positive_actions:
            for neg in negative_actions:
                pos_norm = re.sub(r"\s+", " ", pos.lower().strip())
                neg_norm = re.sub(r"\s+", " ", neg.lower().strip())
                if pos_norm == neg_norm or pos_norm in neg_norm or neg_norm in pos_norm:
                    return Finding(
                        rule_id="P024",
                        severity=Severity.MEDIUM,
                        description="Prompt 示例行为与指令约束可能不一致",
                        remediation="确保Few-shot示例与文本指令的约束条件一致",
                        details={
                            "example_count": len(example_blocks),
                            "conflict": {"positive": pos.strip(), "negative": neg.strip()},
                        },
                    )
                pos_ngrams = _extract_ngrams(pos_norm)
                neg_ngrams = _extract_ngrams(neg_norm)
                overlap = pos_ngrams & neg_ngrams
                if len(overlap) >= 2 and len(overlap) / max(len(pos_ngrams), len(neg_ngrams), 1) >= 0.4:
                    return Finding(
                        rule_id="P024",
                        severity=Severity.MEDIUM,
                        description="Prompt 示例行为与指令约束可能不一致",
                        remediation="确保Few-shot示例与文本指令的约束条件一致",
                        details={
                            "example_count": len(example_blocks),
                            "conflict": {"positive": pos.strip(), "negative": neg.strip()},
                        },
                    )
    return None


def check_p025(text: str) -> Finding | None:
    # R207校准: 输出长度约束仅对长文生成类任务有意义(报告/白皮书/说明书/文章),
    # 短指令型prompt(翻译/压缩/查询)的长度约束需求极低(R206前94%误报)。
    if not _P025_LONGFORM_CTX.search(text):
        return None
    for pattern in _P025_LENGTH_PATTERNS:
        if pattern.search(text):
            return None
    return Finding(
        rule_id="P025",
        severity=Severity.LOW,
        description="Prompt 未指定输出长度范围",
        remediation="添加输出长度约束，如'控制在500字以内'或'至少3个段落'",
    )


# R207校准: P026回退行为仅对问答/客服场景有意义 — 一次性任务prompt无需
# 声明"不确定时"行为(R206前97%误报, 与P010回退策略语义不同: P010查外部依赖失败)。
_P026_QA_CTX = re.compile(r"(?:问答|客服|咨询|答疑|FAQ|Q&A|回答.{0,6}(?:用户|客户|问题)|解答)", re.IGNORECASE)


def check_p026(text: str) -> Finding | None:
    if not _P026_QA_CTX.search(text):
        return None
    for pattern in _P026_FALLBACK_PATTERNS:
        if pattern.search(text):
            return None
    return Finding(
        rule_id="P026",
        severity=Severity.MEDIUM,
        description="Prompt 缺少错误恢复指引",
        remediation="添加不确定时的回退行为，如'如果无法确定，请回复信息不足而不编造'",
    )


def check_p027(text: str) -> Finding | None:
    matches = []
    for pattern in _P027_SENSITIVE_CULTURAL:
        for m in pattern.finditer(text):
            matches.append(m.group(0))
    if not matches:
        return None
    return Finding(
        rule_id="P027",
        severity=Severity.LOW,
        description=f"Prompt 中可能包含文化敏感内容 (发现 {len(matches)} 处)",
        remediation="审查并替换可能冒犯特定文化的表述，使用中立语言",
        details={"matches": matches[:5]},
    )


def check_p028(text: str) -> Finding | None:
    complexity_count = len(_P028_TASK_COMPLEXITY.findall(text))
    has_multi_step = bool(_P028_MULTI_STEP.search(text))
    if complexity_count >= 2 and not has_multi_step:
        return Finding(
            rule_id="P028",
            severity=Severity.MEDIUM,
            description=f"多步骤推理任务缺少链式指令 (复杂度指标: {complexity_count})",
            remediation="添加分步引导，如'首先...然后...最后...'或'step-by-step'",
            details={"complexity_indicators": complexity_count},
        )
    return None


def check_p029(text: str) -> Finding | None:
    has_user_input = False
    for pattern in _P029_USER_INPUT:
        if pattern.search(text):
            has_user_input = True
            break
    if not has_user_input:
        return None
    has_escape = bool(_P029_ESCAPE_PATTERNS.search(text))
    if has_escape:
        return None
    return Finding(
        rule_id="P029",
        severity=Severity.MEDIUM,
        description="Prompt 中用户输入变量未进行转义/校验",
        remediation="对用户输入变量添加转义或校验声明",
    )


def check_p030(text: str) -> Finding | None:
    dep_match = _P030_MODEL_DEPENDENCY.search(text)
    if not dep_match:
        return None
    has_compat = bool(_P030_COMPATIBILITY.search(text))
    if has_compat:
        return None
    return Finding(
        rule_id="P030",
        severity=Severity.LOW,
        description=f"Prompt 过度依赖特定模型 '{dep_match.group(0)}'",
        remediation="声明兼容性或备选模型，如'兼容GPT-4和Claude'",
        details={"dependency": dep_match.group(0)},
    )


_CheckerFn = Callable[[str], Finding | None]

_CHECKERS_P021_P030: list[_CheckerFn] = [
    check_p021,
    check_p022,
    check_p023,
    check_p024,
    check_p025,
    check_p026,
    check_p027,
    check_p028,
    check_p029,
    check_p030,
]


def run_checks_p021_p030(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for checker in _CHECKERS_P021_P030:
        result = checker(text)
        if result is not None:
            findings.append(result)
    return findings
