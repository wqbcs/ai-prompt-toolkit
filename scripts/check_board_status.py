r"""R243-1: 02 任务总板状态列 vs CHANGELOG 声称 vs sha 存在性三向核对(板漂移脚本化)。

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

R294 (P3-17 板 vs 代码盘点机制, 板漂移缺陷类根治——P1-18/P2-04/P2-07/P3-02
五次漂移同根因): 补两个机器精确检查, 均只作用"列"不扫全行(✅ 行说明列的
"仍 ⬜"历史叙述与依赖指向是合法文本, 全行扫必误判——R294 实文校准结论):

check 4 (红, claim backed): ✅ 行**状态列**引用的规则号 P\d{3} 必须存在于
  活规则注册表(get_all_rules 单一真源)——状态列=完成声称, 声称落地 P999
  但注册表无 P999=声称失实(与 sha 腐烂同性质)。前瞻"候选"叙述在说明列,
  不命中, 零误判面。
check 5 (红, 板自相矛盾): ⬜ 行**说明列**出现 `R\d{3}(收口|已落地|落地)`
  = 行文声称完成但状态列未回写(P2-07/R246 型)。降噪: 匹配点前 15 字符
  内出现板号 `P\d+-\d+` = 依赖行引用(如"依赖 P2-15(R244 落地)"), 跳过。

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
# R294 check 4: 规则号引用(三位数, 无连字符——与板号 P2-29 命名空间不撞)
RULE_REF_RE = re.compile(r"\bP(\d{3})\b")
# R294 check 5: 轮次完成声称(收口/已落地/落地)——仅 ⬜ 行说明列, 前 15 字符
# 内有板号 P\d+-\d+ = 依赖引用, 跳过(降噪实据: "依赖 P2-15(R244 落地)")
ROUND_CLAIM_RE = re.compile(r"R(\d{3})\s*(?:收口|已落地|落地)")
BOARD_ID_RE = re.compile(r"P\d+-\d+")


def parse_board(text: str) -> list[tuple[str, list[str]]]:
    """02 板任务行 → [(任务 ID, 列列表)](仅 7 列表格行)。"""
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        rows.append((m.group(1), cells))
    return rows


def load_rule_ids(repo: Path) -> set[str] | None:
    """活规则注册表 ID 集(get_all_rules 单一真源); 加载失败=None(fail-closed)。"""
    try:
        src = str(repo / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from ai_prompt_toolkit.linter.rules import get_all_rules

        return {r.rule_id for r in get_all_rules()}
    except Exception as e:  # 加载失败必须显式红, 不得静默放行(fail-closed)
        print(f"✗ 规则注册表加载失败: {e}", file=sys.stderr)
        return None


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


def is_shallow_repo(repo: Path) -> bool:
    """R335: 浅克隆检测 — 浅仓下 check 1 (sha 存在性) 无法裁决: 历史 sha 缺失
    会被误判"sha 腐烂"(R335 CI 实证根因: 本地全历史全绿/CI 浅克隆红)。
    CI 需 actions/checkout fetch-depth: 0; 守卫 fail-closed 把"环境错配"
    从模糊误红变明确诊断, 不得静默放行。非 git 目录/命令失败 → False
    (退回逐 sha 检查的既有行为, 不新增失败面)。"""
    r = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--board", type=Path, default=BOARD)
    ap.add_argument("--changelog", type=Path, default=CHANGELOG)
    ap.add_argument("--repo", type=Path, default=ROOT)
    args = ap.parse_args(argv)

    if is_shallow_repo(args.repo):
        print("✗ 仓库为浅克隆: check 1 (sha 存在性) 无法裁决——CI 需 actions/checkout fetch-depth: 0")
        return 1

    board = args.board.read_text(encoding="utf-8")
    changelog = args.changelog.read_text(encoding="utf-8")
    rows = parse_board(board)
    added = parse_added_titles(changelog)
    all_titles = "\n".join(t for titles in added.values() for t in titles)

    rule_ids = load_rule_ids(args.repo)
    if rule_ids is None:
        return 1  # fail-closed: 注册表加载失败=check 4 无法裁决, 不得放行

    issues: list[str] = []
    warns: list[str] = []

    for rid, cells in rows:
        status = cells[-1]
        desc = cells[2] if len(cells) > 2 else ""
        if status.startswith("✅"):
            # check 1: sha 存在性
            for sha in SHA_RE.findall(status):
                if not sha_exists(sha, args.repo):
                    issues.append(f"[sha 腐烂] {rid} 引用的 {sha} 在仓库不存在")
            # check 3 (warn): 无引用
            if not SHA_RE.search(status) and "2026-" not in status:
                warns.append(f"[无引用] {rid} 标 ✅ 但状态列无可验证引用(sha/日期)")
            # check 4: 状态列规则引用必须存在于活注册表(声称 backed)
            for num in sorted(set(RULE_REF_RE.findall(status))):
                if f"P{num}" not in rule_ids:
                    issues.append(f"[规则引用失实] {rid} 状态列引用 P{num} 但规则注册表无此规则")
        elif status.startswith("⬜"):
            # check 2: CHANGELOG 声称完成但板未回写
            if rid in all_titles:
                rounds = sorted(k for k, ts in added.items() if rid in "\n".join(ts))
                issues.append(
                    f"[板未回写] {rid} 板状态 ⬜ 但 CHANGELOG Added 标题已声称完成(轮次: {', '.join(rounds)})"
                )
            # check 5: 说明列轮次完成声称 vs ⬜ 状态(板自相矛盾, P2-07 型)
            for m in ROUND_CLAIM_RE.finditer(desc):
                pre = desc[max(0, m.start() - 15) : m.start()]
                if BOARD_ID_RE.search(pre):
                    continue  # 依赖行引用("依赖 P2-15(R244 落地)"), 非本行声称
                issues.append(f"[板自相矛盾] {rid} 板状态 ⬜ 但说明列声称 {m.group(0).strip()}")

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
