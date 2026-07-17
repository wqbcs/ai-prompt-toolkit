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

_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4": (0.03, 0.06),
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3": (0.003, 0.015),
    "claude-3.5": (0.003, 0.015),
    "deepseek": (0.00014, 0.00028),
    "qwen": (0.0004, 0.0012),
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


def estimate_tokens(text: str, model: str = "default") -> TokenEstimate:
    char_count = len(text)
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

    if original_tokens > 8000:
        findings.append(Finding(
            rule_id="TOKEN-001",
            severity=Severity.MEDIUM,
            description=f"Prompt过长({original_tokens} tokens), 建议压缩到4000 tokens以内",
        ))

    if original_tokens > 4000:
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
