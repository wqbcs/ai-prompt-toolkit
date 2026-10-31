"""R359-E1：双修复机制统一 + --fix 回写 e2e 回归护栏。

取证背景（R359）：
1. 双修复机制漂移：CLI --fix 实际路径（linter._get_fix_action if 链, 51 规则）
   与声明面（fixer.AUTO_FIXABLE_RULES 198, README/LSP/MCP/rule_explainer）
   并行漂移 → 149 条"声明可修"在 CLI --fix 静默无效（能力超声称）。
2. 回写断链：lint() 不返回修复后文本（LintResult 无 fixed_text）, CLI 只展示
   "自动修复: N 处"不写回文件 → --fix 是展示态。

收口（R359 选项 A, 用户裁决）：_apply_fixes 对 _get_fix_action 无 action 的
finding 回落 Fixer 引擎安全子集 {P258, P260}（R358 隐藏字符 autofix: 幂等/不
级联/无可见侵入; 交集规则路径 A 优先=行为零漂移; 非安全子集规则 no-op）。
宽回落（全 198 集）会激活 P048 原位标点替换（破 fixed.startswith(text)）+
P072/P080/P100/P120 追加级联 + P048 非幂等（模板 7 轮才收敛, 护栏只许 5）,
违背 test_autofix_append_regression.py 安全护栏与"棘轮只收紧"纪律, 故不收。
"声明=现实"改为让声明面反映真实自动修复集（--fix 自动应用安全子集; 198 集为
修复引擎能力, LSP/显式模式可用）。+ LintResult.fixed_text（条件输出, 非 fix
路径 schema 零漂移）+ CLI 两处回写。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.types import Finding, Severity

ZW = "\u200b"
PROJ_ROOT = Path(__file__).resolve().parent.parent


class TestLintFixFixedText:
    """lint(fix=True) → fixed_text（内核面）。"""

    def setup_method(self) -> None:
        self.linter = PromptLinter()

    def test_p260_fix_returns_fixed_text(self) -> None:
        """P260（5+ 连续零宽, 仅 B 路径规则）修复后 fixed_text 无 zw。"""
        text = f"aaaa{ZW * 5} bbbb\nPlease summarize."
        res = self.linter.lint("t", text, fix=True)
        assert res.fixed_text is not None
        assert ZW not in res.fixed_text
        assert any(f.rule_id == "P260" for f in res.fixed_findings)

    def test_p258_partial_fix_label_remains(self) -> None:
        """P258（词内零宽+伪标签）：zw 剥离, 标签面仍报（设计边界留痕）。"""
        text = f"[S{ZW}YSTEM]\nPlease summarize the following text."
        res = self.linter.lint("t", text, fix=True)
        assert res.fixed_text is not None
        assert ZW not in res.fixed_text
        assert "[SYSTEM]" in res.fixed_text
        assert any(f.rule_id == "P258" for f in res.findings)

    def test_no_fix_no_fixed_text(self) -> None:
        """fix=False → fixed_text=None 且 to_dict 无该键（schema 兼容）。"""
        text = f"aaaa{ZW * 5} bbbb\nPlease summarize."
        res = self.linter.lint("t", text, fix=False)
        assert res.fixed_text is None
        assert "fixed_text" not in res.to_dict()

    def test_to_dict_conditional_output(self) -> None:
        """to_dict 条件输出：有修复才带 fixed_text 键。"""
        text = f"aaaa{ZW * 5} bbbb\nPlease summarize."
        res_fixed = self.linter.lint("t", text, fix=True)
        if res_fixed.fixed_text is not None:
            assert "fixed_text" in res_fixed.to_dict()
            assert ZW not in res_fixed.to_dict()["fixed_text"]


class TestApplyFixesFallback:
    """_apply_fixes 回落 Fixer 引擎（单元锚, 不依赖检测规则触发）。"""

    def setup_method(self) -> None:
        self.linter = PromptLinter()

    def test_fallback_fixes_p260(self) -> None:
        finding = Finding(rule_id="P260", severity=Severity.HIGH, description="测试")
        text = f"aaaa{ZW * 5} bbbb"
        fixed_text, fixed = self.linter._apply_fixes(text, [finding])
        assert ZW not in fixed_text
        assert fixed == [finding]

    def test_fallback_noop_unfixable_rule(self) -> None:
        """非安全子集规则（P001 不在 {P258,P260}）→ no-op（不修不记）。"""
        finding = Finding(rule_id="P001", severity=Severity.HIGH, description="测试")
        fixed_text, fixed = self.linter._apply_fixes("plain text", [finding])
        assert fixed_text == "plain text"
        assert fixed == []

    def test_fallback_idempotent(self) -> None:
        """二次回落无变化（Cf 剥离幂等）。"""
        finding = Finding(rule_id="P260", severity=Severity.HIGH, description="测试")
        text = f"aaaa{ZW * 5} bbbb"
        once, _ = self.linter._apply_fixes(text, [finding])
        twice, fixed2 = self.linter._apply_fixes(once, [finding])
        assert twice == once
        assert fixed2 == []


class TestCliFixWritebackE2E:
    """CLI --fix 端到端：修复必须写回用户文件（subprocess 黑盒）。"""

    def test_cli_fix_writeback(self, tmp_path: Path) -> None:
        f = tmp_path / "e2e.prompt"
        f.write_text(f"aaaa{ZW * 5} bbbb\nPlease summarize.", encoding="utf-8")
        r = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.argv=['prompt-cli','lint','-t',r'" + str(f) + r"','--fix']; "
                "from ai_prompt_toolkit.cli_core import main; main()",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJ_ROOT),
        )
        content = f.read_text(encoding="utf-8")
        assert ZW not in content, f"回写未生效: {content!r}"
        assert "[FIX]" in r.stdout


class TestFixPerformanceWedge:
    """1.8MB 单行目标 lint(fix=True) 有界（R356 入口变换计时纪律, 非 slow）。"""

    def test_1_8mb_fix_bounded(self) -> None:
        linter = PromptLinter()
        text = "x" * 1_800_000 + f"\naaaa{ZW * 5} bbbb"
        start = time.perf_counter()
        res = linter.lint("t", text, fix=True)
        elapsed = time.perf_counter() - start
        assert elapsed < 60.0, f"1.8MB lint(fix=True) 超 60s: {elapsed:.1f}s"
        assert res.fixed_text is not None
        assert ZW not in res.fixed_text
