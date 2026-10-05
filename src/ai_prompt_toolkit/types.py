"""通用类型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from re import Match


class Severity(Enum):
    """严重程度枚举"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    _RANK: ClassVar[dict[Severity, int]]

    def __ge__(self, other: Severity) -> bool:
        return self._RANK[self] >= self._RANK[other]

    def __gt__(self, other: Severity) -> bool:
        return self._RANK[self] > self._RANK[other]

    def __le__(self, other: Severity) -> bool:
        return not self.__gt__(other)

    def __lt__(self, other: Severity) -> bool:
        return not self.__ge__(other)


Severity._RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class ReportStatus(Enum):
    """报告状态枚举"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    PASSED = "passed"


# ── location 契约（R218: 三端唯一事实源, 消除 CLI/LSP/编辑器各自硬编码解析）──
#
# Finding.location 是字符串, 全端统一语义:
#   ""          = 文件级发现（规则无法定位到具体 span）→ 消费端不得猜测行号
#   "L:<line>"  = 行级定位（line 从 1 起）
#   "L:<line>:C:<col>" = 行+列定位（line/col 均从 1 起, VS Code/SARIF 同 1-based 基准）
#   兼容: 旧 "line:col" 纯数字形式 parse_location 仍按 1-based line:col 解析
#   （LSP 曾按此解析, 新代码一律用 build_location 产出规范形式）
# 消费端纪律: location 为空 → 文件级（CLI 不显示行号, 编辑器不猜行,
# SARIF 不写 region）; 禁止用 description 子串搜索等启发式猜行。


def build_location(line: int, column: int | None = None) -> str:
    """从 1-based 行/列构造规范 location 字符串（列缺省=行级）。"""
    line = max(1, int(line))
    if column is None:
        return f"L:{line}"
    return f"L:{line}:C:{max(1, int(column))}"


def parse_location(location: str) -> tuple[int | None, int | None]:
    """解析 location → (1-based line, 1-based col); 文件级/无法解析 → (None, None)。

    兼容形式: "L:5" / "L:5:C:12" / 旧 "5:12"（均 1-based）。
    非法/空 → (None, None)（调用方据此按文件级处理, 不猜行）。
    """
    loc = (location or "").strip()
    if not loc:
        return (None, None)
    if loc.startswith("L:"):
        parts = loc[2:].split(":C:")
        try:
            line = int(parts[0])
            col = int(parts[1]) if len(parts) > 1 else None
        except (ValueError, IndexError):
            return (None, None)
        if line < 1:
            return (None, None)
        return (line, col)
    # 兼容旧 "line:col" 纯数字形式
    parts = loc.split(":")
    try:
        line = int(parts[0])
        col = int(parts[1]) if len(parts) > 1 else None
    except (ValueError, IndexError):
        return (None, None)
    if line < 1:
        return (None, None)
    return (line, col)


def loc_from_match(text: str, m: Match[str]) -> str:
    """从正则 Match 计算 1-based 行:列 location（规则侧唯一入口）。

    line = m.start() 前换行数 + 1; col = m.start() 距本行起点 + 1。
    规则拿到 pattern.search/finditer 的 match 后统一走这里产出 location,
    保证与消费端 parse_location 同基准（1-based, VS Code/SARIF 一致）。
    """
    start = m.start()
    line = text.count("\n", 0, start) + 1
    line_start = text.rfind("\n", 0, start) + 1
    col = start - line_start + 1
    return build_location(line, col)


@dataclass
class Finding:
    """通用发现项"""

    rule_id: str
    severity: Severity
    description: str
    location: str = ""
    remediation: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "remediation": self.remediation,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            rule_id=data["rule_id"],
            severity=Severity(data["severity"]),
            description=data["description"],
            location=data.get("location", ""),
            remediation=data.get("remediation", ""),
            details=data.get("details", {}),
        )


@dataclass
class BaseReport:
    """通用报告基类"""

    timestamp: str
    template_id: str
    status: ReportStatus
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        # R233-P2-02: schema 版本化(与 baseline/LintResult 同值同源, 延迟导入防循环)
        from ai_prompt_toolkit.linter.baseline import SCHEMA_VERSION

        return {
            "schema_version": SCHEMA_VERSION,
            "timestamp": self.timestamp,
            "template_id": self.template_id,
            "status": self.status.value,
            "details": self.details,
            "warnings": self.warnings,
            "findings": [f.to_dict() for f in self.findings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseReport:
        return cls(
            timestamp=data["timestamp"],
            template_id=data["template_id"],
            status=ReportStatus(data["status"]),
            details=data.get("details", {}),
            warnings=data.get("warnings", []),
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
        )
