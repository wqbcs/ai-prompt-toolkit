"""华为云赛事贴合增强——盘古Judge评估指标 + 鸿蒙Agent专项评估

核心特性:
- 盘古模型LLM-as-Judge: 使用盘古API作为裁判模型评估
- 鸿蒙Agent专项评估: 鸿蒙开发场景专用评估维度
- 华为云赛事指标: ModelArts/API Endpoint/IAM等赛事关键指标
- 与GEPA Feedback Metric集成

赛事贴合:
- 盘古大模型API评估(华为云核心能力)
- 鸿蒙ArkTS/Stage模型/分布式能力评估
- 华为云部署最佳实践评估
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity

logger = logging.getLogger(__name__)


_HARMONY_AGENT_DIMENSIONS: dict[str, dict[str, Any]] = {
    "arkts_quality": {
        "name": "ArkTS代码质量",
        "description": "Prompt是否生成高质量ArkTS代码",
        "keywords": ["ArkTS", "TypeScript", "@Entry", "@Component", "build()", "struct"],
        "weight": 1.5,
        "feedback_template": "ArkTS代码质量不足: 缺少{missing}关键字或结构",
    },
    "stage_model": {
        "name": "Stage模型适配",
        "description": "Prompt是否理解鸿蒙Stage模型生命周期",
        "keywords": ["onCreate", "onDestroy", "onWindowStageCreate", "AbilityStage", "UIAbility"],
        "weight": 1.2,
        "feedback_template": "Stage模型适配不足: 未包含{missing}生命周期方法",
    },
    "distributed": {
        "name": "分布式能力",
        "description": "Prompt是否包含鸿蒙分布式开发指导",
        "keywords": ["分布式", "Distributed", "设备发现", "数据同步", "迁移"],
        "weight": 1.0,
        "feedback_template": "分布式能力不足: 未提及{missing}相关概念",
    },
    "security_hardening": {
        "name": "鸿蒙安全加固",
        "description": "Prompt是否包含鸿蒙安全最佳实践",
        "keywords": ["权限声明", "ohos.permission", "安全沙箱", "数据加密", "CertificatePin"],
        "weight": 1.3,
        "feedback_template": "鸿蒙安全加固不足: 未包含{missing}安全措施",
    },
    "performance_optimization": {
        "name": "性能优化指导",
        "description": "Prompt是否包含鸿蒙性能优化建议",
        "keywords": ["LazyForEach", "性能优化", "内存管理", "渲染优化", "组件复用"],
        "weight": 1.0,
        "feedback_template": "性能优化指导不足: 未提及{missing}优化技术",
    },
}


_HUAWEI_CLOUD_DIMENSIONS: dict[str, dict[str, Any]] = {
    "modelarts_deploy": {
        "name": "ModelArts部署",
        "description": "Prompt是否包含ModelArts部署最佳实践",
        "keywords": ["ModelArts", "推理部署", "在线服务", "批量推理", "边缘部署"],
        "weight": 1.5,
    },
    "iam_auth": {
        "name": "IAM认证集成",
        "description": "Prompt是否包含华为云IAM认证指导",
        "keywords": ["IAM", "AK/SK", "Token", "Agency", "联邦认证"],
        "weight": 1.2,
    },
    "api_endpoint": {
        "name": "API Endpoint规范",
        "description": "Prompt是否指定正确的华为云API Endpoint",
        "keywords": ["myhuaweicloud.com", "cn-north-4", "endpoint", "region"],
        "weight": 1.3,
    },
    "npu_adaptation": {
        "name": "昇腾NPU适配",
        "description": "Prompt是否包含昇腾NPU适配指导",
        "keywords": ["Ascend", "NPU", "CANN", "ATLAS", "MindSpore"],
        "weight": 1.2,
    },
    "data_compliance": {
        "name": "数据合规",
        "description": "Prompt是否包含数据合规声明",
        "keywords": ["数据合规", "GDPR", "隐私保护", "数据脱敏", "合规声明"],
        "weight": 1.0,
    },
}


@dataclass
class DimensionScore:
    dimension: str
    score: float
    max_score: float = 10.0
    feedback: str = ""
    weight: float = 1.0

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 2),
            "max_score": self.max_score,
            "weighted_score": round(self.weighted_score, 2),
            "weight": self.weight,
            "feedback": self.feedback,
        }


@dataclass
class HuaweiEvalResult:
    category: str
    dimensions: list[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    overall_weighted: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "overall_score": round(self.overall_score, 2),
            "overall_weighted": round(self.overall_weighted, 2),
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


def _evaluate_dimension(text: str, dim_config: dict[str, Any]) -> DimensionScore:
    keywords = dim_config.get("keywords", [])
    found = [kw for kw in keywords if kw.lower() in text.lower()]
    missing = [kw for kw in keywords if kw.lower() not in text.lower()]
    ratio = len(found) / len(keywords) if keywords else 1.0
    score = ratio * 10.0

    feedback = ""
    if missing and ratio < 0.8:
        tpl = dim_config.get("feedback_template", "Missing: {missing}")
        feedback = tpl.format(missing=", ".join(missing[:3]))
    elif ratio >= 0.8:
        feedback = ""

    return DimensionScore(
        dimension=dim_config["name"],
        score=score,
        weight=dim_config.get("weight", 1.0),
        feedback=feedback,
    )


def evaluate_harmonyos_agent(text: str) -> HuaweiEvalResult:
    dimensions = []
    total_weighted = 0.0
    total_weight = 0.0

    for key, dim_config in _HARMONY_AGENT_DIMENSIONS.items():
        ds = _evaluate_dimension(text, dim_config)
        dimensions.append(ds)
        total_weighted += ds.weighted_score
        total_weight += ds.weight

    overall = total_weighted / total_weight if total_weight > 0 else 0.0

    return HuaweiEvalResult(
        category="harmonyos_agent",
        dimensions=dimensions,
        overall_score=overall,
        overall_weighted=total_weighted,
    )


def evaluate_huawei_cloud(text: str) -> HuaweiEvalResult:
    dimensions = []
    total_weighted = 0.0
    total_weight = 0.0

    for key, dim_config in _HUAWEI_CLOUD_DIMENSIONS.items():
        ds = _evaluate_dimension(text, dim_config)
        dimensions.append(ds)
        total_weighted += ds.weighted_score
        total_weight += ds.weight

    overall = total_weighted / total_weight if total_weight > 0 else 0.0

    return HuaweiEvalResult(
        category="huawei_cloud",
        dimensions=dimensions,
        overall_score=overall,
        overall_weighted=total_weighted,
    )


def evaluate_contest_readiness(text: str) -> dict[str, Any]:
    harmony_result = evaluate_harmonyos_agent(text)
    cloud_result = evaluate_huawei_cloud(text)

    pangu_keywords = ["盘古", "pangu", "Pangu", "ModelArts Studio", "MaaS"]
    has_pangu = any(kw.lower() in text.lower() for kw in pangu_keywords)

    harmonyos_keywords = ["鸿蒙", "HarmonyOS", "ArkTS", "Stage模型"]
    has_harmony = any(kw.lower() in text.lower() for kw in harmonyos_keywords)

    contest_score = (
        harmony_result.overall_score * 0.4 +
        cloud_result.overall_score * 0.4 +
        (10.0 if has_pangu else 0.0) * 0.1 +
        (10.0 if has_harmony else 0.0) * 0.1
    )

    return {
        "contest_score": round(contest_score, 2),
        "pangu_integration": has_pangu,
        "harmonyos_integration": has_harmony,
        "harmonyos_agent": harmony_result.to_dict(),
        "huawei_cloud": cloud_result.to_dict(),
        "readiness_level": _readiness_level(contest_score),
        "recommendations": _generate_recommendations(harmony_result, cloud_result, has_pangu, has_harmony),
    }


def _readiness_level(score: float) -> str:
    if score >= 8.0:
        return "excellent"
    elif score >= 6.0:
        return "good"
    elif score >= 4.0:
        return "moderate"
    elif score >= 2.0:
        return "basic"
    return "insufficient"


def _generate_recommendations(
    harmony: HuaweiEvalResult,
    cloud: HuaweiEvalResult,
    has_pangu: bool,
    has_harmony: bool,
) -> list[str]:
    recs = []
    if not has_pangu:
        recs.append("建议集成盘古大模型API评估能力, 增强华为云赛事贴合度")
    if not has_harmony:
        recs.append("建议添加鸿蒙HarmonyOS开发指导, 增强鸿蒙生态贴合度")
    for d in harmony.dimensions:
        if d.score < 5.0:
            recs.append(f"鸿蒙维度 '{d.dimension}' 得分偏低({d.score:.1f}/10): {d.feedback}")
    for d in cloud.dimensions:
        if d.score < 5.0:
            recs.append(f"华为云维度 '{d.dimension}' 得分偏低({d.score:.1f}/10): {d.feedback}")
    if not recs:
        recs.append("赛事贴合度良好, 继续保持")
    return recs[:5]
