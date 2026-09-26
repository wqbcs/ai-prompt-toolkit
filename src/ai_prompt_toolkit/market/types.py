"""模板市场类型定义和LifecycleManager状态机"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    CANARY = "canary"
    STABLE = "stable"
    DEPRECATED = "deprecated"


class DeployPhase(str, Enum):
    P5 = "5%"
    P25 = "25%"
    P50 = "50%"
    P100 = "100%"


DEPLOY_LADDER = [DeployPhase.P5, DeployPhase.P25, DeployPhase.P50, DeployPhase.P100]
OBSERVATION_DAYS = 7
ROLLBACK_THRESHOLD = -0.20


@dataclass
class Template:
    id: str
    name: str
    version: str
    status: TemplateStatus = TemplateStatus.DRAFT
    author: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    security_scan_passed: bool = False
    lint_score: float = 0.0
    i18n_status: str = "zh_only"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "security_scan_passed": self.security_scan_passed,
            "lint_score": self.lint_score,
            "i18n_status": self.i18n_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class Review:
    reviewer: str
    approved: bool
    score: float = 0.0
    comment: str = ""
    reviewed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "approved": self.approved,
            "score": self.score,
            "comment": self.comment,
            "reviewed_at": self.reviewed_at,
        }


@dataclass
class DeployConfig:
    template_id: str
    phase: DeployPhase = DeployPhase.P5
    phase_started_at: str = ""
    canary_score: float = 0.0
    baseline_score: float = 0.0
    auto_rollback_enabled: bool = True

    @property
    def performance_delta(self) -> float:
        if self.baseline_score == 0:
            return 0.0
        return (self.canary_score - self.baseline_score) / self.baseline_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "phase": self.phase.value,
            "phase_started_at": self.phase_started_at,
            "canary_score": self.canary_score,
            "baseline_score": self.baseline_score,
            "performance_delta": round(self.performance_delta, 3),
            "auto_rollback_enabled": self.auto_rollback_enabled,
        }


_VALID_TRANSITIONS: dict[TemplateStatus, set[TemplateStatus]] = {
    TemplateStatus.DRAFT: {TemplateStatus.REVIEW},
    TemplateStatus.REVIEW: {TemplateStatus.CANARY, TemplateStatus.DRAFT},
    TemplateStatus.CANARY: {TemplateStatus.STABLE, TemplateStatus.DRAFT, TemplateStatus.DEPRECATED},
    TemplateStatus.STABLE: {TemplateStatus.DEPRECATED},
    TemplateStatus.DEPRECATED: set(),
}


class LifecycleManager:
    def transition(self, template: Template, target: TemplateStatus) -> Template:
        valid = _VALID_TRANSITIONS.get(template.status, set())
        if target not in valid:
            raise ValueError(
                f"无效状态转换: {template.status.value} → {target.value}，允许: {[s.value for s in valid]}"
            )
        if target in (TemplateStatus.CANARY, TemplateStatus.STABLE) and not template.security_scan_passed:
            raise ValueError("安全扫描未通过，禁止进入发布流程")
        if template.status == TemplateStatus.REVIEW and target != TemplateStatus.DRAFT:
            pass
        template.status = target
        template.updated_at = datetime.now().isoformat()
        return template

    def can_delete(self, template: Template) -> bool:
        return template.status not in (TemplateStatus.REVIEW, TemplateStatus.CANARY)

    def can_promote(self, template: Template) -> bool:
        return template.status in (TemplateStatus.DRAFT, TemplateStatus.CANARY)
