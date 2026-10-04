"""R230-P2-04: 双基线时间序列数据基础设施

误报率 6.03%→0.91% 的收紧史此前只存在于文档叙述（docs/规则误报率基线.md
表格），没有机器可查的时间序列。本脚本把每轮收口的双基线数字追加进
docs/baseline_history.jsonl —— precision 时间序列是获客渠道（08 发现 1：
社区在自建误报基准，prompt-guard 把"benchmark in CI"当卖点）。

纪律：
- 只追加（append-only）——历史行不改写（可信度叙事的数据基础）
- 每行=一轮收口快照：version/规则数/探针数/误报率/漏检率/finding 基线数
- release_gate 收口时自动跑本脚本（防漏跑，同 gen_rules_doc 门禁序教训）
- 历史回填（--backfill）：从 CHANGELOG 反推的早期点，行内 backfill=true 留痕

用法:
    python scripts/append_baseline_history.py            # 收口追加（自动度量）
    python scripts/append_baseline_history.py --check    # 只读校验（jsonl 合法+单调）
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

HISTORY_FILE = ROOT / "docs" / "baseline_history.jsonl"


def _run_json(script: str, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{script} 失败 (exit {proc.returncode}):\n{proc.stderr[-500:]}")
    return json.loads(proc.stdout)


def _version() -> str:
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0,'src'); from ai_prompt_toolkit import __version__; print(__version__)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _baseline_findings() -> int | None:
    """templates 增量门禁基线 finding 数（若基线文件存在）"""
    bl = ROOT / "baselines" / "templates-baseline.json"
    if not bl.exists():
        return None
    data = json.loads(bl.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        n = data.get("total_findings") or data.get("count")
        if isinstance(n, int):
            return n
    return None


def measure() -> dict:
    fp = _run_json("check_false_positives.py")
    miss = _run_json("check_miss_rate.py")
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": _version(),
        "rules": fp.get("checker_count"),
        "probes": miss.get("probe_count"),
        "tn_probes": None,  # 由调用方补充（漏检脚本 --json 无 TN 细分，保持口径诚实）
        "fp_rate": fp.get("global_rate"),
        "fp_samples": fp.get("sample_count"),
        "miss_rate": miss.get("global_rate"),
        "miss_expected_units": miss.get("expected_total"),
        "template_baseline_findings": _baseline_findings(),
        "backfill": False,
    }


def backfill_rows() -> list[dict]:
    """从 docs/规则误报率基线.md 与 规则漏检率基线.md 总览表反推的历史点。

    口径注意（写进每行 note）：
    - R210 前为 32 样本口径，R210 后 56，R221 后 60 —— 分母变化处不可直接对比
    - 回填点=文档实测值留痕，非重跑结果（重跑会引入规则集漂移）
    """
    return [
        {"round": "R203", "fp_rate": 0.0838, "fp_samples": 32, "rules": 255, "note": "首版基线（32样本口径）"},
        {"round": "R206", "fp_rate": 0.0603, "fp_samples": 32, "rules": 255, "note": "首批100%误报清零"},
        {"round": "R207", "fp_rate": 0.0317, "fp_samples": 32, "rules": 255, "note": "Top8高误报处置"},
        {"round": "R209", "fp_rate": 0.0153, "fp_samples": 32, "rules": 255, "note": "32样本口径最低点"},
        {
            "round": "R210",
            "fp_rate": 0.0204,
            "fp_samples": 56,
            "rules": 255,
            "note": "扩样32→56, 分母口径变化(不可与R210前直接对比)",
        },
        {"round": "R212", "fp_rate": 0.0096, "fp_samples": 56, "rules": 256, "note": "高误报规则清零"},
        {"round": "R215", "fp_rate": 0.0091, "fp_samples": 58, "rules": 260, "note": "58样本口径"},
        {"round": "R221", "fp_rate": 0.0091, "fp_samples": 60, "rules": 261, "note": "FP对称扩样至60样本"},
    ]


def _fmt_rate(v: float | None) -> str:
    return f"{v:.2%}" if isinstance(v, float) else "n/a"


def append(row: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ver = row["version"] or row.get("round") or "n/a"
    print(
        f"✓ 追加: {ver} fp={_fmt_rate(row['fp_rate'])} miss={_fmt_rate(row.get('miss_rate'))} "
        f"rules={row['rules']} probes={row['probes']}"
    )


def check() -> int:
    """只读校验：jsonl 每行合法 + 必填字段齐全。不判单调（扩样会抬升数字）。"""
    if not HISTORY_FILE.exists():
        print("⚠ baseline_history.jsonl 不存在（首轮收口前正常）")
        return 0
    bad = 0
    for i, line in enumerate(HISTORY_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            for k in ("fp_rate", "rules"):
                if k not in row:
                    raise ValueError(f"缺字段 {k}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"✗ 第{i}行非法: {e}")
            bad += 1
    print(f"✓ baseline_history 校验: {'全部合法' if bad == 0 else f'{bad} 行非法'}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="双基线时间序列追加（P2-04）")
    parser.add_argument("--check", action="store_true", help="只读校验不追加")
    parser.add_argument("--backfill", action="store_true", help="回填历史点（幂等：已存在的 round 跳过）")
    args = parser.parse_args()

    if args.check:
        return check()

    if args.backfill:
        existing: set[str] = set()
        if HISTORY_FILE.exists():
            for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if "round" in r:
                        existing.add(r["round"])
        added = 0
        for row in backfill_rows():
            if row["round"] in existing:
                continue
            row = {
                "ts": None,
                "version": None,
                "probes": None,
                "miss_rate": None,
                "miss_expected_units": None,
                "template_baseline_findings": None,
                "backfill": True,
                **row,
            }
            append(row)
            added += 1
        print(f"✓ 回填 {added} 个历史点（已存在跳过）")
        return 0

    row = measure()
    # TN 探针细分（诚实口径：expected 为空的探针数）
    from ai_prompt_toolkit.baselines import _load_golden_probes

    row["tn_probes"] = sum(1 for p in _load_golden_probes() if not p.get("expected"))
    append(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
