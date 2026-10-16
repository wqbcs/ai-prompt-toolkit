"""P1-14: AI 编码助手 UserPromptSubmit hook — prompt 质量 preflight

分发渠道调研(2026-10 实搜, docs/planning/12 §1.4): 2026 新形态是把 prompt
质量检查挂进 AI 编码助手的 UserPromptSubmit hook（Codex/Claude Code 类），
在"人写给模型的 prompt"提交前拦截。Claude Code 与 Codex 的 hook 输入格式
兼容（stdin 收 JSON, 含 `prompt` 字段; exit 2 = 阻断）——**一个通用脚本
覆盖两端**（奥卡姆: 3 个近似脚本=漂移源, 1 个通用+两份配置片段=同一真源）。

边界纪律（T9, 反清单红线）: 这是**质量 preflight**, 不是 CI 安全门禁——
- 分文档: docs/prompt-preflight-hook.md
- 语义隔离: 只做人→模型 prompt 的提交前提示, 不覆盖仓库→CI 面
- 零内核改动: 复用 lint_template 内核(与 lint -s 同一真源, 确定性不变)
- 零 LLM: 纯正则规则执行, 楔子完整

fail-open 契约(与 CI 门禁的 fail-closed 相反, 刻意设计):
hook 是体验层不是安全层(安全层=CI gate)。hook 自身任何异常 → exit 0 放行,
绝不让"门禁工具故障"阻断用户的 AI 助手会话(可用性 > 单点提示)。
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_prompt_toolkit.types import Finding

DEFAULT_FAIL_SEVERITY = "high"  # critical+high 阻断; medium/low 只提示


def extract_prompt(raw: str) -> str:
    """从 hook stdin 提取 prompt 文本。

    Claude Code/Codex UserPromptSubmit 输入: 完整 JSON(含 prompt 字段)。
    宽容回退: 非 JSON(用户手工管道 `echo text | hook`) → 原文即 prompt。
    """
    raw = raw.strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            p = data.get("prompt")
            if isinstance(p, str):
                return p
    except json.JSONDecodeError:
        pass
    return raw


def run_preflight(prompt_text: str, fail_severity: str, nudge: bool) -> tuple[int, str]:
    """执行 preflight, 返回 (exit_code, stdout_payload)

    exit 2 + JSON decision:block = 阻断(Claude Code/Codex 均认)
    exit 0 + 纯文本 = 放行(文本作为上下文注入, 助手可见可忽略)
    exit 0 + 空 = 干净放行
    """
    from ai_prompt_toolkit.linter import lint_template

    def _sev(f: Finding) -> str:
        """Severity 枚举 → 值字符串(枚举值即 'critical'/'high'/... 小写)"""
        v = getattr(f.severity, "value", f.severity)
        return str(v).lower()

    result = lint_template("user-prompt", prompt_text, fix=False, apply_waivers=True)
    findings = result.findings
    if not findings:
        return 0, ""

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    # fail_severity="none" = 永不阻断(只提示); 其他值=该级及以上阻断
    if fail_severity == "none":
        blocking = []
    else:
        fail_rank = rank.get(fail_severity, 1)
        blocking = [f for f in findings if rank.get(_sev(f), 9) <= fail_rank]
    lines = [f"[{_sev(f).upper()}] {f.rule_id}: {f.description}" for f in findings]

    if blocking and not nudge:
        reason = "prompt preflight 拦截(质量门禁): " + "; ".join(lines[:5])
        if len(lines) > 5:
            reason += f" (+{len(lines) - 5} 条)"
        payload = json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "完整发现:\n" + "\n".join(lines),
                },
            },
            ensure_ascii=False,
        )
        return 2, payload

    # nudge 模式 / 仅 medium/low: 放行+提示(纯文本 stdout = 助手上下文)
    return 0, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    nudge = "--nudge" in argv
    fail_severity = DEFAULT_FAIL_SEVERITY
    env = os.environ.get("PROMPT_PREFLIGHT_SEVERITY", "").strip().lower()
    if env in ("critical", "high", "medium", "low", "none"):
        fail_severity = env  # "none"=永不阻断, run_preflight 内显式处理

    try:
        prompt_text = extract_prompt(sys.stdin.read())
        if not prompt_text.strip():
            return 0
        code, payload = run_preflight(prompt_text, fail_severity, nudge)
        if payload:
            sys.stdout.write(payload + "\n")
            sys.stdout.flush()
        return code
    except Exception as e:
        sys.stderr.write(f"prompt-preflight hook 故障(fail-open 放行): {type(e).__name__}: {e}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
