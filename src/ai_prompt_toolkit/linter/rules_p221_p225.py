"""P221-P225 供应链安全Lint规则

LLM供应链安全最佳实践(OWASP LLM03):
- P221: 模型来源未验证(使用未验证来源的LLM模型/微调权重)
- P222: 第三方依赖审计缺失(Prompt管道中第三方API/插件未审计)
- P223: 数据溯源链断裂(训练/微调数据来源不可追溯)
- P224: 模型版本未锁定(生产环境模型版本未固定, 可能被静默更新)
- P225: 供应链签名缺失(模型/数据/配置缺少签名/校验和验证)

覆盖OWASP LLM03(Supply Chain Vulnerabilities)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P221_P225 = [
    LintRule(
        "P221",
        "模型来源未验证",
        "supply_chain",
        Severity.HIGH,
        "使用未验证来源的LLM模型/微调权重, 可能包含后门/恶意行为",
        "模型来源验证: 模型卡(model card)审核+发布者签名+社区评分, 如 verify_model(model_id, publisher='official', min_stars=100)",
        description_en="Using unverified LLM model/fine-tune weights, may contain backdoors/malicious behavior",
        remediation_en="Model verification: model card review+publisher signature+community rating",
        family="supply_model_source",
        owasp_refs=["LLM03"],
    ),
    LintRule(
        "P222",
        "第三方依赖审计缺失",
        "supply_chain",
        Severity.HIGH,
        "Prompt管道中集成的第三方API/插件/工具未做安全审计, 可能泄露数据",
        "依赖审计: 每个第三方依赖需安全评估+权限最小化+数据流审查, 如 audit_dependency(api_name, scope=['data_access', 'network'])",
        description_en="Third-party API/plugin/tool in prompt pipeline lacks security audit, may leak data",
        remediation_en="Dependency audit: security assessment+least privilege+data flow review for each dependency",
        family="supply_dependency_audit",
        owasp_refs=["LLM03"],
    ),
    LintRule(
        "P223",
        "数据溯源链断裂",
        "supply_chain",
        Severity.MEDIUM,
        "训练/微调/评估数据来源不可追溯, 无法验证数据质量和合规性",
        "数据溯源: 记录数据来源+采集时间+许可协议+处理流程, 如 provenance(data, source='usability', license='CC-BY-4.0', collected='2024-01')",
        description_en="Training/fine-tune/eval data source untraceable, cannot verify data quality/compliance",
        remediation_en="Data provenance: record source+collection time+license+processing pipeline",
        family="supply_data_provenance",
        owasp_refs=["LLM03"],
    ),
    LintRule(
        "P224",
        "模型版本未锁定",
        "supply_chain",
        Severity.HIGH,
        "生产环境模型版本未固定, 可能被提供商静默更新导致行为变化",
        "版本锁定: 固定模型版本+变更检测+回滚预案, 如 model = 'gpt-4-0613' (非'gpt-4'), monitor_behavior_drift()",
        description_en="Production model version not pinned, may be silently updated causing behavior changes",
        remediation_en="Version pinning: pin exact model version+change detection+rollback plan",
        family="supply_version_pin",
        owasp_refs=["LLM03"],
    ),
    LintRule(
        "P225",
        "供应链签名缺失",
        "supply_chain",
        Severity.MEDIUM,
        "模型/数据/配置文件缺少签名或校验和, 无法验证完整性",
        "签名验证: 模型SHA256+数据校验和+配置签名, 如 verify_checksum(model_path, expected='sha256:abc...') + sign_config(config, key)",
        description_en="Model/data/config lacks signature or checksum, cannot verify integrity",
        remediation_en="Signature verification: model SHA256+data checksum+config signature",
        family="supply_signature",
        owasp_refs=["LLM03"],
    ),
]

for r in _RULES_P221_P225:
    _RULE_MAP[r.rule_id] = r

# 注: 不含裸"model/模型" — 讨论模型行为("本模型在医疗领域表现有限")不构成供应链面,
# 仅具体模型标识/权重/微调等采购信号才触发来源验证要求
_MODEL_PATTERN = re.compile(
    r"(?:gpt|claude|llama|gemini|qwen|chatglm|deepseek|mistral|ernie|文心|通义千问|kimi|doubao|微调|fine.tun|权重|weights|from_pretrained|load_model|加载模型|载入权重|model.file|model.repo|model.weights)",
    re.IGNORECASE,
)
_MODEL_VERIFY_PATTERN = re.compile(
    # R177: model_compatibility兼容性声明即"已做选型验证" — 模板/资产元数据不应触发来源验证
    r"(?:model.card|模型卡|发布者|publisher|verify_model|社区评分|community.rating|来源验证|source.verify|model_compatibility|模型兼容)",
    re.IGNORECASE,
)
# R209校准: 第三方依赖仅当引入外部可执行代码面(插件/工具调用/第三方库) —
# 原pattern含"依赖/扩展"泛词, "不引入网络依赖/不扩展到其他领域/缓存依赖层"
# 等正常描述恒触发(9/32误报)。"依赖"整词无词边界但语义泛, 收窄到具体代码集成面。
_DEP_PATTERN = re.compile(
    r"(?:plugin|插件|api_key|第三方.*库|third.party|第三方.*服务|第三方.*API|第三方.*组件|依赖.*库|依赖.*组件|tool_call|工具调用|外部.*扩展|加载.*扩展)",
    re.IGNORECASE,
)
_DEP_AUDIT_PATTERN = re.compile(
    r"(?:audit|审计|安全评估|security.assess|权限|permission|data.flow|数据流审查)", re.IGNORECASE
)
_DATA_PATTERN = re.compile(
    r"(?:训练数据|training.data|微调数据|fine.tune.data|评估数据|eval.data|dataset|数据集|corpus|语料)", re.IGNORECASE
)
_PROVENANCE_PATTERN = re.compile(r"(?:溯源|provenance|来源|source|许可|license|CC.BY|采集|collected)", re.IGNORECASE)
_VERSION_PATTERN = re.compile(
    r"(?:model.*=|模型版本|model.version|gpt-4|claude-3|llama-3|qwen2|api_version|api版本)", re.IGNORECASE
)
_VERSION_PIN_PATTERN = re.compile(
    r"(?:版本锁|version.pin|固定版本|pin.*version|0613|0125|特定版本|exact.version|变更检测|behavior.drift)",
    re.IGNORECASE,
)
_SIGN_PATTERN = re.compile(
    r"(?:签名|signature|校验|checksum|sha256|hash|完整性|integrity|verify_checksum|sign_config)", re.IGNORECASE
)
_MODEL_NO_PIN_PATTERN = re.compile(
    r"(?:gpt-4[^-]|claude-3[^-]|llama-3[^-]|qwen2[^-]|model.*latest|latest)", re.IGNORECASE
)


def check_p221(text: str) -> list[Finding]:
    findings = []
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    text = strip_frontmatter(text)  # R178
    if _MODEL_PATTERN.search(text) and not _MODEL_VERIFY_PATTERN.search(text):
        findings.append(Finding("P221", Severity.HIGH, "LLM模型来源未验证(缺model card/发布者签名/社区评分)", "1", "1"))
    return findings


def check_p222(text: str) -> list[Finding]:
    findings = []
    if _DEP_PATTERN.search(text) and not _DEP_AUDIT_PATTERN.search(text):
        # R209: "不引入第三方UI库"等否定约束不是依赖引入, 排除纯否定语境
        # (clean18_React组件误报根因)。任一"第三方/third-party"命中前4字符
        # 含否定词即视为约束声明。
        tp_hits = [m.start() for m in re.finditer("第三方|third.party", text, re.IGNORECASE)]
        negated_only = all(
            re.search(r"(?:不|禁|勿|别|没|no\b|\bnot|don'?t|avoid|without)", text[max(0, i - 4) : i].lower())
            for i in tp_hits
        )
        if not negated_only:
            findings.append(Finding("P222", Severity.HIGH, "第三方依赖未做安全审计(缺权限/数据流审查)", "1", "1"))
    return findings


def check_p223(text: str) -> list[Finding]:
    findings = []
    if _DATA_PATTERN.search(text) and not _PROVENANCE_PATTERN.search(text):
        findings.append(Finding("P223", Severity.MEDIUM, "数据来源不可追溯(缺溯源链/许可/采集记录)", "1", "1"))
    return findings


def check_p224(text: str) -> list[Finding]:
    findings = []
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    text = strip_frontmatter(text)  # R178
    if _MODEL_NO_PIN_PATTERN.search(text) and not _VERSION_PIN_PATTERN.search(text):
        findings.append(Finding("P224", Severity.HIGH, "模型版本未锁定(使用latest或未固定具体版本)", "1", "1"))
    elif _VERSION_PATTERN.search(text) and not _VERSION_PIN_PATTERN.search(text):
        findings.append(Finding("P224", Severity.HIGH, "模型版本未锁定(缺版本固定/变更检测)", "1", "1"))
    return findings


def check_p225(text: str) -> list[Finding]:
    findings = []
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    text = strip_frontmatter(text)  # R178
    if _MODEL_PATTERN.search(text) and not _SIGN_PATTERN.search(text):
        findings.append(Finding("P225", Severity.MEDIUM, "模型/配置缺少签名和校验和验证", "1", "1"))
    return findings
