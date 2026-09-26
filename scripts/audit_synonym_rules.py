"""同义规则审计 — 数据驱动的规则质量治理工具(R173)

审计两步:
1. 描述相似度粗筛: SequenceMatcher对比所有规则的中文描述
2. 语料重叠率验证: 对候选对统计"主触发/从触发/同触"的重叠率
   - 重叠率100%或触发面真子集 → 真冗余对, 应加入 SYNONYM_RULE_GROUPS 同触去重
   - 重叠率<10% → 相关规则, 不处理
   - 从规则触发为0 → 检查是否死规则

用法:
    python scripts/audit_synonym_rules.py                  # 相似度粗筛
    python scripts/audit_synonym_rules.py --corpus <目录>   # 加语料重叠率验证
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def similarity_pairs(threshold: float) -> list[tuple[float, str, str]]:
    from ai_prompt_toolkit.linter.rules import get_all_rules

    rules = get_all_rules()
    pairs = []
    for a, b in combinations(rules, 2):
        r = SequenceMatcher(None, a.description, b.description).ratio()
        if r >= threshold:
            pairs.append((round(r, 2), a.rule_id, b.rule_id))
    return sorted(pairs, reverse=True)


def overlap_audit(pairs: list[tuple[float, str, str]], corpus_dir: Path) -> None:
    from ai_prompt_toolkit.linter.rules import _RULE_MAP, run_all_checks

    texts = [p.read_text(encoding="utf-8", errors="replace") for p in sorted(corpus_dir.glob("*.md"))]
    hits: dict[str, set[int]] = defaultdict(set)
    for idx, text in enumerate(texts):
        for f in run_all_checks(text):
            hits[f.rule_id].add(idx)

    print(f"\n重叠率审计({len(texts)}个语料文件):")
    print(f"{'对':14} {'主触发':>6} {'从触发':>6} {'同触':>6} {'重叠率':>8} {'严重级':>14}")
    for _sim, main, sub in pairs:
        m, s = hits.get(main, set()), hits.get(sub, set())
        union = len(m | s)
        rate = len(m & s) / union if union else 0
        sev_m = _RULE_MAP[main].severity.value if main in _RULE_MAP else "?"
        sev_s = _RULE_MAP[sub].severity.value if sub in _RULE_MAP else "?"
        verdict = "真冗余→去重" if rate >= 0.5 else ("相关→不动" if rate < 0.3 else "部分重叠→复核")
        print(f"{main}~{sub}  {len(m):>6} {len(s):>6} {len(m & s):>6} {rate:>8.0%} {sev_m}/{sev_s}  {verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description="同义规则审计")
    parser.add_argument("--threshold", type=float, default=0.55, help="描述相似度阈值")
    parser.add_argument("--corpus", type=str, default=None, help="语料目录(默认取根目录0*.md)")
    args = parser.parse_args()

    pairs = similarity_pairs(args.threshold)
    print(f"描述相似度≥{args.threshold}: {len(pairs)}对")
    for sim, a, b in pairs[:20]:
        print(f"  {sim} | {a} vs {b}")

    if args.corpus:
        overlap_audit(pairs, Path(args.corpus))
    else:
        print("\n提示: 加 --corpus <目录> 做语料重叠率验证")


if __name__ == "__main__":
    main()
