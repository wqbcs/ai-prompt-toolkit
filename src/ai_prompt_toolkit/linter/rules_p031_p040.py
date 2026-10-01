"""Lint 规则集扩展——P031-P040 Agent/RAG/Multimodal质量检查规则 (R21新增)。"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_AGENT_RULES: list[LintRule] = [
    LintRule(
        "P031",
        "Agent缺失工具调用约束",
        "agent",
        Severity.HIGH,
        "Agent型Prompt未定义工具调用的安全边界和权限限制",
        "添加工具调用约束: 明确可调用工具列表、参数校验规则、权限边界",
        description_en="Agent Prompt does not define security boundaries and permission limits for tool calls",
        remediation_en="Add tool call constraints: specify callable tool list, parameter validation rules, permission boundaries",
        family="agent_tool",
    ),
    LintRule(
        "P032",
        "Agent缺失错误处理策略",
        "agent",
        Severity.MEDIUM,
        "Agent型Prompt未定义工具调用失败时的降级策略",
        "添加错误处理: 定义工具不可用时的fallback行为、重试策略、超时处理",
        description_en="Agent Prompt does not define degradation strategy for tool call failures",
        remediation_en="Add error handling: define fallback behavior when tools unavailable, retry strategy, timeout handling",
        family="agent_error",
    ),
    LintRule(
        "P033",
        "Agent缺失上下文边界",
        "agent",
        Severity.HIGH,
        "Agent型Prompt未限制上下文传递范围，可能导致信息泄露",
        "添加上下文边界: 明确哪些信息可以传递给工具、禁止传递敏感字段",
        description_en="Agent Prompt does not limit context passing scope, may cause information leakage",
        remediation_en="Add context boundary: specify which information can be passed to tools, prohibit passing sensitive fields",
        family="agent_boundary",
    ),
    LintRule(
        "P034",
        "Agent缺失审批机制",
        "agent",
        Severity.MEDIUM,
        "Agent型Prompt未对高风险操作设置人工审批流程",
        "添加审批机制: 高风险操作(删除/支付/发送)需人工确认后才可执行",
        description_en="Agent Prompt does not set up human approval workflow for high-risk operations",
        remediation_en="Add approval mechanism: high-risk operations (delete/payment/send) require human confirmation before execution",
        family="agent_approval",
    ),
]

_RAG_RULES: list[LintRule] = [
    LintRule(
        "P035",
        "RAG缺失检索源验证",
        "rag",
        Severity.HIGH,
        "RAG型Prompt未验证检索内容的可信度和来源",
        "添加检索源验证: 标注内容来源、验证可信度、区分可信与不可信来源",
        description_en="RAG Prompt does not verify the credibility and source of retrieved content",
        remediation_en="Add retrieval source validation: annotate content sources, verify credibility, distinguish trusted from untrusted sources",
        family="rag_retrieval",
    ),
    LintRule(
        "P036",
        "RAG缺失幻觉检测提示",
        "rag",
        Severity.MEDIUM,
        "RAG型Prompt未指示模型在检索结果不包含答案时承认不知",
        "添加幻觉检测指令: '如果检索结果中未包含相关信息，请明确说明'",
        description_en="RAG Prompt does not instruct the model to acknowledge when retrieval results contain no answer",
        remediation_en="Add hallucination detection instruction: 'If retrieval results do not contain relevant information, please state so explicitly'",
        family="rag_hallucination",
    ),
    LintRule(
        "P037",
        "RAG缺失引用标注要求",
        "rag",
        Severity.MEDIUM,
        "RAG型Prompt未要求模型标注答案来源的引用",
        "添加引用标注: 要求模型在每个陈述后标注来源段落编号或引用标记",
        description_en="RAG Prompt does not require the model to annotate answer source citations",
        remediation_en="Add citation annotation: require the model to annotate source paragraph numbers or citation markers after each statement",
        family="rag_citation",
    ),
]

_MULTIMODAL_RULES: list[LintRule] = [
    LintRule(
        "P038",
        "多模态缺失输入类型验证",
        "multimodal",
        Severity.HIGH,
        "多模态Prompt未验证输入的类型(图片/音频/视频)和大小限制",
        "添加输入验证: 限制接受的文件类型、最大文件大小、分辨率范围",
        description_en="Multimodal Prompt does not validate input types (image/audio/video) and size limits",
        remediation_en="Add input validation: restrict accepted file types, max file size, resolution range",
        family="multimodal_input",
    ),
    LintRule(
        "P039",
        "多模态缺失内容安全检查",
        "multimodal",
        Severity.HIGH,
        "多模态Prompt未对非文本输入进行内容安全检查",
        "添加内容安全: 对图片/音频执行安全检测，过滤不当内容后再处理",
        description_en="Multimodal Prompt does not perform content safety checks on non-text inputs",
        remediation_en="Add content safety: perform safety detection on images/audio, filter inappropriate content before processing",
        family="multimodal_safety",
    ),
    LintRule(
        "P040",
        "多模态缺失降级策略",
        "multimodal",
        Severity.MEDIUM,
        "多模态Prompt未定义非文本输入不可用时的降级方案",
        "添加降级策略: 定义图片/音频无法处理时的纯文本fallback行为",
        description_en="Multimodal Prompt does not define degradation strategy when non-text input is unavailable",
        remediation_en="Add degradation strategy: define text-only fallback behavior when images/audio cannot be processed",
        family="multimodal_fallback",
    ),
]

for r in _AGENT_RULES + _RAG_RULES + _MULTIMODAL_RULES:
    _RULE_MAP[r.rule_id] = r

_AGENT_TOOL_PATTERNS = [
    re.compile(
        r"(?:调用|执行|运行|invoke|call|execute|run)\s*(?:工具|函数|API|插件|tool|function|plugin|API)", re.IGNORECASE
    ),
    re.compile(r"(?:tool_call|function_call|plugin_use|use_tool)", re.IGNORECASE),
    re.compile(r"(?:搜索|查询|检索|search|query|retrieve)\s*(?:工具|引擎|tool|engine)", re.IGNORECASE),
]

_AGENT_ERROR_PATTERNS = [
    re.compile(r"(?:失败|错误|异常|超时|不可用|fail|error|exception|timeout|unavailable)", re.IGNORECASE),
    re.compile(r"(?:降级|回退|备选|fallback|retry|retry|重试|替代方案)", re.IGNORECASE),
]

_AGENT_CONTEXT_PATTERNS = [
    re.compile(
        r"(?:传递|发送|转发|pass|send|forward|transmit)\s*(?:上下文|参数|信息|context|param|info)", re.IGNORECASE
    ),
    re.compile(
        r"(?:上下文|参数|信息|context|param|info)\s*(?:传递|发送|转发|pass|send|forward|transmit)", re.IGNORECASE
    ),
    re.compile(
        r"(?:禁止|不允许|不得|forbidden|not\s+allowed|must\s+not)\s*(?:传递|发送|泄露|pass|send|leak)", re.IGNORECASE
    ),
]

_AGENT_APPROVAL_PATTERNS = [
    re.compile(r"(?:审批|确认|授权|approve|confirm|authorize|human\s+in\s+the\s+loop)", re.IGNORECASE),
    re.compile(r"(?:删除|支付|发送|转账|delete|payment|send|transfer)\s*.*(?:需|必须|require|must)", re.IGNORECASE),
]

_RAG_SOURCE_PATTERNS = [
    re.compile(r"(?:来源|出处|引用|source|citation|reference|origin)", re.IGNORECASE),
    re.compile(r"(?:可信|验证|核实|trusted|verified|validate|authentic)", re.IGNORECASE),
]

_RAG_HALLUCINATION_PATTERNS = [
    re.compile(
        r"(?:不知|不确定|无法确定|找不到|未包含|I don't know|not sure|cannot determine|not found|not contain)",
        re.IGNORECASE,
    ),
    re.compile(r"(?:如果.*不包含|如果.*未找到|if.*not\s+(?:found|contain|include))", re.IGNORECASE),
    # R212-6: 真RAG样本的"资料缺失声明"措辞(clean32「资料中没有相关信息」/
    # clean38「if the context does not cover」) — 未覆盖/没有相关信息即幻觉兜底
    re.compile(
        r"(?:未覆盖|没有相关信息|无相关|资料中没有|not\s+cover|no\s+information|does\s+not\s+cover)",
        re.IGNORECASE,
    ),
]

_RAG_CITATION_PATTERNS = [
    re.compile(r"(?:引用|标注|来源|cite|annotation|reference|source)", re.IGNORECASE),
    re.compile(r"(?:段落|编号|出处|paragraph|number|origin)", re.IGNORECASE),
]

# R212-6: RAG语境门 — 与P035(R180)同构。裸"查询/query/搜索"触发使SQL/业务
# 查询prompt误判为RAG面(clean06/34/48/41各1条误报)。真实RAG检索面=检索引擎/
# 知识库/向量库等组合证据, 纯SQL查询不构成。
# R214-B2: 日语RAG词面 — 検索/ナレッジベース(知识库); 检(检)与検(检, 日文)是不同字符,
# 与中文干净样本无碰撞(58样本0日语)
# R214-B3: 繁体词面(知識庫/檢索) + CJK空格插入容忍(检\s*索/知\s*识\s*库) —
# atk50(繁体)/atk52(空格插入"知 识库")实测漏检; 容忍限于门内(门是P035-P037/P257
# 共用入口, 扩面=全部RAG规则受益, 58干净样本0新增误报验证)
_RAG_CTX_GATE = re.compile(
    r"(?:检\s*索|RAG|知\s*识\s*库|知識\s*庫|檢\s*索|knowledge\s+base|retriev|向量|vector.{0,6}store|文档库|"
    r"検索|ナレッジベース|"
    r"(?:search|query).{0,10}(?:engine|index))",
    re.IGNORECASE,
)

_MULTIMODAL_INPUT_PATTERNS = [
    # R212-6: 英文媒体词加词边界 — "imageUrl"/"filename"等标识符子串不是
    # 多模态输入(clean52 React组件误报根因); 中文词无边界问题保持原样。
    re.compile(
        r"(?:图片|图像|音频|视频|照片|\bimage\b|\baudio\b|\bvideo\b|\bphoto\b|\bpicture\b|\bmedia\b)",
        re.IGNORECASE,
    ),
    # R212-6: 移除裸"文件/file/attach" — 代码审查/配置类prompt的"diff文件"
    # 即误触发(7样本7条误报)。真实多模态输入=媒体词或显式上传/附件语境。
    re.compile(r"(?:上传|附件|upload|attachment)", re.IGNORECASE),
]

_MULTIMODAL_VALIDATION_PATTERNS = [
    re.compile(r"(?:类型|格式|大小|分辨率|type|format|size|resolution|dimension)", re.IGNORECASE),
    re.compile(r"(?:限制|最大|不超过|limit|max|not\s+exceed|up\s+to)", re.IGNORECASE),
]

_MULTIMODAL_SAFETY_PATTERNS = [
    re.compile(r"(?:安全检查|内容检测|过滤|审核|safe|content\s+check|filter|moderat)", re.IGNORECASE),
    re.compile(r"(?:不当|违规|harmful|inappropriate|violation|NSFW)", re.IGNORECASE),
]

_MULTIMODAL_FALLBACK_PATTERNS = [
    re.compile(r"(?:降级|回退|备选|fallback|degrad|alternat)", re.IGNORECASE),
    re.compile(r"(?:纯文本|仅文本|text\s+only|plain\s+text)", re.IGNORECASE),
]


def check_p031(text: str) -> Finding | None:
    rule = _RULE_MAP["P031"]
    has_tool = any(p.search(text) for p in _AGENT_TOOL_PATTERNS)
    if not has_tool:
        return None
    has_constraint = bool(
        re.search(
            r"(?:约束|限制|权限|边界|constraint|limit|permission|boundary|restrict|whitelist|白名单)",
            text,
            re.IGNORECASE,
        )
    )
    if has_constraint:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p032(text: str) -> Finding | None:
    rule = _RULE_MAP["P032"]
    has_tool = any(p.search(text) for p in _AGENT_TOOL_PATTERNS)
    if not has_tool:
        return None
    has_error_handling = any(p.search(text) for p in _AGENT_ERROR_PATTERNS)
    if has_error_handling:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p033(text: str) -> Finding | None:
    rule = _RULE_MAP["P033"]
    has_context = any(p.search(text) for p in _AGENT_CONTEXT_PATTERNS)
    if not has_context:
        return None
    has_boundary = bool(
        re.search(
            r"(?:禁止|不允许|不得|敏感|脱敏|forbidden|not\s+allowed|must\s+not|sensitive|redact|mask)",
            text,
            re.IGNORECASE,
        )
    )
    if has_boundary:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p034(text: str) -> Finding | None:
    rule = _RULE_MAP["P034"]
    has_high_risk = bool(
        re.search(r"(?:删除|支付|发送|执行命令|转账|delete|payment|send|execute|transfer)", text, re.IGNORECASE)
    )
    if not has_high_risk:
        return None
    has_approval = any(p.search(text) for p in _AGENT_APPROVAL_PATTERNS)
    if has_approval:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p035(text: str) -> Finding | None:
    rule = _RULE_MAP["P035"]
    # R180: 需RAG检索语境证据 — "订单查询"等业务查询不构成RAG面
    has_retrieval = bool(
        re.search(
            r"(?:检索|RAG|知识库|knowledge\s+base|retriev|向量库|vector.{0,6}store|文档库|"
            r"(?:search|query).{0,10}(?:engine|index))",
            text,
            re.IGNORECASE,
        )
    )
    if not has_retrieval:
        return None
    has_source_validation = any(p.search(text) for p in _RAG_SOURCE_PATTERNS)
    if has_source_validation:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p036(text: str) -> Finding | None:
    rule = _RULE_MAP["P036"]
    # R212-6: RAG语境门(同P035/R180) — 裸"查询/query"是SQL/业务词汇, 不构成检索面
    if not _RAG_CTX_GATE.search(text):
        return None
    has_hallucination_check = any(p.search(text) for p in _RAG_HALLUCINATION_PATTERNS)
    if has_hallucination_check:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p037(text: str) -> Finding | None:
    rule = _RULE_MAP["P037"]
    # R212-6: RAG语境门(同P035/R180)
    if not _RAG_CTX_GATE.search(text):
        return None
    has_citation = any(p.search(text) for p in _RAG_CITATION_PATTERNS)
    if has_citation:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p038(text: str) -> Finding | None:
    rule = _RULE_MAP["P038"]
    # R212-6: 触发门收窄在INPUT侧(移除裸文件/file+媒体词加边界) — 已足够区分
    # 真多模态与纯文本prompt。VALIDATION侧"类型/格式/大小"对真多模态prompt
    # 正是正确校验(图片大小/格式限制), 不可再加媒体专词门(会误伤内置多模态模板)。
    has_multimodal = any(p.search(text) for p in _MULTIMODAL_INPUT_PATTERNS)
    if not has_multimodal:
        return None
    has_validation = any(p.search(text) for p in _MULTIMODAL_VALIDATION_PATTERNS)
    if has_validation:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p039(text: str) -> Finding | None:
    rule = _RULE_MAP["P039"]
    has_multimodal = any(p.search(text) for p in _MULTIMODAL_INPUT_PATTERNS)
    if not has_multimodal:
        return None
    has_safety = any(p.search(text) for p in _MULTIMODAL_SAFETY_PATTERNS)
    if has_safety:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p040(text: str) -> Finding | None:
    rule = _RULE_MAP["P040"]
    has_multimodal = any(p.search(text) for p in _MULTIMODAL_INPUT_PATTERNS)
    if not has_multimodal:
        return None
    has_fallback = any(p.search(text) for p in _MULTIMODAL_FALLBACK_PATTERNS)
    if has_fallback:
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def run_checks_p031_p040(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for checker in [
        check_p031,
        check_p032,
        check_p033,
        check_p034,
        check_p035,
        check_p036,
        check_p037,
        check_p038,
        check_p039,
        check_p040,
    ]:
        result = checker(text)
        if result is not None:
            findings.append(result)
    return findings
