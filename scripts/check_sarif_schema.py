"""R246-P2-07: SARIF 离线结构 validator

收口 02 板 P2-07 验收"SARIF 过 validator"的**离线口径**：
- 零网络（不拉 OASIS 官方 JSON schema——schema 数 MB 且需联网，破坏楔子
  "离线可跑"；air-gap/信创场景不可用）
- 零新依赖（stdlib json 断言）
- 校验 Code Scanning 上传必需的结构子集：$schema / version=2.1.0 /
  runs[] 非空 / tool.driver.name+version / results[].ruleId+level+message.text /
  locations[].physicalLocation.artifactLocation.uri

GitHub Code Scanning 上传侧的完整校验由 CI 既有 upload-sarif 动作兜底；
本脚本是**本地门禁**的机器护栏（同一 SARIF 本地就能裁决，不依赖上传结果）。

退出码: 0=结构合法, 1=结构非法, 2=参数/文件错误
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SARIF_LEVELS = {"none", "note", "warning", "error"}


def _fail(msg: str) -> int:
    print(f"✗ SARIF 结构校验失败: {msg}")
    return 1


def validate_sarif(data: dict) -> int:
    """对 SARIF dict 做结构子集校验。0=合法, 1=非法。"""
    if data.get("version") != "2.1.0":
        return _fail(f"version != 2.1.0: {data.get('version')!r}")
    if "$schema" not in data:
        return _fail("$schema 缺失")

    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        return _fail("runs 缺失或为空")

    for i, run in enumerate(runs):
        if not isinstance(run, dict):
            return _fail(f"runs[{i}] 非对象")
        driver = run.get("tool", {}).get("driver", {})
        if not driver.get("name"):
            return _fail(f"runs[{i}].tool.driver.name 缺失")
        if not driver.get("version"):
            return _fail(f"runs[{i}].tool.driver.version 缺失")

        for j, result in enumerate(run.get("results", [])):
            if not result.get("ruleId"):
                return _fail(f"runs[{i}].results[{j}].ruleId 缺失")
            level = result.get("level")
            if level not in _SARIF_LEVELS:
                return _fail(f"runs[{i}].results[{j}].level 非法: {level!r}")
            msg = result.get("message", {}).get("text")
            if not isinstance(msg, str) or not msg:
                return _fail(f"runs[{i}].results[{j}].message.text 缺失")
            # locations 存在时结构必须完整
            for k, loc in enumerate(result.get("locations", [])):
                phys = loc.get("physicalLocation", {})
                if "artifactLocation" not in phys:
                    return _fail(f"runs[{i}].results[{j}].locations[{k}].physicalLocation.artifactLocation 缺失")
                if not phys["artifactLocation"].get("uri"):
                    return _fail(f"runs[{i}].results[{j}].locations[{k}].physicalLocation.artifactLocation.uri 缺失")
                region = phys.get("region")
                if region is not None:
                    line = region.get("startLine")
                    if not isinstance(line, int) or line < 1:
                        return _fail(f"runs[{i}].results[{j}].locations[{k}].region.startLine 非法: {line!r}")

    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"用法: {argv[0]} <report.sarif>")
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"✗ 文件不存在: {path}")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return _fail(f"非法 JSON: {e}")
    if not isinstance(data, dict):
        return _fail("顶层非对象")
    rc = validate_sarif(data)
    if rc == 0:
        n = sum(len(r.get("results", [])) for r in data.get("runs", []))
        print(f"✓ SARIF 结构 OK: {n} results, version 2.1.0")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
