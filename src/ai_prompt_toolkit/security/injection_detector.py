"""注入检测器——基于预编译正则的 Prompt 注入模式匹配。"""

from __future__ import annotations

import re
import time

from ai_prompt_toolkit.security.types import InjectionRule
from ai_prompt_toolkit.types import Finding, Severity

_SCAN_TIME_WARN_MS = 10


_BUILTIN_RULES: list[InjectionRule] = [
    InjectionRule(
        rule_id="INJ-001",
        name="指令覆盖",
        pattern=r"ignore\s+.*previous\s+.*instruction",
        severity=Severity.HIGH,
        description="检测到指令覆盖模式：尝试让模型忽略之前的指令",
        remediation="移除或重写指令覆盖语句，确保Prompt遵循预期流程",
    ),
    InjectionRule(
        rule_id="INJ-002",
        name="角色劫持",
        pattern=r"you\s+are\s+now\s+.*(?:admin|root|system)",
        severity=Severity.HIGH,
        description="检测到角色劫持模式：尝试将模型角色切换为高权限身份",
        remediation="移除角色切换语句，或使用明确的角色边界约束",
    ),
    InjectionRule(
        rule_id="INJ-003",
        name="数据外泄",
        pattern=r"(?:output|print|send)\s+.*(?:secret|key|token)",
        severity=Severity.HIGH,
        description="检测到数据外泄模式：尝试让模型输出敏感信息",
        remediation="移除敏感信息输出指令，添加输出过滤约束",
    ),
    InjectionRule(
        rule_id="INJ-004",
        name="越权操作",
        pattern=r"(?:execute|run|eval|exec)\s+.*command",
        severity=Severity.MEDIUM,
        description="检测到越权操作模式：尝试执行系统命令",
        remediation="移除命令执行语句，限制模型操作范围",
    ),
    InjectionRule(
        rule_id="INJ-005",
        name="模板逃逸",
        pattern=r"\{\{[^#/].*?\}\}.*\{\{[^#/]",
        severity=Severity.MEDIUM,
        description="检测到模板逃逸模式：连续的模板插值可能被利用逃逸沙箱",
        remediation="审查模板插值使用，确保不可被用户输入注入",
    ),
    InjectionRule(
        rule_id="INJ-006",
        name="间接注入",
        pattern=r"(?:retrieved|fetched|search).*?(?:ignore|disregard|forget)\s+.*(?:instruction|rule|constraint)",
        severity=Severity.CRITICAL,
        description="检测到间接注入模式：通过检索内容注入恶意指令(OWASP LLM01)",
        remediation="对检索内容进行注入检测，添加内容可信度标记",
    ),
    InjectionRule(
        rule_id="INJ-007",
        name="越狱攻击",
        pattern=r"(?:DAN|jailbreak|bypass|circumvent).*(?:filter|safety|guard|restriction|policy)",
        severity=Severity.CRITICAL,
        description="检测到越狱攻击模式：尝试绕过安全过滤器(OWASP LLM02)",
        remediation="添加安全边界约束，使用多层防御机制",
    ),
    InjectionRule(
        rule_id="INJ-008",
        name="多轮攻击",
        pattern=r"(?:wait|actually|never\s*mind|on\s*second\s*thought).*?(?:reveal|show|tell|output)\s+.*(?:secret|key|password|token)",
        severity=Severity.HIGH,
        description="检测到多轮攻击模式：通过逐步引导泄露敏感信息(OWASP LLM06)",
        remediation="实施会话级安全策略，限制跨轮对话权限升级",
    ),
    InjectionRule(
        rule_id="INJ-009",
        name="编码绕过",
        pattern=r"(?:base64|utf-8|unicode|\\x[0-9a-f]{2}|\\u[0-9a-f]{4})[^\n。！？!?；;]{0,20}(?:\n[^\n。！？!?；;]{0,4})?(?:decode|interpret|parse|exec)(?![A-Za-z0-9_])",
        severity=Severity.HIGH,
        description="检测到编码绕过模式：使用编码手段规避安全检测(OWASP LLM02)",
        remediation="对编码内容先解码再检测，禁止动态解码执行",
    ),
    InjectionRule(
        rule_id="INJ-010",
        name="多语言注入",
        pattern=r"(?<!不得建议)(?<!不得提供)(?<!不提供)(?:忽略|无视|忘记|绕过)[^\n。！？!?；;]{0,12}(?:\n[^\n。！？!?；;]{0,4})?(?:指令|规则|限制|约束|安全)",
        severity=Severity.HIGH,
        description="检测到多语言注入模式：使用中文变体规避英文检测",
        remediation="扩展检测规则至多语言，添加中文注入模式库",
    ),
    InjectionRule(
        rule_id="INJ-011",
        name="系统提示泄露",
        # R353: 未界 `.*` → 同行有界 {0,40} + 跨单行 {0,6}（R352 同惯用法）— redoctor O(n^4)，
        # 密集锚点 20KB 实测 411ms 破 <100ms/file 楔子；有界化后 O(n)，新命中⊆旧命中(不重引 FP)。
        # N=40 取英文自然短语面("show me the contents of the system prompt" gap=24)×1.5 余量;
        # M=6 覆盖"第二步："(5 字)跨行形态(= INJ-014 既有 M 上限)
        pattern=r"(?:repeat|echo|output|print|show|display)[^\n。！？!?；;]{0,40}(?:\n[^\n。！？!?；;]{0,6})?(?:system|initial|original|first)\s*(?:prompt|instruction|message)",
        severity=Severity.HIGH,
        description="检测到系统提示泄露模式：尝试获取系统级提示词(OWASP LLM07)",
        remediation="添加系统提示保护层，禁止输出系统级指令",
    ),
    InjectionRule(
        rule_id="INJ-012",
        name="输出操纵",
        pattern=r"(?:always|must|should|need\s*to)\s+(?:respond|reply|answer|output)\s+(?:with|using|in)\s+(?:only|exactly|just)\s+",
        severity=Severity.MEDIUM,
        description="检测到输出操纵模式：强制模型以特定格式响应(OWASP LLM05)",
        remediation="添加输出格式约束白名单，拒绝非预期格式要求",
    ),
    InjectionRule(
        rule_id="INJ-013",
        name="权限提升",
        pattern=r"(?:sudo|admin|root|superuser|elevated|escalat).*(?:privilege|permission|access|role|right)",
        severity=Severity.HIGH,
        description="检测到权限提升模式：尝试获取更高权限(OWASP LLM08)",
        remediation="实施最小权限原则，添加权限边界检查",
    ),
    InjectionRule(
        rule_id="INJ-014",
        name="供应链注入",
        pattern=r"(?:import|include|require|load|fetch)[ \t]+[^\n。！？!?；;]{0,20}(?:\n[^\n。！？!?；;]{0,6})?(?:url|remote|external|untrusted|https?://)",
        severity=Severity.MEDIUM,
        description="检测到供应链注入模式：尝试加载外部不可信资源(OWASP LLM03)",
        remediation="限制外部资源加载，添加来源白名单验证",
    ),
    InjectionRule(
        rule_id="INJ-015",
        name="情感操纵",
        pattern=r"(?:please|我求你|求求|begging|desperate|紧急|urgent|life\s*or\s*death|救命).*(?:ignore|bypass|skip|override|break)\s+.*(?:rule|limit|constraint|restriction)",
        severity=Severity.MEDIUM,
        description="检测到情感操纵模式：利用情感压力绕过安全限制(OWASP LLM02变体)",
        remediation="添加情感操纵检测层，安全规则不受情感语境影响",
    ),
    InjectionRule(
        rule_id="INJ-016",
        name="编码注入",
        pattern=r"(?:base64|hex|rot13|unicode|url.encode|atob|btoa|\\x[0-9a-f]{2}|\\u[0-9a-f]{4}).*(?:exec|eval|run|execute|system|command)",
        severity=Severity.HIGH,
        description="检测到编码注入模式：通过编码绕过安全检测执行命令(OWASP LLM01变体)",
        remediation="对编码内容进行解码后再检测，禁止编码后执行命令",
    ),
    InjectionRule(
        rule_id="INJ-017",
        name="多语言绕过",
        pattern=r"(?<!不得建议)(?<!不得提供)(?<!不提供)(?:忽略|无视|跳过|绕过|取消|删除|移除|覆写|替换)[^\n。！？!?；;]{0,12}(?:\n[^\n。！？!?；;]{0,4})?(?:规则|限制|约束|安全|防护|过滤|检查|指令|以上)",
        severity=Severity.MEDIUM,
        description="检测到中文多语言绕过模式：利用非英文指令绕过安全过滤",
        remediation="添加多语言安全规则匹配，确保中英文指令均受约束",
    ),
    InjectionRule(
        rule_id="INJ-018",
        name="递归注入",
        pattern=r"(?:translate|interpret|parse|process|analyze).*(?:the\s+following|below|this).*(?:ignore|bypass|override|disregard).*(?:instruction|rule|safety|constraint)",
        severity=Severity.HIGH,
        description="检测到递归注入模式：通过中间任务间接注入恶意指令(OWASP LLM01变体)",
        remediation="对中间任务输出进行注入检测，添加内容可信度标记",
    ),
    InjectionRule(
        rule_id="INJ-019",
        name="分片注入",
        # R353: 两处未界 `.*` → 同行有界 {0,40} + 跨单行 {0,6}（R352 同惯用法）— redoctor O(n^4)，
        # 密集锚点 20KB 实测 329ms 破 <100ms/file 楔子；有界化后 O(n)，新命中⊆旧命中(不重引 FP)。
        # N=40 取英文自然短语面("merge them into the final prompt" gap=23)×1.5 余量;
        # M=6 覆盖"第二步："(5 字)跨行形态(= INJ-014 既有 M 上限)
        pattern=r"(?:part\s+\d|step\s+\d|section\s+\d|第[一二三四五六七八九十\d]+[部分步节])[^\n。！？!?；;]{0,40}(?:\n[^\n。！？!?；;]{0,6})?(?:combine|merge|assemble|concatenate|join|拼接|合并|组装)[^\n。！？!?；;]{0,40}(?:\n[^\n。！？!?；;]{0,6})?(?:instruction|prompt|rule|directive|指令|规则|提示)",
        severity=Severity.HIGH,
        description="检测到分片注入模式：将恶意指令拆分到多个部分，通过合并触发攻击(OWASP LLM01变体)",
        remediation="检测跨段指令组合，添加分片组装安全检查",
    ),
]


class InjectionDetector:
    def __init__(
        self, rules: list[InjectionRule] | None = None, *, extra_rules: list[InjectionRule] | None = None
    ) -> None:
        self._rules = list(rules or _BUILTIN_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)
        self._compiled: list[tuple[InjectionRule, re.Pattern[str]]] = []
        self._compile_rules()

    def _compile_rules(self) -> None:
        self._compiled = [(rule, re.compile(rule.pattern, re.IGNORECASE | re.DOTALL)) for rule in self._rules]

    @property
    def rules(self) -> list[InjectionRule]:
        return list(self._rules)

    def add_rule(self, rule: InjectionRule) -> None:
        self._rules.append(rule)
        compiled = re.compile(rule.pattern, re.IGNORECASE | re.DOTALL)
        self._compiled.append((rule, compiled))

    def remove_rule(self, rule_id: str) -> bool:
        new_rules = [r for r in self._rules if r.rule_id != rule_id]
        if len(new_rules) == len(self._rules):
            return False
        self._rules = new_rules
        self._compile_rules()
        return True

    def detect(self, text: str, *, template_id: str = "") -> list[Finding]:
        start = time.perf_counter()
        findings: list[Finding] = []
        lines = text.splitlines()

        for rule, pattern in self._compiled:
            full_match = pattern.search(text)
            if not full_match:
                continue
            matched_text = full_match.group(0)
            match_start = full_match.start()
            line_number = self._find_line_number(lines, match_start)
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    description=rule.description,
                    location=f"line {line_number}" if line_number > 0 else "full_text",
                    remediation=rule.remediation,
                    details={
                        "matched_text": matched_text,
                        "template_id": template_id,
                        "line_number": line_number,
                        "rule_name": rule.name,
                    },
                )
            )

        elapsed = (time.perf_counter() - start) * 1000
        if elapsed > _SCAN_TIME_WARN_MS:
            findings.append(
                Finding(
                    rule_id="INJ-PERF",
                    severity=Severity.INFO,
                    description=f"注入检测耗时 {elapsed:.1f}ms，超出10ms阈值",
                    location="",
                    remediation="优化规则或减少模板长度",
                    details={"scan_time_ms": elapsed},
                )
            )

        return findings

    @staticmethod
    def _find_line_number(lines: list[str], char_offset: int) -> int:
        current = 0
        for i, line in enumerate(lines):
            if current + len(line) >= char_offset:
                return i + 1
            current += len(line) + 1
        return 0
