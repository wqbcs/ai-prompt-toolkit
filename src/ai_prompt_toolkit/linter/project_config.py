"""P2-03: 项目级 lint 配置发现 — promptlint.toml / pyproject.toml [tool.promptlint]

对标 ruff 配置发现惯例(03 §E2): 双位置 + 目录向上查找 + 项目根锚定。
不重复造轮子: 消费层复用 LintConfig 数据模型(lint_config.py), 本模块只做
发现 + TOML 解析 + 校验, 把结果映射进 LintConfig 既有字段与三个新增字段
(severity_overrides/waivers/gap_max_rate) — YAML 加载路径零改动。

Schema 最小面(02 P2-03 / R233 §3.2, 对标 promptlint .promptlintrc 并集最小面):

    # promptlint.toml (或 pyproject.toml 的 [tool.promptlint] 段)
    include_rules = ["P1"]          # 前缀支持(同 CLI --rules 的 expand 语义)
    exclude_rules = ["P048"]
    fail_on = "high"                # 可选 critical/high/medium, CLI --fail-on 优先
    waivers = ["P119"]              # 全局 waiver 列表(配置级, git 史为审计留痕)
    [severity_overrides]
    P012 = "low"
    [gap]
    max_rate = 0.86                 # gap-report 门禁: 平均缺口率超阈值退出码1

纪律:
- fail-safe: 未知规则ID/非法值 → stderr 警告并忽略, 不崩 lint(与 waiver 同纪律)
- 协议面: 发现/加载信息走 stderr 或 CLI 层 echo, 不污染 --json/--stdio stdout
- 分层: 本模块只依赖 stdlib + LintConfig, 无 CLI/click 依赖(P4-01 层ing纪律)
"""

from __future__ import annotations

import sys
from pathlib import Path

from ai_prompt_toolkit.linter.lint_config import LintConfig

# 发现候选(就近优先: 每层先 promptlint.toml 后 pyproject.toml)
_CONFIG_NAMES = ("promptlint.toml", "pyproject.toml")
_VALID_FAIL_ON = ("critical", "high", "medium")
_VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")
_KNOWN_KEYS = ("include_rules", "exclude_rules", "fail_on", "waivers", "severity_overrides", "gap")


def _read_toml(path: Path) -> dict:
    """读 TOML; 解析失败/缺依赖 → {} (fail-safe, 配置不该弄崩 lint)"""
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomli as tomllib
            except ImportError:
                return {}
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:  # OSError/TOMLDecodeError 等 — 配置不该弄崩 lint
        print(f"promptlint 配置解析失败(已忽略, 使用默认配置): {path}: {e}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _promptlint_section(path: Path) -> dict:
    """取配置段: pyproject 只认 [tool.promptlint]; promptlint.toml 三态兼容
    ([tool.promptlint] 表 / [promptlint] 表 / 顶层裸键)"""
    from typing import Any, cast

    data = _read_toml(path)
    if path.name == "pyproject.toml":
        tool = data.get("tool", {})
        return cast("dict[str, Any]", tool.get("promptlint", {}))
    for section in (data.get("tool", {}).get("promptlint"), data.get("promptlint")):
        if isinstance(section, dict):
            return section
    # 顶层裸键(promptlint.toml 允许不套表头)
    return {k: v for k, v in data.items() if not isinstance(v, dict) or k in ("gap", "severity_overrides")}


def find_project_config(start_dir: Path | None = None) -> Path | None:
    """从 start_dir(默认 cwd)向上查找项目配置, 锚定 git 根或文件系统根。

    ruff 语义: 每层检查 promptlint.toml → pyproject.toml(须含 [tool.promptlint]
    段, 否则跳过), 第一个命中即返回(就近优先)。
    """
    cur = (start_dir or Path.cwd()).resolve()
    while True:
        for name in _CONFIG_NAMES:
            candidate = cur / name
            if candidate.is_file():
                if name == "pyproject.toml":
                    section = _promptlint_section(candidate)
                    if section:
                        return candidate
                else:
                    return candidate
        # git 根锚定: 本层是 git 根(检查完即停)或到文件系统根
        if (cur / ".git").exists() or cur.parent == cur:
            return None
        cur = cur.parent


def load_project_config(path: Path | None) -> LintConfig:
    """解析项目配置 → LintConfig(未知键进 extra 留痕; 非法值 fail-safe 忽略)"""
    if path is None:
        return LintConfig()
    section = _promptlint_section(path)
    warnings: list[str] = []

    def _str_list(key: str) -> list[str]:
        v = section.get(key, [])
        if isinstance(v, list):
            return [str(x) for x in v]
        if v:
            warnings.append(f"{key} 应为字符串数组, 已忽略: {v!r}")
        return []

    def _check_rule_ids(ids: list[str], key: str) -> list[str]:
        from ai_prompt_toolkit.linter.rules import get_all_rules  # 局部导入防循环引用

        known = {r.rule_id for r in get_all_rules()}
        out: list[str] = []
        for tok in ids:
            tok = tok.strip().upper()
            if not tok:
                continue
            # 前缀容忍(与 expand_rule_ids 同语义): 精确命中或有前缀展开即合法
            if tok in known or any(r.startswith(tok) for r in known):
                out.append(tok)
            else:
                warnings.append(f"{key}: 未知规则ID {tok} 已忽略")
        return out

    severity_overrides: dict[str, str] = {}
    raw_overrides = section.get("severity_overrides", {})
    if isinstance(raw_overrides, dict):
        from ai_prompt_toolkit.linter.rules import get_all_rules

        known = {r.rule_id for r in get_all_rules()}
        for rule_id, sev in raw_overrides.items():
            rid = str(rule_id).upper()
            sev_s = str(sev).lower()
            if sev_s not in _VALID_SEVERITIES:
                warnings.append(f"severity_overrides: {rid} 的严重度 {sev!r} 非法, 已忽略")
                continue
            if rid in known or any(r.startswith(rid) for r in known):
                severity_overrides[rid] = sev_s
            else:
                warnings.append(f"severity_overrides: 未知规则ID {rid} 已忽略")
    elif raw_overrides:
        warnings.append(f"severity_overrides 应为表, 已忽略: {raw_overrides!r}")

    fail_on = section.get("fail_on")
    if fail_on is not None:
        fail_on = str(fail_on).lower()
        if fail_on not in _VALID_FAIL_ON:
            warnings.append(f"fail_on 应为 {'/'.join(_VALID_FAIL_ON)}, 已忽略: {fail_on!r}")
            fail_on = "high"
    else:
        fail_on = "high"

    gap_section = section.get("gap", {})
    gap_max_rate: float | None = None
    if isinstance(gap_section, dict) and gap_section.get("max_rate") is not None:
        try:
            gap_max_rate = float(gap_section["max_rate"])
            if not 0.0 <= gap_max_rate <= 1.0:
                warnings.append(f"gap.max_rate 应在 0-1, 已忽略: {gap_max_rate}")
                gap_max_rate = None
        except (TypeError, ValueError):
            warnings.append(f"gap.max_rate 非法数值, 已忽略: {gap_section['max_rate']!r}")

    for w in warnings:
        print(f"promptlint 配置警告: {w}", file=sys.stderr)

    return LintConfig(
        include_rules=_check_rule_ids(_str_list("include_rules"), "include_rules"),
        exclude_rules=_check_rule_ids(_str_list("exclude_rules"), "exclude_rules"),
        fail_on=fail_on,
        severity_overrides=severity_overrides,
        waivers=_check_rule_ids(_str_list("waivers"), "waivers"),
        gap_max_rate=gap_max_rate,
        extra={k: v for k, v in section.items() if k not in _KNOWN_KEYS},
    )
