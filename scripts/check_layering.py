"""R254-P4-10: 分层方向机器护栏 — 04 §1 依赖方向铁律(只允许上层 import 下层)

背景(04 §7.3 原始登记, 14 §4 约束 4): 04 §1 铁律"adapters→io→rules→kernel,
只允许上层 import 下层; rules 不得 import io; kernel 零第三方"此前只有
R233-P4-01 手测结论(docs/planning/14)无机器护栏。R254 预扫实证该手测面会
漂移: linter/ 存在 1 条 14 §3 未登记的包内跨层边(linter/test_suite.py →
cli_helpers, 函数内延迟 import)——14 §3 违规边清单 7 条全是第三方边, 包内
跨层边漏测(与 P3-17 板漂移同族: 人肉核查面必漏)。本脚本把铁律变机器全查。

与 check_layer_deps.py (P4-02) 正交(不重复造轮子):
- check_layer_deps: kernel 层**零第三方**(第三方面)
- 本脚本: 包内**跨层 import 方向**(第一方面: L1 rules→io/adapters / L2 kernel→非kernel)

检查项(与 04 §1 + 14 §1 逐条对应, 见 R254_改进方案 §3.1):
- L1 rules→io: linter/ 全部 .py(kernel+rules 扩展混放, 14 §2 G2)禁止 import
  io 顶层模块(cli_core/cli_helpers/cli_error_formatter/config/promptkit_
  config/data_reader)、cli 包 与 adapters 模块(dataset_api/playground/market/
  ab_test/lsp_server)
- L2 kernel 第一方纯度: kernel 清单(check_layer_deps.kernel_files() 单一真源)
  禁止 import 第一方模块中不在 kernel 清单的目标——**全第一方面**检查(含顶层
  暂混模块): 新顶层模块想进 kernel 依赖面必须显式登记豁免或入 14 §1 清单,
  防无声渗入。14 §2 G2"允许暂混"的既知边入豁免表留痕。

不实现(正交面): L3 kernel 零第三方 = check_layer_deps.py 已覆盖(R254 §2.1
选型: 不引 import-linter 依赖, 纯 stdlib 与既有 20+ check_*.py 同形态)。

豁免表纪律(import-linter ignore_imports 语义借鉴, 不引依赖):
- 每条 (源文件, 目标) 精确粒度豁免, 必须带 14 文档编号 + 处置归属轮次
- 对应修复落地后必须同 commit 删豁免行(防永久豁免, check_layer_deps
  KNOWN_VIOLATION_EDGES 同纪律)
- 豁免目标不再命中 → 提示面输出(不阻断; 防豁免腐烂告警面,
  import-linter unmatched_ignore_imports_alerting 弱化版)

用法:
    python scripts/check_layering.py            # 校验, 违规 exit 1
    python scripts/check_layering.py --json     # JSON 输出
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "ai_prompt_toolkit"
sys.path.insert(0, str(ROOT / "scripts"))

from check_layer_deps import kernel_files  # noqa: E402  单一真源, 零复制

# io 顶层模块(14 §1 第三行)+ cli 包 + adapters 模块(14 §1 第四行):
# rules/kernel 层禁止 import(依赖方向铁律: 只允许上层 import 下层)
FORBIDDEN_TARGETS: dict[str, str] = {
    "cli_core": "io(14 §1 第三行)",
    "cli_helpers": "io(14 §1 第三行)",
    "cli_error_formatter": "io(14 §1 第三行)",
    "config": "io(14 §1 第三行)",
    "promptkit_config": "io(14 §1 第三行)",
    "data_reader": "io(14 §1 第三行)",
    "cli": "io/cli 包(14 §1 第三行)",
    "dataset_api": "adapters(14 §1 第四行)",
    "playground": "adapters(14 §1 第四行)",
    "market": "adapters(14 §1 第四行)",
    "ab_test": "adapters(14 §1 第四行)",
    "linter/lsp_server": "adapters(14 §1 第四行, 位置在 linter/ 包内=V6 同族)",
}

# R254-P4-10 留痕豁免面: (源文件相对包根, 目标) → 理由。
# 豁免纪律: 每条带 14 文档编号 + 处置归属轮次; 修复落地同 commit 删行(防永久豁免)。
# 粒度=(源, 目标) 精确对, 非文件级通配: 豁免文件的新跨层目标仍红。
# 首跑实证基线(R254 预扫): 全部 linter/ 第一方 import 边中仅 2 条未豁免跨层边。
KNOWN_CROSS_LAYER_EDGES: dict[tuple[str, str], str] = {
    # L1: 模板发现职责渗入规则层(14 §2 G6 发现/配置散落同族); R254 预扫实证=
    # R233 手测未登记的包内跨层边(14 §3 只列第三方边)。函数内延迟 import
    # discover_templates(测试套件发现模板, 测试面非 lint 主路径)。
    ("linter/test_suite.py", "cli_helpers"): (
        "L1(14 §2 G6: 模板发现是 io 职责; P4-07 窗口下沉 kernel 辅助或改路径传参)"
    ),
    # L2: 14 §2 G2"允许暂混"决策的显式登记面 — probe_framework 是纯 stdlib
    # 顶层模块(零第三方, 已核验), 实为 kernel 级(OWASP 2026 定义/探针框架),
    # 顶层位置=暂混。处置=P4-07 抽 kernel/ 子包时随迁 + 同 commit 删豁免行。
    ("linter/owasp_mapping.py", "probe_framework"): (
        "L2(14 §2 G2 暂混: probe_framework 纯 stdlib 实为 kernel 级; P4-07 抽 kernel/ 子包随迁)"
    ),
}


def first_party_import_targets(path: Path, src: Path) -> set[str]:
    """解析文件全部第一方 import 的完整模块路径(模块面, 不含纯符号名)。

    覆盖四形态:
    1. import ai_prompt_toolkit.x(.y)
    2. from ai_prompt_toolkit.x import y  (y 是符号名, 不产额外目标)
    3. from .x import y / from . import x (相对 1 级: 自身包内)
    4. from ..x import y / from .. import x (相对 2 级: 上级包内)
    符号级跨层 import(如 from ai_prompt_toolkit.cli_helpers import f)由
    形态 2 的模块路径 cli_helpers 覆盖, 无遗漏面; `from <pkg> import name` 的
    name 是符号名/子模块名同形歧义面, 按**文件存在性过滤**区分(__version__
    等符号名 → False 跳过; 真实子模块 → True 纳入判定)。显式模块路径形态
    (1/2)不受存在性过滤——import 了该路径即模块引用, 无论本地是否有文件。
    """
    rel = path.relative_to(src)
    # 文件所在目录的包路径分量: linter/f.py → ('linter',); f.py → ()
    # (rel.parent.parts: PurePath('.').parts == (), 不含根标记, 防双点)
    base_parts = list(rel.parent.parts)
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "ai_prompt_toolkit" or a.name.startswith("ai_prompt_toolkit."):
                    out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module == "ai_prompt_toolkit" or (node.module and node.module.startswith("ai_prompt_toolkit.")):
                    out.add(node.module)
                    # from ai_prompt_toolkit import name: name 可能是子模块
                    # (存在性过滤: __version__ 等符号名跳过)
                    if node.module == "ai_prompt_toolkit":
                        for a in node.names:
                            if _name_is_module(src, a.name):
                                out.add("ai_prompt_toolkit." + a.name)
            else:
                parts = list(base_parts)
                up = node.level - 1
                if up > 0:
                    parts = parts[:-up] if up <= len(parts) else []
                if node.module:
                    out.add("ai_prompt_toolkit." + ".".join(parts + [node.module]))
                else:
                    # from . import x / from .. import x: x 可能是子模块
                    # (存在性过滤, 相对 base 目录)
                    base_dir = src / Path(*parts) if parts else src
                    for a in node.names:
                        if _name_is_module(base_dir, a.name):
                            out.add("ai_prompt_toolkit." + ".".join(parts + [a.name]))
    return out


def _name_is_module(base: Path, name: str) -> bool:
    """name 相对 base 目录是否为模块(子包含 __init__.py 或 .py 文件); 符号名 False。"""
    p = base / name
    if p.is_dir():
        return (p / "__init__.py").exists()
    return (base / (name + ".py")).exists()


def _target_key(mod: str) -> str:
    """完整模块路径 → 判定键: 顶层模块名, 或 linter/ 内文件的 'linter/名'。

    ai_prompt_toolkit            → '' (裸包, 不判)
    ai_prompt_toolkit.cli_helpers → cli_helpers
    ai_prompt_toolkit.linter.rules → linter/rules
    ai_prompt_toolkit.types      → types
    """
    if mod == "ai_prompt_toolkit":
        return ""
    sub = mod[len("ai_prompt_toolkit.") :]
    if sub.startswith("linter."):
        return "linter/" + sub[len("linter.") :]
    return sub.split(".")[0] if sub else ""


def scan(src: Path, kernel: set[str], exempt: dict[tuple[str, str], str]) -> dict:
    """分层扫描纯函数。

    src: 包根目录(含 __init__.py 的包, 如 src/ai_prompt_toolkit)
    kernel: kernel 层文件相对路径集合(posix, 如 {'types.py', 'linter/rules.py'})
    exempt: (源相对路径, 目标键) → 理由 的留痕豁免表
    返回: {missing_kernel_files, violations, exemptions_hit, unused_exemptions, ok}
    """
    missing = [f for f in sorted(kernel) if not (src / f).exists()]
    linter_files = sorted((src / "linter").rglob("*.py")) if (src / "linter").is_dir() else []

    violations: list[dict[str, str]] = []
    exempt_hit: set[tuple[str, str]] = set()

    for py in linter_files:
        rel = py.relative_to(src).as_posix()
        is_kernel = rel in kernel
        for mod in sorted(first_party_import_targets(py, src)):
            key = _target_key(mod)
            if not key:
                continue
            # L1: linter/ 全部(kernel+rules 扩展)→ io/adapters 禁入面
            if key in FORBIDDEN_TARGETS:
                edge = (rel, key)
                if edge in exempt:
                    exempt_hit.add(edge)
                    continue
                violations.append(
                    {
                        "file": rel,
                        "target": key,
                        "import": mod,
                        "check": f"L1 rules→{FORBIDDEN_TARGETS[key]}",
                    }
                )
            # L2: kernel → 第一方非 kernel 目标(全第一方面, 含顶层暂混模块)
            if is_kernel:
                cand = key + ".py"  # 'types.py' / 'linter/x.py' / 顶层 'x.py'
                if cand not in kernel:
                    edge = (rel, key)
                    if edge in exempt:
                        exempt_hit.add(edge)
                        continue
                    violations.append(
                        {
                            "file": rel,
                            "target": key,
                            "import": mod,
                            "check": "L2 kernel→非kernel",
                        }
                    )

    unused = [f"{s} → {t}" for (s, t) in sorted(exempt) if (s, t) not in exempt_hit]
    return {
        "missing_kernel_files": missing,
        "violations": violations,
        "exemptions_hit": sorted(f"{s} → {t}" for s, t in exempt_hit),
        "unused_exemptions": unused,
        "ok": not violations and not missing,
    }


def main() -> int:
    kernel = {p.relative_to(SRC).as_posix() for p in kernel_files()}
    result = scan(SRC, kernel, KNOWN_CROSS_LAYER_EDGES)

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    if result["missing_kernel_files"]:
        print("✗ kernel 清单文件缺失(清单与代码漂移, 同步 docs/planning/14 §1):")
        for m in result["missing_kernel_files"]:
            print(f"  ✗ {m}")
        return 1

    print(f"分层方向验证: L1 rules→io/adapters / L2 kernel 第一方纯度(留痕豁免 {len(result['exemptions_hit'])} 条命中)")
    for u in result["unused_exemptions"]:
        print(f"  (提示) 豁免未命中={u} — 对应边已消失, 同 commit 删豁免行(防永久豁免)")
    if result["violations"]:
        print("✗ 跨层 import 违规(04 §1 依赖方向铁律: 只允许上层 import 下层):")
        for v in result["violations"]:
            print(f"  ✗ [{v['check']}] {v['file']}: import {v['import']} (目标 {v['target']})")
        print("修复: 依赖移上层(io/adapters); 属合法 kernel 模块则同步 14 §1 清单")
        print("      (check_layer_deps.kernel_files); 确属既知暂混面 → 登记")
        print("      KNOWN_CROSS_LAYER_EDGES(带 14 编号+处置轮次, 修复时同 commit 删)")
        return 1
    print("✓ 无未豁免跨层 import(L1/L2 全过; 既知暂混面已留痕豁免)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
