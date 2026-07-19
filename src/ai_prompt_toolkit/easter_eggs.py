"""情感化彩蛋功能 — P3-06

体验鬼才哲学: "最好的体验是用户感觉不到体验"
- 里程碑庆祝: Lint满分/红队0漏洞/评估9分+
- 彩蛋触发: 特殊命令/时间彩蛋/隐藏功能
- 进度激励: 连续使用天数/总Lint次数/修复问题数
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_MILESTONE_MESSAGES = {
    "lint_perfect": [
        "Lint满分! 你的Prompt写得太漂亮了，像诗一样工整。",
        "100分! 这份Prompt值得被装裱在博物馆里。",
        "完美Lint! 仿佛看到了Prompt界的蒙娜丽莎。",
    ],
    "redteam_safe": [
        "0漏洞! 你的Prompt比银行金库还安全。",
        "红队全军覆没! 这防御力堪比华为云安全。",
        "无懈可击! 黑客看了都要转行。",
    ],
    "eval_excellent": [
        "评估9分+! 你的Prompt已经是行业标杆了。",
        "优秀! 这份Prompt可以直接上生产环境。",
        "超高分! 其他Prompt都在向你学习。",
    ],
    "first_lint": [
        "欢迎来到Prompt质量世界! 你已经迈出了关键第一步。",
    ],
    "first_fix": [
        "第一个修复! 每个优秀的Prompt都从修复开始。",
    ],
    "streak_7": [
        "连续7天使用! 坚持就是胜利，你已经是Prompt达人了。",
    ],
    "streak_30": [
        "连续30天! 你是真正的Prompt匠人。",
    ],
    "fix_100": [
        "修复100个问题! 你的Prompt修炼已臻化境。",
    ],
}


_TIME_BASED_EGGS = {
    "new_year": (1, 1, "新年快乐! 新的一年，Prompt质量更上一层楼!"),
    "spring_festival": (1, 22, "春节快乐! 愿你的Prompt如春联般工整!"),
    "mid_autumn": (9, 29, "中秋快乐! 月圆Prompt更圆!"),
    "national_day": (10, 1, "国庆快乐! 为国产AI生态贡献力量!"),
    "programmers_day": (10, 24, "程序员节快乐! 1024行代码，1024分Prompt!"),
    "christmas": (12, 25, "Merry Christmas! 愿你的Prompt如圣诞树般完美!"),
}


_HIDEN_COMMANDS = {
    "prompt-cli easter-egg": "你发现了彩蛋! 体验鬼才为你点赞!",
    "prompt-cli version --verbose": "版本详情(含隐藏的commit hash)",
    "prompt-cli lint --celebrate": "在Lint结束时显示庆祝动画",
}


@dataclass
class UserProgress:
    total_lints: int = 0
    total_fixes: int = 0
    total_evals: int = 0
    total_redteams: int = 0
    streak_days: int = 0
    perfect_lints: int = 0
    safe_redteams: int = 0
    excellent_evals: int = 0


def check_milestone(progress: UserProgress, event: str, score: float = 0.0) -> str | None:
    if event == "lint" and score == 100.0:
        progress.perfect_lints += 1
        if progress.perfect_lints == 1:
            return _pick_message("lint_perfect")
    elif event == "redteam" and score == 100.0:
        progress.safe_redteams += 1
        if progress.safe_redteams == 1:
            return _pick_message("redteam_safe")
    elif event == "evaluate" and score >= 9.0:
        progress.excellent_evals += 1
        if progress.excellent_evals == 1:
            return _pick_message("eval_excellent")
    elif event == "first_lint" and progress.total_lints == 1:
        return _pick_message("first_lint")
    elif event == "first_fix" and progress.total_fixes == 1:
        return _pick_message("first_fix")
    elif progress.streak_days == 7:
        return _pick_message("streak_7")
    elif progress.streak_days == 30:
        return _pick_message("streak_30")
    elif progress.total_fixes == 100:
        return _pick_message("fix_100")
    return None


def check_time_egg() -> str | None:
    now = time.localtime()
    month, day = now.tm_mon, now.tm_mday
    for key, (m, d, msg) in _TIME_BASED_EGGS.items():
        if month == m and day == d:
            return msg
    return None


def get_motivational_quote() -> str:
    quotes = [
        "好的Prompt是写出来的，更是改出来的。",
        "每个被Lint发现的问题，都是进步的机会。",
        "Prompt工程师：让AI听懂人类的语言。",
        "安全不是终点，而是持续的旅程。",
        "简洁是最终的复杂。 — 达芬奇",
        "代码写得好不好，Prompt说了算。",
        "今天的100分，是明天改进的起点。",
        "最好的Prompt，是用户感觉不到的Prompt。",
    ]
    return random.choice(quotes)


def _pick_message(category: str) -> str:
    messages = _MILESTONE_MESSAGES.get(category, ["恭喜!"])
    return random.choice(messages)


def format_celebration(message: str) -> str:
    border = "=" * 50
    return f"\n{border}\n  {message}\n{border}\n"


_WELCOME_ASCII = r"""
  ___  _   _    ___  _  ___  ___ ___ ___
 / _ \| \ | |  / _ \| |/ / |/ __/ __| _ \
| (_) |  \| | | (_) | ' <| | (__\__ \   /
 \___/|_|\__|  \___/|_|\_\_|\___|___/_|_\
"""

_FIRST_RUN_TIPS = [
    "快速开始: prompt-cli lint -s your-prompt.md",
    "安全扫描: prompt-cli scan -s your-prompt.md",
    "交互向导: prompt-cli wizard",
    "质量评估: prompt-cli evaluate -t your-prompt.md",
    "查看帮助: prompt-cli --help",
]


def is_first_run() -> bool:
    marker = Path.home() / ".ai-prompt-toolkit" / ".initialized"
    if marker.exists():
        return False
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(time.time()), encoding="utf-8")
    return True


def show_welcome() -> None:
    from ai_prompt_toolkit.output import console
    console.print(_WELCOME_ASCII, style="bold blue")
    console.print("\n  欢迎使用 AI Prompt Toolkit!", style="bold")
    console.print("  你的AI提示词质量工具链，让Prompt更安全、更优质。\n", style="dim")
    console.print("  快速上手:", style="bold")
    for tip in _FIRST_RUN_TIPS:
        console.print(f"    {tip}", style="cyan")
    time_egg = check_time_egg()
    if time_egg:
        console.print(f"\n  {time_egg}", style="bold yellow")
