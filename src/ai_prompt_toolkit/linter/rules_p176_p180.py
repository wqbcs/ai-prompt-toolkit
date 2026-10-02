"""P176-P180高级安全与质量Lint规则

参考garak/promptfoo开源项目的高级检测能力:
- P176: 多轮对话上下文污染(参考garak continuation probe)
- P177: Base64/编码混淆注入(参考garak encoding probe)
- P178: Prompt影子指令(隐藏在格式化中的指令)
- P179: 输出格式劫持(强制模型输出特定格式绕过)
- P180: 链式Prompt注入(跨步骤传播的注入)

覆盖OWASP LLM01(Prompt Injection), LLM02(Sensitive Information), LLM06(Excessive Agency)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P176_P180 = [
    LintRule(
        "P176",
        "多轮对话上下文污染",
        "security",
        Severity.CRITICAL,
        "Prompt存在多轮对话上下文污染风险, 攻击者可通过历史消息注入恶意指令(参考garak continuation probe)",
        "对每轮用户输入进行隔离校验, 使用system消息锁定角色, 实现上下文窗口滑动隔离",
        description_en="Multi-turn conversation context pollution risk, attacker can inject via history messages (ref: garak continuation probe)",
        remediation_en="Isolate each user input, lock role with system message, implement context window sliding isolation",
        family="multi_turn_injection",
        owasp_refs=["LLM01"],
    ),
    LintRule(
        "P177",
        "Base64编码混淆注入",
        "security",
        Severity.CRITICAL,
        "Prompt包含Base64/十六进制/Unicode编码内容, 可能混淆绕过安全检测(参考garak encoding probe)",
        "解码所有编码内容后进行安全审查, 禁止Prompt中包含未解码的编码指令",
        description_en="Prompt contains Base64/hex/Unicode encoded content, may bypass security checks (ref: garak encoding probe)",
        remediation_en="Decode all encoded content for security review, prohibit undecoded instructions in prompts",
        family="encoding_injection",
        owasp_refs=["LLM01"],
    ),
    LintRule(
        "P178",
        "影子指令注入",
        "security",
        Severity.HIGH,
        "Prompt包含隐藏在格式化标记(HTML/Markdown/注释)中的影子指令, 可能被模型执行",
        "审查所有格式化标记内的内容, 移剥离指令性内容, 对HTML注释<!-- -->和Markdown链接做安全过滤",
        description_en="Prompt contains shadow instructions hidden in formatting markers (HTML/Markdown/comments), may be executed by model",
        remediation_en="Audit all formatting marker content, strip directive content, filter HTML comments and Markdown links",
        family="shadow_instruction",
        owasp_refs=["LLM01", "LLM06"],
    ),
    LintRule(
        "P179",
        "输出格式劫持",
        "security",
        Severity.HIGH,
        "Prompt存在输出格式劫持风险, 攻击者可强制模型输出特定格式(如JSON/SQL)绕过输出过滤",
        "对模型输出进行格式校验和内容过滤, 限制输出格式白名单, 实现输出结构约束",
        description_en="Output format hijacking risk, attacker can force specific output format (JSON/SQL) to bypass output filters",
        remediation_en="Validate and filter model output format, restrict output format whitelist, implement output structure constraints",
        family="format_hijack",
        owasp_refs=["LLM01", "LLM06"],
    ),
    LintRule(
        "P180",
        "链式Prompt注入",
        "security",
        Severity.CRITICAL,
        "Prompt存在跨步骤链式注入传播风险, 恶意内容可从步骤N传播到步骤N+1(参考promptfoo chain scan)",
        "每步输出作为下步输入前进行安全清洗, 实现步骤间沙箱隔离, 对中间结果做注入检测",
        description_en="Cross-step chain injection propagation risk, malicious content can spread from step N to N+1 (ref: promptfoo chain scan)",
        remediation_en="Sanitize each step output before next input, implement step sandboxing, detect injection in intermediate results",
        family="chain_injection",
        owasp_refs=["LLM01", "LLM02"],
    ),
]

for r in _RULES_P176_P180:
    _RULE_MAP[r.rule_id] = r


# R179: base64启发式收紧 — 须含数字(真编码)且排除纯字母短语("Critical/Major/Minor"曾误匹配),
# 长度>=20且4的倍数(base64编码特性)
_B64_PATTERN = re.compile(
    r"(?<![A-Za-z0-9+/])(?=[A-Za-z0-9+/]*[0-9])(?=[A-Za-z0-9+/]*[A-Za-z])[A-Za-z0-9+/]{20,}={0,2}(?![A-Za-z0-9+/=])",
    re.ASCII,
)
_HEX_PATTERN = re.compile(r"(?:0x[0-9a-fA-F]{2,})+")
_UNICODE_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}", re.IGNORECASE)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_MD_LINK = re.compile(r"\[.*?\]\(.*?\)")
_SHADOW_CMD = re.compile(
    r"(?:ignore|forget|override|disregard|bypass)\s+(?:previous|above|all|instructions|rules)", re.IGNORECASE
)
_FORMAT_HIJACK = re.compile(
    r"(?:respond\s+(?:only\s+)?in\s+(?:JSON|SQL|HTML|XML|YAML|CSV|Python|JavaScript))", re.IGNORECASE
)
_CHAIN_REF = re.compile(r"(?:previous|prior|last|above)\s+(?:step|output|result|answer|response)", re.IGNORECASE)


def check_p176(text: str) -> list[Finding]:
    findings = []
    has_role = bool(re.search(r"(?:你是|You are|作为|Act as|ROLE)", text, re.IGNORECASE))
    # R169校准: 需真实多轮会话语义 — 裸"对话/上下文/历史"对单轮Prompt误触发CRITICAL
    has_multi_turn = bool(
        re.search(
            r"(?:多轮|multi.turn|每轮|对话历史|历史消息|轮次|conversation.{0,8}history|chat.{0,6}history|multi.turn.{0,8}(?:chat|dialog|conversation))",
            text,
            re.IGNORECASE,
        )
    )
    if has_multi_turn and not has_role:
        findings.append(Finding("P176", Severity.CRITICAL, "多轮对话缺少角色锁定, 存在上下文污染风险"))
    has_isolation = bool(re.search(r"(?:隔离|isolate|沙箱|sandbox|窗口|window)", text, re.IGNORECASE))
    if has_multi_turn and not has_isolation:
        findings.append(Finding("P176", Severity.HIGH, "多轮对话未实现上下文窗口隔离"))
    return findings


def check_p177(text: str) -> list[Finding]:
    findings = []
    b64_matches = [m for m in _B64_PATTERN.finditer(text) if len(m.group()) >= 16]
    if b64_matches:
        findings.append(
            Finding("P177", Severity.CRITICAL, f"检测到{len(b64_matches)}处Base64编码内容, 可能混淆绕过安全检测")
        )
    if _HEX_PATTERN.search(text):
        findings.append(Finding("P177", Severity.HIGH, "检测到十六进制编码内容"))
    if _UNICODE_ESCAPE.search(text):
        findings.append(Finding("P177", Severity.MEDIUM, "检测到Unicode转义序列"))
    return findings


def check_p178(text: str) -> list[Finding]:
    findings = []
    for m in _HTML_COMMENT.finditer(text):
        if _SHADOW_CMD.search(m.group()):
            findings.append(Finding("P178", Severity.CRITICAL, f"HTML注释中包含影子指令: {m.group()[:50]}"))
    for m in _MD_LINK.finditer(text):
        link_text = m.group()
        if _SHADOW_CMD.search(link_text):
            findings.append(Finding("P178", Severity.HIGH, "Markdown链接中包含影子指令"))
    if _SHADOW_CMD.search(text):
        has_protection = bool(re.search(r"(?:过滤|filter|审查|audit|禁止|prohibit)", text, re.IGNORECASE))
        if not has_protection:
            findings.append(Finding("P178", Severity.HIGH, "检测到影子指令但缺少防护声明"))
    return findings


# R207校准: 格式劫持风险仅当prompt处理不可信输入时才成立 — 纯指令prompt无注入面
# (R206前94%误报, 原第二分支has_output恒真)。
# R207二次收窄: 注入面来自"外部内容"(网页/外部文档/抓取数据), 用户交互输入
# 本身是受控渠道(用户自持数据/第三方库名/引用编号要求均非内容注入面)。
_UNTRUSTED_INPUT_CTX = re.compile(
    r"(?:外部内容|外部文档|外部数据|网页|抓取|爬取|第三方内容"
    r"|untrusted|external\s+(?:content|document|data|text|source))",
    re.IGNORECASE,
)


def check_p179(text: str) -> list[Finding]:
    findings = []
    if _FORMAT_HIJACK.search(text):
        has_constraint = bool(
            re.search(r"(?:限制|restrict|白名单|whitelist|校验|validate|约束|constraint)", text, re.IGNORECASE)
        )
        if not has_constraint:
            findings.append(Finding("P179", Severity.HIGH, "检测到输出格式强制但缺少格式约束声明"))
    # R207: 第二分支(输出未配置格式过滤)仅在处理不可信输入时构成劫持风险,
    # 否则任何含"输出"的prompt恒触发(R206前94%误报)
    if _UNTRUSTED_INPUT_CTX.search(text):
        has_output = bool(re.search(r"(?:输出|output|返回|return|响应|response)", text, re.IGNORECASE))
        has_filter = bool(re.search(r"(?:过滤|filter|校验|validate|检查|check)", text, re.IGNORECASE))
        if has_output and not has_filter:
            findings.append(Finding("P179", Severity.MEDIUM, "处理外部输入但输出未配置格式过滤, 存在格式劫持风险"))
    return findings


def check_p180(text: str) -> list[Finding]:
    findings = []
    # R178收紧: 需"步骤间数据传递"的链式编排证据 — 裸"步骤/流程/链式思考"是普通工作流描述
    has_chain = _CHAIN_REF.search(text) or bool(
        re.search(
            r"(?:上一步|前一步|步骤.{0,8}输出|输出.{0,8}(?:作为|传入|交给| feeding)|previous.{0,6}step|step.{0,6}output"
            r"|串联调用|级联调用|链式Prompt|多步骤.{0,8}(?:执行|调用)|中间结果.{0,8}(?:传递|输入))",
            text,
            re.IGNORECASE,
        )
    )
    if has_chain:
        has_sanitize = bool(re.search(r"(?:清洗|sanitize|消毒|clean|过滤|filter|检查|check)", text, re.IGNORECASE))
        if not has_sanitize:
            findings.append(Finding("P180", Severity.CRITICAL, "链式Prompt步骤间未配置安全清洗"))
        has_sandbox = bool(re.search(r"(?:沙箱|sandbox|隔离|isolate|独立|independent)", text, re.IGNORECASE))
        if not has_sandbox:
            findings.append(Finding("P180", Severity.HIGH, "链式Prompt步骤间未实现沙箱隔离"))
    return findings
