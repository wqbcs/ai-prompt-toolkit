"""Lint 规则集——30 条 Prompt 质量检查规则 (P001-P030)。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class LintRule:
    rule_id: str
    name: str
    category: str
    severity: Severity
    description: str
    remediation: str
    description_en: str = ""
    remediation_en: str = ""
    family: str = ""

    def to_dict(self, lang: str = "zh") -> dict[str, Any]:
        desc = self.description if lang == "zh" else (self.description_en or self.description)
        rem = self.remediation if lang == "zh" else (self.remediation_en or self.remediation)
        result = {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category,
            "severity": self.severity.value,
            "description": desc,
            "remediation": rem,
        }
        if self.family:
            result["family"] = self.family
        return result


_ALL_RULES: list[LintRule] = [
    # ── 结构类 P001-P005 ──
    LintRule("P001", "缺失角色定义", "structure", Severity.HIGH,
             "Prompt 未定义角色(Role)，模型可能无法聚焦预期行为",
             "在 Prompt 开头添加明确的角色声明，如 '你是一个专业的...'", family="role_definition"),
    LintRule("P002", "缺失输出格式", "structure", Severity.MEDIUM,
             "Prompt 未指定输出格式要求，模型输出可能不一致",
             "添加输出格式说明，如 JSON/Markdown/列表等结构化要求", family="output_format"),
    LintRule("P003", "缺失约束条件", "structure", Severity.MEDIUM,
             "Prompt 缺少约束/限制条件，模型行为边界不明确",
             "添加明确的约束条件，如字数限制、禁止事项、边界条件", family="constraint"),
    LintRule("P004", "Prompt 过长", "structure", Severity.MEDIUM,
             "Prompt 超过 2000 字符，可能导致模型注意力分散",
             "精简 Prompt 内容，移除冗余描述，拆分为多个子任务", family="length_control"),
    LintRule("P005", "Prompt 过短", "structure", Severity.LOW,
             "Prompt 不足 50 字符，指令可能不够明确",
             "补充足够的上下文、示例和约束条件", family="length_control"),
    # ── 安全类 P006-P010 ──
    LintRule("P006", "敏感信息暴露", "security", Severity.HIGH,
             "Prompt 中可能包含 API Key、密码等敏感信息",
             "移除敏感信息，使用环境变量或占位符替代", family="data_leak"),
    LintRule("P007", "注入风险", "security", Severity.HIGH,
             "Prompt 中存在可被注入的开放输入点",
             "对用户输入进行转义/校验，添加输入边界约束", family="injection"),
    LintRule("P008", "权限过宽", "security", Severity.MEDIUM,
             "Prompt 赋予模型过宽的操作权限",
             "限制模型权限范围，使用最小权限原则", family="permission"),
    LintRule("P009", "无审计日志", "security", Severity.LOW,
             "Prompt 未包含审计/追踪相关指令",
             "添加审计指令，要求模型记录关键决策过程", family="audit"),
    LintRule("P010", "无回退策略", "security", Severity.MEDIUM,
             "Prompt 缺少错误处理和回退策略",
             "添加异常处理指令，明确模型遇到不确定情况时的行为", family="error_handling"),
    # ── 性能类 P011-P015 ──
    LintRule("P011", "Token 浪费", "performance", Severity.LOW,
             "Prompt 中存在大量无意义的填充文本",
             "移除填充文本，保持简洁高效", family="token_efficiency"),
    LintRule("P012", "冗余重复", "performance", Severity.MEDIUM,
             "Prompt 中存在重复的指令或描述",
             "合并重复内容，保持指令唯一性", family="token_efficiency"),
    LintRule("P013", "无效示例", "performance", Severity.MEDIUM,
             "Prompt 中包含无效或低质量示例",
             "提供高质量、有代表性的 Few-shot 示例", family="fewshot_quality"),
    LintRule("P014", "嵌套过深", "performance", Severity.MEDIUM,
             "Prompt 中的条件/逻辑嵌套超过 3 层",
             "简化逻辑结构，扁平化条件判断", family="complexity"),
    LintRule("P015", "约束过多", "performance", Severity.LOW,
             "Prompt 中约束条件超过 10 条，可能导致模型困惑",
             "精简约束条件，保留最关键的限制", family="complexity"),
    # ── 质量类 P016-P020 ──
    LintRule("P016", "歧义表述", "quality", Severity.HIGH,
             "Prompt 中存在模糊、歧义的表述",
             "使用精确、无歧义的语言描述需求", family="clarity"),
    LintRule("P017", "矛盾指令", "quality", Severity.HIGH,
             "Prompt 中存在相互矛盾的指令",
             "审查并统一矛盾的指令，确保逻辑一致", family="consistency"),
    LintRule("P018", "缺失 Few-shot", "quality", Severity.MEDIUM,
             "Prompt 缺少 Few-shot 示例引导",
             "添加 2-3 个高质量的输入输出示例", family="fewshot_quality"),
    LintRule("P019", "CoT 缺失", "quality", Severity.LOW,
             "复杂推理任务缺少 Chain-of-Thought 引导",
             "添加 '让我们一步步思考' 或分步推理引导", family="reasoning"),
    LintRule("P020", "无评估标准", "quality", Severity.MEDIUM,
             "Prompt 缺少输出质量评估标准",
             "添加明确的评估标准和验收条件", family="evaluation"),
    # ── 安全扩展类 P021-P024 ──
    LintRule("P021", "编码混淆", "security", Severity.HIGH,
             "Prompt 中存在 Base64/Unicode/Hex 编码混淆内容",
             "移除或解码混淆内容，使用明文表达意图", family="encoding_attack"),
    LintRule("P022", "模板注入标记", "security", Severity.CRITICAL,
             "Prompt 中存在模板注入标记 {{}}/${}",
             "对模板变量进行校验和转义，避免注入攻击", family="injection"),
    LintRule("P023", "指令冲突", "quality", Severity.HIGH,
             "Prompt 中存在正向与负向指令指向同一动作对象",
             "审查并统一矛盾的指令，确保逻辑一致", family="consistency"),
    LintRule("P024", "示例与指令不一致", "quality", Severity.MEDIUM,
             "Prompt Few-shot 示例行为与文本指令约束不一致",
             "确保 Few-shot 示例与文本指令的约束条件一致", family="fewshot_quality"),
    # ── 结构增强类 P025-P026 ──
    LintRule("P025", "输出长度未指定", "structure", Severity.LOW,
             "Prompt 未指定输出字数/段落/Token 范围",
             "添加输出长度约束，如'控制在500字以内'", family="output_format"),
    LintRule("P026", "缺少错误恢复指引", "structure", Severity.MEDIUM,
             "Prompt 未指定不确定时的回退行为",
             "添加错误恢复指引，如'如果无法确定，请回复信息不足'", family="error_handling"),
    # ── 质量增强类 P027-P030 ──
    LintRule("P027", "文化敏感内容", "quality", Severity.LOW,
             "Prompt 中可能包含冒犯特定文化的表述",
             "审查并替换可能冒犯特定文化的表述，使用中立语言", family="cultural"),
    LintRule("P028", "链式指令缺失", "quality", Severity.MEDIUM,
             "多步骤推理任务缺少 step-by-step 引导",
             "添加分步引导，如'首先...然后...最后...'", family="reasoning"),
    LintRule("P029", "变量未转义", "security", Severity.MEDIUM,
             "Prompt 中用户输入变量未进行转义/校验",
             "对用户输入变量添加转义或校验声明", family="injection"),
    LintRule("P030", "过度依赖", "quality", Severity.LOW,
             "Prompt 过度依赖特定模型/平台未声明兼容性",
             "声明兼容性或备选模型", family="portability"),
]

_RULE_MAP: dict[str, LintRule] = {r.rule_id: r for r in _ALL_RULES}

_SENSITIVE_PATTERNS = [
    re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(?:secret|token)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(?:AK|SK)\s*[:=]\s*[A-Za-z0-9]{16,}", re.IGNORECASE),
]

_AMBIGUOUS_WORDS = re.compile(
    r"(?:可能|大概|也许|maybe|perhaps|possibly|some|somehow|sort\s+of|kind\s+of|差不多|左右|或许|似乎|不一定)",
    re.IGNORECASE,
)

_ROLE_PATTERNS = [
    re.compile(r"你(?:是一?(?:个|名|位))?(?:是|作为|扮演)\s*.{1,}", re.UNICODE),
    re.compile(r"你是一?(?:个|名|位)\s*.{2,}", re.UNICODE),
    re.compile(r"(?:you\s+are|act\s+as|role[:：])\s+.{2,}", re.IGNORECASE),
    re.compile(r"(?:作为|角色|role)\s*[:：]", re.IGNORECASE),
]

_OUTPUT_FORMAT_PATTERNS = [
    re.compile(r"输出(?:格式|为|以|方式)", re.UNICODE),
    re.compile(r"(?:format|output\s+as|respond\s+in|return\s+(?:a|the))\s+", re.IGNORECASE),
    re.compile(r"(?:JSON|Markdown|列表|表格|XML|YAML|CSV)", re.IGNORECASE),
]

_CONSTRAINT_PATTERNS = [
    re.compile(r"(?:不要|不可|禁止|不能|不允许|不得|切勿|must\s+not|do\s+not|never|avoid|forbidden|禁止|限制)", re.IGNORECASE),
    re.compile(r"(?:不超过|最多|至少|最少|限制|字数|长度|max\s+\d+|min\s+\d+)", re.IGNORECASE),
]

_USER_INPUT_PATTERNS = [
    re.compile(r"\{\{.*?user.*?\}\}", re.IGNORECASE),
    re.compile(r"\{user_input\}", re.IGNORECASE),
    re.compile(r"<user_input>.*?</user_input>", re.IGNORECASE | re.DOTALL),
    re.compile(r"\$\{.*?\}", re.IGNORECASE),
]


def check_p001(text: str) -> Finding | None:
    rule = _RULE_MAP["P001"]
    for pattern in _ROLE_PATTERNS:
        if pattern.search(text):
            return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p002(text: str) -> Finding | None:
    rule = _RULE_MAP["P002"]
    for pattern in _OUTPUT_FORMAT_PATTERNS:
        if pattern.search(text):
            return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p003(text: str) -> Finding | None:
    rule = _RULE_MAP["P003"]
    for pattern in _CONSTRAINT_PATTERNS:
        if pattern.search(text):
            return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p004(text: str) -> Finding | None:
    rule = _RULE_MAP["P004"]
    if len(text) > 2000:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (当前 {len(text)} 字符)",
                       remediation=rule.remediation,
                       details={"length": len(text)})
    return None


def check_p005(text: str) -> Finding | None:
    rule = _RULE_MAP["P005"]
    if len(text) < 50:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (当前 {len(text)} 字符)",
                       remediation=rule.remediation,
                       details={"length": len(text)})
    return None


def check_p006(text: str) -> Finding | None:
    rule = _RULE_MAP["P006"]
    matches = []
    for pattern in _SENSITIVE_PATTERNS:
        for m in pattern.finditer(text):
            matches.append(m.group(0))
    if not matches:
        return None
    redacted = [m[:15] + "***REDACTED***" if len(m) > 15 else m[:5] + "***" for m in matches[:5]]
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=f"{rule.description} (发现 {len(matches)} 处)",
                   remediation=rule.remediation,
                   details={"matches": redacted, "total_count": len(matches)})


def check_p007(text: str) -> Finding | None:
    rule = _RULE_MAP["P007"]
    for pattern in _USER_INPUT_PATTERNS:
        if pattern.search(text):
            has_escape = bool(re.search(r"转义|escape|sanitize|校验|验证|validate", text, re.IGNORECASE))
            if not has_escape:
                return Finding(rule_id=rule.rule_id, severity=rule.severity,
                               description=rule.description, remediation=rule.remediation)
    return None


def check_p008(text: str) -> Finding | None:
    rule = _RULE_MAP["P008"]
    broad_perms = re.findall(
        r"(?:可以|能|may|can|allowed)\s+.*(?:任何|任意|所有|anything|everything|all|any)",
        text, re.IGNORECASE,
    )
    if not broad_perms:
        broad_zh = re.findall(r"(?:任何|任意|所有)", text)
        if broad_zh:
            has_restriction = bool(re.search(r"(?:仅|只|只能|仅限|限制|limit|only|restrict)", text, re.IGNORECASE))
            if not has_restriction:
                broad_perms = broad_zh
    if not broad_perms:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation,
                   details={"matches": broad_perms[:3]})


def check_p009(text: str) -> Finding | None:
    rule = _RULE_MAP["P009"]
    if re.search(r"审计|audit|日志|log|记录|trace|追踪", text, re.IGNORECASE):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p010(text: str) -> Finding | None:
    rule = _RULE_MAP["P010"]
    if re.search(r"如果.*(?:失败|出错|错误|异常|无法)|if.*(?:fail|error|exception|unable)|otherwise|否则|回退|fallback", text, re.IGNORECASE):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p011(text: str) -> Finding | None:
    rule = _RULE_MAP["P011"]
    lines = text.splitlines()
    filler_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or (len(stripped) < 5 and not stripped.startswith(("#", "{", "}", "-"))):
            filler_count += 1
    ratio = filler_count / max(len(lines), 1)
    if ratio > 0.4:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (填充率 {ratio:.0%})",
                       remediation=rule.remediation,
                       details={"filler_ratio": round(ratio, 2)})
    return None


def check_p012(text: str) -> Finding | None:
    rule = _RULE_MAP["P012"]
    sentences = re.split(r"[。.!！\n]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 4]
    seen: dict[str, int] = {}
    for s in sentences:
        normalized = re.sub(r"\s+", " ", s.lower())
        seen[normalized] = seen.get(normalized, 0) + 1
    duplicates = {k: v for k, v in seen.items() if v > 1}
    if not duplicates:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=f"{rule.description} (发现 {len(duplicates)} 处重复)",
                   remediation=rule.remediation,
                   details={"duplicate_count": len(duplicates)})


def check_p013(text: str) -> Finding | None:
    rule = _RULE_MAP["P013"]
    example_blocks = re.findall(r"(?:示例|例子|example|e\.g\.)[:：\s]*(.*?)(?=\n\n|\n[^#\s]|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not example_blocks:
        return None
    weak = []
    for block in example_blocks:
        block = block.strip()
        if len(block) < 20:
            weak.append(block[:50])
    if weak:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (发现 {len(weak)} 个低质量示例)",
                       remediation=rule.remediation,
                       details={"weak_examples": weak[:3]})
    return None


def check_p014(text: str) -> Finding | None:
    rule = _RULE_MAP["P014"]
    depth = 0
    max_depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    if max_depth > 3:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (最大嵌套深度 {max_depth})",
                       remediation=rule.remediation,
                       details={"max_depth": max_depth})
    return None


def check_p015(text: str) -> Finding | None:
    rule = _RULE_MAP["P015"]
    constraint_count = 0
    for pattern in _CONSTRAINT_PATTERNS:
        constraint_count += len(pattern.findall(text))
    if constraint_count > 10:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=f"{rule.description} (当前 {constraint_count} 条约束)",
                       remediation=rule.remediation,
                       details={"constraint_count": constraint_count})
    return None


def check_p016(text: str) -> Finding | None:
    rule = _RULE_MAP["P016"]
    matches = _AMBIGUOUS_WORDS.findall(text)
    if not matches:
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=f"{rule.description} (发现 {len(matches)} 处歧义词)",
                   remediation=rule.remediation,
                   details={"ambiguous_words": matches[:5]})


def check_p017(text: str) -> Finding | None:
    rule = _RULE_MAP["P017"]
    positive = re.findall(r"(?:要|必须|需要|should|must|need\s+to)\s+(.{5,30})", text, re.IGNORECASE)
    negative = re.findall(r"(?:不要|不可|禁止|must\s+not|do\s+not|never)\s+(.{5,30})", text, re.IGNORECASE)
    for p in positive:
        for n in negative:
            p_norm = re.sub(r"\s+", " ", p.lower().strip())
            n_norm = re.sub(r"\s+", " ", n.lower().strip())
            if p_norm == n_norm:
                return Finding(rule_id=rule.rule_id, severity=rule.severity,
                               description=f"{rule.description} (矛盾: '{p.strip()}' vs '{n.strip()}')",
                               remediation=rule.remediation,
                               details={"positive": p.strip(), "negative": n.strip()})
    return None


def check_p018(text: str) -> Finding | None:
    rule = _RULE_MAP["P018"]
    if re.search(r"(?:示例|example|如：|如下|for\s+example|e\.g\.)", text, re.IGNORECASE):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


def check_p019(text: str) -> Finding | None:
    rule = _RULE_MAP["P019"]
    task_complexity = sum(1 for _ in re.finditer(r"(?:分析|推理|比较|评估|判断|analyze|reason|compare|evaluate|judge)", text, re.IGNORECASE))
    has_cot = bool(re.search(r"(?:一步步|逐步|step\s+by\s+step|思考过程|chain\s+of\s+thought|CoT|推理链)", text, re.IGNORECASE))
    if task_complexity >= 2 and not has_cot:
        return Finding(rule_id=rule.rule_id, severity=rule.severity,
                       description=rule.description, remediation=rule.remediation,
                       details={"complexity_indicators": task_complexity})
    return None


def check_p020(text: str) -> Finding | None:
    rule = _RULE_MAP["P020"]
    if re.search(r"(?:评估标准|验收条件|评分|质量标准|evaluation|criteria|grading|rubric)", text, re.IGNORECASE):
        return None
    return Finding(rule_id=rule.rule_id, severity=rule.severity,
                   description=rule.description, remediation=rule.remediation)


_CheckerFn = Callable[[str], Finding | None]

_CHECKERS: list[_CheckerFn] = [
    check_p001, check_p002, check_p003, check_p004, check_p005,
    check_p006, check_p007, check_p008, check_p009, check_p010,
    check_p011, check_p012, check_p013, check_p014, check_p015,
    check_p016, check_p017, check_p018, check_p019, check_p020,
]

from ai_prompt_toolkit.linter.rules_p021_p030 import (  # noqa: E402
    check_p021, check_p022, check_p023, check_p024, check_p025,
    check_p026, check_p027, check_p028, check_p029, check_p030,
    run_checks_p021_p030,
)

from ai_prompt_toolkit.linter.rules_p031_p040 import (  # noqa: E402
    check_p031, check_p032, check_p033, check_p034, check_p035,
    check_p036, check_p037, check_p038, check_p039, check_p040,
    run_checks_p031_p040,
)

from ai_prompt_toolkit.linter.rules_p041_p050 import (  # noqa: E402
    check_p041, check_p042, check_p043, check_p044, check_p045,
    check_p046, check_p047, check_p048, check_p049, check_p050,
    run_checks_p041_p050,
)

from ai_prompt_toolkit.linter.rules_p051_p055 import (  # noqa: E402
    check_p051, check_p052, check_p053, check_p054, check_p055,
    run_checks_p051_p055,
)

from ai_prompt_toolkit.linter.rules_p056_p062 import (  # noqa: E402
    check_p056, check_p057, check_p058, check_p059, check_p060,
    check_p061, check_p062,
    run_checks_p056_p062,
)

_CHECKERS_EXTENDED: list[_CheckerFn] = _CHECKERS + [
    check_p021, check_p022, check_p023, check_p024, check_p025,
    check_p026, check_p027, check_p028, check_p029, check_p030,
    check_p031, check_p032, check_p033, check_p034, check_p035,
    check_p036, check_p037, check_p038, check_p039, check_p040,
    check_p041, check_p042, check_p043, check_p044, check_p045,
    check_p046, check_p047, check_p048, check_p049, check_p050,
    check_p051, check_p052, check_p053, check_p054, check_p055,
    check_p056, check_p057, check_p058, check_p059, check_p060,
    check_p061, check_p062,
]

from ai_prompt_toolkit.linter.rules_p063_p070 import (  # noqa: E402
    check_p063, check_p064, check_p065, check_p066,
    check_p067, check_p068, check_p069, check_p070,
)

_CHECKERS_EXTENDED.extend([
    check_p063, check_p064, check_p065, check_p066,
    check_p067, check_p068, check_p069, check_p070,
])

from ai_prompt_toolkit.linter.rules_p071_p080 import (  # noqa: E402
    check_p071, check_p072, check_p073, check_p074,
    check_p075, check_p076, check_p077, check_p078,
    check_p079, check_p080,
)

_CHECKERS_EXTENDED.extend([
    check_p071, check_p072, check_p073, check_p074,
    check_p075, check_p076, check_p077, check_p078,
    check_p079, check_p080,
])

from ai_prompt_toolkit.linter.rules_p081_p085 import (  # noqa: E402
    check_p081, check_p082, check_p083, check_p084,
    check_p085,
)

_CHECKERS_EXTENDED.extend([
    check_p081, check_p082, check_p083, check_p084,
    check_p085,
])

from ai_prompt_toolkit.linter.rules_p086_p095 import (  # noqa: E402
    check_p086, check_p087, check_p088, check_p089, check_p090,
    check_p091, check_p092, check_p093, check_p094, check_p095,
)

_CHECKERS_EXTENDED.extend([
    check_p086, check_p087, check_p088, check_p089, check_p090,
    check_p091, check_p092, check_p093, check_p094, check_p095,
])

from ai_prompt_toolkit.linter.rules_p096_p100 import (  # noqa: E402
    check_p096, check_p097, check_p098, check_p099, check_p100,
)

_CHECKERS_EXTENDED.extend([
    check_p096, check_p097, check_p098, check_p099, check_p100,
])

from ai_prompt_toolkit.linter.rules_p101_p110 import (  # noqa: E402
    check_p101, check_p102, check_p103, check_p104, check_p105,
    check_p106, check_p107, check_p108, check_p109, check_p110,
)

_CHECKERS_EXTENDED.extend([
    check_p101, check_p102, check_p103, check_p104, check_p105,
    check_p106, check_p107, check_p108, check_p109, check_p110,
])

from ai_prompt_toolkit.linter.rules_p111_p120 import (  # noqa: E402
    check_p111, check_p112, check_p113, check_p114, check_p115,
    check_p116, check_p117, check_p118, check_p119, check_p120,
)

_CHECKERS_EXTENDED.extend([
    check_p111, check_p112, check_p113, check_p114, check_p115,
    check_p116, check_p117, check_p118, check_p119, check_p120,
])

from ai_prompt_toolkit.linter.rules_p121_p130 import (  # noqa: E402
    check_p121, check_p122, check_p123, check_p124, check_p125,
    check_p126, check_p127, check_p128, check_p129, check_p130,
)

_CHECKERS_EXTENDED.extend([
    check_p121, check_p122, check_p123, check_p124, check_p125,
    check_p126, check_p127, check_p128, check_p129, check_p130,
])

from ai_prompt_toolkit.linter.rules_p131_p140 import (  # noqa: E402
    check_p131, check_p132, check_p133, check_p134, check_p135,
    check_p136, check_p137, check_p138, check_p139, check_p140,
)

_CHECKERS_EXTENDED.extend([
    check_p131, check_p132, check_p133, check_p134, check_p135,
    check_p136, check_p137, check_p138, check_p139, check_p140,
])


def get_all_rules() -> list[LintRule]:
    return list(_RULE_MAP.values())


def get_rule(rule_id: str) -> LintRule | None:
    return _RULE_MAP.get(rule_id)


def run_all_checks(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for checker in _CHECKERS_EXTENDED:
        result = checker(text)
        if result is not None:
            findings.append(result)
    p017_triggered = any(f.rule_id == "P017" for f in findings)
    p023_triggered = any(f.rule_id == "P023" for f in findings)
    if p017_triggered and p023_triggered:
        for f in findings:
            if f.rule_id == "P017":
                f.severity = Severity.LOW
    return findings
