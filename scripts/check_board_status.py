"""R243-1: 02 任务总板状态列 vs CHANGELOG 声称 vs sha 存在性三向核对(板漂移脚本化)。

背景(02 P3-17 R241 刷新): 3 轮内 3 处板漂移——R239 P1-18(登记时能力已存在)、
R241 P3-02/P3-09(完成轮次未回写状态列)。根因=状态列与代码/CHANGELOG 实际脱节,
人肉抽查(每 10 轮 3-5 项)防不住。本脚本把"完成声称 vs 板状态"变机器全查:

check 1 (红): ✅ 行引用的 commit sha 必须在本仓库存在(`git cat-file -e <sha>^{}`)
  ——防 sha 腐烂(引用更正/换分支后旧 sha 失效=引用失真)。
check 2 (红): ⬜ 行的任务 ID 若出现在 CHANGELOG 任一 `### Added` 标题中=
  漂移(该轮声称完成但板未回写)——本轮实证根因的机器护栏。
  降噪面: Added 标题=轮次产出摘要(只写实际交付项), 规则号(P257/P267 三位数)
  不在板 ID 权威集(连字符形态)内不误判; ⏸/暂停行非 ⬜ 不命中。
check 3 (黄, 不阻断): ✅ 行无任何可验证引用(7-10 位 hex sha 或 2026- 日期)
  ——回写纪律(R239 起: 状态列必须带引用)的存量提示面, 旧行不追红。

用法:
    python scripts/check_board_status.py                 # 默认真板+真 CHANGELOG
    python scripts/check_board_status.py --board X --changelog Y
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "docs" / "planning" / "02_任务总板.md"
CHANGELOG = ROOT / "CHANGELOG.md"

SHA_RE = re.compile(r"\b[0-9a-f]{7,10}\b")
ROW_RE = re.compile(r"^\|\s*([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*)\s*\|")
ADDED_TITLE_RE = re.compile(r"^### Added \(([^)]+)\)")


def parse_board(text: str) -> list[tuple[str, str]]:
    """02 板任务行 → [(任务 ID, 状态列)](仅 7 列表格行)。"""
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        rows.append((m.group(1), cells[-1]))
    return rows


def parse_added_titles(text: str) -> dict[str, list[str]]:
    """CHANGELOG `### Added` 标题 → {轮次标签: 标题文本}(标题=轮次产出摘要)。"""
    out: dict[str, list[str]] = {}
    m_round = re.compile(r"^(R\d{3})")
    for line in text.splitlines():
        m = ADDED_TITLE_RE.match(line.strip())
        if not m:
            continue
        title = m.group(1)
        r = m_round.match(title)
        key = r.group(1) if r else "?"
        out.setdefault(key, []).append(title)
    return out


def sha_exists(sha: str, repo: Path) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", sha + "^{}"],
            cwd=repo,
            capture_output=True,
        ).returncode
        == 0
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--board", type=Path, default=BOARD)
    ap.add_argument("--changelog", type=Path, default=CHANGELOG)
    ap.add_argument("--repo", type=Path, default=ROOT)
    args = ap.parse_args(argv)

    board = args.board.read_text(encoding="utf-8")
    changelog = args.changelog.read_text(encoding="utf-8")
    rows = parse_board(board)
    added = parse_added_titles(changelog)
    all_titles = "\n".join(t for titles in added.values() for t in titles)

    issues: list[str] = []
    warns: list[str] = []

    for rid, status in rows:
        if status.startswith("✅"):
            # check 1: sha 存在性
            for sha in SHA_RE.findall(status):
                if not sha_exists(sha, args.repo):
                    issues.append(f"[sha 腐烂] {rid} 引用的 {sha} 在仓库不存在")
            # check 3 (warn): 无引用
            if not SHA_RE.search(status) and "2026-" not in status:
                warns.append(f"[无引用] {rid} 标 ✅ 但状态列无可验证引用(sha/日期)")
        elif status.startswith("⬜"):
            # check 2: CHANGELOG 声称完成但板未回写
            if rid in all_titles:
                rounds = sorted(k for k, ts in added.items() if rid in "\n".join(ts))
                issues.append(
                    f"[板未回写] {rid} 板状态 ⬜ 但 CHANGELOG Added 标题已声称完成(轮次: {', '.join(rounds)})"
                )

    print(f"02 总板任务行: {len(rows)} (✅/⬜/⏸ 等)")
    if issues:
        print("✗ 板状态漂移:")
        for i in issues:
            print(f"  - {i}")
        print("  修复: 回写 02 状态列(带 commit sha+验证引用, R239 起回写纪律)")
        for w in warns:
            print(f"  (提示) {w}")
        return 1
    for w in warns:
        print(f"  (提示) {w}")
    print("✓ 板状态与 CHANGELOG/sha 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
