"""R212: CLI python -m 入口真bug回归测试

R212-1: `python -m ai_prompt_toolkit.cli_core` 原只显示3/68条命令
(__main__守卫在命令簇import之前执行, 且命令簇导包加载第二模块实例)。
修复后 -m 两种形式均须暴露完整命令集, 与prompt-cli一致。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _help_commands(module: str) -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )
    assert proc.returncode == 0, f"{module} --help 失败: {proc.stderr[:300]}"
    # 帮助输出 "Commands:" 段落下每条命令两空格开头
    m = re.search(r"Commands:\n(.*?)(?:\n\n|$)", proc.stdout, re.DOTALL)
    assert m, f"{module} 帮助缺少Commands段"
    return re.findall(r"^  (\S+)", m.group(1), re.MULTILINE)


def test_cli_core_module_help_full_commands():
    """cli_core直跑: 命令数与导入式main一致(≥50), 关键命令簇齐全"""
    cmds = _help_commands("ai_prompt_toolkit.cli_core")
    assert len(cmds) >= 50, f"cli_core -m 命令数仅{len(cmds)}: {cmds[:10]}..."
    for expected in ("lint", "scan", "score", "compile", "probe", "playground"):
        assert expected in cmds, f"关键命令 {expected} 缺失, 实际: {cmds}"


def test_package_module_help_full_commands():
    """python -m ai_prompt_toolkit (包入口) 命令数齐全"""
    cmds = _help_commands("ai_prompt_toolkit")
    assert len(cmds) >= 50, f"包 -m 命令数仅{len(cmds)}"
    assert "lint" in cmds


def test_both_module_forms_consistent():
    """两种 -m 形式暴露同一命令集(双main group已消除)"""
    a = set(_help_commands("ai_prompt_toolkit"))
    b = set(_help_commands("ai_prompt_toolkit.cli_core"))
    assert a == b, f"命令集不一致: 仅包入口有{a - b}, 仅cli_core有{b - a}"


def test_entry_commands_registered_once():
    """导入式main: 命令数与CLI入口一致(67级), 无重复注册"""
    from ai_prompt_toolkit.cli_core import main

    cmds = sorted(main.commands.keys())
    assert len(cmds) >= 50
    assert len(set(cmds)) == len(cmds)
