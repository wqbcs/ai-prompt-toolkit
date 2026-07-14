"""灰度发布管理 — 阶梯式灰度+自动回滚+紧急状态"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from ai_prompt_toolkit.market.types import (
    DEPLOY_LADDER,
    OBSERVATION_DAYS,
    ROLLBACK_THRESHOLD,
    DeployConfig,
    DeployPhase,
    LifecycleManager,
    Template,
    TemplateStatus,
)

logger = logging.getLogger(__name__)


class DeployManager:
    def __init__(self, lifecycle: LifecycleManager | None = None) -> None:
        self._lifecycle = lifecycle or LifecycleManager()
        self._deployments: dict[str, DeployConfig] = {}

    def start_canary(self, template: Template, baseline_score: float = 0.0) -> DeployConfig:
        if template.status != TemplateStatus.REVIEW:
            raise ValueError(f"只有review状态的模板才能启动灰度，当前: {template.status.value}")
        if not template.security_scan_passed:
            raise ValueError("安全扫描未通过，禁止启动灰度发布")
        template = self._lifecycle.transition(template, TemplateStatus.CANARY)
        config = DeployConfig(
            template_id=template.id,
            phase=DeployPhase.P5,
            phase_started_at=datetime.now().isoformat(),
            baseline_score=baseline_score,
        )
        self._deployments[template.id] = config
        logger.info("灰度发布启动: %s (基线=%.2f)", template.id, baseline_score)
        return config

    def promote(self, template: Template, canary_score: float) -> DeployConfig:
        config = self._deployments.get(template.id)
        if not config:
            raise ValueError(f"模板 {template.id} 不在灰度发布中")
        config.canary_score = canary_score
        if config.performance_delta <= ROLLBACK_THRESHOLD:
            logger.warning("性能下降 %.1f%% 超过阈值，触发自动回滚: %s",
                           config.performance_delta * 100, template.id)
            return self.rollback(template, reason="performance_degradation")
        current_idx = next(
            (i for i, p in enumerate(DEPLOY_LADDER) if p == config.phase), -1
        )
        if current_idx < 0 or current_idx >= len(DEPLOY_LADDER) - 1:
            template = self._lifecycle.transition(template, TemplateStatus.STABLE)
            config.phase = DeployPhase.P100
            config.phase_started_at = datetime.now().isoformat()
            logger.info("灰度发布完成，模板 %s 进入stable", template.id)
        else:
            config.phase = DEPLOY_LADDER[current_idx + 1]
            config.phase_started_at = datetime.now().isoformat()
            logger.info("灰度推进: %s → %s", template.id, config.phase.value)
        return config

    def rollback(self, template: Template, reason: str = "manual") -> DeployConfig:
        config = self._deployments.get(template.id)
        if not config:
            raise ValueError(f"模板 {template.id} 不在灰度发布中")
        try:
            template = self._lifecycle.transition(template, TemplateStatus.DRAFT)
            logger.info("灰度回滚: %s (原因: %s)", template.id, reason)
        except ValueError as e:
            logger.error("回滚失败: %s — 标记为紧急状态", e)
            template.metadata["emergency"] = True
            template.metadata["emergency_reason"] = reason
            template.metadata["emergency_at"] = datetime.now().isoformat()
        if config:
            config.phase = DeployPhase.P5
            config.phase_started_at = datetime.now().isoformat()
        return config

    def check_observation(self, template_id: str) -> str | None:
        config = self._deployments.get(template_id)
        if not config:
            return None
        if not config.phase_started_at:
            return None
        try:
            started = datetime.fromisoformat(config.phase_started_at)
        except (ValueError, TypeError):
            return None
        elapsed = datetime.now() - started
        if elapsed >= timedelta(days=OBSERVATION_DAYS):
            return "ready_for_promote"
        remaining = timedelta(days=OBSERVATION_DAYS) - elapsed
        return f"观察期剩余 {remaining.days} 天"

    def get_config(self, template_id: str) -> DeployConfig | None:
        return self._deployments.get(template_id)
