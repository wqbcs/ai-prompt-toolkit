"""R213-P0-3: MCP 配置安全扫描器 — 配置级 8 项检查 + tool description security 族规则。

定位红线(见 docs/R213-改进方案与开源调研-v2.md P0-3): 只扫 MCP 配置面 —
tool 的 `description` 就是 prompt 文本, 走 security 族 Lint 规则(见
_DESC_SECURITY_CATEGORIES 注释); 配置本身做 8 项安全检查(借鉴 PromptSonar
MCP-011~109 规则语义, 非抄代码)。
不做: MCP 客户端、运行时执行路径、MCP 协议层扫描。

R227-P2-20: rug pull / 隐藏通道面(Microsoft 官方点名的 MCP 攻击面, 12 §1.8):
- MCP-108 description 隐藏通道(C0/ANSI ESC/C1/Unicode Tags U+E0000-E007F) —
  零宽/BiDi 族已由 P260/P261 覆盖(security 族过滤自动作用于 description),
  本项只补 C0/C1/Tags 缺口, 与存量规则不重叠
- MCP-109(HIGH) description 漂移已批准基线 / MCP-110(MEDIUM) 新描述未批准 —
  sha256 基线 + 显式批准动作(--baseline-out), 行业共识形态(开源参考
  mcplint description hash 基线 / mcp-sentinel rug-pull detector /
  mcplint-sec MCP012 lockfile 漂移), 纯 stdlib 零新依赖

Risk Score 0-100: 机械派生自 LintResult.quality_score 的同一张扣分权重表
(critical=12/high=6/medium=1/low=0.1/info=0, 同规则只计一次) — 无新公式,
score = min(100, 扣分和), 分档 ≤20 LOW / ≤45 MEDIUM / ≤70 HIGH / >70 CRITICAL。

误报纪律: 通用 env 变量引用(${API_KEY})是 MCP 官方推荐模式, 不告警;
只标记高敏宿主凭据透传(SSH_AUTH_SOCK/AWS_SESSION_TOKEN 类) — 宁窄勿滥。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity

# ---------------------------------------------------------------- 配置结构识别

_SERVER_CONTAINER_KEYS = ("mcpServers", "servers", "mcp_servers")


def _extract_servers(cfg: Any) -> list[tuple[str, dict[str, Any]]]:
    """从多种 MCP 配置形态中提取 (server名, 配置) 列表。"""
    if isinstance(cfg, dict):
        for key in _SERVER_CONTAINER_KEYS:
            if key in cfg and isinstance(cfg[key], dict):
                return [(str(k), v) for k, v in cfg[key].items() if isinstance(v, dict)]
        if "command" in cfg or "url" in cfg:
            return [("root", cfg)]
    if isinstance(cfg, list):
        return [(f"server{i}", e) for i, e in enumerate(cfg) if isinstance(e, dict)]
    return []


# ---------------------------------------------------------------- 配置级检查

_HTTP_PLAIN_RE = re.compile(r"http://")
# 硬编码凭据: 键名语义(值非 ${VAR} 引用时)
_CRED_KEY_RE = re.compile(
    r"(?i)^(api[_-]?key|token|access[_-]?token|auth[_-]?token|secret|client[_-]?secret|password|passwd|"
    r"access[_-]?key|secret[_-]?key|private[_-]?key|bearer)$"
)
# 硬编码凭据: 值形态(各平台密钥前缀)
_SECRET_VALUE_RE = re.compile(
    r"(?i)\b(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{8,}|AKIA[A-Z0-9]{12,})"
)
_ENV_REF_RE = re.compile(r"^\$\{?[A-Za-z_][A-Za-z0-9_]*\}?$")
# 高敏宿主凭据透传(仅此类, 通用 ${API_KEY} 不告警 — 那是官方推荐模式)
_HOST_CRED_RE = re.compile(
    r"(SSH_AUTH_SOCK|AWS_SESSION_TOKEN|GOOGLE_APPLICATION_CREDENTIALS|KUBECONFIG|/run/user/\d+/ssh\.agent)"
)
_UNPINNED_PACKAGER = {"npx", "uvx", "npm"}
_ROUTE_KEY_RE = re.compile(r"(?i)^(route_?to|upstream|delegate|delegate_?to|forward_?to|proxy_?to|chained)$")
_AUTO_APPROVE_TRUE_KEYS = ("autoexecute", "autoapprove", "auto_approve", "alwaysallow", "always_allow")


def _entry_strings(entry: dict[str, Any]) -> list[str]:
    """收集 entry 里所有需要字符串扫描的值(url/command/args)。"""
    out: list[str] = []
    for key in ("url", "command"):
        v = entry.get(key)
        if isinstance(v, str):
            out.append(v)
    args = entry.get("args")
    if isinstance(args, list):
        out.extend(a for a in args if isinstance(a, str))
    return out


def _check_http_plane(name: str, entry: dict[str, Any]) -> Finding | None:
    for s in _entry_strings(entry):
        if _HTTP_PLAIN_RE.search(s):
            return Finding(
                "MCP-101",
                Severity.HIGH,
                f"[{name}] MCP 端点使用 http:// 明文传输(凭据/流量可被中间人截获)",
                f"::server:{name}",
                "改用 https:// 端点; stdio 服务器不应出现 http:// 端点",
            )
    return None


def _walk_values(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """(键名, 字符串值) 对 — 覆盖顶层与 env 两层。"""
    out: list[tuple[str, str]] = []
    for k, v in entry.items():
        if isinstance(v, str):
            out.append((k, v))
        elif k == "env" and isinstance(v, dict):
            for ek, ev in v.items():
                if isinstance(ev, str):
                    out.append((ek, ev))
    return out


def _check_hardcoded_creds(name: str, entry: dict[str, Any]) -> Finding | None:
    for key, value in _walk_values(entry):
        if _CRED_KEY_RE.match(key) and value and not _ENV_REF_RE.match(value):
            return Finding(
                "MCP-102",
                Severity.CRITICAL,
                f"[{name}] MCP 配置硬编码凭据字段 '{key}'(应使用 ${{ENV}} 引用)",
                f"::server:{name}",
                '改用环境变量引用(如 "${API_KEY}"), 并轮换已泄露的凭据',
            )
        if _SECRET_VALUE_RE.search(value):
            return Finding(
                "MCP-102",
                Severity.CRITICAL,
                f"[{name}] MCP 配置含密钥形态字面量('{key}' 字段, 已脱敏: {value[:8]}***)",
                f"::server:{name}",
                "移除字面量, 改用环境变量引用, 并轮换该凭据",
            )
    return None


def _check_wildcard_perm(name: str, entry: dict[str, Any]) -> Finding | None:
    perms = entry.get("permissions")
    if isinstance(perms, list) and any(p == "*" for p in perms if isinstance(p, str)):
        return Finding(
            "MCP-103",
            Severity.HIGH,
            f"[{name}] MCP 权限配置使用通配符 permissions: ['*'](最小权限原则被绕过)",
            f"::server:{name}",
            "显式列出所需权限, 禁用通配符",
        )
    for key in ("allowAll", "allow_all"):
        if entry.get(key) is True:
            return Finding(
                "MCP-103",
                Severity.HIGH,
                f"[{name}] MCP 配置 {key}: true — 全量放行",
                f"::server:{name}",
                "移除全量放行, 显式列出所需权限",
            )
    return None


def _check_auto_approve(name: str, entry: dict[str, Any]) -> Finding | None:
    lowered = {str(k).lower(): v for k, v in entry.items()}
    for key in _AUTO_APPROVE_TRUE_KEYS:
        if lowered.get(key) is True:
            return Finding(
                "MCP-104",
                Severity.HIGH,
                f"[{name}] MCP 配置 {key}: true — 工具调用免审批(OWASP LLM06 Excessive Agency)",
                f"::server:{name}",
                "关闭自动审批, 敏感操作保留人工确认(HITL)",
            )
    for key in ("approvalrequired", "approval_required"):
        if lowered.get(key) is False:
            return Finding(
                "MCP-104",
                Severity.HIGH,
                f"[{name}] MCP 配置 {key}: false — 工具调用免审批",
                f"::server:{name}",
                "设为 true, 敏感操作保留人工确认(HITL)",
            )
    return None


def _check_env_passthrough(name: str, entry: dict[str, Any]) -> Finding | None:
    env = entry.get("env")
    if not isinstance(env, dict):
        return None
    for key, value in env.items():
        if isinstance(value, str) and (_HOST_CRED_RE.search(key) or _HOST_CRED_RE.search(value)):
            return Finding(
                "MCP-105",
                Severity.HIGH,
                f"[{name}] MCP 配置透传高敏宿主凭据(env.{key})给 MCP 服务器",
                f"::server:{name}",
                "最小化凭据面: 只透传该服务器真正需要的变量; SSH agent socket 等尤其敏感",
            )
    return None


def _check_unpinned_package(name: str, entry: dict[str, Any]) -> Finding | None:
    command = entry.get("command")
    if not isinstance(command, str):
        return None
    base = command.strip().rsplit("/", 1)[-1]
    args = entry.get("args")
    args = [a for a in args if isinstance(a, str)] if isinstance(args, list) else []
    if base in _UNPINNED_PACKAGER and args and not any("@" in a or "==" in a for a in args):
        return Finding(
            "MCP-106",
            Severity.MEDIUM,
            f"[{name}] MCP 服务器用 {base} 拉取未固定版本的包(供应链可变性, OWASP LLM03)",
            f"::server:{name}",
            "固定版本(如 pkg@1.2.3)或改用本地安装的可执行文件",
        )
    return None


def _check_route_delegation(name: str, entry: dict[str, Any]) -> Finding | None:
    for key in entry:
        if _ROUTE_KEY_RE.match(str(key)):
            return Finding(
                "MCP-107",
                Severity.MEDIUM,
                f"[{name}] MCP 配置含链式路由/委托字段 '{key}'(信任链延伸, 需审计目标服务器)",
                f"::server:{name}",
                "确认路由目标的信任边界, 对上游服务器单独做 mcp-lint",
            )
    return None


# ---------------------------------------------------------------- rug pull / 隐藏通道 (R227-P2-20)

# 隐藏通道字符: C0 控制符(合法 \t\n\r 排除) / DEL / C1 / Unicode Tags(U+E0000-E007F)。
# ANSI 转义从 ESC(U+001B) 起头, 已含在 C0 段。零宽/BiDi 族(U+200B 等)不入本集 —
# P260/P261 经 security 族过滤已覆盖 description 字段, 双报无价值。
_HIDDEN_CHANNEL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\U000E0000-\U000E007F]")


def _check_hidden_channel(name: str, entry: dict[str, Any]) -> Finding | None:
    """MCP-108: description 含隐藏通道字符(ANSI转义/C1/Unicode Tags, Microsoft 官方点名面)。"""
    desc = entry.get("description")
    if not isinstance(desc, str):
        return None
    m = _HIDDEN_CHANNEL_RE.search(desc)
    if not m:
        return None
    ch = m.group(0)
    return Finding(
        "MCP-108",
        Severity.HIGH,
        f"[{name}] MCP tool description 含隐藏通道字符 U+{ord(ch):X}(C0/ANSI转义/C1/Unicode Tags) — 隐藏=注入通道(OWASP LLM01)",
        f"::server:{name}::description",
        "移除 description 隐藏字符并核查服务器来源是否被篡改; 零宽/BiDi 形态由 P260/P261 覆盖",
        details={"server": name, "char": f"U+{ord(ch):X}"},
    )


def description_fingerprint(desc: str) -> str:
    """已批准基线指纹: description 原文 sha256(纯 stdlib, 确定性)。"""
    return hashlib.sha256(desc.encode("utf-8")).hexdigest()


def fingerprint_servers(text: str) -> dict[str, str]:
    """从单个 MCP 配置提取 {server名: description_sha256}(--baseline-out 基线生成用)。"""
    cfg = json.loads(text)
    out: dict[str, str] = {}
    for name, entry in _extract_servers(cfg):
        desc = entry.get("description")
        if isinstance(desc, str) and desc.strip():
            out[name] = description_fingerprint(desc)
    return out


def check_description_baseline(name: str, entry: dict[str, Any], baseline: dict[str, str]) -> list[Finding]:
    """MCP-109/110: description 对已批准基线(rug pull 静态检测, opt-in)。

    - 基线内且漂移(含 description 被移除/清空 — 移除本身即篡改形态) → MCP-109 HIGH(rug pull 信号, OWASP LLM03)
    - 有新 description 但不在基线 → MCP-110 MEDIUM(未批准新描述)
    - 不在基线且无 description → 不报(无攻击面)
    """
    findings: list[Finding] = []
    desc = entry.get("description")
    desc = desc if (isinstance(desc, str) and desc.strip()) else None
    if name not in baseline:
        if desc is not None:
            findings.append(
                Finding(
                    "MCP-110",
                    Severity.MEDIUM,
                    f"[{name}] MCP tool description 不在已批准基线内(新/未批准描述) — 审查后用 --baseline-out 批准",
                    f"::server:{name}::description",
                    "确认描述可信后 mcp-lint --baseline-out 重生成批准基线(独立 commit 留痕)",
                    details={"server": name},
                )
            )
        return findings
    if desc is None or description_fingerprint(desc) != baseline[name]:
        findings.append(
            Finding(
                "MCP-109",
                Severity.HIGH,
                f"[{name}] MCP tool description 偏离已批准基线(rug pull 信号: 批准后描述被改, OWASP LLM03)",
                f"::server:{name}::description",
                "排查描述变更来源; 变更合法则 --baseline-out 重生成基线并独立 commit 留痕",
                details={
                    "server": name,
                    "expected_sha256": baseline[name],
                    "actual_sha256": description_fingerprint(desc) if desc is not None else None,
                },
            )
        )
    return findings


_CONFIG_CHECKS = (
    _check_http_plane,
    _check_hardcoded_creds,
    _check_wildcard_perm,
    _check_auto_approve,
    _check_env_passthrough,
    _check_unpinned_package,
    _check_route_delegation,
    _check_hidden_channel,
)


# ---------------------------------------------------------------- 入口

# Description 扫描 = 仅 security 族规则。一行 tool description 的真实威胁面是
# 注入/泄露/凭据索取 — 结构/质量/RAG 类规则对单行文本是品类错配
# (R213 实测: structure 5条恒触发, rag_security 对"搜索/读取"措辞误触发)。
# 误报纪律(0.96%基线)优先于规则覆盖广度。
_DESC_SECURITY_CATEGORIES = frozenset(
    {
        "security",
        "inference_security",
        "agent_security",
        "multimodal_security",
        "supply_chain",
        "arkts_security",
        "federated_security",
        "pii_enhanced",
        "hallucination_security",
        "inference2security",
    }
)
_DESC_RULE_IDS: set[str] | None = None


def _description_rule_ids() -> set[str]:
    """惰性计算 description 扫描适用的规则ID集(security族, 单一事实源=get_all_rules)。"""
    global _DESC_RULE_IDS
    if _DESC_RULE_IDS is None:
        from ai_prompt_toolkit.linter.rules import get_all_rules  # 局部导入防循环引用

        _DESC_RULE_IDS = {r.rule_id for r in get_all_rules() if r.category in _DESC_SECURITY_CATEGORIES}
    return _DESC_RULE_IDS


def scan_mcp_config(
    text: str, source: str = "mcp.json", description_baseline: dict[str, str] | None = None
) -> list[Finding]:
    """扫描单个 MCP 配置: 8 项配置级检查 + 每个 server 的 description 走 security 族规则。

    description 是 tool 的自然语言说明 — 就是 prompt 文本, 走既有规则集
    (不新造检测), 但限 security 族(见 _DESC_SECURITY_CATEGORIES 注释)。
    description_baseline(可选): 已批准描述基线 {server: sha256} — 传入后启用
    rug pull 检测(MCP-109 漂移/MCP-110 未批准)。
    JSON 解析失败抛 json.JSONDecodeError 由调用方处理。
    """
    from ai_prompt_toolkit.linter.rules import run_all_checks  # 局部导入防循环引用

    active = _description_rule_ids()
    cfg = json.loads(text)
    baseline = description_baseline or {}
    findings: list[Finding] = []
    for name, entry in _extract_servers(cfg):
        for check in _CONFIG_CHECKS:
            f = check(name, entry)
            if f:
                findings.append(f)
        if description_baseline is not None:
            findings.extend(check_description_baseline(name, entry, baseline))
        desc = entry.get("description")
        if isinstance(desc, str) and desc.strip():
            for f in run_all_checks(desc):
                if f.rule_id not in active:
                    continue
                findings.append(
                    Finding(
                        f.rule_id,
                        f.severity,
                        f"[{name}] {f.description}",
                        f"::server:{name}::description",
                        f.remediation,
                        details={"server": name},
                    )
                )
    return findings


# ---------------------------------------------------------------- Risk Score

# 与 LintResult.quality_score 同一张权重表(机械派生, 无新公式)
_RISK_WEIGHTS = {"critical": 12.0, "high": 6.0, "medium": 1.0, "low": 0.1, "info": 0.0}
_RISK_BANDS = ((20, "LOW"), (45, "MEDIUM"), (70, "HIGH"))


def compute_risk_score(findings: list[Finding]) -> tuple[int, str]:
    """Risk Score 0-100(越高越危险) + 分档。同规则只计一次(与 quality_score 同口径)。"""
    seen: set[str] = set()
    total = 0.0
    for f in findings:
        if f.rule_id in seen:
            continue
        seen.add(f.rule_id)
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        total += _RISK_WEIGHTS.get(sev, 0.1)
    score = int(min(100.0, total))
    for threshold, band in _RISK_BANDS:
        if score <= threshold:
            return score, band
    return score, "CRITICAL"


# ---------------------------------------------------------------- 文件发现


def discover_mcp_configs(target: str | Path) -> list[Path]:
    """发现 MCP 配置文件: 显式文件直接返回; 目录递归找含 mcpServers/servers 键的 .json。"""
    p = Path(target)
    if p.is_file():
        return [p] if p.suffix == ".json" else []
    if p.is_dir():
        hits: list[Path] = []
        for jf in sorted(p.rglob("*.json")):
            try:
                content = jf.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if any(k in content for k in ("mcpServers", "mcp_servers")) or re.search(
                r"^\s*\{\s*\"servers\"\s*:", content, re.MULTILINE
            ):
                hits.append(jf)
        return hits
    return []
