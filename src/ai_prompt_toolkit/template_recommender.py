"""智能模板推荐 — 基于场景/行业/模型推荐最佳模板

P2-06: 智能推荐减少模板选择疲劳
- 场景匹配: 用户场景→推荐模板
- 行业匹配: 行业标签→最佳实践模板
- 模型适配: 根据模型特性推荐
- 评分排序: 综合lint_score+市场评分+下载量
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateRecommendation:
    template_id: str
    name: str
    category: str
    industry: str
    model_compatibility: list[str]
    lint_score: float
    market_rating: float
    download_count: int
    relevance_score: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "industry": self.industry,
            "lint_score": self.lint_score,
            "market_rating": self.market_rating,
            "download_count": self.download_count,
            "relevance_score": round(self.relevance_score, 2),
            "reason": self.reason,
        }


_BUILTIN_TEMPLATES: list[TemplateRecommendation] = [
    TemplateRecommendation("general-assistant", "通用助手", "general", "通用", ["gpt-4", "claude-3", "deepseek"], 92.0, 4.5, 1200),
    TemplateRecommendation("code-reviewer", "代码审查", "development", "科技", ["gpt-4", "claude-3"], 88.0, 4.7, 890),
    TemplateRecommendation("translator-pro", "专业翻译", "translation", "通用", ["gpt-4", "deepseek", "qwen"], 95.0, 4.3, 2100),
    TemplateRecommendation("data-analyst", "数据分析", "analytics", "金融", ["gpt-4", "claude-3"], 85.0, 4.1, 650),
    TemplateRecommendation("doc-writer", "文档撰写", "writing", "通用", ["gpt-4", "qwen", "deepseek"], 90.0, 4.4, 1500),
    TemplateRecommendation("security-auditor", "安全审计", "security", "科技", ["gpt-4", "claude-3"], 82.0, 4.6, 420),
    TemplateRecommendation("huawei-cloud-assistant", "华为云助手", "cloud", "华为云", ["qwen", "deepseek", "pangu"], 93.0, 4.8, 3200),
    TemplateRecommendation("rag-assistant", "RAG助手", "retrieval", "通用", ["gpt-4", "claude-3", "qwen"], 87.0, 4.2, 780),
    TemplateRecommendation("customer-service", "客服助手", "service", "电商", ["qwen", "deepseek"], 91.0, 4.5, 2800),
    TemplateRecommendation("education-tutor", "教育辅导", "education", "教育", ["gpt-4", "qwen"], 89.0, 4.3, 950),
    TemplateRecommendation("medical-assistant", "医疗助手", "medical", "医疗", ["gpt-4", "pangu"], 86.0, 4.0, 320),
    TemplateRecommendation("legal-advisor", "法律顾问", "legal", "法律", ["gpt-4", "claude-3"], 84.0, 3.9, 280),
    TemplateRecommendation("creative-writer", "创意写作", "creative", "媒体", ["gpt-4", "claude-3"], 88.0, 4.6, 1100),
    TemplateRecommendation("api-doc-generator", "API文档生成", "development", "科技", ["gpt-4", "deepseek"], 91.0, 4.4, 680),
    TemplateRecommendation("harmonyos-dev", "鸿蒙开发助手", "development", "华为云", ["qwen", "pangu"], 90.0, 4.7, 1500),
]

_WEIGHT_CONFIG = {
    "lint_score": 0.3,
    "market_rating": 0.25,
    "download_count": 0.15,
    "category_match": 0.15,
    "industry_match": 0.1,
    "model_match": 0.05,
}


class TemplateRecommender:
    def __init__(self, templates: list[TemplateRecommendation] | None = None):
        self._templates = templates or list(_BUILTIN_TEMPLATES)

    def recommend(
        self,
        category: str | None = None,
        industry: str | None = None,
        model: str | None = None,
        top_n: int = 5,
    ) -> list[TemplateRecommendation]:
        results: list[TemplateRecommendation] = []
        for t in self._templates:
            score = 0.0
            reasons: list[str] = []

            score += (t.lint_score / 100.0) * _WEIGHT_CONFIG["lint_score"] * 100

            score += (t.market_rating / 5.0) * _WEIGHT_CONFIG["market_rating"] * 100

            max_dl = max((tt.download_count for tt in self._templates), default=1)
            score += (t.download_count / max_dl) * _WEIGHT_CONFIG["download_count"] * 100

            if category:
                if t.category == category:
                    score += _WEIGHT_CONFIG["category_match"] * 100
                    reasons.append(f"场景匹配: {category}")
                elif category in t.category:
                    score += _WEIGHT_CONFIG["category_match"] * 50

            if industry:
                if t.industry == industry:
                    score += _WEIGHT_CONFIG["industry_match"] * 100
                    reasons.append(f"行业匹配: {industry}")

            if model:
                model_lower = model.lower()
                if any(model_lower in m.lower() for m in t.model_compatibility):
                    score += _WEIGHT_CONFIG["model_match"] * 100
                    reasons.append(f"模型适配: {model}")

            t.relevance_score = score
            t.reason = " | ".join(reasons) if reasons else "综合评分推荐"
            results.append(t)

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_n]

    def get_categories(self) -> list[str]:
        return sorted(set(t.category for t in self._templates))

    def get_industries(self) -> list[str]:
        return sorted(set(t.industry for t in self._templates))

    def get_template(self, template_id: str) -> TemplateRecommendation | None:
        for t in self._templates:
            if t.template_id == template_id:
                return t
        return None
