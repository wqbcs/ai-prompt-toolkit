"""R235-P4-02: 核心零依赖验证 — kernel 层零第三方 runtime import 的机器护栏

R233-P4-01 分层测绘(docs/planning/14)手测结论"kernel 层零第三方"固化为机器护栏:
每轮门禁链跑一次, kernel 层出现第三方 runtime import 即红。

与 check_dep_manifest.py 正交(不重复造轮子, 复用其 runtime_imports 扫描基建):
- check_dep_manifest: **包级** — src 全量第三方 import ⊆ pyproject 声明(防 jinja2 事故)
- 本脚本: **层级** — kernel 层(规则引擎/finding 模型)不允许任何第三方 import
  (不仅"声明了才允许", 而是"根本不允许")——5 年架构不变量"任意端技术栈迭代
  不影响业务内核"的静态护栏: 内核零依赖=内核可被任何语言端复用(WASM/Node/Rust 桥)

kernel 层清单来源: 14 §1 第一行(实测归属)。清单变更纪律: 与 14 文档同步改
(改清单必须带理由+过 code review; 清单文件缺=红, 诚实失败)。

规则(与 R233 手测同口径):
- stdlib(sys.stdlib_module_names)排除
- 第一方(ai_prompt_toolkit)排除
- TYPE_CHECKING 块内 import 不算 runtime(复用 check_dep_manifest.runtime_imports)
- 第三方顶层 import(含 pyyaml→yaml 映射面)出现即违规

用法:
    python scripts/check_layer_deps.py            # 校验, 违规 exit 1
    python scripts/check_layer_deps.py --json     # JSON 输出
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "ai_prompt_toolkit"
sys.path.insert(0, str(ROOT / "scripts"))

from check_dep_manifest import runtime_imports  # noqa: E402  复用扫描基建, 不新造


def kernel_files() -> list[Path]:
    """kernel 层文件清单(14 §1 第一行; glob 展开规则族)。

    变更纪律: 与 docs/planning/14 §1 同步(改清单=改架构边界, 必须带理由)。
    新增 rules_p*.py 自动纳入(glob); 新增独立 kernel 模块须显式加行+同步 14 文档。
    """
    files: list[Path] = [
        SRC / "types.py",
        SRC
        / "errors.py",  # R344-RE-1b: 异常层次(纯 stdlib, 与 types 同叶模块性质; baseline 解码护栏需 ValidationError)
        SRC / "linter" / "linter.py",
        SRC / "linter" / "rules.py",
        SRC / "linter" / "linear_scan.py",  # R344-RE-1b: 线性扫描原语(纯 stdlib, 无界 .* 模式的线性等价重写)
        SRC / "linter" / "baseline.py",
        SRC / "linter" / "waivers.py",
        SRC / "linter" / "target_model.py",
        SRC / "linter" / "owasp_mapping.py",
        SRC / "linter" / "owasp_agentic_mapping.py",
        SRC / "linter" / "nist_rmf_mapping.py",
        SRC / "linter" / "structured_diff.py",
        SRC / "linter" / "friendly_descriptions.py",
        SRC / "linter" / "lcov_export.py",
    ]
    files.extend(sorted((SRC / "linter").glob("rules_*.py")))
    return files


# R235-P4-02 留痕豁免面: 与 14 §3 违规边编号一一对应。
# 豁免纪律: 每条必须带 14 §3 违规边号 + 处置归属轮次; 对应修复落地后必须同 commit
# 删豁免行(防永久豁免)。豁免≠放行——是"已知+已排期"的显式登记。
# (14 §3 V1-V4/V6/V7 属"rules 扩展/adapters"层, 不在 kernel 清单内, 不入本豁免面;
#  只有 V5 落在 kernel glob 内 → 本表仅此一条)
KNOWN_VIOLATION_EDGES: dict[str, str] = {
    # V5: 唯一规则文件内 yaml(延迟 import, frontmatter 解析) — 14 §3 处置=P4-07 候选首改
    "src/ai_prompt_toolkit/linter/rules_p051_p055.py": "V5(14 §3: frontmatter 延迟 import; P4-07 候选首改: 抽 frontmatter 解析进 kernel 辅助)",
}


def main() -> int:
    import sys as _sys

    stdlib = set(_sys.stdlib_module_names)
    first_party = {"ai_prompt_toolkit"}

    files = kernel_files()
    # 诚实失败: 清单文件缺=红(防清单漂移静默放行)
    missing = [str(f.relative_to(ROOT)) for f in files if not f.exists()]
    if missing:
        print("✗ kernel 清单文件缺失(清单与代码漂移, 同步 docs/planning/14 §1):")
        for m in missing:
            print(f"  ✗ {m}")
        return 1

    raw: list[dict[str, str]] = []
    for py in files:
        for name in runtime_imports(py):
            if name in stdlib or name in first_party:
                continue
            raw.append({"file": py.relative_to(ROOT).as_posix(), "import": name})

    # 已知违规边(14 §3, 已排期)→ 豁免; 未登记的第三方 import → 红
    known = [v for v in raw if v["file"] in KNOWN_VIOLATION_EDGES]
    unknown = [v for v in raw if v["file"] not in KNOWN_VIOLATION_EDGES]

    if "--json" in _sys.argv:
        print(
            json.dumps(
                {
                    "kernel_files": len(files),
                    "known_exemptions": [
                        {"file": v["file"], "import": v["import"], "reason": KNOWN_VIOLATION_EDGES[v["file"]]}
                        for v in known
                    ],
                    "violations": unknown,
                    "ok": not unknown,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"核心零依赖验证: kernel 层 {len(files)} 文件")
        if known:
            print(f"留痕豁免 {len(known)} 条(14 §3 已排期违规边, 非红):")
            for v in known:
                print(f"  ⚠ {v['file']}: import {v['import']} — {KNOWN_VIOLATION_EDGES[v['file']]}")
        if unknown:
            print("✗ kernel 层出现未登记的第三方 runtime import(5 年架构不变量: 内核零依赖):")
            for v in unknown:
                print(f"  ✗ {v['file']}: import {v['import']}")
            print("修复: 第三方 import 移 io/adapters 层, 或改 stdlib; 属合法 kernel 模块则同步 14 §1 清单")
            return 1
        print("✓ kernel 层无未登记第三方 runtime import(已知违规边已排期豁免, 与 R233-P4-01 一致)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
