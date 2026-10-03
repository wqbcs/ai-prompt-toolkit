"""R226-P1-14: AI 编码助手 UserPromptSubmit hook(preflight)回归测试

边界纪律(T9): 质量 preflight 与 CI 安全门禁语义隔离——
- fail-open 契约: hook 自身故障 exit 0 放行(体验层不阻断用户会话)
- 阻断语义: critical/high finding → exit 2 + decision:block JSON
- nudge 模式: 永不阻断, 只注入提示上下文
- 格式兼容: Claude Code / Codex 的 UserPromptSubmit 输入均为
  stdin JSON(含 prompt 字段) + exit 2 阻断(2026-10 实搜核实)
"""

from __future__ import annotations

import json
import subprocess
import sys

from ai_prompt_toolkit.cli.preflight_hook import extract_prompt, run_preflight

# 触发 critical 的正样本(P161 未声明注入防护 + P022 模板注入标记)
_ATTACK = "模板渲染引擎处理 {{user_input}} 变量，无转义。"
# 干净英文 prompt(角色/格式/约束/长度齐全)
_CLEAN = (
    "You are a senior software engineer. Please summarize the following "
    "document. Output as JSON with keys 'title' and 'summary'. Keep it under "
    "200 words. Do not invent facts not present in the source."
)


def _run_hook(stdin_text: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", "--preflight-hook", *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


class TestExtractPrompt:
    def test_json_input_extracts_prompt_field(self):
        assert extract_prompt('{"prompt": "hello"}') == "hello"

    def test_json_without_prompt_field_falls_back_to_raw(self):
        # 非 UserPromptSubmit 形状(如 PreToolUse) → 原文回退(fail-open 语义)
        raw = '{"tool": "Bash"}'
        assert extract_prompt(raw) == raw

    def test_plain_text_fallback(self):
        assert extract_prompt("plain text prompt") == "plain text prompt"

    def test_empty(self):
        assert extract_prompt("") == ""
        assert extract_prompt("   \n") == ""


class TestRunPreflightDirect:
    """run_preflight 直调(不 spawn 进程, 快)"""

    def test_attack_blocked_by_default(self):
        code, payload = run_preflight(_ATTACK, "high", nudge=False)
        assert code == 2
        data = json.loads(payload)
        assert data["decision"] == "block"
        # reason 只带前5条(防长提示), P022(critical)在其内; P161 在 additionalContext 全文
        assert "P022" in data["reason"]
        assert "P161" in data["hookSpecificOutput"]["additionalContext"]

    def test_nudge_never_blocks(self):
        code, payload = run_preflight(_ATTACK, "high", nudge=True)
        assert code == 0
        assert payload  # 提示仍注入(纯文本)

    def test_severity_low_still_blocks_critical(self):
        # low 阈值 = rank 3, critical(0)/high(1)/medium(2) 均 ≤3 → 仍阻断
        code, _ = run_preflight(_ATTACK, "low", nudge=False)
        assert code == 2

    def test_severity_none_never_blocks(self):
        # none = 永不阻断(只提示)
        code, payload = run_preflight(_ATTACK, "none", nudge=False)
        assert code == 0
        assert payload  # 提示仍注入

    def test_clean_prompt_passes(self):
        code, _payload = run_preflight(_CLEAN, "high", nudge=False)
        assert code == 0

    def test_block_payload_has_hook_specific_output(self):
        _, payload = run_preflight(_ATTACK, "high", nudge=False)
        data = json.loads(payload)
        assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "additionalContext" in data["hookSpecificOutput"]


class TestPreflightHookE2E:
    """真子进程 e2e(hook 的部署形态就是被 AI 助手 spawn 的独立进程)"""

    def test_block_exit_2_with_json(self):
        p = _run_hook(json.dumps({"prompt": _ATTACK}, ensure_ascii=False))
        assert p.returncode == 2, p.stderr
        data = json.loads(p.stdout)
        assert data["decision"] == "block"

    def test_clean_exit_0(self):
        p = _run_hook(json.dumps({"prompt": _CLEAN}, ensure_ascii=False))
        assert p.returncode == 0, p.stderr

    def test_nudge_mode_exit_0(self):
        p = _run_hook(json.dumps({"prompt": _ATTACK}, ensure_ascii=False), "--nudge")
        assert p.returncode == 0, p.stderr
        assert p.stdout.strip()  # 提示文本注入

    def test_empty_prompt_silent_pass(self):
        p = _run_hook(json.dumps({"prompt": ""}))
        assert p.returncode == 0
        assert p.stdout.strip() == ""

    def test_malformed_input_fail_open(self):
        """fail-open 契约: 非 JSON 垃圾输入不崩溃(回退原文为 prompt, 不抛)"""
        p = _run_hook("\x00\x01not json at all")
        assert p.returncode in (0, 2)  # 0=回退后无阻断级发现, 2=回退后有
        assert "Traceback" not in p.stderr

    def test_env_severity_override(self):
        p = subprocess.run(
            [sys.executable, "-m", "ai_prompt_toolkit", "--preflight-hook"],
            input=json.dumps({"prompt": _ATTACK}, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            env={**__import__("os").environ, "PROMPT_PREFLIGHT_SEVERITY": "none"},
        )
        # severity=none → 阈值 lowest(critical 也放行)
        assert p.returncode == 0, p.stderr
