"""Token压缩分析模块

参考:
- headroom (https://github.com/headroomlabs-ai/headroom): 59.7k stars, 编码Agent减20% token, JSON减60-95%
- LLMLingua: 基于小模型的Token级压缩, 压缩率2-10x
- Anthropic Prompt Caching: 服务端缓存系统Prompt, 减少50-90%输入成本

核心能力:
1. Token估算: 基于字符数+模型类型估算Token消耗
2. 冗余检测: 检测Prompt中的冗余内容(重复短语/无效空格/过长示例)
3. 压缩建议: 给出具体的Token优化建议
4. 成本估算: 根据模型定价估算API调用成本
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


_TOKEN_RATIOS: dict[str, float] = {
    "gpt-4": 0.75,
    "gpt-4o": 0.75,
    "gpt-4o-mini": 0.75,
    "gpt-3.5-turbo": 0.75,
    "claude-3": 0.70,
    "claude-3.5": 0.70,
    "gemini-pro": 0.70,
    "deepseek": 0.65,
    "qwen": 0.60,
    "default": 0.70,
}

_TOKEN_RATIOS_V2: dict[str, float] = {
    **_TOKEN_RATIOS,
    "pangu": 0.55,
    "ernie": 0.60,
    "glm": 0.62,
    "kimi": 0.60,
    "minimax": 0.60,
    "gemini-2.0": 0.72,
    "llama-3": 0.75,
    "mistral": 0.72,
    "yi": 0.60,
    "baichuan": 0.58,
}

_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4": (0.03, 0.06),
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3": (0.003, 0.015),
    "claude-3.5": (0.003, 0.015),
    "claude-4": (0.003, 0.015),
    "deepseek": (0.00014, 0.00028),
    "deepseek-r1": (0.00055, 0.00219),
    "qwen": (0.0004, 0.0012),
    "qwen-max": (0.002, 0.006),
    "pangu": (0.0012, 0.004),
    "ernie-4.0": (0.0012, 0.012),
    "glm-4": (0.001, 0.001),
    "kimi": (0.0012, 0.0012),
    "minimax": (0.001, 0.001),
    "gemini-pro": (0.000375, 0.0015),
    "gemini-2.0": (0.0, 0.0),
    "mistral-large": (0.002, 0.006),
    "llama-3": (0.0, 0.0),
    "default": (0.003, 0.015),
}

_REDUNDANCY_PATTERNS = [
    (r"(\b\w+\b)\s+\1\b", "重复单词", 0.5),
    (r"[ \t]{2,}", "多余空格", 0.3),
    (r"\n{3,}", "多余空行", 0.2),
    (r"(.{20,}?)\1{2,}", "重复段落", 2.0),
    (r"(?:example|示例|例子)\s*\d+[:：].*?(?=(?:example|示例|例子)\s*\d+[:：]|$)", "过多示例(>3个可精简)", 1.5),
    (r"(?:注意|Note|IMPORTANT|WARNING)[:：].*?(?=(?:注意|Note|IMPORTANT|WARNING)[:：]|$)", "过多警告标记", 1.0),
]


@dataclass
class TokenEstimate:
    model: str
    char_count: int
    estimated_tokens: int
    estimated_input_cost_usd: float
    estimated_output_cost_usd: float
    ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "char_count": self.char_count,
            "estimated_tokens": self.estimated_tokens,
            "estimated_input_cost_usd": round(self.estimated_input_cost_usd, 6),
            "estimated_output_cost_usd": round(self.estimated_output_cost_usd, 6),
            "ratio": round(self.ratio, 3),
        }


@dataclass
class CompressionSuggestion:
    suggestion_id: str
    category: str
    description: str
    estimated_savings_tokens: int
    estimated_savings_percent: float
    priority: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "category": self.category,
            "description": self.description,
            "estimated_savings_tokens": self.estimated_savings_tokens,
            "estimated_savings_percent": round(self.estimated_savings_percent, 1),
            "priority": self.priority,
        }


@dataclass
class TokenAnalysisResult:
    original_tokens: int
    optimized_tokens: int
    savings_tokens: int
    savings_percent: float
    estimate: TokenEstimate
    suggestions: list[CompressionSuggestion] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_tokens": self.original_tokens,
            "optimized_tokens": self.optimized_tokens,
            "savings_tokens": self.savings_tokens,
            "savings_percent": round(self.savings_percent, 1),
            "estimate": self.estimate.to_dict(),
            "suggestions": [s.to_dict() for s in self.suggestions],
            "findings": [f.to_dict() for f in self.findings],
        }


_TIKTOKEN_MODEL_MAP: dict[str, str] = {
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
}


def _tiktoken_count(text: str, model: str) -> int | None:
    try:
        import tiktoken
    except ImportError:
        return None
    encoding_name = _TIKTOKEN_MODEL_MAP.get(model)
    if not encoding_name:
        for key in _TIKTOKEN_MODEL_MAP:
            if model.lower().startswith(key):
                encoding_name = _TIKTOKEN_MODEL_MAP[key]
                break
    if not encoding_name:
        return None
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return None


def estimate_tokens(text: str, model: str = "default") -> TokenEstimate:
    char_count = len(text)
    exact_count = _tiktoken_count(text, model)
    if exact_count is not None:
        estimated_tokens = exact_count
        ratio = round(estimated_tokens / max(char_count, 1), 3)
    else:
        ratio = _TOKEN_RATIOS.get(model, _TOKEN_RATIOS["default"])
        for key in _TOKEN_RATIOS:
            if model.lower().startswith(key):
                ratio = _TOKEN_RATIOS[key]
                break
        estimated_tokens = max(int(char_count * ratio), 1)
    pricing = _PRICING.get("default", (0.003, 0.015))
    for key in _PRICING:
        if model.lower().startswith(key):
            pricing = _PRICING[key]
            break
    input_cost = estimated_tokens / 1000 * pricing[0]
    output_cost = estimated_tokens / 1000 * pricing[1]
    return TokenEstimate(
        model=model, char_count=char_count, estimated_tokens=estimated_tokens,
        estimated_input_cost_usd=input_cost, estimated_output_cost_usd=output_cost,
        ratio=ratio,
    )


def detect_redundancy(text: str) -> list[CompressionSuggestion]:
    suggestions: list[CompressionSuggestion] = []
    sid = 0
    for pattern, name, savings_factor in _REDUNDANCY_PATTERNS:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            sid += 1
            savings = int(len(str(matches[0])) * savings_factor * 0.7)
            suggestions.append(CompressionSuggestion(
                suggestion_id=f"COMP-{sid:03d}",
                category="redundancy",
                description=f"{name}: 发现{len(matches)}处, 清理可节省约{max(savings, 1)} tokens",
                estimated_savings_tokens=max(savings, 1),
                estimated_savings_percent=min(savings / max(len(text) * 0.7, 1) * 100, 50),
                priority="medium" if savings < 50 else "high",
            ))
    return suggestions


def analyze_prompt_tokens(text: str, model: str = "default") -> TokenAnalysisResult:
    estimate = estimate_tokens(text, model)
    original_tokens = estimate.estimated_tokens

    suggestions = detect_redundancy(text)
    findings: list[Finding] = []

    total_savings = sum(s.estimated_savings_tokens for s in suggestions)
    optimized_tokens = max(original_tokens - total_savings, 1)
    savings_percent = (total_savings / max(original_tokens, 1)) * 100

    char_count = len(text)
    if original_tokens > 8000 or char_count > 12000:
        findings.append(Finding(
            rule_id="TOKEN-001",
            severity=Severity.MEDIUM,
            description=f"Prompt过长({original_tokens} tokens, {char_count} chars), 建议压缩到4000 tokens以内",
        ))

    if original_tokens > 4000 or char_count > 6000:
        suggestions.append(CompressionSuggestion(
            suggestion_id="COMP-STR-001",
            category="structure",
            description="使用变量模板替代重复内容, 考虑条件编译按场景裁剪",
            estimated_savings_tokens=original_tokens // 4,
            estimated_savings_percent=25.0,
            priority="high",
        ))

    if text.count("\n") > len(text) / 30:
        suggestions.append(CompressionSuggestion(
            suggestion_id="COMP-FMT-001",
            category="formatting",
            description="过多换行, 合并短行为段落可节省5-10% tokens",
            estimated_savings_tokens=original_tokens // 15,
            estimated_savings_percent=7.0,
            priority="low",
        ))

    total_savings = sum(s.estimated_savings_tokens for s in suggestions)
    optimized_tokens = max(original_tokens - total_savings, 1)
    savings_percent = (total_savings / max(original_tokens, 1)) * 100

    return TokenAnalysisResult(
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        savings_tokens=total_savings,
        savings_percent=savings_percent,
        estimate=estimate,
        suggestions=suggestions,
        findings=findings,
    )


@dataclass
class MultiModelComparison:
    text_length: int
    estimates: list[TokenEstimate]
    cheapest_model: str
    most_efficient_model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_length": self.text_length,
            "estimates": [e.to_dict() for e in self.estimates],
            "cheapest_model": self.cheapest_model,
            "most_efficient_model": self.most_efficient_model,
        }


_DEFAULT_COMPARE_MODELS = [
    "gpt-4o", "claude-3.5", "deepseek", "qwen", "pangu", "glm-4", "kimi", "gemini-pro",
]


def compare_models(text: str, models: list[str] | None = None) -> MultiModelComparison:
    if not models:
        models = _DEFAULT_COMPARE_MODELS
    estimates = [estimate_tokens(text, m) for m in models]
    cheapest = min(estimates, key=lambda e: e.estimated_input_cost_usd)
    most_efficient = min(estimates, key=lambda e: e.estimated_tokens)
    return MultiModelComparison(
        text_length=len(text),
        estimates=estimates,
        cheapest_model=cheapest.model,
        most_efficient_model=most_efficient.model,
    )
