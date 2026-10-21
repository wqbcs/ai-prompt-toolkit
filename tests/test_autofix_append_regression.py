"""R335-P0-AV02：追加型 Auto-fix 文本损坏回归测试。

对应 v0.2 任务书 Phase 2 的 8 类场景。全部打在真实实现上：

- `PromptLinter._get_fix_action`（修复动作生成，`lint(fix=True)` 的实际分支）
- `PromptLinter._apply_fixes`（修复执行，CLI `--fix` 与 LSP/explainer 共用）
- `ai_prompt_toolkit.linter.linter.apply_fix_action`（单个动作的执行器）

历史缺陷（v0.1 复现）：`original=text[-30:]` 配 `replacement=text + 后缀`，
经 `str.replace(original, replacement, 1)` 后得到 `text[:-30] + text + 后缀`，
即把"追加"表达成"替换"，导致原文被复制一份，且每条追加规则再翻一倍
（pangu-multimodal.md 1445 → 1,483,243 字符）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_prompt_toolkit.linter.auto_fix_verification import AutoFixVerifier, VerificationStatus
from ai_prompt_toolkit.linter.linter import FixAction, PromptLinter, apply_fix_action
from ai_prompt_toolkit.types import Finding, Severity

_TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "ai_prompt_toolkit" / "templates"

# 追加型修复规则：P005（前置最低内容要求）+ P025/P026/P029 + _AUTO_APPEND 表
APPEND_RULES = [
    "P005",
    "P025",
    "P026",
    "P029",
    "P131",
    "P132",
    "P135",
    "P140",
    "P175",
]

# 一段普通中文 Prompt（长度 < 50，可触发 P005 的短文本分支）
BASE = "你是一个专业的客服助手，请按照以下要求回答用户提出的问题，语气友好。"


def _finding(rule_id: str) -> Finding:
    return Finding(rule_id=rule_id, severity=Severity.MEDIUM, description=f"{rule_id} 回归测试")


# ── 1. 追加型修复只保留一份原文 ──────────────────────────────────────────


@pytest.mark.parametrize("rule_id", APPEND_RULES)
def test_append_rule_declares_append_semantics(rule_id: str) -> None:
    """追加型动作必须显式声明追加语义，而不是伪装成替换。"""
    action = PromptLinter()._get_fix_action(_finding(rule_id), BASE)
    assert action is not None
    assert action.append is True
    # 追加语义下 replacement 只是待追加后缀，不能包含整篇原文
    assert not action.replacement.startswith(BASE)


@pytest.mark.parametrize("rule_id", APPEND_RULES)
def test_append_keeps_single_copy_of_original(rule_id: str) -> None:
    """修复后原文只出现一次，长度增量等于后缀长度。"""
    linter = PromptLinter()
    action = linter._get_fix_action(_finding(rule_id), BASE)
    assert action is not None

    fixed, applied = linter._apply_fixes(BASE, [_finding(rule_id)])

    assert [f.rule_id for f in applied] == [rule_id]
    assert fixed.startswith(BASE)
    assert fixed.count(BASE) == 1, f"{rule_id} 复制了原文：出现 {fixed.count(BASE)} 次"
    assert len(fixed) == len(BASE) + len(action.replacement)


# ── 2. 追加内容正确出现，且不覆盖/丢失原文其它部分 ────────────────────────


def test_append_keeps_every_original_line() -> None:
    """多行原文的每一行都必须保留，追加内容出现在末尾。"""
    linter = PromptLinter()
    text = "第一行：你是客服助手。\n第二行：回答要简洁。\n第三行：不要编造事实。"
    action = linter._get_fix_action(_finding("P026"), text)
    assert action is not None

    fixed, _ = linter._apply_fixes(text, [_finding("P026")])

    for line in text.splitlines():
        assert line in fixed
    assert fixed.startswith(text)
    assert fixed.endswith(action.replacement)
    assert len(fixed) == len(text) + len(action.replacement)


def test_multiple_append_rules_do_not_compound() -> None:
    """多条追加规则叠加时不得指数膨胀（原缺陷每命中一条就翻倍）。"""
    linter = PromptLinter()
    rule_ids = ["P025", "P131", "P132", "P135"]
    findings = [_finding(r) for r in rule_ids]

    fixed, applied = linter._apply_fixes(BASE, findings)

    assert [f.rule_id for f in applied] == rule_ids
    assert fixed.count(BASE) == 1
    assert fixed.count(BASE) * 4 < len(fixed) < len(BASE) + 4 * 200


# ── 3. 锚点缺失/不适用时不得静默破坏文本 ─────────────────────────────────


def test_missing_anchor_is_noop() -> None:
    """替换型动作锚点不存在时返回原文，不得插入或截断。"""
    action = FixAction(
        rule_id="P999",
        original="这段文字不在原文里",
        replacement="替换内容",
        description="锚点缺失用例",
    )
    text = "原文内容，保持不变。"
    assert apply_fix_action(text, action) == text


def test_empty_anchor_is_noop() -> None:
    """替换型动作空锚点会匹配到位置 0，必须拦截为无操作。"""
    action = FixAction(rule_id="P999", original="", replacement="X", description="空锚点用例")
    text = "原文"
    assert apply_fix_action(text, action) == text


def test_replace_action_without_match_is_not_reported_as_fixed() -> None:
    """锚点缺失时不得记为"已修复"（原实现无条件 append 到 fixed）。"""
    linter = PromptLinter()
    # P016 只在文本中存在歧义词时才产出动作；这里文本无歧义词 → 无动作
    text = "请严格按照规范输出结果。"
    action = linter._get_fix_action(_finding("P016"), text)
    assert action is None

    fixed, applied = linter._apply_fixes(text, [_finding("P016")])
    assert fixed == text
    assert applied == []


# ── 4. 普通替换型修复仍然正确 ────────────────────────────────────────────


def test_replace_mode_p016_still_works() -> None:
    """歧义词替换：命中词被替换，长度按词长变化，不复制原文。"""
    linter = PromptLinter()
    text = "这可能大概也许是正确的结果"
    fixed, applied = linter._apply_fixes(text, [_finding("P016")])

    assert [f.rule_id for f in applied] == ["P016"]
    assert "可能" not in fixed
    assert fixed.count(text) == 0
    assert len(fixed) == len(text) - len("可能") + len("需要")


def test_replace_mode_p006_redaction_still_works() -> None:
    """敏感信息遮蔽：原文片段消失，标记出现，且不复制原文。

    注：P006 的 `\\S+` 会把密钥后的中文一并吞掉（`api_key=***REDACTED***` 后
    "连接服务"丢失）。这是替换型修复的另一个独立缺陷，不属于 v0.2 追加型损坏范围，
    已登记在交付报告"未解决问题"一节，此处只保证本任务不改变遮蔽的主要语义。
    """
    linter = PromptLinter()
    text = "使用api_key=sk-1234567890abcdef连接服务"
    fixed, applied = linter._apply_fixes(text, [_finding("P006")])

    assert [f.rule_id for f in applied] == ["P006"]
    assert "sk-1234567890abcdef" not in fixed
    assert "***REDACTED***" in fixed
    assert fixed.startswith("使用")
    assert fixed.count(text) == 0
    assert len(fixed) < len(text)


# ── 5. 中文、Unicode、多行、不同换行符 ───────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "第一段😀\r\n第二段中文\r\n第三段结尾",  # CRLF + emoji
        "第一行\n第二行\n第三行",  # LF
        "只有一行中文，没有换行符。",
        "混合 English 与中文 with spaces 以及 emoji 🚀 结尾",
    ],
)
def test_append_handles_unicode_and_newlines(text: str) -> None:
    linter = PromptLinter()
    action = linter._get_fix_action(_finding("P025"), text)
    assert action is not None

    fixed, _ = linter._apply_fixes(text, [_finding("P025")])

    assert fixed.startswith(text)
    assert fixed.count(text) == 1
    assert len(fixed) == len(text) + len(action.replacement)


# ── 6. 重复执行的行为符合明确设计（追加型 = 幂等） ───────────────────────


@pytest.mark.parametrize("rule_id", ["P005", "P025", "P131"])
def test_append_second_run_is_idempotent(rule_id: str) -> None:
    """追加后缀已存在时不得重复追加。"""
    linter = PromptLinter()
    once, applied_first = linter._apply_fixes(BASE, [_finding(rule_id)])
    assert applied_first

    twice, applied_second = linter._apply_fixes(once, [_finding(rule_id)])

    assert twice == once
    assert applied_second == []


def test_append_five_runs_stay_stable() -> None:
    """连续 5 次执行后长度稳定（原实现每次翻倍）。"""
    linter = PromptLinter()
    current = BASE
    lengths = []
    for _ in range(5):
        current, _ = linter._apply_fixes(current, [_finding("P025")])
        lengths.append(len(current))

    assert len(set(lengths[1:])) == 1, f"长度未收敛: {lengths}"
    assert lengths[-1] < 2 * len(BASE)


# ── 7. 边界情况：空文本、短文本、尾部不足 30 字符 ───────────────────────


@pytest.mark.parametrize("text", ["", "短", "刚好不到三十个字符的一段话", "x" * 29, "x" * 30])
def test_append_on_short_or_empty_text(text: str) -> None:
    """短文本/空文本也必须只追加一次，不能依赖固定长度锚点。"""
    linter = PromptLinter()
    action = linter._get_fix_action(_finding("P025"), text)
    assert action is not None

    fixed, applied = linter._apply_fixes(text, [_finding("P025")])

    assert [f.rule_id for f in applied] == ["P025"]
    assert fixed == text + action.replacement


def test_append_on_long_text_does_not_use_tail_anchor() -> None:
    """长文本（> 30 字符）的追加增量必须与文本长度无关。"""
    linter = PromptLinter()
    short = "短文本指令。"
    long = "长文本指令。" * 40
    action_short = linter._get_fix_action(_finding("P025"), short)
    action_long = linter._get_fix_action(_finding("P025"), long)
    assert action_short is not None and action_long is not None
    assert action_short.replacement == action_long.replacement

    fixed_long, _ = linter._apply_fixes(long, [_finding("P025")])
    assert len(fixed_long) == len(long) + len(action_long.replacement)


# ── 8. 长度/内容与验证状态之间不存在矛盾 ────────────────────────────────


def test_template_autofix_does_not_duplicate_text() -> None:
    """真实模板（历史缺陷样本）修复后前缀出现次数不得增加。"""
    path = _TEMPLATES / "general-assistant.md"
    text = path.read_text(encoding="utf-8")
    linter = PromptLinter()

    findings = linter.lint("tpl", text).findings
    fixed, applied = linter._apply_fixes(text, findings)

    assert applied, "该模板历史上会触发追加型修复，此处应至少有一条动作"
    probe = text[:25]
    assert fixed.count(probe) == text.count(probe)
    assert fixed.startswith(text)
    assert len(fixed) < 2 * len(text), f"文本膨胀: {len(text)} -> {len(fixed)}"


@pytest.mark.parametrize("path", sorted(_TEMPLATES.glob("*.md")), ids=lambda p: p.name)
def test_no_bundled_template_blows_up(path: Path) -> None:
    """26 个自带模板整体验收：不得出现倍数级膨胀或原文复制。"""
    text = path.read_text(encoding="utf-8")
    linter = PromptLinter()

    findings = linter.lint("tpl", text).findings
    fixed, _applied = linter._apply_fixes(text, findings)

    probe = text[:25]
    assert fixed.count(probe) == text.count(probe), f"{path.name} 原文前缀被复制"
    assert len(fixed) <= len(text) * 2 + 2000, f"{path.name} 膨胀 {len(text)} -> {len(fixed)}"


def test_verifier_result_is_consistent_with_text_growth() -> None:
    """验证层的文本增量与状态不得自相矛盾。"""
    text = (_TEMPLATES / "pangu-multimodal.md").read_text(encoding="utf-8")
    result = AutoFixVerifier().verify(text)

    assert result.status is not VerificationStatus.ERROR
    assert len(result.fixed_text) <= len(text) * 2 + 2000
    assert result.fixed_text.count(text[:25]) == text.count(text[:25])
    if result.text_changed is False:
        assert result.status is VerificationStatus.NOT_APPLIED


# ── 9. 级联收敛：追加会引出新规则，但必须在有限轮次内稳定 ─────────────────


def test_known_suffixes_never_duplicate_across_runs() -> None:
    """同一条声明后缀反复执行后仍只出现一次（不依赖后缀位于末尾）。"""
    linter = PromptLinter()
    suffixes = [
        "\n\n请将回答控制在500字以内。",
        "\n\n[安全声明] 音频输入仅用于语音识别，禁止用于声纹识别或身份认证",
    ]
    current = BASE
    for _ in range(4):
        findings = [_finding("P025"), _finding("P131")]
        current, _ = linter._apply_fixes(current, findings)

    for suffix in suffixes:
        assert current.count(suffix) == 1, f"后缀重复追加: {suffix!r}"
    assert current.count(BASE) == 1


@pytest.mark.parametrize("path", sorted(_TEMPLATES.glob("*.md")), ids=lambda p: p.name)
def test_repeated_fix_converges(path: Path) -> None:
    """反复执行修复必须收敛：轮次有限、长度有界、原文不复制。"""
    text = path.read_text(encoding="utf-8")
    linter = PromptLinter()

    current = text
    rounds = 0
    while rounds < 6:
        findings = linter.lint("tpl", current).findings
        nxt, _applied = linter._apply_fixes(current, findings)
        if nxt == current:
            break
        current, rounds = nxt, rounds + 1

    assert rounds <= 5, f"{path.name} 未在 5 轮内收敛"
    assert len(current) <= len(text) * 2 + 2000, f"{path.name} 收敛后仍膨胀: {len(current)}"
    assert current.count(text[:25]) == text.count(text[:25])
