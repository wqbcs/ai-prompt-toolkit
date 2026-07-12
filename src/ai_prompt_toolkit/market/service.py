"""MarketService — 模板市场主服务，提交/查询/安全门禁"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from ai_prompt_toolkit.market.deploy import DeployManager
from ai_prompt_toolkit.market.review import ReviewPipeline
from ai_prompt_toolkit.market.types import (
    DeployConfig,
    LifecycleManager,
    Review,
    Template,
    TemplateStatus,
)

logger = logging.getLogger(__name__)


class MarketService:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path.cwd() / "_market"
        self._templates: dict[str, Template] = {}
        self._lifecycle = LifecycleManager()
        self._review_pipeline = ReviewPipeline()
        self._deploy_mgr = DeployManager(self._lifecycle)
        self._load()

    def _load(self) -> None:
        data_file = self._data_dir / "templates.json"
        if not data_file.exists():
            return
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("templates", []):
                tpl = Template(
                    id=item["id"],
                    name=item.get("name", ""),
                    version=item.get("version", "1.0"),
                    status=TemplateStatus(item.get("status", "draft")),
                    author=item.get("author", ""),
                    description=item.get("description", ""),
                    tags=item.get("tags", []),
                    security_scan_passed=item.get("security_scan_passed", False),
                    lint_score=item.get("lint_score", 0.0),
                    i18n_status=item.get("i18n_status", "zh_only"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                )
                self._templates[tpl.id] = tpl
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error("加载市场数据失败: %s", e)

    def _save(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "templates": [t.to_dict() for t in self._templates.values()],
        }
        data_file = self._data_dir / "templates.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def submit(self, template: Template) -> Template:
        if template.id in self._templates:
            raise ValueError(f"模板 {template.id} 已存在")
        template.status = TemplateStatus.DRAFT
        template.created_at = datetime.now().isoformat()
        template.updated_at = template.created_at
        self._templates[template.id] = template
        self._save()
        logger.info("模板提交: %s", template.id)
        return template

    def query(self, template_id: str) -> Template | None:
        return self._templates.get(template_id)

    def list_templates(self, status: TemplateStatus | None = None) -> list[Template]:
        templates = list(self._templates.values())
        if status:
            templates = [t for t in templates if t.status == status]
        return templates

    def start_review(self, template_id: str) -> str:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        return self._review_pipeline.start_review(template)

    def submit_review(self, template_id: str, review: Review) -> None:
        self._review_pipeline.submit_review(template_id, review)

    def check_review_gate(self, template_id: str) -> dict[str, Any]:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        return self._review_pipeline.check_gate(template)

    def start_deploy(self, template_id: str, baseline_score: float = 0.0) -> DeployConfig:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        config = self._deploy_mgr.start_canary(template, baseline_score)
        self._save()
        return config

    def promote_deploy(self, template_id: str, canary_score: float) -> DeployConfig:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        config = self._deploy_mgr.promote(template, canary_score)
        self._save()
        return config

    def rollback_deploy(self, template_id: str, reason: str = "manual") -> DeployConfig:
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        config = self._deploy_mgr.rollback(template, reason)
        self._save()
        return config

    def get_status(self, template_id: str) -> dict[str, Any]:
        template = self._templates.get(template_id)
        if not template:
            return {"error": f"模板 {template_id} 不存在"}
        result: dict[str, Any] = {
            "template": template.to_dict(),
        }
        reviews = self._review_pipeline.get_reviews(template_id)
        if reviews:
            result["reviews"] = [r.to_dict() for r in reviews]
        deploy_config = self._deploy_mgr.get_config(template_id)
        if deploy_config:
            result["deploy"] = deploy_config.to_dict()
        return result
