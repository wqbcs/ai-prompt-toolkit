"""Lint规则集扩展——P166-P170 Prompt输出安全防护

R76新增(参考llm-guard输出扫描器):
- P166: Prompt输出内容过滤声明缺失
- P167: Prompt幻觉防护声明缺失
- P168: Prompt偏见检测声明缺失
- P169: Prompt毒性内容过滤声明缺失
- P170: Prompt引用验证声明缺失

参考: llm-guard输出扫描器(NoRefusal/Bias/Toxicity/Relevance/FactualConsistency)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P166_P170: list[LintRule] = [
    LintRule(
        "P166",
        "Prompt输出内容过滤声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明输出内容过滤(禁止类型/格式验证/长度限制)",
        "声明输出过滤: 禁止输出代码/SQL/HTML, 格式验证JSON/Markdown, 长度限制<2000字符",
        description_en="Prompt missing output content filtering declaration",
        remediation_en="Declare output filtering: No code/SQL/HTML output, JSON/Markdown validation, length<2000",
        family="output_filtering",
    ),
    LintRule(
        "P167",
        "Prompt幻觉防护声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明幻觉防护(事实核查/来源引用/不确定性标注)",
        "声明幻觉防护: 要求标注不确定信息, 引用来源URL, 禁止编造数据/日期/人名",
        description_en="Prompt missing hallucination protection declaration",
        remediation_en="Declare hallucination protection: Mark uncertainty, cite sources, no fabricated data",
        family="hallucination_protection",
    ),
    LintRule(
        "P168",
        "Prompt偏见检测声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明偏见检测(公平性/代表性/中立性)",
        "声明偏见检测: 输出需公平无歧视, 覆盖多样代表性, 保持中立立场",
        description_en="Prompt missing bias detection declaration",
        remediation_en="Declare bias detection: Fair non-discriminatory, diverse representation, neutral stance",
        family="bias_detection",
    ),
    LintRule(
        "P169",
        "Prompt毒性内容过滤声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明毒性内容过滤(仇恨言论/骚扰/自残/暴力)",
        "声明毒性过滤: 禁止仇恨言论/骚扰/自残/暴力内容, 检测并拒绝毒性输出",
        description_en="Prompt missing toxicity content filtering declaration",
        remediation_en="Declare toxicity filtering: No hate speech/harassment/self-harm/violence, detect and reject",
        family="toxicity_filtering",
    ),
    LintRule(
        "P170",
        "Prompt引用验证声明缺失",
        "security",
        Severity.MEDIUM,
        "Prompt未声明引用验证(来源可追溯/URL可达性/事实一致性)",
        "声明引用验证: 所有事实声明需附来源, URL需可达, 与参考文档事实一致",
        description_en="Prompt missing citation verification declaration",
        remediation_en="Declare citation verification: Facts need sources, URLs reachable, consistent with references",
        family="citation_verification",
    ),
]

for r in _RULES_P166_P170:
    _RULE_MAP[r.rule_id] = r

# R206校准: 移除泛词(输出/响应/回答/结果/生成/返回/回复/格式/文本/output/response/answer/result/
# generat/return/reply/format/text) — 干净prompt的"输出格式/生成代码"即误触发(100%误报率),
# 保留"自由输出/用户输入直出/外部内容回显"等注入语义词
_OUTPUT_FILTER_CTX = re.compile(
    r"(?:直接输出.*用户|用户.*内容.*输出|回显|echo|自由.*回复|原样.*输出|原封不动|verbatim|raw.*output|输出.*外部内容|外部.*内容.*输出|用户输入.*返回)",
    re.IGNORECASE,
)

_OUTPUT_FILTER_DECL = re.compile(
    r"(?:输出.*过滤|output.*filter|禁止.*代码|no.*code|格式.*验证|format.*validat|长度.*限制|length.*limit|内容.*过滤|content.*filter|类型.*限制|type.*restrict|输出.*验证|output.*validat)",
    re.IGNORECASE,
)

# R208校准: 幻觉防护仅当prompt真实存在幻觉风险面 — 要求引用/来源/事实性/
# 知识回答语义。原pattern含"数据/生成/描述/解释"泛词(任何数据处理prompt
# 恒触发, R207前23/32干净样本误报), 且英文单词内嵌子串误配
# ("refactor"含"fact", "describe"含"describ")。
_HALLUCINATION_CTX = re.compile(
    r"(?:知识|knowledge|事实|文献引用|来源引用|引用.{0,10}(?:来源|出处|文献|权威|资料)|cite|来源|参考|reference"
    r"|\bfact\w*|\bstatistic\w*|\binformation\b|\bknowledge\b|\bsource\b)",
    re.IGNORECASE,
)

_HALLUCINATION_DECL = re.compile(
    r"(?:幻觉|hallucin|事实.*核查|fact.*check|不确定|uncertain|来源.*引用|source.*cite|禁止.*编造|no.*fabricat|标注.*不确定|mark.*uncertain|幻觉.*防护|hallucinat.*protect"
    r"|do\s+not\s+invent|don'?t\s+invent|不虚构|不臆造|不杜撰"
    r"|仅依据|仅基于|only\s+based\s+on|不补充.*之外)",
    re.IGNORECASE,
)

# R210校准: 偏见检测仅当prompt涉及受保护属性区分/群体评价 —
# 原CTX含"判断/推荐/分类/分析"泛词, 几乎所有决策类prompt恒触发
# (R210新样本暴露14/56误报)。普通分类(工单/日志/代码)不涉及群体偏见。
# 英文词必须加词边界: age误配Agent/usage, group误配SQL的GROUP BY;
# 去掉裸"简历"(简历优化是写作任务, 非群体评价), 保留招聘筛选等强信号。
_BIAS_CTX = re.compile(
    r"(?:性别|gender|种族|\brace\b|民族|\bethnic\w*\b|年龄|\bage\b|残疾|\bdisab\w*\b|宗教|religion|职业|profession"
    r"|候选人|candidate|招聘|hiring|人群|\bdemographic\w*\b"
    r"|\bperson\b.{0,20}?\bevaluat\w*|\bperson\b.{0,20}?\bclassif\w*)",
    re.IGNORECASE,
)

_BIAS_DECL = re.compile(
    r"(?:偏见|bias|公平|fair|歧视|discriminat|中立|neutral|代表性|representat|多样|diverse|无偏|unbiased|偏见.*检测|bias.*detect"
    r"|忽略.{0,8}(?:性别|年龄|种族|民族|宗教|gender|age|race|ethnic)|只依据技能|仅依据技能)",
    re.IGNORECASE,
)

# R209校准: 毒性防护仅当prompt真实暴露用户生成内容输入面(UGC/评论/社区/
# 群聊) — 原pattern含"用户/反馈/互动"泛词, 几乎所有prompt恒触发
# (11/32干净样本误报)。"客服/助手"服务场景本身不构成毒性输入面。
_TOXICITY_CTX = re.compile(
    r"(?:UGC|用户生成|评论|comment|社交|social|社区|community|论坛|forum|群聊|group\s?chat"
    r"|回复.*用户.*评论|user\s+generated|社交.*内容|社交.*帖子)",
    re.IGNORECASE,
)

_TOXICITY_DECL = re.compile(
    r"(?:毒性|toxic|仇恨|hatred|骚扰|harass|自残|self.?harm|暴力|violen|冒犯|offens|毒性.*过滤|toxic.*filter|禁止.*仇恨|no.*hate|内容.*审核|content.*moderat)",
    re.IGNORECASE,
)

# R209校准: 引用溯源仅当prompt明确要求研究/文献/事实核查语义 —
# 原pattern含"数据/报告/统计"泛词, 任何数据类prompt恒触发(8/32误报)。
# 英文单词加词边界防子串误配。
_CITATION_CTX = re.compile(
    r"(?:研究|research|论文|paper|文献|literature|来源引用|文献引用|引用.{0,6}(?:来源|出处|文献)|cite|参考来源|reference\s?source"
    r"|\bevidence\b|\bfact\s?check\w*|学术|academic|来源追溯|source\s?trace)",
    re.IGNORECASE,
)

_CITATION_DECL = re.compile(
    r"(?:引用.*验证|citation.*verif|来源.*追溯|source.*trace|URL.*可达|URL.*reachab|事实.*一致|fact.*consist|参考.*验证|reference.*validat|引用.*声明|citation.*declar"
    r"|引用.*编号|来源编号|文档\s*ID|citation.*number|引用来源|来源.*编号"
    # R210: "Cite the source paragraph number" — 声明引用来源编号(R210 clean38暴露)
    r"|cite\w*.{0,15}(?:source|paragraph|number|page))",
    re.IGNORECASE,
)


def check_p166(text: str) -> Finding | None:
    rule = _RULE_MAP["P166"]
    if not _OUTPUT_FILTER_CTX.search(text):
        return None
    if _OUTPUT_FILTER_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p167(text: str) -> Finding | None:
    rule = _RULE_MAP["P167"]
    if not _HALLUCINATION_CTX.search(text):
        return None
    if _HALLUCINATION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p168(text: str) -> Finding | None:
    rule = _RULE_MAP["P168"]
    if not _BIAS_CTX.search(text):
        return None
    if _BIAS_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p169(text: str) -> Finding | None:
    rule = _RULE_MAP["P169"]
    if not _TOXICITY_CTX.search(text):
        return None
    if _TOXICITY_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )


def check_p170(text: str) -> Finding | None:
    rule = _RULE_MAP["P170"]
    if not _CITATION_CTX.search(text):
        return None
    if _CITATION_DECL.search(text):
        return None
    return Finding(
        rule_id=rule.rule_id, severity=rule.severity, description=rule.description, remediation=rule.remediation
    )
