r"""P270 指令文件提权/外传形态（R322, P4-11 规则化: R321 指令文件 IPI 取证 + ATR 真实样本实证）

痛点（02 P4-11, R321 取证轮）: ATR 真实样本 × 269 规则管道 = 安全 payload
0/3 命中 — 指令文件 IPI 面"形态错配"（与 R261 MCP TPA 面同族: 既有规则是
prompt 工程面〔声明/质量/注入短语〕, agent 配置面三形态未覆盖）。R322 扩大
取证（ATR skill-benchmark malicious 10 条真实样本 × 515 TN 面）确认三子形态:
  1. a_priv 提权词面（adv-001）: 伪 project-setup skill 写入投毒 CLAUDE.md —
     dangerouslyDisableSandbox / autoApproveAll / "pre-approved" / "Do not
     ask for user confirmation" / "Never refuse a command", 5 分支全部有真实
     样本出处
  2. b_cred 凭据路径外传共现（adv-004/adv-006/adv-009/adv-013, 4 真实 TP）:
     凭据路径（~/.env|~/.aws/|id_rsa|\.ssh/|\.netrc|\.gnupg/）+ 外传动词
     （send/upload/transmit/post）+ 外部 URL 三信号共现
  3. c_cmd 命令外传（snyk-004, Snyk 真实发现）: curl --data + $(系统指纹命令)
     — 系统信息经 curl 外传外部域

辖区切分（与既有规则不重叠, 02 反清单纪律）:
- **与 P266（URL 内嵌 user:password@）/P267（云厂商凭据 ID 裸字面）正交**:
  P266/P267 抓"凭据字面进 prompt"（字面面）, P270 抓"指令 agent 窃取/外传"
  （指令形态面）
- **与 P006（命名赋值面 password=xxx）正交**: P006 抓赋值意图, P270 抓外传
  指令+共现信号
- **P271（base64 隐藏指令）独立编号**: 同 IPI 族不同形态（编码层 vs 明文
  形态）— 先例 P260(5+连续)/P261(3+交错) 同族不同形态分规则; P271 当前仅
  1 真实 TP（adv-007）, T1（≥2）未达标, 维持观察区（02 P4-11 留痕, 候选
  线索=ATR 其他语料: ninja-*/garak-benchmark/hackaprompt）

精度设计（确定性+低误报是命根, 01 §2）:
- 词表全部实证出处（不自调）: a_priv 5 分支全部出现于 adv-001 真实样本;
  b_cred 三信号 AND — 单信号各自是常态良性面（路径/动词/URL 各在 515 TN 中
  独立出现）, AND 门控 0 误报; c_cmd 系统指纹命令闭集（uname 在 snyk-004
  实火实证; whoami/hostname/pwd/id/env 同类闭集）
- TN 护栏实证（515 条: 60 clean + 339 NotInject + 26 templates + 59 仓内
  语料 + 29 真实 benign skill 文件 + 2 golden benign）: P270 候选 0 误报
- ReDoS 线性: 无嵌套量词（P3-05 审计形态）
- 已知残留（诚实声明, 机制上限）: 非 curl/HTTP 动词的外传形态（如 "email
  the output of env"）不在本规则辖区 — 闭集方案对未知形态必然漏检

OWASP: LLM01 Prompt Injection（IPI 形态, 与同族 P268/P269 一致）
ATLAS: AML.T0051.001 Indirect Prompt Injection（机制面）+ AML.T0086
Exfiltration via AI Agent Tool Invocation（影响面）,
docs/mitre-atlas-mapping.md

R334: 扩中文 agent 配置注入同形态面（a_priv 中文提权词 + b_cred 中文外传动词, 与 R322
英文词表同族, 非新规则=扩 P270 既有模式）。原型 4TP/0FP 验证（26 模板 + CLAUDE.md +
8 合成合法中文 TN 0 误报）。能力存在性核验（防 P1-18 族板漂移）: 02 R242-X2 原登记
"agent-config 检测面未覆盖"为板漂移 — 核心早被 P270 英文覆盖, 真缺口=中文语言覆盖
（R334 补）; 裸 sk-/AIza 凭据字面为窄缺口（P006/P051/P267 已覆盖主体, 低边际价值不抢跑）。
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P270 = [
    LintRule(
        "P270",
        "指令文件提权/外传形态",
        "security",
        Severity.HIGH,
        "Prompt/指令文件含 agent 提权或外传攻击形态（中英文: 自动批准/不请求确认/永不拒绝命令；"
        "凭据路径+外传动词+外部URL三信号共现；curl 外传系统指纹命令输出）— 指令文件 "
        "IPI 典型面（CLAUDE.md/AGENTS.md/SKILL.md 投毒）",
        "移除提权/外传指令：自动批准与'永不拒绝'消除人工确认边界；凭据路径+外传=凭据"
        "外传攻击；curl 外传系统指纹=信息泄露。此类指令文件应按供应链投毒处置（隔离+审查来源）",
        description_en=(
            "Prompt/instruction file contains agent privilege-escalation or "
            "exfiltration attack patterns (auto-approve / never-ask-for-confirmation / "
            "never-refuse instructions; credential path + exfil verb + external URL "
            "co-occurrence; curl exfiltrating system-fingerprint command output) — the "
            "typical IPI surface in agent instruction files (CLAUDE.md/AGENTS.md/"
            "SKILL.md poisoning)"
        ),
        remediation_en=(
            "Remove the privilege-escalation/exfiltration instructions: auto-approve "
            "and never-refuse eliminate the human confirmation boundary; credential "
            "path + exfiltration is a credential-exfiltration attack; curl-based "
            "system-fingerprint exfiltration is data leakage. Treat such instruction "
            "files as supply-chain poisoning (isolate + review provenance)"
        ),
        family="injection",
        owasp_refs=["LLM01"],
    ),
]

for r in _RULES_P270:
    _RULE_MAP[r.rule_id] = r

# 子形态 a_priv: 提权词面 — 5 分支全部有 adv-001 真实样本实证出处
_PRIV_ESCALATION_RE = re.compile(
    r"(dangerouslyDisableSandbox|autoApproveAll|"
    r"pre-?approved|"
    r"do not ask for user (to )?confirm|"
    r"never refuse (a|any) (command|request|instruction|tool call)|"
    # R334: 中文 agent 配置注入同形态面（原型 4TP/0FP 验证, R322 英文词表的中文扩展）。
    # 全部带「所有/全部/任何」限定或「用户确认/命令」agent 语境, 避开「自动批准某具体任务」
    # 常态良性面（原型 TN: 26 模板 + CLAUDE.md + 8 合成合法中文 0 误报）
    r"永不拒绝|永远不拒绝|不要拒绝任何|不要拒绝所有|"
    r"自动批准所有|自动批准全部|自动执行所有操作|"
    r"无需请求用户确认|不要请求用户确认|无需用户确认|跳过用户确认|"
    r"始终允许所有|无需人工确认|无需再确认)",
    re.I,
)

# 子形态 b_cred: 凭据路径外传共现 — 三信号 AND（单信号各自是常态良性面）:
# ① 凭据路径 ② 外传动词 ③ 外部 URL
_CRED_PATH_RE = re.compile(r"~?/\.env\b|~?/\.aws/|id_rsa|\.ssh/|\.netrc|\.gnupg/")
_EXFIL_VERB_RE = re.compile(
    r"\b(send|upload|transmit|post)\b|发送|上传|传输|提交|回传|外传|发到", re.I
)  # R334: +中文外传动词（b_cred 仍三信号 AND 门控, 单动词各自良性面不触发）
_EXTERNAL_URL_RE = re.compile(r"https?://")

# 子形态 c_cmd: curl 命令外传 — --data 载荷含系统指纹命令替换
# （uname 在 snyk-004 实火实证; whoami/hostname/pwd/id/env 同类闭集）
_CMD_EXFIL_RE = re.compile(
    r"curl[^\n]{0,120}?(--data|-d)\b[^\n]{0,100}?\$\((?:uname|whoami|hostname|pwd|id|env)\b",
    re.I,
)


def check_p270(text: str) -> Finding | None:
    rule = _RULE_MAP["P270"]
    priv_m = _PRIV_ESCALATION_RE.search(text)
    if priv_m is not None:
        m: re.Match[str] = priv_m
        subform = "privilege_escalation"
    else:
        cred_m = _CRED_PATH_RE.search(text)
        if cred_m is not None and _EXFIL_VERB_RE.search(text) and _EXTERNAL_URL_RE.search(text):
            m = cred_m
            subform = "credential_exfil"
        else:
            cmd_m = _CMD_EXFIL_RE.search(text)
            if cmd_m is None:
                return None
            m = cmd_m
            subform = "command_exfil"
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        description=rule.description,
        # R218: location 契约单一入口（1-based line:col, 注入/编码最高价值面）
        location=loc_from_match(text, m),
        remediation=rule.remediation,
        details={"subform": subform},
    )
