# 条件编译命令行入口 (__main__)

> 完整的Python命令行入口，可直接运行

```python
"""
条件编译命令行入口

用法:
    python -m _compiler --source input.md --output output.md --var lang=zh --flag debug
    python -m _compiler --source input.md --env prod --fallback warn
    python -m _compiler --source input.md --report-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List


# ──────────────────────────────────────────
#  参数解析
# ──────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    p = argparse.ArgumentParser(
        prog="conditional-compile",
        description="条件编译运行时 — 将包含条件指令的文本编译为最终输出",
    )

    p.add_argument(
        "--source", "-s",
        type=str,
        required=True,
        help="源文件路径",
    )
    p.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出文件路径（默认 stdout）",
    )
    p.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="变量定义（可多次使用）",
    )
    p.add_argument(
        "--flag",
        action="append",
        default=[],
        metavar="FLAG",
        help="功能标志（可多次使用）",
    )
    p.add_argument(
        "--env",
        type=str,
        default="dev",
        choices=["dev", "staging", "prod"],
        help="环境名称（默认 dev）",
    )
    p.add_argument(
        "--fallback",
        type=str,
        default="warn",
        choices=["empty", "skip", "warn"],
        help="回退策略（默认 warn）",
    )
    p.add_argument(
        "--report-only",
        action="store_true",
        help="仅输出编译报告，不输出编译结果",
    )
    p.add_argument(
        "--report-file",
        type=str,
        default=None,
        help="将报告写入指定 JSON 文件",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="禁用缓存",
    )
    p.add_argument(
        "--cache-size",
        type=int,
        default=128,
        help="缓存最大条目数（默认 128）",
    )

    return p


# ──────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────

def parse_variables(var_list: List[str]) -> Dict[str, Any]:
    """解析 --var KEY=VALUE 参数

    支持自动类型推断: int / float / bool / str
    """
    result: Dict[str, Any] = {}
    for item in var_list:
        if "=" not in item:
            print(f"警告: 忽略无效变量定义 {item!r}（格式应为 KEY=VALUE）", file=sys.stderr)
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = _infer_type(value.strip())
    return result


def _infer_type(value: str) -> Any:
    """自动推断字符串的类型"""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


# ──────────────────────────────────────────
#  编译管线
# ──────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> Dict[str, Any]:
    """执行完整编译管线

    Returns:
        包含 output / report / timing 的字典
    """
    from lexer import Lexer
    from parser import Parser
    from evaluator import CompilationContext
    from renderer import render, FallbackStrategy
    from cache import LRUCache

    start_time = time.monotonic()

    # ── 读取源文件 ──
    source_path = Path(args.source)
    if not source_path.exists():
        raise FileNotFoundError(f"源文件不存在: {source_path}")

    source = source_path.read_text(encoding="utf-8")

    # ── 解析变量和标志 ──
    variables = parse_variables(args.var)
    flags = set(args.flag)

    # ── 缓存 ──
    cache: LRUCache | None = None
    if not args.no_cache:
        cache = LRUCache(max_size=args.cache_size, ttl_seconds=3600)
        cache_key = LRUCache.make_key(source, variables, args.env)
        cached = cache.get(cache_key)
        if cached is not None:
            elapsed = time.monotonic() - start_time
            return {
                "output": cached,
                "report": {"cache_hit": True, "elapsed_seconds": round(elapsed, 4)},
                "timing": elapsed,
            }
    else:
        cache_key = ""

    # ── 词法分析 ──
    tokens = Lexer.tokenize(source)

    # ── 语法解析 ──
    ast = Parser.parse(tokens)

    # ── 条件求值 + 渲染 ──
    ctx = CompilationContext(variables=variables, flags=flags, env=args.env)
    fallback = FallbackStrategy(args.fallback)
    output, report = render(ast, ctx, fallback)

    # ── 写入缓存 ──
    if cache is not None and cache_key:
        cache.put(cache_key, output)

    elapsed = time.monotonic() - start_time

    return {
        "output": output,
        "report": {
            "cache_hit": False,
            "output_length": report.output_length,
            "conditions_evaluated": report.conditions_evaluated,
            "conditions_matched": report.conditions_matched,
            "warnings": report.warnings,
            "branches_taken": report.branches_taken,
            "elapsed_seconds": round(elapsed, 4),
        },
        "timing": elapsed,
    }


# ──────────────────────────────────────────
#  主入口
# ──────────────────────────────────────────

def main(argv: List[str] | None = None) -> int:
    """命令行主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_pipeline(args)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"编译失败: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    output_text = result["output"]
    report_data = result["report"]

    # ── 输出结果 ──
    if not args.report_only:
        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"输出已写入: {args.output}")
        else:
            print(output_text)

    # ── 输出报告 ──
    if args.report_file:
        Path(args.report_file).write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"报告已写入: {args.report_file}")
    else:
        print("\n── 编译报告 ──")
        for key, value in report_data.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```
