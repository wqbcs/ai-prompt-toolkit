"""R294-P3-17: 板 vs 代码盘点机制（check_board_status check 4/5）机器护栏。

背景: 板漂移缺陷类 5 次实证（P1-18/P2-04/P2-07/P3-02 + R293 P2-29 状态滞后），
R294 在既有 check 1-3 上补两个机器精确检查:
- check 4 (红): ✅ 行状态列引用的 P\\d{3} 必须存在于活规则注册表(声称 backed)
- check 5 (红): ⬜ 行说明列出现轮次完成声称(R\\d{3} 收口/落地)= 板自相矛盾
  (降噪: 匹配点前 15 字符内有板号 = 依赖引用, 跳过)

合成板/CHANGELOG 全 hermetic(tmp_path), 注册表真源=本仓 src(只读, 不改)。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_board_status.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("check_board_status_r294", SCRIPT)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(mod, board: str, changelog: str, tmp_path: Path) -> tuple[int, str]:
    b = tmp_path / "board.md"
    c = tmp_path / "CHANGELOG.md"
    b.write_text(board, encoding="utf-8")
    c.write_text(changelog, encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(["--board", str(b), "--changelog", str(c), "--repo", str(ROOT)])
    return code, buf.getvalue()


EMPTY_LOG = "# CHANGELOG\n"


class TestCheck4RuleReference:
    def test_real_rule_ref_passes(self, mod, tmp_path: Path) -> None:
        """✅ 行状态列引用真实规则(P001 注册表必有) → 不红。"""
        board = "| T1-01 | 任务 | 说明 | - | 验收 | S | ✅ 2026-01-01 R900：P001 落地 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 0, out
        assert "规则引用失实" not in out

    def test_phantom_rule_ref_fails(self, mod, tmp_path: Path) -> None:
        """✅ 行状态列引用 P999(注册表无) → 红(声称失实, 与 sha 腐烂同性质)。"""
        board = "| T1-01 | 任务 | 说明 | - | 验收 | S | ✅ 2026-01-01 R900：P999 落地 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 1, out
        assert "[规则引用失实] T1-01" in out
        assert "P999" in out

    def test_desc_rule_ref_not_checked(self, mod, tmp_path: Path) -> None:
        """说明列的规则号是前瞻叙述(候选/观察), 状态列才是要 backed 的声称面。"""
        board = "| T1-01 | 任务 | 后续 P999 候选另立观察行 | - | 验收 | S | ✅ 2026-01-01 R900 落地 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 0, out

    def test_board_id_not_confused_with_rule(self, mod, tmp_path: Path) -> None:
        """板号 P2-29(连字符) 与规则号 P\\d{3}(无连字符) 命名空间不撞。"""
        board = "| P2-29 | 任务 | 说明 | - | 验收 | S | ✅ 2026-01-01 R900 落地 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 0, out


class TestCheck5SelfContradiction:
    def test_round_claim_in_desc_fails(self, mod, tmp_path: Path) -> None:
        """⬜ 行说明列声称 R901 收口(无板号前缀) → 红(P2-07 型自相矛盾)。"""
        board = "| T1-03 | 任务 | R901 收口：实查已实现 | - | 验收 | S | ⬜ 待实施 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 1, out
        assert "[板自相矛盾] T1-03" in out
        assert "R901 收口" in out

    def test_dependency_ref_excluded(self, mod, tmp_path: Path) -> None:
        """⬜ 行说明列 '依赖 P2-15(R901 落地)' = 依赖行引用, 非本行声称 → 不红。"""
        board = "| T1-04 | 任务 | 依赖 P2-15（R901 落地）, 本项为后续面 | - | 验收 | S | ⬜ 待实施 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 0, out
        assert "板自相矛盾" not in out

    def test_done_row_with_claim_passes(self, mod, tmp_path: Path) -> None:
        """✅ 行说明列的完成叙述是合法文本(仅状态列⬜才构成矛盾)。"""
        board = "| T1-05 | 任务 | R901 落地：真语料实测绿 | - | 验收 | S | ✅ 2026-01-01 R901 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 0, out


class TestLegacyChecksAndFailClosed:
    def test_check2_changelog_claim_still_fires(self, mod, tmp_path: Path) -> None:
        """既有 check 2(⬜ 行 + CHANGELOG Added 声称)不回归。"""
        board = "| T1-06 | 任务 | 说明 | - | 验收 | S | ⬜ 待实施 |\n"
        log = "### Added (R900: T1-06 落地)\n"  # Added 标题=轮次产出摘要(rid 在括号内)
        code, out = _run(mod, board, log, tmp_path)
        assert code == 1, out
        assert "[板未回写] T1-06" in out

    def test_registry_load_failure_is_red(self, mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """注册表加载失败 = check 4 无法裁决 → fail-closed 红, 不得静默放行。"""
        monkeypatch.setattr(mod, "load_rule_ids", lambda repo: None)
        board = "| T1-01 | 任务 | 说明 | - | 验收 | S | ✅ 2026-01-01 R900 落地 |\n"
        code, out = _run(mod, board, EMPTY_LOG, tmp_path)
        assert code == 1, out
