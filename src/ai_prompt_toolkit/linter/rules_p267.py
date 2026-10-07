r"""P267 AWS 凭据 ID 字面暴露（R241, R241-X2, 凭据族缺口补强）

痛点（R240 勘误 + R241 T-7 评估实证，07 T-7）：prompt 内 AWS Access Key ID
（AKIA/ASIA/ABIA/ACCA 前缀 + 16 位大写，共 20 位）字面出现——全量规则重验
PII/凭据族（P006/P051/P252-255/P266）零覆盖（AKIA 文本仅触发结构类
P001-003/P005/P177 等非凭据规则）。AWS key ID 是凭据对的一半，真实 key ID
出现在 prompt 中≈高置信度"真实凭据对正在被处理"标记（secret 常伴生；
gitleaks/trufflehog 将 AWS key ID 列为最高优先 secret 形态）。

辖区切分（与既有规则不重叠，02 反清单纪律）：
- **仅报 20 位定长 AWS key ID 字面**——前缀集取 AWS IAM 官方文档 4 前缀
  （AKIA 长期/ASIA 临时 STS/ABIA 长期 2023+/ACCA 临时 2023+）；gitleaks
  规则里的 A3T 系其自标 "might not be a valid AWS token" 的遗留形态，
  置信度不足不纳入（A15：凭先验不写，对照真源收窄）
- 与 P051（硬编码凭据，key/password 命名赋值面）互补：P051 管命名面
  （aws_access_key_id=xxx 即使值不合规也报），P267 管云厂商凭据标识符
  字面形态（无命名上下文也报，精确度高）
- 与 P266（连接串内嵌面）正交：P266 管 URL user:password@ 段，P267 管
  独立 token 字面
- **SSN 不在本规则**（对抗审查修正）：裸 `\d{3}-\d{2}-\d{4}` 匹配电话/
  日期/序列号/订单号=高误报磁铁，与本项目"FP 率是赛道生死指标"的楔子
  冲突；SSN 转 07 T-7 观察区（需关键词上下文增强+真实语料 FP 量化后
  再评估）

精度设计（确定性+低误报是命根，01 §2；R241 原型实证 11/11）：
- 正则 `\b(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b`——20 位定长，`\b` 双向
  锚定使 19/21 位及嵌入长 token 的形态不匹配（只报精确 20 位，零长度
  容差）
- **原型精度 11/11**：TP 4（AKIA 长期/ASIA 临时×2）全中 + TN 7（短 key/
  小写/15 尾 19 位/日期 2026-10-06/电话 212-555-1234/订单号/版本号）
  全排除
- **双基线冲击面验证**：clean_prompts 120 行零命中 + 26 模板零命中 +
  既有 golden TN 零误伤（立项前全量验证，非事后）
- ReDoS 线性：全字面锚点+固定长度字符类，无嵌套量词/重叠星号（P3-05
  形态）

OWASP: LLM02 Sensitive Information Disclosure（2026 号，重键恒等；与同族
P252-255/P266 字面量一致——R240 A15 纪律：声明前对照
OWASP_LLM_TOP_10_2026 单一真源，不凭 2025 先验）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P267 = [
    LintRule(
        "P267",
        "AWS凭据ID字面暴露",
        "security",
        Severity.CRITICAL,
        "Prompt中含AWS Access Key ID字面(AKIA/ASIA/ABIA/ACCA前缀+16位大写, "
        "共20位) — key ID是凭据对的一半, 出现即高置信度真实凭据对正在被处理"
        "(secret常伴生, 对话记录/日志/模型输出面均可复现); 与P051(命名赋值面)"
        "互补, 本规则管云厂商凭据标识符字面形态",
        "凭据移出prompt: 环境变量/KMS/IAM Role引用, prompt内不保留key ID; "
        "已暴露的key ID立即轮换(key ID暴露即使secret未暴露也需轮换, "
        "凭据对任一半泄露即失效)",
        description_en=(
            "AWS Access Key ID literal (AKIA/ASIA/ABIA/ACCA prefix + 16 uppercase "
            "alphanumeric chars, 20 total) in the prompt — the key ID is half of the "
            "credential pair; its presence is a high-confidence marker that a real "
            "credential pair is being handled (secret often co-located, reproducible "
            "from chat logs, traces, model outputs); complements P051 (named "
            "assignment form): this rule covers the bare cloud-credential-token form"
        ),
        remediation_en=(
            "Move the credential out of the prompt: reference it via environment "
            "variable, KMS, or IAM Role; never keep the key ID in the prompt. Rotate "
            "any exposed key ID immediately (an exposed half of the pair invalidates "
            "the credential even without the secret)"
        ),
        family="pii_exposure",
        # 2026 LLM02=Sensitive Information Disclosure, 重键恒等; 与同族
        # P252-255/P266 字面量一致 (R240 A15 纪律, 声明前对照 2026 单一真源)
        owasp_refs=["LLM02"],
    ),
]

for r in _RULES_P267:
    _RULE_MAP[r.rule_id] = r

# AWS Access Key ID — AWS IAM 官方 4 前缀 (AKIA 长期 / ASIA 临时 STS /
# ABIA 长期 2023+ / ACCA 临时 2023+) + 16 位大写字母数字, 共 20 位定长。
# \b 双向锚定: 19/21 位及嵌入长 token 不匹配 (零长度容差, 只报精确形态)。
# A3T 未纳入: gitleaks 自标 "might not be a valid AWS token" 的遗留形态,
# 置信度不足 (A15: 对照真源收窄, 不凭先验扩)。
# 全字面锚点+固定长度, ReDoS 线性形态 (P3-05 审计惯例)
_AWS_KEY_ID_RE = re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b")


def check_p267(text: str) -> Finding | None:
    rule = _RULE_MAP["P267"]
    m = _AWS_KEY_ID_RE.search(text)
    if m:
        return Finding(
            rule_id=rule.rule_id,
            severity=rule.severity,
            description=rule.description,
            location=loc_from_match(text, m),
            remediation=rule.remediation,
            details={"matched_span_len": len(m.group(0))},
        )
    return None
