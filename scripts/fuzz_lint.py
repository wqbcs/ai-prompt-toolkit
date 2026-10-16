"""P3-04: lint_template 入口 fuzz 目标（R303 设计定稿 / R304 落地第一片）

安全工具被 fuzz 挂掉=致命讽刺（板行 P3-04）。Atheris（Python 官方推荐）
fuzz `lint_template(name, text)` 入口——随机字节/超长/Unicode 边界/嵌套引号
全走同一确定性内核，任何异常=门禁工具自身缺陷，作业红。

平台面（R303 spike 机器证据）: Atheris 3.1.0 无任何版本 Windows wheel
（历史文件全清单=仅 macosx+manylinux x86_64）→ 本脚本在 Windows 本地不可跑，
CI/Linux 侧执行（ubuntu-latest + pip install atheris, [dev] 工具链，零运行时
新依赖）。与楔子关系=红队输入验证（不在确定性门禁主链内，零 LLM）。

seed 语料: golden 探针（data/golden_attacks.json）逐条落盘——探针集是既有
对抗语料的单一真源，首分钟高覆盖（不另造语料=奥卡姆）。

用法（Linux/CI）:
    pip install atheris
    python scripts/fuzz_lint.py --corpus <dir>   # corpus 缺失时先 --seed
    python scripts/fuzz_lint.py --seed <dir>     # 从 golden 探针生成 seed

CI 短 fuzz（设计定稿，workflow 接线=发布后）: ubuntu-latest +
max_total_time=300（5min 墙钟）+ crash=作业红；72h 马拉松=发布后长时环境
项（Actions 6h 上限，本地 Linux VM/self-hosted runner）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_FILE = REPO_ROOT / "src" / "ai_prompt_toolkit" / "data" / "golden_attacks.json"

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_prompt_toolkit.linter import lint_template  # noqa: E402


def export_seed_corpus(corpus_dir: Path, golden_file: Path = GOLDEN_FILE) -> int:
    """golden 探针逐条落盘为 seed 语料（确定性: 同输入逐字节一致）。

    返回写入文件数。corpus_dir 不存在时自动创建。
    """
    data = json.loads(golden_file.read_text(encoding="utf-8"))
    probes = data["probes"]
    corpus_dir.mkdir(parents=True, exist_ok=True)
    for i, probe in enumerate(probes):
        (corpus_dir / f"probe_{i:04d}").write_text(probe["text"], encoding="utf-8")
    return len(probes)


def lint_text(name: str, text: str) -> None:
    """内核对抗面入口: 任意 (name, text) str 输入不抛。

    fuzz 面的 Windows 可测投影（Atheris 无 Windows wheel, R303 spike）——
    测试直接打此面; Atheris 的 ConsumeUnicode 产出即 str, 语义等价。
    name 面同步打（模板名参与规则匹配路径, 如 P160 文件名模式）。
    """
    lint_template(name, text)


def fuzz_target(data: bytes) -> None:
    """Atheris 目标函数（仅 Linux/CI 执行）: 任意字节喂入内核, 异常=crash=作业红。"""
    dp = _provider(data)
    lint_text(dp.ConsumeUnicode(64), dp.ConsumeUnicode(1 << 16))


def _provider(data: bytes):
    import atheris

    return atheris.FuzzedDataProvider(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="P3-04: lint_template 入口 fuzz")
    parser.add_argument("--corpus", type=Path, help="Atheris 语料目录(存在则作为 seed)")
    parser.add_argument("--seed", type=Path, help="从 golden 探针生成 seed 语料目录(生成后退出)")
    args = parser.parse_args()

    if args.seed is not None:
        n = export_seed_corpus(args.seed)
        print(f"seed 语料已生成: {args.seed} ({n} 条, 真源={GOLDEN_FILE.name})")
        return

    # Atheris 懒导入: Windows 本地/CI 未装 atheris 时 --seed 与 import 检查仍可用
    import atheris

    atheris.Fuzz(
        fuzz_target,
        corpus=args.corpus if args.corpus and args.corpus.is_dir() else None,
        max_total_time=300,  # R303 定稿: CI 短 fuzz 5min 墙钟
    )


if __name__ == "__main__":
    main()
