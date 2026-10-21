"""Auto-fix Verification v0.1 —— 自动修复安全性与修复后验证层。

职责边界（本模块只做验证，不改修复引擎）:
  1. 记录修复前后文本，判断文本是否变化、修复是否抛异常;
  2. 对修复后文本重新执行静态检查（不重复应用修复）;
  3. 用 (规则ID, 位置) 多元集匹配 Finding，区分 消失/残留/新增/级别变化;
  4. 检查幂等性：对修复结果再修一次，文本若仍变化则报告非幂等;
  5. 统一返回五态结果 NOT_APPLIED / VERIFIED / INCOMPLETE / REGRESSION / ERROR。

设计纪律(与项目既有楔子一致):
  - 不调用 LLM、不联网、零新增第三方依赖;
  - 不吞异常后报成功：任一环节异常 → ERROR，并在 messages 留痕;
  - 不以"文本变了"判定修复成功，也不以"没有新增 Finding"判定修复正确;
  - 无法稳定匹配时保留不确定性(matching_uncertain)，不宣称问题已解决;
  - 不修改入参对象与原始文本(frozen dataclass + tuple)。

接入方式(默认):
  - lint 走 `PromptLinter.lint()`（与 CLI 同一内核、同一 waiver 语义）;
  - fix 走 `PromptLinter._apply_fixes()` —— 与 `lint(fix=True)` 完全同一条修复路径。
    LintResult 目前不返回修复后文本，故复用之；后续若要公开化，建议在上游加
    一个 `apply_fixes()` 公共方法，本模块只改默认适配器、不动调用方。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from ai_prompt_toolkit.types import Finding, Severity

__all__ = [
    "AutoFixVerifier",
    "SeverityChange",
    "VerificationResult",
    "VerificationStatus",
    "default_fix",
    "default_lint",
    "verify_auto_fix",
]


class VerificationStatus(str, Enum):
    """验证结论五态（语义互斥，NOT_APPLIED 与 INCOMPLETE 不可混用）。"""

    NOT_APPLIED = "not_applied"
    """未应用修复：文本没有变化（无 finding、无可修复规则、或修复为空操作）。"""

    VERIFIED = "verified"
    """原问题消失、无新增 Finding、无级别恶化（幂等性另记 idempotent 字段）。"""

    INCOMPLETE = "incomplete"
    """修复后有原问题残留，或未满足调用方声明的严格条件（如要求幂等）。"""

    REGRESSION = "regression"
    """出现新增 Finding，或既有 Finding 严重级别被抬高。"""

    ERROR = "error"
    """验证过程本身异常（原始检查/修复/复检/idempotency 检查抛错）。"""


@dataclass(frozen=True)
class SeverityChange:
    """同一 (规则ID, 位置) 在修复前后的严重级别变化。"""

    rule_id: str
    location: str
    before: Severity
    after: Severity

    @property
    def escalated(self) -> bool:
        return self.after > self.before

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "location": self.location,
            "before": self.before.value,
            "after": self.after.value,
            "escalated": self.escalated,
        }


@dataclass(frozen=True)
class VerificationResult:
    """一次自动修复验证的完整结果（所有计数均由真实对比计算，非填充值）。"""

    status: VerificationStatus
    original_text: str
    fixed_text: str
    text_changed: bool
    original_findings: tuple[Finding, ...] = ()
    remaining_findings: tuple[Finding, ...] = ()
    disappeared_findings: tuple[Finding, ...] = ()
    new_findings: tuple[Finding, ...] = ()
    severity_changes: tuple[SeverityChange, ...] = ()
    idempotent: bool | None = None
    matching_uncertain: bool = False
    messages: tuple[str, ...] = field(default_factory=tuple)

    # ── 计数一律由元组长度实时推导，避免"数字与明细不一致" ──
    @property
    def original_count(self) -> int:
        return len(self.original_findings)

    @property
    def remaining_count(self) -> int:
        return len(self.remaining_findings)

    @property
    def disappeared_count(self) -> int:
        return len(self.disappeared_findings)

    @property
    def new_count(self) -> int:
        return len(self.new_findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "text_changed": self.text_changed,
            "original_count": self.original_count,
            "remaining_count": self.remaining_count,
            "disappeared_count": self.disappeared_count,
            "new_count": self.new_count,
            "severity_changes": [c.to_dict() for c in self.severity_changes],
            "idempotent": self.idempotent,
            "matching_uncertain": self.matching_uncertain,
            "remaining_findings": [f.to_dict() for f in self.remaining_findings],
            "disappeared_findings": [f.to_dict() for f in self.disappeared_findings],
            "new_findings": [f.to_dict() for f in self.new_findings],
            "messages": list(self.messages),
        }


LintFn = Callable[[str], Sequence[Finding]]
FixFn = Callable[[str, Sequence[Finding]], tuple[str, Sequence[Finding]]]


# ── 默认适配器：与 CLI 同一条 lint / fix 路径 ──────────────────────────────
_SHARED_LINTER: Any = None


def _shared_linter() -> Any:
    """延迟构造单例 PromptLinter（规则加载有成本，验证多文件时不必重复付）。"""
    global _SHARED_LINTER
    if _SHARED_LINTER is None:
        from ai_prompt_toolkit.linter.linter import PromptLinter

        _SHARED_LINTER = PromptLinter()
    return _SHARED_LINTER


def default_lint(text: str) -> Sequence[Finding]:
    """默认检查函数：与 `prompt-cli lint` 同一内核（含 waiver / 配置默认面）。"""
    findings = _shared_linter().lint("<auto-fix-verification>", text).findings
    return cast("Sequence[Finding]", findings)


def default_fix(text: str, findings: Sequence[Finding]) -> tuple[str, Sequence[Finding]]:
    """默认修复函数：直接复用 `PromptLinter._apply_fixes`（`lint(fix=True)` 的同一实现）。"""
    linter = _shared_linter()
    apply_fixes = getattr(linter, "_apply_fixes", None)
    if apply_fixes is None:  # 上游若重命名，明确失败而不是伪造成功
        raise AttributeError("PromptLinter 未提供 _apply_fixes，验证层需同步适配真实接口")
    fixed_text, fixed_findings = apply_fixes(text, list(findings))
    fixed_text = str(fixed_text)
    return fixed_text, tuple(fixed_findings)


def _key(f: Finding) -> tuple[str, str]:
    return (f.rule_id, getattr(f, "location", "") or "")


def _sort_key(f: Finding) -> tuple[int, str, str]:
    """同一 (规则,位置) 内多条 finding 的稳定配对序：级别降序 → 描述 → 修复建议。"""
    return (-Severity._RANK[f.severity], f.description, f.remediation)


@dataclass(frozen=True)
class AutoFixVerifier:
    """自动修复验证器。

    lint_fn / fix_fn 可注入（测试与其它修复引擎复用），默认值即项目真实实现。
    require_idempotent=True 时，非幂等修复判为 INCOMPLETE（默认 False：非幂等
    不必然是错误，只记录 idempotent=False 并在 messages 说明）。
    """

    lint_fn: LintFn = default_lint
    fix_fn: FixFn = default_fix
    require_idempotent: bool = False

    def verify(self, text: str) -> VerificationResult:
        messages: list[str] = []

        # ① 原始检查
        try:
            before = tuple(self.lint_fn(text))
        except Exception as exc:
            return self._error(text, f"原始检查失败: {type(exc).__name__}: {exc}")

        if not before:
            return VerificationResult(
                status=VerificationStatus.NOT_APPLIED,
                original_text=text,
                fixed_text=text,
                text_changed=False,
                messages=("输入无 Finding，未执行修复",),
            )

        # ② 执行修复（只此一次；后续复检不得再次应用修复）
        try:
            fixed_text, _applied = self.fix_fn(text, before)
        except Exception as exc:
            return self._error(text, f"修复执行失败: {type(exc).__name__}: {exc}", original=before)

        fixed_text = str(fixed_text)
        text_changed = fixed_text != text
        if not text_changed:
            return VerificationResult(
                status=VerificationStatus.NOT_APPLIED,
                original_text=text,
                fixed_text=fixed_text,
                text_changed=False,
                original_findings=before,
                messages=(
                    f"修复未改变文本（原有 {len(before)} 条 Finding 全部保留）",
                    "可能原因：命中规则不在自动修复表内，或修复为空操作",
                ),
            )

        # ③ 修复后复检
        try:
            after = tuple(self.lint_fn(fixed_text))
        except Exception as exc:
            return self._error(
                text,
                f"修复后复检失败: {type(exc).__name__}: {exc}",
                original=before,
                fixed=fixed_text,
                changed=True,
            )

        remaining, disappeared, new, severity_changes, uncertain = _diff_findings(before, after)

        # ④ 幂等性：对修复结果再修一次（异常只降级为 idempotent=None，不改变主结论）
        idempotent: bool | None
        try:
            second_text, _ = self.fix_fn(fixed_text, after)
            idempotent = str(second_text) == fixed_text
        except Exception as exc:
            idempotent = None
            messages.append(f"幂等性检查异常，结论未知: {type(exc).__name__}: {exc}")

        # ⑤ 结论裁决
        escalated = [c for c in severity_changes if c.escalated]
        if new:
            status = VerificationStatus.REGRESSION
            messages.append(f"修复引入 {len(new)} 条新 Finding: {_ids(new)}")
        elif escalated:
            status = VerificationStatus.REGRESSION
            messages.append(f"修复后 {len(escalated)} 条 Finding 严重级别被抬高: {_ids(escalated)}")
        elif remaining:
            status = VerificationStatus.INCOMPLETE
            messages.append(f"修复后仍有 {len(remaining)} 条原 Finding 残留: {_ids(remaining)}")
        elif self.require_idempotent and idempotent is False:
            status = VerificationStatus.INCOMPLETE
            messages.append("调用方要求幂等，但第二次修复仍改变了文本")
        else:
            status = VerificationStatus.VERIFIED
            messages.append(f"原 {len(disappeared)} 条 Finding 已消失，且未引入新问题")

        if uncertain:
            messages.append("存在同规则同位置(或空位置)的多条 Finding，配对可能不唯一，结论保留不确定性")
        if idempotent is False and status is VerificationStatus.VERIFIED:
            messages.append("非幂等：第二次修复仍改变文本（未判为失败，按规则设计核实）")
        if disappeared:
            messages.append(f"已消失 {len(disappeared)} 条: {_ids(disappeared)}")

        return VerificationResult(
            status=status,
            original_text=text,
            fixed_text=fixed_text,
            text_changed=text_changed,
            original_findings=before,
            remaining_findings=tuple(remaining),
            disappeared_findings=tuple(disappeared),
            new_findings=tuple(new),
            severity_changes=tuple(severity_changes),
            idempotent=idempotent,
            matching_uncertain=uncertain,
            messages=tuple(messages),
        )

    def _error(
        self,
        text: str,
        message: str,
        *,
        original: tuple[Finding, ...] = (),
        fixed: str | None = None,
        changed: bool = False,
    ) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            original_text=text,
            fixed_text=text if fixed is None else fixed,
            text_changed=changed,
            original_findings=original,
            messages=(message,),
        )


def _ids(findings: Sequence[Any]) -> str:
    """规则ID摘要（Finding 或 SeverityChange 均可）。"""
    ids: list[str] = []
    for item in findings:
        rid = getattr(item, "rule_id", "?")
        loc = getattr(item, "location", "") or ""
        ids.append(f"{rid}@{loc}" if loc else rid)
    return ", ".join(ids)


def _diff_findings(
    before: Sequence[Finding], after: Sequence[Finding]
) -> tuple[list[Finding], list[Finding], list[Finding], list[SeverityChange], bool]:
    """用 (规则ID, 位置) 多元集配对，返回 (残留, 消失, 新增, 级别变化, 是否存在匹配不确定性)。

    不以数量相减判定：同规则不同位置必须分别配对；位置为空且同规则多条时无法
    区分具体是哪一条，只按多重集计数并标记不确定性。
    """
    b_buckets: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    a_buckets: dict[tuple[str, str], list[Finding]] = defaultdict(list)
    for f in before:
        b_buckets[_key(f)].append(f)
    for f in after:
        a_buckets[_key(f)].append(f)

    remaining: list[Finding] = []
    disappeared: list[Finding] = []
    new: list[Finding] = []
    severity_changes: list[SeverityChange] = []
    uncertain = False

    for key in sorted(set(b_buckets) | set(a_buckets)):
        bs = sorted(b_buckets.get(key, []), key=_sort_key)
        as_ = sorted(a_buckets.get(key, []), key=_sort_key)
        paired = min(len(bs), len(as_))
        for i in range(paired):
            b, a = bs[i], as_[i]
            remaining.append(a)
            if a.severity is not b.severity:
                severity_changes.append(SeverityChange(b.rule_id, key[1], b.severity, a.severity))
        disappeared.extend(bs[paired:])
        new.extend(as_[paired:])
        if key[1] == "" and max(len(bs), len(as_)) > 1:
            uncertain = True

    remaining.sort(key=_sort_key)
    disappeared.sort(key=_sort_key)
    new.sort(key=_sort_key)
    severity_changes.sort(key=lambda c: (c.rule_id, c.location))
    return remaining, disappeared, new, severity_changes, uncertain


def verify_auto_fix(
    text: str,
    *,
    lint_fn: LintFn = default_lint,
    fix_fn: FixFn = default_fix,
    require_idempotent: bool = False,
) -> VerificationResult:
    """一次性验证便利入口（等价于 AutoFixVerifier(...).verify(text)）。"""
    return AutoFixVerifier(lint_fn=lint_fn, fix_fn=fix_fn, require_idempotent=require_idempotent).verify(text)
