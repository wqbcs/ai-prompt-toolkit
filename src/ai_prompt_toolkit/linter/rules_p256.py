"""P256 模板变量完整性 — 确定性结构检查 (R212)

复用 promptci/PromptOps 的 VariableGate/render 变量检测思路(思路复用, 非代码复用),
落地为本项目 lint 体系的一等公民规则。检测两类确定性渲染缺陷:

1. 畸形占位符(HIGH): {{ }} 空占位 / {{my-var}} 含连字符等渲染器 \\w+ 不认的名字 —
   render_template 的 _VAR_PATTERN 会静默保留原样, 运行时才暴露(最贵的发现时机)。
   放行: {{#if x}}/{{/if}} handlebars指令、{{var|default('x')}} 合法语法。
2. 未声明引用(HIGH): prompt存在显式变量声明段(# 变量/# Inputs/variables:),
   但正文引用了声明列表之外的变量。

负样本纪律(沿用R211, 从第一天断言):
- 隐式变量风格(无声明段, clean43-46形态: 变量只在正文出现)不报"未声明" —
  这类prompt的变量由调用方上下文提供, 无声明可校验, 报=噪音。
- |default('x') 有回退值的变量不报 — 未填充也有兜底。
- 代码围栏内的 {{...}} 剥离(P101先例)。
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P256 = [
    LintRule(
        "P256",
        "模板变量完整性",
        "structure",
        Severity.HIGH,
        "模板占位符畸形({{ }}/{{my-var}}渲染器不识别, 静默未填充)或引用了声明段之外的变量, 渲染期才暴露",
        "变量完整性: 占位符名仅用\\w+, 有回退用{{var|default('x')}}; 显式声明段与正文引用交叉核对",
        description_en=(
            "Malformed template placeholders ({{ }}, {{my-var}} — renderer keeps them silently) "
            "or references to variables missing from the declared variables section, surfacing only at render time"
        ),
        remediation_en=(
            "Variable integrity: placeholder names use \\w+ only, use {{var|default('x')}} for fallbacks; "
            "cross-check declared section against body references"
        ),
        family="template_integrity",
        owasp_refs=[],
    ),
]

for r in _RULES_P256:
    _RULE_MAP[r.rule_id] = r

# 复用渲染器同款合法变量pattern(与prompt_template._VAR_PATTERN保持同义),
# 任何不被它完整匹配的 {{...}} 即畸形占位符(渲染器会静默保留原样)。
_VALID_VAR = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*default\(['\"][^'\"]*['\"]\))?\s*\}\}")
_ANY_BRACE = re.compile(r"\{\{(.*?)\}\}")
# handlebars/jinja指令: #if/#each/~/if//end 等 — 合法模板语法, 非变量引用
_TEMPLATE_DIRECTIVE = re.compile(r"^[#/~!%]")
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
# 显式变量声明段: "# 变量"/"# Inputs"/"variables:" 等标题
_DECL_HEADER = re.compile(
    r"^(?:#{1,4}\s*(?:变量|输入变量|模板变量|变量声明|variables?|input variables?|template variables?)\s*:?\s*$"
    r"|variables?\s*:\s*$)",
    re.IGNORECASE | re.MULTILINE,
)
_NEXT_HEADER = re.compile(r"^#{1,4}\s", re.MULTILINE)
_DECL_LINE_VAR = re.compile(r"\{\{\s*(\w+)")


def _strip_fences(text: str) -> str:
    return _CODE_FENCE.sub("", text)


def _declared_names(text: str) -> set[str] | None:
    """提取显式变量声明段内的变量名; 无声明段返回None(隐式变量风格, 不做交叉校验)"""
    headers = list(_DECL_HEADER.finditer(text))
    if not headers:
        return None
    names: set[str] = set()
    for m in headers:
        start = m.end()
        nxt = _NEXT_HEADER.search(text, start)
        section = text[start : nxt.start()] if nxt else text[start:]
        # 声明段内: - name: 描述 形式 + 行内 {{name}} 形式(客户姓名: {{customer_name}})
        for line in section.splitlines():
            line = line.strip().lstrip("-*").strip()
            name_m = re.match(r"^([\w\u4e00-\u9fff]+)\s*[:：]", line)
            if name_m:
                names.add(name_m.group(1))
            names.update(_DECL_LINE_VAR.findall(line))
    return names


def check_p256(text: str) -> list[Finding]:
    findings: list[Finding] = []
    body = _strip_fences(text)
    braces = _ANY_BRACE.findall(body)
    if not braces:
        return findings

    # 检查1: 畸形占位符 — 任何 {{...}} 内容不被渲染器pattern完整匹配
    valid_spans = [(m.start(), m.end()) for m in _VALID_VAR.finditer(body)]
    for m in _ANY_BRACE.finditer(body):
        inner = m.group(1).strip()
        if not inner or _TEMPLATE_DIRECTIVE.match(inner):
            continue  # 空占位/模板指令另行处理
        covered = any(s <= m.start() and m.end() <= e for s, e in valid_spans)
        if covered:
            continue
        if not inner:
            continue
        findings.append(
            Finding(
                "P256",
                Severity.HIGH,
                f"畸形占位符 '{{{{{inner}}}}}' — 渲染器不识别(变量名须为\\w+, 回退用|default), 将静默未填充",
                "1",
                "1",
            )
        )

    # 检查2: 显式声明段存在时, 正文引用须在声明内(|default变量有回退, 放行)
    declared = _declared_names(body)
    if declared is not None:
        for name in sorted({m.group(1) for m in _VALID_VAR.finditer(body)}):
            # 声明段内的引用不算"正文引用"
            if _VALID_VAR.search(body) and name in declared:
                continue
            findings.append(
                Finding(
                    "P256",
                    Severity.HIGH,
                    f"引用了变量声明段之外的变量 '{{{name}}}' — 渲染时将保留原样未填充",
                    "1",
                    "1",
                )
            )
    return findings
