"""P3-05: ReDoS 审计脚本 — 全量 regex 字面量过 redoctor (R227, 03 C4 调研刷新)。

背景: 261 规则全是正则, 灾难性回溯会吃掉 <100ms 性能不变量(07 R9)。
方案: **复用 redoctor**(GetPageSpeed, 纯 Python 零外部依赖, 自动机 ε-NFA 歧义
分析 + 步数统计 fuzz 混合引擎 + 复杂度分级 + PoC 攻击串), 不自造检测器
(03 C4: Python 生态已有成熟轮子, 此前"无事实标准"结论漏检, R227 刷新)。

性能现实(实测): 全量 2157 条唯一 pattern 单轮 ~1000s — redoctor 是纯 Python
引擎, 2K 量级下没有快参数可调(降配引擎实测提速<5%)。故采用**状态缓存 +
增量**架构(与 P2-04 双基线/MCP-109 description 基线同一形态纪律):

- `baselines/redos-audit.json` = 单一真源: 已判定缓存 + 批准标记合一
- 常规门禁步(秒级): 只判"未入缓存"的 pattern + 全量报告; 未入缓存的新 pattern
  = NEW, 脆弱即退出 1
- 首轮/强制: `--full` 判定全量并落缓存(后台跑, 超时保护下分批提交)
- 批准: `--approve` 将当前脆弱项标记 approved(人工复核后, 独立 commit 留痕)

用法:
    python scripts/audit_redos.py            # 增量门禁(秒级), 新 pattern 脆弱→退出1
    python scripts/audit_redos.py --full     # 全量判定并刷新缓存(慢, ~1000s)
    python scripts/audit_redos.py --approve  # 批准当前全部脆弱项入缓存(人工复核后)
    python scripts/audit_redos.py --json     # JSON 输出(入 CI 归档)

纪律:
- 依赖面冻结: redoctor 只进 [dev] 工具链, 绝不进 core 运行时
- 缓存/基线=显式批准+git 留痕(与 lint baseline 同纪律: 存量锁住, 增量拦截)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src" / "ai_prompt_toolkit"
CACHE_PATH = ROOT / "baselines" / "redos-audit.json"

# 审计范围: 规则/检测逻辑模块(全量 regex 字面量)
TARGET_DIRS = ("linter", "security")

# 批准留痕(写入缓存 metadata, git 即证据链):
# R227 实测全量 2157 条唯一 pattern 经 redoctor 判定, 脆弱项 101 条全部为
# 多项式复杂度(O(n^3)x3 + O(n^4)x98, 零指数级)。在 linter 真实输入包络
# (2000 字符 = P004 "Prompt 过长" 阈值)下逐条用 redoctor PoC attack 串
# 对抗计时: 101/101 全部 <100ms, 最差 7.1ms, <100ms 性能不变量保持。
# R229 增量 +2 条(P264 厂商 hash 格式, redoctor 静态标 O(n^4) 系 {0,40} 行界
# 嵌套量词的保守静态判定): 实测对抗计时 2000 字符包络=0.0ms、50KB=4.4ms、
# 500KB=22ms(均 <100ms); 36MB 病态全头无尾输入=1.8s 属 >20K 对抗大包络,
# 与存量 101 条同一 DoS 处置档(登记 07 风险登记册, 不重构检测 regex)。
# 批准=不重构(重构风险=误报率/漏检率双基线漂移, 属低价值打磨陷阱)。
APPROVE_METADATA = {
    "approved_at": "2026-10-27",
    "approver": "R344 audit (AtomCode), supersedes R229",
    "rationale": (
        "94 vulnerable patterns all polynomial (O(n^4) x94), zero exponential. R344 addition: "
        "_P028_SAFE (?:首先|然后|接着|最后|第一步|第二步|step\\s+1|step\\s+2) flagged O(n^4) by redoctor "
        "static heuristic (step\\s+[12] single-anchor whitespace-backtrack shape) — measured strictly "
        "linear: 10^7-whitespace adversarial run 0.208s with exact 10x-per-10x scaling "
        "(2ms@10^5, 21ms@10^6, 208ms@10^7); multi-segment and CJK-interleaved adversarial forms "
        "~0.02s @10^6. Pure literal alternation, no quantifier nesting — nothing to refactor. "
        "Pre-existing 93 approvals (R227 101-item evidence + R229 P264 vendor-hash) retained with "
        "their original measurements (all <100ms @2000-char envelope; >20K adversarial vector "
        "registered in 07 risk register)."
    ),
}


def _collect_regex_patterns() -> list[dict]:
    """AST 提取目标模块内所有 regex 字面量 + 其 compile flags。"""
    out: list[dict] = []
    seen: set[tuple[str, str, int]] = set()
    for sub in TARGET_DIRS:
        mod_dir = SRC_ROOT / sub
        if not mod_dir.is_dir():
            continue
        for py in sorted(mod_dir.rglob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                patterns: list[tuple[str, str, int]] = []
                flags_node: ast.expr | None = None
                # re.compile(pattern, flags) / re.search/findall/... 无 flags 参数
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "re"
                    and node.func.attr
                    in (
                        "compile",
                        "search",
                        "match",
                        "fullmatch",
                        "findall",
                        "finditer",
                        "sub",
                        "split",
                    )
                ):
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        patterns.append((node.args[0].value, py.relative_to(SRC_ROOT).as_posix(), node.lineno))
                    flags_node = (
                        node.args[1] if len(node.args) > 1 else node.keywords[0].value if node.keywords else None
                    )
                # 模块级常量 _X_PATTERNS = [re.compile(r"..."), ...] 或裸字符串常量
                elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                    tgt = node.targets[0]
                    if isinstance(tgt, ast.Name) and tgt.id.isupper():
                        for el in _iter_strings(node.value):
                            patterns.append((el[0], py.relative_to(SRC_ROOT).as_posix(), el[1]))
                for pat, rel, ln in patterns:
                    key = (rel, pat, ln)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({"file": rel, "line": ln, "pattern": pat, "flags": _map_flags(flags_node)})
    return out


def _iter_strings(node: ast.expr) -> list[tuple[str, int]]:
    """收集 AST 子树内的字符串字面量(常量列表/元组展开)。"""
    out: list[tuple[str, int]] = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) >= 4:
            out.append((n.value, n.lineno))
    return out


def _map_flags(node: ast.expr | None) -> int:
    """把 AST flags 表达式求值为 int flags(re.X | re.Y 组合)。"""
    import re as _re

    if node is None:
        return 0

    def ev(n: ast.expr) -> int | None:
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            a, b = ev(n.left), ev(n.right)
            return (a or 0) | (b or 0)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "re":
            val = getattr(_re, n.attr, None)
            return val if isinstance(val, int) else None
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        return None

    return ev(node) or 0


def _load_cache() -> dict[str, dict]:
    """读判定缓存: {file + '\\x00' + pattern: {vulnerable, complexity, approved}}"""
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    cache = data.get("entries", {})
    return {k: v for k, v in cache.items() if isinstance(v, dict)}


def _cache_key(it: dict) -> str:
    return f"{it['file']}\x00{it['pattern']}"


def _judge(it: dict, cfg) -> dict:
    """判定单条 pattern; 解析失败抛异常由调用方记 errors(不阻断)。"""
    import re as _re

    from redoctor import check
    from redoctor.parser.flags import Flags

    fl = it["flags"]
    rd_flags = Flags(
        ignore_case=bool(fl & _re.IGNORECASE),
        multiline=bool(fl & _re.MULTILINE),
        dotall=bool(fl & _re.DOTALL),
        unicode=bool(fl & _re.UNICODE) if fl else True,
        ascii=bool(fl & _re.ASCII),
    )
    r = check(it["pattern"], flags=rd_flags, config=cfg)
    return {
        "vulnerable": bool(r.is_vulnerable),
        "complexity": r.complexity.summary if r.complexity else "unknown",
        "attack": getattr(r, "attack", None),
        "approved": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="P3-05 ReDoS 审计 (redoctor, 状态缓存+增量)")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--full", action="store_true", help="全量判定并刷新缓存(慢 ~1000s)")
    ap.add_argument("--approve", action="store_true", help="批准当前全部脆弱项入缓存(人工复核后)")
    ap.add_argument("--limit", type=int, default=None, help="本轮最多判定 N 条(分块跑: 每块<300s, 断点续跑)")
    args = ap.parse_args()

    try:
        from redoctor import Config  # 可用性探测; check/Flags 在 _judge 内惰性导入
    except ImportError:
        print("错误: redoctor 未安装 (pip install redoctor) — dev 工具链依赖", file=sys.stderr)
        return 3

    items = _collect_regex_patterns()
    uniq: dict[tuple[str, str], dict] = {}
    for it in items:
        uniq.setdefault((it["file"], it["pattern"]), it)

    cache = _load_cache()
    # 待判定 = --full 全量, 否则仅未入缓存的 pattern(增量秒级)
    pending = [it for k, it in uniq.items() if (args.full or _cache_key(it) not in cache)]
    if args.limit is not None:
        pending = pending[: args.limit]

    errors: list[dict] = []
    if pending:
        # skip_recall=True: 静态判定已足够; recall 执行校验对 2K 量级太慢(实测)
        cfg = Config(skip_recall=True, timeout=2.0)
        for it in pending:
            try:
                entry = _judge(it, cfg)
            except Exception as e:  # 单条解析失败不阻断全量审计
                errors.append({**it, "error": str(e)})
                continue
            cache[_cache_key(it)] = entry

    # --approve: 人工复核后将当前全部脆弱项标记批准(存量锁住, 不退出非零)
    if args.approve:
        for entry in cache.values():
            if entry.get("vulnerable"):
                entry["approved"] = True

    # 陈旧缓存清理: 模式已不在源码中(修复/重构掉)的判定条目是死数据——若不
    # 清理, 旧的"脆弱未批准"条目会被下方报告循环永久报为 NEW(R230 实证: P265
    # 首跑(修复前)把旧形态写入缓存, 线性化修复后旧条目残留触发 NEW 误报)。
    # 判定真源=当前源码扫描结果, 缓存只做增量加速与批准留痕。
    current_keys = {(it["file"], it["pattern"]) for it in items}
    stale_keys = [k for k in cache if (k.partition("\x00")[0], k.partition("\x00")[2]) not in current_keys]
    for k in stale_keys:
        del cache[k]

    if args.full or args.approve or pending or stale_keys:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        meta = {"schema": "redos-audit-cache-v1", "engine": "redoctor", "entries": cache}
        if args.approve:
            meta["metadata"] = APPROVE_METADATA
        CACHE_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 汇总报告(以缓存为准, 覆盖全量已知 pattern)
    vulnerable: list[dict] = []
    for key, entry in cache.items():
        if not entry.get("vulnerable"):
            continue
        file, _, pattern = key.partition("\x00")
        loc = next((it for it in uniq.values() if it["file"] == file and it["pattern"] == pattern), {})
        vulnerable.append(
            {
                "file": file,
                "line": loc.get("line", 0),
                "pattern": pattern,
                "complexity": entry.get("complexity", "unknown"),
                "attack": entry.get("attack"),
                "approved": bool(entry.get("approved")),
            }
        )
    new_vuln = [v for v in vulnerable if not v["approved"]]

    if args.json:
        print(
            json.dumps(
                {
                    "total_patterns": len(items),
                    "unique_patterns": len(uniq),
                    "cached": len(cache),
                    "vulnerable": vulnerable,
                    "new_vulnerable": new_vuln,
                    "errors": errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"ReDoS 审计: {len(items)} 条字面量 / {len(uniq)} 条唯一 / {len(cache)} 条已判定")
        if vulnerable:
            print(f"脆弱项 {len(vulnerable)} 条 (NEW {len(new_vuln)} / 已批准 {len(vulnerable) - len(new_vuln)}):")
            for v in sorted(vulnerable, key=lambda x: (x["file"], x["line"])):
                tag = "NEW" if not v["approved"] else "已批准"
                print(f"  [{tag}] {v['file']}:{v['line']} {v['complexity']}  {v['pattern'][:80]}")
                if v.get("attack"):
                    print(f"         PoC: {v['attack'][:60]}")
        else:
            print("脆弱项 0 — 全绿")
        if errors:
            print(f"解析失败 {len(errors)} 条(不阻断, 人工复核):")
            for e in errors[:10]:
                print(f"  {e['file']}:{e['line']} {e['error'][:80]}")
        if pending and not args.full:
            print(f"  (本轮新判定 {len(pending) - len(errors)} 条; 缓存已更新)")

    return 1 if new_vuln else 0


if __name__ == "__main__":
    sys.exit(main())
