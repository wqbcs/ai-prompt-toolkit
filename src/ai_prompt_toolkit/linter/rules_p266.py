r"""P266 连接串密码字面暴露（R240, R240-X2, PII 族缺口补强）

痛点（R239 PII 面 10 例对照实证，08 增量区）：prompt 内连接串
`scheme://user:password@host` 字面密码——PII 族（P005/P006/P050-053/
P252-255）对其零命中，仅 P044（boundary_erosion）不一致命中（mysql/mongo
命中、postgres/amqp 不命中，且 P044 辖区意图=上下文边界约束非凭据检测）。
prompt-guard PII 类+prompt-injection-scanner SDE 类双信号验证面。

辖区切分（与既有规则不重叠，02 反清单纪律）：
- **仅报含 user:password@ 段的连接串**——密码段必须非空（`user:@` 空密码
  占位不报，属待填充占位符）
- **不报无密码 URL**（`https://user@host` 无冒号分隔）/无 user 段连接串
  （`jdbc:mysql://host:port/db` 凭据走 KMS 是正解，不报）
- 与 P006（密钥/口令命名面，password=xxx 赋值形态）互补：P006 管
  赋值/声明面，P266 管 URL 内嵌面——两辖区正交不重叠
- 与 P044 互补：P044 是 Agent 上下文边界约束（HIGH，意图面），P266 是
  凭据字面检测（CRITICAL，与 P006 同级），P044 不一致命中不再是该面唯一
  防线

精度设计（确定性+低误报是命根，01 §2；R240 原型实证）：
- 正则 `scheme://user:password@host`——密码段 `[^\s@]+` 到 @ 为止，user 段
  `[^:/@\s]+`（排除 : 防误吞 scheme 后内容），host 段 `[\w.-]+`
- **原型精度 11/11**：6 TP（mysql/postgres/amqp/mongodb+srv/redis/generic
  http）全中 + 5 TN（user@ 无密码/jdbc 无 user/环境变量引用/host:port
  无 user/空密码占位）全排除
- **双基线冲击面验证**：157 探针 TN 41 条零误报 + clean_prompts 120 行零
  命中 + 26 模板零命中（立项前全量验证，非事后）
- ReDoS 线性：全字面锚点+单段字符类，无嵌套量词/重叠星号（P3-05 形态）

OWASP: LLM06 Sensitive Information Disclosure（连接串密码=敏感信息字面
暴露，与 P005/P006/P252-255 同映射先例）
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P266 = [
    LintRule(
        "P266",
        "连接串密码字面暴露",
        "security",
        Severity.CRITICAL,
        "Prompt中含带密码段的连接串(scheme://user:password@host, 密码非空) — "
        "凭据字面进 prompt 即泄露(对话记录/日志/模型输出面均可复现); "
        "与P006(赋值面password=xxx)互补, 本规则管URL内嵌面",
        "凭据移出prompt: 环境变量/密钥管理服务(KMS)引用, prompt内只保留无密码的"
        "连接信息(scheme://host:port/db); 已暴露的凭据立即轮换",
        description_en=(
            "Connection string with embedded password (scheme://user:password@host, "
            "non-empty password) in the prompt — a literal credential in a prompt is a "
            "leak (reproducible from chat logs, traces, and model outputs); complements "
            "P006 (assignment form password=xxx): this rule covers the URL-embedded form"
        ),
        remediation_en=(
            "Move the credential out of the prompt: reference it via environment variable "
            "or KMS, keep only password-free connection info (scheme://host:port/db) in "
            "the prompt; rotate any already-exposed credential"
        ),
        family="pii_exposure",
        # R240 对抗审查修正: 2025 号 LLM06 经重键表(06→03)落到 2026 LLM03
        # =Excessive Agency(过度代理), 语义错误 — 连接串密码泄露=敏感信息
        # 暴露, 应为 2026 LLM02=Sensitive Information Disclosure, 与同族 PII
        # 规则 P252-255(字面量 LLM02, 重键恒等)一致。2025 号 LLM02 重键恒等,
        # 故直接声明 LLM02。
        owasp_refs=["LLM02"],
    ),
]

for r in _RULES_P266:
    _RULE_MAP[r.rule_id] = r

# scheme://user:password@host — 密码段非空到 @; user 段排除 : (防误吞);
# 全字面锚点+单段字符类, ReDoS 线性形态 (P3-05 审计惯例)
_CONNSTR_PASSWORD_RE = re.compile(
    r"(?:[a-zA-Z][a-zA-Z0-9+.\-]*)://"  # scheme
    r"[^:/@\s]+"  # user (非空, 排除 :/@/空白)
    r":"  # 密码分隔冒号 (必须 — user@ 无密码 URL 不报)
    r"[^\s@]+"  # password (非空, 到 @ 为止)
    r"@"  # user-info/host 边界
    r"[\w.\-]+"  # host
)


def check_p266(text: str) -> Finding | None:
    rule = _RULE_MAP["P266"]
    m = _CONNSTR_PASSWORD_RE.search(text)
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
