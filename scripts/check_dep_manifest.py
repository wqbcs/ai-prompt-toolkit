"""R225-P0-05: 依赖清单一致性校验 — jinja2 未声明事故的反向护栏

历史事故(R223 五连红同源): 本地 venv 有未声明依赖(jinja2 等),
src 运行时 import 了它但 pyproject 未声明 → 本地全绿, CI 干净环境静默降级丢数据。

本脚本断言: **src 运行时 import 的第三方顶层包 ⊆ pyproject [project] dependencies 声明**
- 标准库(PEP 3107 sys.stdlib_module_names)排除
- 第一方(ai_prompt_toolkit)排除
- `if TYPE_CHECKING:` 块内 import 不算运行时(类型标注用途)
- 第三方包名→顶层 import 名映射见 PKG_IMPORT_MAP(仅登记与发行名不同的包)

新增可选依赖组([ab_test]/[lsp]/[full])中的包, 若被 src 顶层路径运行时 import,
同样必须声明 — 除非该 import 在显式标记的"可选功能降级"点(见 OPTIONAL_IMPORT_MARKERS)。

用法:
    python scripts/check_dep_manifest.py            # 校验, 违规 exit 1
    python scripts/check_dep_manifest.py --json     # JSON 输出
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "ai_prompt_toolkit"
PYPROJECT = ROOT / "pyproject.toml"

# 发行名 → 顶层 import 名(仅登记不一致的; 一致的 click/rich/jsonschema/cachetools/jinja2 免登)
PKG_IMPORT_MAP: dict[str, list[str]] = {
    "pyyaml": ["yaml"],
}

# 可选功能降级点: 这些文件里的 import 允许走 except ImportError 降级/惰性加载,
# 未声明时不判违规。登记纪律: 每个文件必须写明降级行为, 且降级不得静默丢数据
# (R223 jinja2 教训) — 新登记必须过 code review
OPTIONAL_IMPORT_FILES = {
    "linter/lsp_server.py",  # pygls/lsprotocol: [lsp] 可选组
    "judge.py",  # scipy/numpy: [ab_test] 可选组
    "statistics.py",  # scipy/numpy: [ab_test] 可选组
    "market/api.py",  # fastapi: [full] 可选组
    "huawei_cloud/iam.py",  # 华为云 SDK: 云端可选
    # R225 初跑检出的 9 处, 逐一审定降级行为后登记:
    "ab_test/provider.py",  # httpx: [ab_test] 组; 惰性import+缺依赖时抛ProviderError带pip提示
    "ab_test/providers/ascend_npu.py",  # mindspore_lite: 昇腾设备专有SDK; 惰性+缺依赖时模拟推理fallback(显式标注)
    "ab_test/providers/huawei_modelarts.py",  # httpx: [ab_test] 组; 惰性+ProviderError带pip提示
    "cli/commands/template_commands.py",  # uvicorn: [full] 组(serve命令); 惰性+缺依赖时exit 2带pip提示
    "dataset_api.py",  # fastapi: 仅被 playground/server 导入(即 serve 命令链路, [full] 组)
    "playground/server.py",  # fastapi/starlette: [full] 组; serve 命令专用 Web 面
    "linter/token_analyzer.py",  # tiktoken: 惰性+缺依赖时回退字符数估算(估算精度降, 不丢数据)
    "multimodal_token_counter.py",  # tiktoken: 惰性+缺依赖时回退估算
    "schema.py",  # pydantic: 模块级try, _HAS_PYDANTIC 标志+完整手写验证fallback
}

# 已知合法的非 pyproject 包(系统级/构建期, 运行时不依赖)
ALLOWED_UNDECLARED: set[str] = {
    "setuptools",  # 构建期, importlib.metadata 读取
}


def declared_packages() -> dict[str, list[str]]:
    """pyproject [project] dependencies → {发行名: [顶层import名]}"""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps: list[str] = data.get("project", {}).get("dependencies", [])
    result: dict[str, list[str]] = {}
    for dep in deps:
        m = re.match(r"^([A-Za-z0-9._\-]+)", dep)
        if not m:
            continue
        pkg = m.group(1).lower()
        result[pkg] = PKG_IMPORT_MAP.get(pkg, [pkg.lower().replace("-", "_")])
    return result


def runtime_imports(path: Path) -> set[str]:
    """提取文件的运行时顶层 import 名(排除 TYPE_CHECKING 块)"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    # 剔除 TYPE_CHECKING 块内的 import(按行号匹配 If 块)
    tc_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            is_tc = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
                isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
            )
            if is_tc:
                for sub in ast.walk(node):
                    if isinstance(sub, (ast.Import, ast.ImportFrom)):
                        tc_lines.add(sub.lineno)
    if tc_lines:
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and node.lineno not in tc_lines:
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.lineno not in tc_lines:
                    names.add(node.module.split(".")[0])
    return names


def optional_file(path: Path) -> bool:
    rel = path.relative_to(SRC).as_posix()
    return rel in OPTIONAL_IMPORT_FILES


def main() -> int:
    declared = declared_packages()
    import_names: set[str] = {n for imports in declared.values() for n in imports}
    import_names |= {"ai_prompt_toolkit", "setuptools"}  # 第一方
    stdlib = set(sys.stdlib_module_names)

    violations: list[dict[str, str]] = []
    checked_files = 0
    for py in sorted(SRC.rglob("*.py")):
        checked_files += 1
        for name in runtime_imports(py):
            if name in stdlib or name in import_names or name in ALLOWED_UNDECLARED:
                continue
            if optional_file(py):
                continue  # 可选功能降级点, 豁免(见 OPTIONAL_IMPORT_FILES 注释)
            violations.append({
                "file": py.relative_to(ROOT).as_posix(),
                "import": name,
            })

    if "--json" in sys.argv:
        print(json.dumps({
            "checked_files": checked_files,
            "declared": sorted(declared),
            "violations": violations,
            "ok": not violations,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"依赖清单一致性: 扫描 {checked_files} 文件, 声明 {len(declared)} 个 core 包")
        if violations:
            print("✗ 运行时 import 了未声明的包(jinja2 事故类缺陷):")
            for v in violations:
                print(f"  ✗ {v['file']}: import {v['import']}")
            print("修复: 加进 pyproject [project] dependencies, 或确认属可选功能降级点后登记 OPTIONAL_IMPORT_FILES")
            return 1
        print("✓ src 运行时 import ⊆ pyproject core 声明")
    return 0


if __name__ == "__main__":
    sys.exit(main())
