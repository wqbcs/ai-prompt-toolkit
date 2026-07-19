"""A/B测试类型定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ALIYUN = "aliyun"
    DEEPSEEK = "deepseek"
    HUAWEI = "huawei"
    PANGU = "pangu"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    GROQ = "groq"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    PERPLEXITY = "perplexity"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    BAIDU = "baidu"
    MINIMAX = "minimax"


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ModelConfig:
    provider: ProviderType
    model_name: str
    api_key_env: str = ""
    api_base: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    extra_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "api_key_env": self.api_key_env,
            "api_base": self.api_base,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra_params": self.extra_params,
        }


@dataclass
class EvaluationDimension:
    dimension_id: str
    name: str
    description: str = ""
    weight: float = 1.0
    scoring_mode: str = "auto"
    min_score: float = 0.0
    max_score: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "scoring_mode": self.scoring_mode,
            "min_score": self.min_score,
            "max_score": self.max_score,
        }


@dataclass
class TestDataset:
    dataset_id: str
    name: str
    items: list[dict[str, str]] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "items": self.items,
            "description": self.description,
        }


@dataclass
class ModelResult:
    model_config: ModelConfig
    prompt_template: str
    response: str = ""
    latency_ms: float = 0.0
    token_count: int = 0
    cost: float = 0.0
    status: TestStatus = TestStatus.PENDING
    error_message: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_config": self.model_config.to_dict(),
            "prompt_template": self.prompt_template,
            "response": self.response,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "cost": self.cost,
            "status": self.status.value,
            "error_message": self.error_message,
            "scores": self.scores,
            "metadata": self.metadata,
        }


@dataclass
class TestResult:
    test_id: str
    model_a_result: ModelResult
    model_b_result: ModelResult
    dimension: EvaluationDimension
    winner: str = ""
    confidence: float = 0.0
    p_value: float = 1.0
    effect_size: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "model_a_result": self.model_a_result.to_dict(),
            "model_b_result": self.model_b_result.to_dict(),
            "dimension": self.dimension.to_dict(),
            "winner": self.winner,
            "confidence": self.confidence,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "timestamp": self.timestamp,
        }


@dataclass
class WinRateCell:
    model_a: str
    model_b: str
    dimension_id: str
    wins_a: int = 0
    wins_b: int = 0
    ties: int = 0
    total: int = 0
    win_rate_a: float = 0.0
    win_rate_b: float = 0.0
    significant: bool = False
    p_value: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "dimension_id": self.dimension_id,
            "wins_a": self.wins_a,
            "wins_b": self.wins_b,
            "ties": self.ties,
            "total": self.total,
            "win_rate_a": self.win_rate_a,
            "win_rate_b": self.win_rate_b,
            "significant": self.significant,
            "p_value": self.p_value,
        }


@dataclass
class StatisticalReport:
    test_id: str
    total_tests: int = 0
    completed_tests: int = 0
    failed_tests: int = 0
    win_rate_matrix: list[WinRateCell] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "total_tests": self.total_tests,
            "completed_tests": self.completed_tests,
            "failed_tests": self.failed_tests,
            "win_rate_matrix": [w.to_dict() for w in self.win_rate_matrix],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


@dataclass
class OptimalMatch:
    model_config: ModelConfig
    prompt_template: str
    scenario: str = ""
    dimensions: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_config": self.model_config.to_dict(),
            "prompt_template": self.prompt_template,
            "scenario": self.scenario,
            "dimensions": self.dimensions,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class ABTestConfig:
    test_id: str
    models: list[ModelConfig] = field(default_factory=list)
    datasets: list[TestDataset] = field(default_factory=list)
    dimensions: list[EvaluationDimension] = field(default_factory=list)
    prompt_templates: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    significance_level: float = 0.05
    min_sample_size: int = 30

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "models": [m.to_dict() for m in self.models],
            "datasets": [d.to_dict() for d in self.datasets],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "prompt_templates": self.prompt_templates,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "significance_level": self.significance_level,
            "min_sample_size": self.min_sample_size,
        }
