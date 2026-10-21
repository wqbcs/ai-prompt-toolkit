"""R243-1: 02 总板状态列 vs CHANGELOG 声称 vs sha 存在性三向核对测试。

覆盖: parse_board 行面/非任务行排除; parse_added_titles 轮次键;
check 1 sha 腐烂(红); check 2 板未回写(红, 轮次定位);
check 3 无引用(黄不阻断); 真板全绿 e2e。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_board_status.py"
TRUE_BOARD = ROOT / "docs" / "planning" / "02_任务总板.md"
TRUE_CHANGELOG = ROOT / "CHANGELOG.md"

sys.path.insert(0, str(ROOT / "scripts"))
import check_board_status as cbs  # noqa: E402


@pytest.fixture()
def board(tmp_path: Path) -> Path:
    p = tmp_path / "board.md"
    p.write_text(
        "\n".join(
            [
                "| 编号 | 任务 | 说明 | 依赖 | 验收标准 | 估时 | 状态 |",
                "|---|---|---|---|---|---|---|",
                "| P0-03 | 转公开 | — | — | public | S | ⬜ 待用户 |",
                "| P3-02 | 已完成项 | — | — | — | S | ✅ 2026-10-01 (c1de19d 验证) |",
                "| P3-09 | 无引用项 | — | — | — | S | ✅ 完成 |",
                "| R243-X1 | 暂停项 | — | — | — | S | ⏸ 暂停 |",
                "非表格行 P9-99 不应解析",
            ]
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def changelog(tmp_path: Path) -> Path:
    p = tmp_path / "CHANGELOG.md"
    p.write_text(
        "\n".join(
            [
                "# Changelog",
                "## 67.34.35",
                "### Added (R243: 板漂移脚本化)",
                "- 内容",
                "### Changed (R243: 其他)",
                "- 内容",
            ]
        ),
        encoding="utf-8",
    )
    return p


def run_check(board: Path, changelog: Path, repo: Path | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(SCRIPT), "--board", str(board), "--changelog", str(changelog)]
    if repo is not None:
        cmd += ["--repo", str(repo)]
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return r.returncode, r.stdout


def test_parse_board_rows_and_status_column(board: Path) -> None:
    """R294 契约: parse_board → [(任务 ID, 列列表)], 状态列=cells[-1]。"""
    rows = cbs.parse_board(board.read_text(encoding="utf-8"))
    by_id = dict(rows)
    assert by_id["P0-03"][-1] == "⬜ 待用户"
    assert by_id["P3-02"][-1] == "✅ 2026-10-01 (c1de19d 验证)"
    assert by_id["R243-X1"][-1] == "⏸ 暂停"
    # 非表格行的 P9-99 不解析
    assert all(rid != "P9-99" for rid, _ in rows)


def test_parse_added_titles_round_key(changelog: Path) -> None:
    added = cbs.parse_added_titles(changelog.read_text(encoding="utf-8"))
    assert "R243" in added
    assert any("板漂移脚本化" in t for t in added["R243"])


def test_true_board_clean(board: Path, changelog: Path) -> None:
    rc, out = run_check(board, changelog)
    assert rc == 0, out
    assert "✓" in out


def test_check2_unwritten_board_goes_red(board: Path, tmp_path: Path) -> None:
    # P0-03 板状态 ⬜ 但 Added 标题声称完成 → 红 + 轮次定位
    cl = tmp_path / "cl.md"
    cl.write_text("### Added (R244: P0-03 转公开完成)\n", encoding="utf-8")
    rc, out = run_check(board, cl)
    assert rc == 1
    assert "板未回写" in out
    assert "P0-03" in out
    assert "R244" in out


def test_check3_no_reference_is_warn_not_red(board: Path, changelog: Path) -> None:
    rc, out = run_check(board, changelog)
    # P3-09 ✅ 无 sha 无日期 = 黄(提示)不阻断
    assert rc == 0
    assert "无引用" in out
    assert "P3-09" in out


def test_check1_sha_rot_goes_red(board: Path, changelog: Path, tmp_path: Path) -> None:
    # c1de19d 在真仓库存在; 换成 deadbe1 = sha 腐烂红
    bad = tmp_path / "board_bad.md"
    bad.write_text(board.read_text(encoding="utf-8").replace("c1de19d", "deadbe1"), encoding="utf-8")
    rc, out = run_check(bad, changelog)
    assert rc == 1
    assert "sha 腐烂" in out
    assert "P3-02" in out


def test_true_board_e2e_clean() -> None:
    rc, out = run_check(TRUE_BOARD, TRUE_CHANGELOG)
    assert rc == 0, out
    assert "✓ 板状态与 CHANGELOG/sha 一致" in out


def test_shallow_repo_fails_closed(tmp_path: Path, board: Path, changelog: Path) -> None:
    """R335: 浅克隆下 check 1 (sha 存在性) 无法裁决 → fail-closed 红 + 明确诊断
    (CI 浅克隆实证: 本地全历史全绿/CI 红, 误报面="sha 腐烂"而非环境错配)。"""
    src = tmp_path / "src_repo"
    src.mkdir()

    def git(*args: str, cwd: Path) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    git("init", "-q", cwd=src)
    git("config", "user.email", "test@test", cwd=src)
    git("config", "user.name", "test", cwd=src)
    (src / "f.txt").write_text("1\n", encoding="utf-8")
    git("add", ".", cwd=src)
    git("commit", "-q", "-m", "c1", cwd=src)
    # 真浅克隆: --no-local 强制 pack 传输(本地路径默认 hardlink 会把全对象带过去,
    # 那造不出浅仓 — R335 复现实证)
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", "--no-local", str(src), str(shallow)],
        check=True,
        capture_output=True,
    )
    rc, out = run_check(board, changelog, repo=shallow)
    assert rc == 1
    assert "浅克隆" in out
    # 守卫先于 sha 检查触发: 不得出现"sha 腐烂"误报(R335 CI 误红面)
    assert "sha 腐烂" not in out
