"""R344-RE-1b 探针测试: 线性化模式 A/B 锚定 + DoS 性能楔子（非 slow, 门禁内实跑）

背景: R343-RE-1 只修了 P108; 本轮实测 linter 规则层另有 19 处无界 `.*` 模式
对「锚点重复、目标缺失」长单行输入挂死/超线性（恶意 PR 塞超长单行 .md 挂死
CI lint 门禁的 DoS 攻击面）→ 统一线性等价重写（linter/linear_scan.py）。

A/B 锚定: 原正则字面量保留在本文件作参照 — 每模式结构用例 + 种子 fuzz 断言
`old.search(t) is not None == new(t)`（铁锚定等价, 消除「锚定开发者理解」缺口;
含大小写/跨行/CRLF/重叠/子串语义面）。

性能楔子: 各模块 runner 200k 最坏单行 <2s（进程内）+ 全量 lint 200k 复合最坏
单行子进程 <45s（修复前挂死 = 红; **非 slow** — 门禁 `pytest -k "not slow"`
实跑, 堵住 R343 主 DoS 回归被 slow 标记排除出门禁的缺口）。
"""

from __future__ import annotations

import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ai_prompt_toolkit.linter.linear_scan import (
    LinearSearch,
    ab_a_wsnum,
    ab_b_ws,
    ab_ws_a,
    line_a_before_b,
    line_alt_a_before_b,
    line_alt_cooccur,
    line_cooccur,
    span_between,
    span_double_brace_var,
    span_triple,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ab(old: re.Pattern, new, toks: list[str]) -> dict:
    return {"old": old, "new": new, "toks": toks}


# (原正则参照, 线性等价实现, fuzz 词表) — 顺序与规则文件改动一一对应
_AB: list[dict] = [
    _ab(
        re.compile(r"必须.*?禁止|禁止.*?必须", re.IGNORECASE),
        lambda t: line_cooccur(t, "必须", "禁止"),
        ["必须", "禁止", "x", "\n", "。"],
    ),
    _ab(
        re.compile(r"always.*?never|never.*?always", re.IGNORECASE),
        lambda t: line_cooccur(t, "always", "never", ci=True),
        ["always", "never", "ALWAYS", "NEVER", "x", "\n"],
    ),
    _ab(
        re.compile(r"简短.*?详细|详细.*?简短", re.IGNORECASE),
        lambda t: line_cooccur(t, "简短", "详细"),
        ["简短", "详细", "x", "\n"],
    ),
    _ab(
        re.compile(r"简洁.*?全面|全面.*?简洁", re.IGNORECASE),
        lambda t: line_cooccur(t, "简洁", "全面"),
        ["简洁", "全面", "x", "\n"],
    ),
    _ab(
        re.compile(r"简短.*?完整|完整.*?简短", re.IGNORECASE),
        lambda t: line_cooccur(t, "简短", "完整"),
        ["简短", "完整", "x", "\n"],
    ),
    _ab(
        re.compile(r"严格.*?灵活|灵活.*?严格", re.IGNORECASE),
        lambda t: line_cooccur(t, "严格", "灵活"),
        ["严格", "灵活", "x", "\n"],
    ),
    _ab(
        re.compile(
            r"(?:concise|brief).*?(?:detailed|comprehensive)|(?:detailed|comprehensive).*?(?:concise|brief)",
            re.IGNORECASE,
        ),
        lambda t: line_alt_cooccur(t, ("concise", "brief"), ("detailed", "comprehensive"), ci=True),
        ["concise", "brief", "detailed", "comprehensive", "CONCISE", "x", "\n"],
    ),
    _ab(
        re.compile(r"首先.*然后", re.IGNORECASE),
        lambda t: line_a_before_b(t, re.compile("首先", re.IGNORECASE), re.compile("然后", re.IGNORECASE)),
        ["首先", "然后", "x", "\n"],
    ),
    _ab(
        re.compile(r"先.*后", re.IGNORECASE),
        lambda t: line_a_before_b(t, re.compile("先", re.IGNORECASE), re.compile("后", re.IGNORECASE)),
        ["先", "后", "x", "\n"],
    ),
    _ab(
        re.compile(r"调用.*API|API.*调用", re.IGNORECASE),
        lambda t: line_alt_cooccur(t, ("调用",), ("api",), ci=True),
        ["调用", "API", "api", "Api", "x", "\n"],
    ),
    _ab(
        re.compile(r"\{\{.*?user.*?\}\}", re.IGNORECASE),
        lambda t: span_triple(t, "{{", "user", "}}", ci=True),
        ["{{", "}}", "user", "USER", "x", "\n"],
    ),
    _ab(
        re.compile(r"<user_input>.*?</user_input>", re.IGNORECASE | re.DOTALL),
        lambda t: span_between(t, "<user_input>", "</user_input>", ci=True, dotall=True),
        ["<user_input>", "</user_input>", "x", "\n"],
    ),
    _ab(re.compile(r"\$\{.*?\}", re.IGNORECASE), lambda t: span_between(t, "${", "}", ci=True), ["${", "}", "x", "\n"]),
    _ab(re.compile(r"\{\{[^#/}].*?\}\}"), span_double_brace_var, ["{{", "}}", "#", "/", "x", "\n"]),
    _ab(re.compile(r"\$\{[^}]+\}"), lambda t: span_between(t, "${", "}", gap=1, dotall=True), ["${", "}", "x", "\n"]),
    _ab(re.compile(r"<%.*?%>"), lambda t: span_between(t, "<%", "%>"), ["<%", "%>", "x", "\n"]),
    _ab(re.compile(r"\{%.*?%\}"), lambda t: span_between(t, "{%", "%}"), ["{%", "%}", "{{%", "x", "\n"]),
    _ab(
        re.compile(r"\$\{.*?input.*?\}", re.IGNORECASE),
        lambda t: span_triple(t, "${", "input", "}", ci=True),
        ["${", "}", "input", "INPUT", "x", "\n"],
    ),
    _ab(
        re.compile(r"(?:删除|支付|发送|转账|delete|payment|send|transfer)\s*.*(?:需|必须|require|must)", re.IGNORECASE),
        lambda t: ab_ws_a(
            t,
            ("删除", "支付", "发送", "转账", "delete", "payment", "send", "transfer"),
            ("需", "必须", "require", "must"),
            ci=True,
        ),
        ["删除", "支付", "delete", "payment", "send", "transfer", "需", "必须", "require", "must", "x", "\n"],
    ),
    _ab(
        re.compile(r"(?:如果.*不包含|如果.*未找到|if.*not\s+(?:found|contain|include))", re.IGNORECASE),
        lambda t: (
            line_a_before_b(t, re.compile("如果", re.IGNORECASE), re.compile("不包含|未找到", re.IGNORECASE))
            or ab_b_ws(t, ("if",), "not", ("found", "contain", "include"), ci=True)
        ),
        ["如果", "不包含", "未找到", "if", "not", "found", "contain", "include", "x", "\n"],
    ),
    _ab(
        re.compile(
            r"(?:当|如果|when|if)\s*.*(?:发生|出现|遇到|occur|happen|encounter|无结果|不可用|失败|fail|unavailable|empty)",
            re.IGNORECASE,
        ),
        lambda t: ab_ws_a(
            t,
            ("当", "如果", "when", "if"),
            (
                "发生",
                "出现",
                "遇到",
                "occur",
                "happen",
                "encounter",
                "无结果",
                "不可用",
                "失败",
                "fail",
                "unavailable",
                "empty",
            ),
            ci=True,
        ),
        ["当", "如果", "when", "if", "发生", "出现", "遇到", "fail", "x", "\n"],
    ),
    _ab(
        re.compile(r"(?:同时|兼具|既是.*又是|both.*and|not\s+only.*but\s+also)", re.IGNORECASE),
        lambda t: (
            bool(re.search(r"同时|兼具", t))
            or line_a_before_b(t, re.compile("既是", re.IGNORECASE), re.compile("又是", re.IGNORECASE))
            or line_a_before_b(t, re.compile("both", re.IGNORECASE), re.compile("and", re.IGNORECASE))
            or line_a_before_b(t, re.compile(r"not\s+only", re.IGNORECASE), re.compile(r"but\s+also", re.IGNORECASE))
        ),
        ["同时", "兼具", "既是", "又是", "both", "and", "not", "only", "but", "also", "x", "\n"],
    ),
    _ab(
        re.compile(r"(?:如果.*失败|失败则|出错则|if.*fail|fallback|降级|跳过|skip)", re.IGNORECASE),
        lambda t: (
            bool(re.search(r"失败则|出错则|fallback|降级|跳过|skip", t, re.IGNORECASE))
            or line_a_before_b(t, re.compile("如果", re.IGNORECASE), re.compile("失败", re.IGNORECASE))
            or line_a_before_b(t, re.compile("if", re.IGNORECASE), re.compile("fail", re.IGNORECASE))
        ),
        ["如果", "失败", "if", "fail", "fallback", "降级", "跳过", "skip", "失败则", "出错则", "x", "\n"],
    ),
    _ab(
        re.compile(r"(?:最近.*轮|仅参考|截断|摘要|summar|truncat|last\s+\d+\s+turn)", re.IGNORECASE),
        lambda t: (
            bool(re.search(r"仅参考|截断|摘要|summar|truncat|last\s+\d+\s+turn", t, re.IGNORECASE))
            or line_a_before_b(t, re.compile("最近", re.IGNORECASE), re.compile("轮", re.IGNORECASE))
        ),
        ["最近", "轮", "仅参考", "截断", "摘要", "summar", "truncat", "last", "5", "turn", "x", "\n"],
    ),
    # 子集吞并验证: 截至.*月 ⊆ 截至（字面量已含, 无界支冗余可删）— fuzz 实证
    _ab(
        re.compile(
            r"(?:截止|截至|cutoff|knowledge\s+cut|截至.*月|更新至|as\s+of|仅依据|仅基于|only\s+based\s+on)",
            re.IGNORECASE,
        ),
        lambda t: bool(
            re.search(
                r"截止|截至|cutoff|knowledge\s+cut|更新至|as\s+of|仅依据|仅基于|only\s+based\s+on", t, re.IGNORECASE
            )
        ),
        [
            "截止",
            "截至",
            "cutoff",
            "knowledge",
            "cut",
            "月",
            "更新至",
            "as",
            "of",
            "仅依据",
            "仅基于",
            "only",
            "based",
            "on",
            "x",
            "\n",
        ],
    ),
    _ab(
        re.compile(
            r"(?:字数|字符|[Tt]oken|段落|篇幅|长度|words?|characters?|tokens?|paragraphs?|length).*?(?:\d+|限制|范围|以内|不超过|至少)",
            re.IGNORECASE,
        ),
        lambda t: line_alt_a_before_b(
            t,
            ("字数", "字符", "token", "段落", "篇幅", "长度", "word", "character", "paragraph", "length"),
            re.compile(r"\d+|限制|范围|以内|不超过|至少", re.IGNORECASE),
            ci=True,
        ),
        [
            "字数",
            "字符",
            "token",
            "TOKEN",
            "段落",
            "篇幅",
            "长度",
            "word",
            "words",
            "123",
            "限制",
            "范围",
            "以内",
            "不超过",
            "至少",
            "x",
            "\n",
        ],
    ),
    _ab(
        re.compile(
            r"(?:不超过|最多|至少|最少|min\s+\d+|max\s+\d+|no\s+more\s+than\s+\d+|at\s+least\s+\d+).*(?:字|词|[Tt]oken|段落|word|token|paragraph|character)",
            re.IGNORECASE,
        ),
        lambda t: ab_a_wsnum(
            t,
            ("不超过", "最多", "至少", "最少"),
            (("min", "num"), ("max", "num"), ("no", "more", "than", "num"), ("at", "least", "num")),
            ("字", "词", "token", "段落", "word", "paragraph", "character"),
            ci=True,
        ),
        [
            "不超过",
            "最多",
            "至少",
            "最少",
            "min",
            "100",
            "max",
            "200",
            "no",
            "more",
            "than",
            "at",
            "least",
            "字",
            "词",
            "token",
            "段落",
            "word",
            "x",
            "\n",
        ],
    ),
    _ab(
        re.compile(
            r"如果.*(?:失败|出错|错误|异常|无法|不确定|不清楚)|if.*(?:fail|error|exception|unable|uncertain)",
            re.IGNORECASE,
        ),
        lambda t: (
            line_a_before_b(
                t,
                re.compile("如果", re.IGNORECASE),
                re.compile(r"失败|出错|错误|异常|无法|不确定|不清楚", re.IGNORECASE),
            )
            or line_a_before_b(
                t, re.compile("if", re.IGNORECASE), re.compile(r"fail|error|exception|unable|uncertain", re.IGNORECASE)
            )
        ),
        [
            "如果",
            "if",
            "失败",
            "出错",
            "错误",
            "异常",
            "无法",
            "不确定",
            "不清楚",
            "fail",
            "error",
            "exception",
            "unable",
            "uncertain",
            "x",
            "\n",
        ],
    ),
    _ab(
        re.compile(r"(?:首先|然后|接着|最后|第一步|第二步|step\s+1|step\s+2|首先.*然后|first.*then)", re.IGNORECASE),
        lambda t: (
            bool(re.search(r"(?:首先|然后|接着|最后|第一步|第二步|step\s+1|step\s+2)", t, re.IGNORECASE))
            or line_a_before_b(t, re.compile("first", re.IGNORECASE), re.compile("then", re.IGNORECASE))
        ),
        ["首先", "然后", "接着", "最后", "第一步", "第二步", "step", "1", "2", "first", "then", "x", "\n"],
    ),
    _ab(
        re.compile(
            r"如果.*(?:失败|出错|错误|异常|无法)|if.*(?:fail|error|exception|unable)|otherwise|否则|回退|fallback",
            re.IGNORECASE,
        ),
        lambda t: (
            bool(re.search(r"otherwise|否则|回退|fallback", t, re.IGNORECASE))
            or line_a_before_b(
                t, re.compile("如果", re.IGNORECASE), re.compile(r"失败|出错|错误|异常|无法", re.IGNORECASE)
            )
            or line_a_before_b(
                t, re.compile("if", re.IGNORECASE), re.compile(r"fail|error|exception|unable", re.IGNORECASE)
            )
        ),
        [
            "如果",
            "if",
            "失败",
            "出错",
            "错误",
            "异常",
            "无法",
            "fail",
            "error",
            "exception",
            "unable",
            "otherwise",
            "否则",
            "回退",
            "fallback",
            "x",
            "\n",
        ],
    ),
]


def _corpus(entry: dict, idx: int) -> list[str]:
    a, b = entry["toks"][0], entry["toks"][1]
    struct = [
        "",
        a,
        b,
        a + b,
        b + a,
        a + "\n" + b,
        a + "\r\n" + b,
        a + " " + b,
        a * 3,
        (a + "\n") * 5,
        a + b + "\n" + a,
    ]
    rng = random.Random(1000 + idx)
    toks = entry["toks"]
    fuzz = []
    for _ in range(300):
        n = rng.randint(0, 35)
        fuzz.append("".join(p + rng.choice(["", " ", "\n"]) for p in (rng.choice(toks) for _ in range(n))))
    return struct + fuzz


@pytest.mark.parametrize("entry, idx", [(e, i) for i, e in enumerate(_AB)], ids=[f"ab-{i}" for i in range(len(_AB))])
def test_re1b_ab_equivalence(entry: dict, idx: int) -> None:
    """A/B 铁锚定: 原正则 vs 线性实现, 结构 + 种子 fuzz 全等价"""
    for t in _corpus(entry, idx):
        old = entry["old"].search(t) is not None
        new = entry["new"](t)
        assert old == new, f"分歧: {t!r} old={old} new={new}"


def _worst(tokens: str, n: int = 200_000) -> str:
    """最坏形态: 锚点重复、目标缺失、单行, 共 n 字符"""
    return (tokens * (n // len(tokens) + 1))[:n]


def test_re1b_p101_p110_bounded() -> None:
    from ai_prompt_toolkit.linter.rules_p101_p110 import run_checks_p101_p110

    t = _worst("必须 简短 严格 首先 先 concise always ")
    t0 = time.perf_counter()
    run_checks_p101_p110(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_p021_p030_bounded() -> None:
    from ai_prompt_toolkit.linter.rules_p021_p030 import run_checks_p021_p030

    t = _worst("字数 如果 {{x ${ <% {{% first 段落 ")
    t0 = time.perf_counter()
    run_checks_p021_p030(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_p031_p040_bounded() -> None:
    from ai_prompt_toolkit.linter.rules_p031_p040 import run_checks_p031_p040

    t = _worst("delete 如果 if ")
    t0 = time.perf_counter()
    run_checks_p031_p040(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_p041_p050_bounded() -> None:
    from ai_prompt_toolkit.linter.rules_p041_p050 import run_checks_p041_p050

    t = _worst("当 if 既是 both not only ")
    t0 = time.perf_counter()
    run_checks_p041_p050(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_p063_p070_bounded() -> None:
    from ai_prompt_toolkit.linter.rules_p063_p070 import run_checks_p063_p070

    t = _worst("如果 if 最近 截至 ")
    t0 = time.perf_counter()
    run_checks_p063_p070(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_fixer_p103_bounded() -> None:
    from ai_prompt_toolkit.linter.fixer import _fix_p103_conflict

    t = _worst("简短 简洁 严格 ")
    t0 = time.perf_counter()
    _fix_p103_conflict(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_rules_user_input_fallback_bounded() -> None:
    from ai_prompt_toolkit.linter import rules as r

    t = _worst("{{ ${ <user_input> 调用 如果 if ")
    t0 = time.perf_counter()
    r.check_p007(t)
    r.check_p010(t)
    assert time.perf_counter() - t0 < 2.0


def test_re1b_full_lint_200k_single_line_bounded(tmp_path: Path) -> None:
    """门禁面 DoS 楔子: 全量 271 规则 × 200k 复合最坏单行, 子进程 60s 护栏内完成
    （修复前 P102/P103/… 灾难性回溯 → 子进程超时 = 红; 非 slow → 门禁实跑）"""
    worst = "必须 简短 严格 首先 先 字数 如果 当 既是 最近 截至 delete if both only first concise always {{x ${ " * 4000
    assert len(worst) > 150_000
    f = tmp_path / "worst.prompt.md"
    f.write_text(worst, encoding="utf-8")
    t0 = time.perf_counter()
    p = subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", "lint", "-t", str(f)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )
    dt = time.perf_counter() - t0
    out = p.stdout + p.stderr
    assert "Traceback" not in out, out[-500:]
    assert dt < 45, f"lint 200k 复合最坏耗时 {dt:.1f}s（修复前挂死）"


def test_re1b_rule_entries_linear_wrapped() -> None:
    """集成锚定: 暴露面模式已换 LinearSearch 包装（有界模式保留 re.Pattern）"""
    from ai_prompt_toolkit.linter import rules as r
    from ai_prompt_toolkit.linter import rules_p021_p030 as p21
    from ai_prompt_toolkit.linter import rules_p031_p040 as p31
    from ai_prompt_toolkit.linter import rules_p041_p050 as p41
    from ai_prompt_toolkit.linter import rules_p063_p070 as p63
    from ai_prompt_toolkit.linter import rules_p101_p110 as p110

    assert isinstance(p110._CONTRADICTION_PATTERNS[0][0], LinearSearch)
    assert isinstance(p110._CONTRADICTION_PATTERNS[1][0], LinearSearch)
    assert isinstance(p110._CONTRADICTION_PATTERNS[2][0], re.Pattern)  # 有界模式未动
    assert all(isinstance(e, LinearSearch) for e, _ in p110._CONFLICT_PATTERNS)
    assert isinstance(p110._TOOL_CHAIN_STRONG, LinearSearch)
    assert isinstance(p110._TOOL_CHAIN_WEAK, LinearSearch)
    assert isinstance(r._FALLBACK_CTX, LinearSearch)
    assert isinstance(r._USER_INPUT_PATTERNS[0], LinearSearch)
    assert isinstance(r._USER_INPUT_PATTERNS[1], re.Pattern)  # {user_input} 字面量未动
    assert isinstance(p21._P022_PATTERNS[0], LinearSearch)
    assert isinstance(p21._P022_PATTERNS[4], re.Pattern)  # import{ 有界未动
    assert isinstance(p21._P025_LENGTH_PATTERNS[0], LinearSearch)
    assert isinstance(p21._P026_FALLBACK_PATTERNS[0], LinearSearch)
    assert isinstance(p21._P028_MULTI_STEP, LinearSearch)
    assert isinstance(p21._P029_USER_INPUT[0], LinearSearch)
    assert isinstance(p31._AGENT_APPROVAL_PATTERNS[1], LinearSearch)
    assert isinstance(p31._RAG_HALLUCINATION_PATTERNS[1], LinearSearch)
    assert isinstance(p41._H2_CONSTRAINT_SCAFFOLD_PATTERNS[0], LinearSearch)
    assert isinstance(p41._H7_MULTI_ROLE_CONFLICT_PATTERNS[0], LinearSearch)
    assert isinstance(p63._CHAIN_ERROR_ISOLATION, LinearSearch)
    assert isinstance(p63._CONTEXT_LIMIT, LinearSearch)
    # _CUTOFF_PATTERN: 截至.*月 支被 截至 字面量吞并 → 纯安全正则即可
    assert isinstance(p63._CUTOFF_PATTERN, re.Pattern)


def test_re1b_fixer_p103_behavior_preserved() -> None:
    from ai_prompt_toolkit.linter.fixer import _fix_p103_conflict

    out = _fix_p103_conflict("输出要简短 但又要详细")
    assert "详细" in out and "冲突约束说明" in out
    out2 = _fix_p103_conflict("要求简洁且全面")
    assert "全面" in out2 and "冲突约束说明" in out2
    assert _fix_p103_conflict("没有冲突词") == "没有冲突词"


def test_re1b_finditer_equivalence() -> None:
    """finditer A/B: span 系列包装 vs 原正则 — 全匹配序列（group(0), 非重叠）等价"""
    from ai_prompt_toolkit.linter import rules as r
    from ai_prompt_toolkit.linter import rules_p021_p030 as p21

    cases = [
        (re.compile(r"\{\{.*?user.*?\}\}", re.IGNORECASE), r._USER_INPUT_PATTERNS[0]),
        (re.compile(r"<user_input>.*?</user_input>", re.IGNORECASE | re.DOTALL), r._USER_INPUT_PATTERNS[2]),
        (re.compile(r"\$\{.*?\}", re.IGNORECASE), r._USER_INPUT_PATTERNS[3]),
        (re.compile(r"\{\{[^#/}].*?\}\}"), p21._P022_PATTERNS[0]),
        (re.compile(r"\$\{[^}]+\}"), p21._P022_PATTERNS[1]),
        (re.compile(r"<%.*?%>"), p21._P022_PATTERNS[2]),
        (re.compile(r"\{%.*?%\}"), p21._P022_PATTERNS[3]),
        (re.compile(r"\$\{.*?input.*?\}", re.IGNORECASE), p21._P029_USER_INPUT[2]),
    ]
    toks = [
        "{{",
        "}}",
        "${",
        "}",
        "<%",
        "%>",
        "{{%",
        "{%",
        "%}",
        "user",
        "USER",
        "input",
        "<user_input>",
        "</user_input>",
        "x",
        "\n",
        "。",
        "#",
        "/",
    ]
    rng = random.Random(42)
    for old, new in cases:
        corpus = [
            "",
            "{{user}}",
            "${a}${b}",
            "<%x%>",
            "{{a}}{{b}}",
            "<user_input>1</user_input>z</user_input>",
            "{{user}}\nmore",
            "x",
            "{{#bad}}",
            "${}",
        ]
        for _ in range(120):
            corpus.append("".join(rng.choice(toks) for _ in range(rng.randint(0, 20))))
        for t in corpus:
            old_g = [m.group(0) for m in old.finditer(t)]
            new_g = [m.group(0) for m in new.finditer(t)]
            assert old_g == new_g, f"finditer 分歧: {t!r} old={old_g} new={new_g}"


def test_re1b_finditer_consumers_behavior() -> None:
    """消费点行为保持: check_p022/p029/p007 的 finditer+group(0) 路径"""
    from ai_prompt_toolkit.linter import rules as r
    from ai_prompt_toolkit.linter import rules_p021_p030 as p21

    f = p21.check_p022("你好 {{user_name}} 再见")
    assert f is not None and "{{user_name}}" in str(f.details["matches"])
    assert p21.check_p022("没有模板变量") is None
    assert p21.check_p022("```\n{{x}}\n```") is None  # R179 代码块剥离仍生效
    f2 = r.check_p007("输入 <user_input>你好</user_input>")
    assert f2 is not None
    f3 = p21.check_p029("使用 ${user_input} 占位")
    assert f3 is not None
    assert p21.check_p029("无占位符") is None
