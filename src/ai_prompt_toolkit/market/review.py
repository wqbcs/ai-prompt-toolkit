"""评审流水线 — 安全扫描门禁+评分+超时机制"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Sequence

from ai_prompt_toolkit.market.types import Review, Template, TemplateStatus

logger = logging.getLogger(__name__)

REVIEW_TIMEOUT_DAYS = 14
REVIEW_REMINDER_DAYS = 14
REVIEW_AUTO_CLOSE_DAYS = 21
MIN_APPROVAL_SCORE = 3.5
MIN_REVIEWERS = 1


class ReviewPipeline:
    def __init__(self) -> None:
        self._reviews: dict[str, list[Review]] = {}

    def start_review(self, template: Template) -> str:
        if template.status != TemplateStatus.DRAFT:
            raise ValueError(f"只有draft状态的模板才能进入评审，当前: {template.status.value}")
        template.status = TemplateStatus.REVIEW
        template.updated_at = datetime.now().isoformat()
        self._reviews[template.id] = []
        logger.info("模板 %s 进入评审流程", template.id)
        return template.id

    def submit_review(self, template_id: str, review: Review) -> None:
        if template_id not in self._reviews:
            self._reviews[template_id] = []
        self._reviews[template_id].append(review)
        review.reviewed_at = datetime.now().isoformat()
        logger.info("评审提交: %s by %s (approved=%s, score=%.1f)",
                     template_id, review.reviewer, review.approved, review.score)

    def check_gate(self, template: Template) -> dict[str, Any]:
        reviews = self._reviews.get(template.id, [])
        approved_count = sum(1 for r in reviews if r.approved)
        avg_score = 0.0
        if reviews:
            avg_score = sum(r.score for r in reviews) / len(reviews)
        gate_results: dict[str, Any] = {
            "security_scan_passed": template.security_scan_passed,
            "min_reviewers": approved_count >= MIN_REVIEWERS,
            "approval_count": approved_count,
            "avg_score": round(avg_score, 2),
            "score_threshold": avg_score >= MIN_APPROVAL_SCORE,
            "passed": False,
        }
        gate_results["passed"] = (
            template.security_scan_passed
            and approved_count >= MIN_REVIEWERS
            and avg_score >= MIN_APPROVAL_SCORE
        )
        return gate_results

    def check_timeout(self, template: Template) -> str | None:
        if template.status != TemplateStatus.REVIEW:
            return None
        reviews = self._reviews.get(template.id, [])
        if not reviews:
            return None
        first_review = reviews[0]
        if not first_review.reviewed_at:
            return None
        try:
            review_time = datetime.fromisoformat(first_review.reviewed_at)
        except (ValueError, TypeError):
            return None
        elapsed = datetime.now() - review_time
        if elapsed > timedelta(days=REVIEW_AUTO_CLOSE_DAYS):
            logger.warning("评审超时自动关闭: %s (%d天)", template.id, elapsed.days)
            return "auto_closed"
        if elapsed > timedelta(days=REVIEW_REMINDER_DAYS):
            return "reminder"
        return None

    def get_reviews(self, template_id: str) -> list[Review]:
        return self._reviews.get(template_id, [])
