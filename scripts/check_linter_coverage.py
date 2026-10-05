"""R232-P3-09: linter 包覆盖率棘轮(90%, 只收紧不放松)。

覆盖率数字从"展示"变"门禁": 覆盖率是"尺子可信"的机器护栏——规则越多,
未被测试触碰的规则分支越多, 整体覆盖率下降=检测面在裸奔。

设计(对抗性审查后):
1. 口径=行覆盖(coverage.xml 的 lines), 分支覆盖只记录不门禁(分支率受
   exclude_lines/防御分支影响, 棘轮信号噪声大)。
2. 范围=ai_prompt_toolkit/linter/ 全包(规则+引擎+waiver/baseline 等)。
   实测基线: 92.44% (5542/5995, R232 收口时 pytest 全量)。
3. 棘轮语义: 低于 90% 即红; 90% 是地板不是目标——未来只允许调高
   (改本常量=独立 commit+理由, 与 mypy 棘轮同纪律)。
4. 数据来源: 同一进程链上游的 pytest --cov 生成的 coverage.xml。
   CI 接在 test 作业"Run tests"之后(数据与判定同作业, 无陈旧问题);
   本地 release_gate 该步放在第 1 步(pytest)之后跑才有数据。
5. 无 coverage.xml / 无 linter 行数据 → 红(诚实失败: 覆盖率门禁缺数据
   不可静默放行, 与 mypy 棘轮"缺基线文件即红"同惯例)。

用法:
    python scripts/check_linter_coverage.py            # <90% 红
    python scripts/check_linter_coverage.py --min 92   # 临时收紧检查
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MIN = 90.0  # R232-P3-09 棘轮地板(实测 92.44% 起步, 只升不降)
LINTER_MARKER = "linter"  # 源路径含该段= linter 包


def measure_linter_coverage(xml_path: Path) -> tuple[int, int]:
    """从 coverage.xml 提取 linter 包的 (covered, total) 行覆盖。"""
    root = ET.parse(xml_path).getroot()
    packages = root.find("packages")
    if packages is None:
        return 0, 0
    covered = total = 0
    for pkg in packages.findall("package"):
        classes = pkg.find("classes")
        if classes is None:
            continue
        for cls in classes.findall("class"):
            if LINTER_MARKER not in (cls.get("filename") or ""):
                continue
            lines_el = cls.find("lines")
            if lines_el is None:
                continue
            for line in lines_el.findall("line"):
                total += 1
                if line.get("hits") not in ("0", None):
                    covered += 1
    return covered, total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=float, default=DEFAULT_MIN, help=f"覆盖率地板%%(默认 {DEFAULT_MIN})")
    ap.add_argument("--xml", default="coverage.xml", help="coverage.xml 路径(默认 仓库根)")
    args = ap.parse_args()

    xml_path = ROOT / args.xml
    if not xml_path.exists():
        print(f"✗ 缺 {xml_path} — 先跑带 --cov 的 pytest(门禁缺数据不静默放行)")
        return 1

    covered, total = measure_linter_coverage(xml_path)
    if total == 0:
        print("✗ coverage.xml 无 linter 行数据 — 门禁缺数据不静默放行")
        return 1

    pct = covered / total * 100
    print(f"linter 包行覆盖: {pct:.2f}% ({covered}/{total}) | 棘轮地板: {args.min:.1f}%")
    if pct < args.min:
        print(f"✗ 覆盖率低于棘轮地板 — 新代码未带测试, 禁止收口(只收紧不放松)")
        return 1
    print("✓ 覆盖率棘轮通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
