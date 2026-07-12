# 安全扫描器 (Scanner)

> 完整的Python安全扫描器实现，可直接运行

```python
"""
安全扫描器 — 检测条件编译指令中的注入攻击

5 条注入规则:
    1. 代码注入 (import/exec/eval)
    2. 路径穿越 (../  /etc/passwd)
    3. 环境逃逸 (环境变量泄露)
    4. 继承链滥用 (super().__class__ 等)
    5. 模板注入 (Jinja2/SSTI 特征)

用法:
    from scanner import Scanner, SecurityScanResult
    result = Scanner.scan(source_text)
"""

from __future__ import annotations

import re
import enum
import dataclasses
from typing import List, Dict, Any, Optional


# ──────────────────────────────────────────
#  安全等级
# ──────────────────────────────────────────

class Severity(enum.Enum):
    """安全风险等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ──────────────────────────────────────────
#  扫描结果
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class SecurityFinding:
    """安全发现

    Attributes:
        rule_id:    规则 ID
        severity:   严重等级
        message:    问题描述
        line:       行号
        column:     列号
        context:    上下文片段
        remediation: 修复建议
    """
    rule_id: str
    severity: Severity
    message: str
    line: int
    column: int
    context: str
    remediation: str

    def __repr__(self) -> str:
        return (
            f"[{self.severity.value.upper()}] {self.rule_id}: {self.message} "
            f"(L{self.line}:{self.column})"
        )


@dataclasses.dataclass
class SecurityScanResult:
    """安全扫描结果

    Attributes:
        source_hash:  源文本哈希
        findings:     发现列表
        passed:       是否通过扫描（无 CRITICAL/HIGH）
        scan_duration_ms: 扫描耗时
        metadata:     元数据
    """
    source_hash: str
    findings: List[SecurityFinding]
    passed: bool
    scan_duration_ms: float
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def summary(self) -> str:
        """生成扫描摘要"""
        by_severity: Dict[str, int] = {}
        for f in self.findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

        lines = [
            f"扫描结果: {'通过' if self.passed else '未通过'}",
            f"耗时: {self.scan_duration_ms:.1f}ms",
            f"发现: {len(self.findings)} 项",
        ]
        for sev in ("critical", "high", "medium", "low", "info"):
            if sev in by_severity:
                lines.append(f"  {sev}: {by_severity[sev]}")

        if self.findings:
            lines.append("\n详细:")
            for f in self.findings:
                lines.append(f"  {f}")
                lines.append(f"    修复: {f.remediation}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "source_hash": self.source_hash,
            "passed": self.passed,
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "message": f.message,
                    "line": f.line,
                    "column": f.column,
                    "context": f.context,
                    "remediation": f.remediation,
                }
                for f in self.findings
            ],
        }


# ──────────────────────────────────────────
#  注入规则定义
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class InjectionRule:
    """注入检测规则

    Attributes:
        rule_id:      规则 ID
        name:         规则名称
        severity:     严重等级
        pattern:      正则表达式
        message:      问题描述模板
        remediation:  修复建议
    """
    rule_id: str
    name: str
    severity: Severity
    pattern: re.Pattern[str]
    message: str
    remediation: str


_RULES: List[InjectionRule] = [
    InjectionRule(
        rule_id="INJ-001",
        name="代码注入",
        severity=Severity.CRITICAL,
        pattern=re.compile(
            r"\b(import|exec|eval|compile|__import__|getattr|setattr|delattr|globals|locals)\b\s*[\(\s]"
        ),
        message="检测到潜在代码注入: {match}",
        remediation="禁止在条件表达式中使用 import/exec/eval 等函数，改用预定义变量",
    ),
    InjectionRule(
        rule_id="INJ-002",
        name="路径穿越",
        severity=Severity.HIGH,
        pattern=re.compile(
            r"(\.\./|\.\.\\|/etc/|/proc/|/var/|C:\\|\\\\)"
        ),
        message="检测到路径穿越特征: {match}",
        remediation="禁止在条件表达式中引用文件路径，使用环境变量或标志代替",
    ),
    InjectionRule(
        rule_id="INJ-003",
        name="环境逃逸",
        severity=Severity.HIGH,
        pattern=re.compile(
            r"\b(os\.environ|sys\.|subprocess|socket|http|urllib|requests)\b"
        ),
        message="检测到环境逃逸特征: {match}",
        remediation="禁止访问操作系统环境变量和网络模块，使用编译上下文变量",
    ),
    InjectionRule(
        rule_id="INJ-004",
        name="继承链滥用",
        severity=Severity.CRITICAL,
        pattern=re.compile(
            r"(__class__|__bases__|__mro__|__subclasses__|__globals__|__builtins__|__dict__|super\(\))"
        ),
        message="检测到继承链滥用: {match}",
        remediation="禁止使用 Python 魔术属性访问继承链，条件表达式仅允许简单比较",
    ),
    InjectionRule(
        rule_id="INJ-005",
        name="模板注入",
        severity=Severity.HIGH,
        pattern=re.compile(
            r"(\{\{.*?\}\}|\$\{.*?\}|<%.*?%>|#\{.*?\}|~\$.*?\$~|jinja|flask|django)"
        ),
        message="检测到模板注入特征: {match}",
        remediation="禁止在条件编译指令中嵌套模板语法，确保条件表达式纯净",
    ),
]


# ──────────────────────────────────────────
#  继承链审计
# ──────────────────────────────────────────

_INHERITANCE_DANGER_RE = re.compile(
    r"(\.__class__|.__bases__|.__mro__|.__subclasses__|.__globals__|.__builtins__|super\(\))"
)


def audit_inheritance_chain(expression: str) -> List[str]:
    """审计表达式中的继承链访问

    Returns:
        发现的危险模式列表
    """
    findings: List[str] = []
    for m in _INHERITANCE_DANGER_RE.finditer(expression):
        findings.append(m.group(0))
    return findings


# ──────────────────────────────────────────
#  扫描器
# ──────────────────────────────────────────

class Scanner:
    """安全扫描器

    扫描条件编译指令中的注入攻击和安全风险。
    """

    @staticmethod
    def scan(source: str) -> SecurityScanResult:
        """扫描源文本

        Args:
            source: 包含条件编译指令的源文本

        Returns:
            SecurityScanResult 扫描结果
        """
        import hashlib
        import time

        start = time.monotonic()
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        findings: List[SecurityFinding] = []

        lines = source.split("\n")

        for line_idx, line in enumerate(lines, start=1):
            # 提取条件编译指令内容
            directives = Scanner._extract_directives(line)

            for directive_content, col_offset in directives:
                for rule in _RULES:
                    for m in rule.pattern.finditer(directive_content):
                        findings.append(SecurityFinding(
                            rule_id=rule.rule_id,
                            severity=rule.severity,
                            message=rule.message.format(match=m.group(0)),
                            line=line_idx,
                            column=col_offset + m.start(),
                            context=directive_content[:80],
                            remediation=rule.remediation,
                        ))

            # 继承链审计（整行）
            chain_findings = audit_inheritance_chain(line)
            for cf in chain_findings:
                # 避免重复（INJ-004 已覆盖）
                if not any(f.rule_id == "INJ-004" and f.line == line_idx for f in findings):
                    col = line.find(cf) + 1
                    findings.append(SecurityFinding(
                        rule_id="INJ-004",
                        severity=Severity.CRITICAL,
                        message=f"继承链审计发现: {cf}",
                        line=line_idx,
                        column=col,
                        context=line[:80],
                        remediation="禁止使用 Python 魔术属性访问继承链",
                    ))

        elapsed_ms = (time.monotonic() - start) * 1000
        passed = not any(f.severity in (Severity.CRITICAL, Severity.HIGH) for f in findings)

        return SecurityScanResult(
            source_hash=source_hash,
            findings=findings,
            passed=passed,
            scan_duration_ms=elapsed_ms,
        )

    @staticmethod
    def _extract_directives(line: str) -> List[tuple[str, int]]:
        """从行中提取条件编译指令内容

        Returns:
            [(directive_content, column_offset), ...]
        """
        results: List[tuple[str, int]] = []
        pattern = re.compile(r"<<(?:if|elseif)\s+(.+?)>>")

        for m in pattern.finditer(line):
            results.append((m.group(1), m.start()))

        return results


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    # ── 测试 1: 安全文本 ──
    result = Scanner.scan("<<if lang=='zh'>>你好<<endif>>")
    assert_eq("安全-通过", result.passed, True)
    assert_eq("安全-无发现", len(result.findings), 0)

    # ── 测试 2: 代码注入 import ──
    result = Scanner.scan("<<if __import__('os')>>x<<endif>>")
    assert_eq("import-未通过", result.passed, False)
    assert_eq("import-发现", any(f.rule_id == "INJ-001" for f in result.findings), True)

    # ── 测试 3: exec/eval ──
    result = Scanner.scan("<<if eval('1+1')>>x<<endif>>")
    assert_eq("eval-未通过", result.passed, False)
    assert_eq("eval-规则", any(f.rule_id == "INJ-001" for f in result.findings), True)

    # ── 测试 4: 路径穿越 ──
    result = Scanner.scan("<<if path=='../../../etc/passwd'>>x<<endif>>")
    assert_eq("路径穿越-未通过", result.passed, False)
    assert_eq("路径穿越-规则", any(f.rule_id == "INJ-002" for f in result.findings), True)

    # ── 测试 5: 环境逃逸 ──
    result = Scanner.scan("<<if os.environ>>x<<endif>>")
    assert_eq("环境逃逸-未通过", result.passed, False)
    assert_eq("环境逃逸-规则", any(f.rule_id == "INJ-003" for f in result.findings), True)

    # ── 测试 6: 继承链滥用 ──
    result = Scanner.scan("<<if x.__class__.__bases__>>x<<endif>>")
    assert_eq("继承链-未通过", result.passed, False)
    assert_eq("继承链-规则", any(f.rule_id == "INJ-004" for f in result.findings), True)

    # ── 测试 7: 模板注入 ──
    result = Scanner.scan("<<if {{config}}>>x<<endif>>")
    assert_eq("模板注入-未通过", result.passed, False)
    assert_eq("模板注入-规则", any(f.rule_id == "INJ-005" for f in result.findings), True)

    # ── 测试 8: 混合安全与不安全 ──
    result = Scanner.scan("<<if lang=='zh'>>OK<<if eval('x')>>BAD<<endif>>")
    assert_eq("混合-未通过", result.passed, False)

    # ── 测试 9: 报告摘要 ──
    result = Scanner.scan("<<if import os>>x<<endif>>")
    summary = result.summary()
    assert_eq("摘要-非空", len(summary) > 0, True)

    # ── 测试 10: to_dict 序列化 ──
    result = Scanner.scan("<<if eval('1')>>x<<endif>>")
    d = result.to_dict()
    assert_eq("序列化-有findings", len(d["findings"]) > 0, True)
    assert_eq("序列化-passed", d["passed"], False)

    # ── 测试 11: 继承链审计 ──
    chains = audit_inheritance_chain("x.__class__.__bases__")
    assert_eq("继承链审计", len(chains) > 0, True)

    print(f"\nScanner 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
