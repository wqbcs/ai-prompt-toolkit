# A/B测试最优匹配推荐器 (Recommender)

> 完整的Python最优匹配推荐器实现，可直接运行

```python
"""
A/B 测试最优匹配推荐器

基于多维度评分（质量/延迟/成本/稳定性）推荐最优 Provider

用法:
    from recommender import Recommender, ProviderMetrics
    rec = Recommender()
    rec.add_metrics("openai", metrics1)
    rec.add_metrics("anthropic", metrics2)
    best = rec.recommend()
"""

from __future__ import annotations

import enum
import dataclasses
from typing import Dict, List, Optional, Tuple, Any


# ──────────────────────────────────────────
#  数据类型
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class ProviderMetrics:
    """Provider 指标

    Attributes:
        provider:        Provider 名称
        quality_score:   质量评分 (0-1, 越高越好)
        avg_latency_ms:  平均延迟 (ms, 越低越好)
        p99_latency_ms:  P99 延迟 (ms)
        cost_per_1k_tokens: 每千 Token 成本 (USD)
        success_rate:    成功率 (0-1)
        n_samples:       样本数
        tokens_per_second: 生成速度 (tokens/s)
    """
    provider: str
    quality_score: float = 0.0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    cost_per_1k_tokens: float = 0.0
    success_rate: float = 1.0
    n_samples: int = 0
    tokens_per_second: float = 0.0

    def validate(self) -> List[str]:
        """校验指标合法性"""
        issues: List[str] = []
        if not (0 <= self.quality_score <= 1):
            issues.append(f"quality_score 超出 [0,1]: {self.quality_score}")
        if not (0 <= self.success_rate <= 1):
            issues.append(f"success_rate 超出 [0,1]: {self.success_rate}")
        if self.avg_latency_ms < 0:
            issues.append(f"avg_latency_ms 为负: {self.avg_latency_ms}")
        if self.cost_per_1k_tokens < 0:
            issues.append(f"cost_per_1k_tokens 为负: {self.cost_per_1k_tokens}")
        return issues


class OptimizationGoal(enum.Enum):
    """优化目标"""
    QUALITY = "quality"          # 质量优先
    LATENCY = "latency"          # 延迟优先
    COST = "cost"                # 成本优先
    BALANCED = "balanced"        # 均衡
    STABILITY = "stability"      # 稳定性优先


@dataclasses.dataclass(frozen=True, slots=True)
class Recommendation:
    """推荐结果

    Attributes:
        provider:       推荐的 Provider
        score:          综合得分
        goal:           优化目标
        breakdown:      各维度得分
        reason:         推荐理由
        alternatives:   备选方案
        warnings:       警告
    """
    provider: str
    score: float
    goal: OptimizationGoal
    breakdown: Dict[str, float]
    reason: str
    alternatives: List[Tuple[str, float]] = dataclasses.field(default_factory=list)
    warnings: List[str] = dataclasses.field(default_factory=list)

    def __repr__(self) -> str:
        alt_str = ", ".join(f"{p}({s:.3f})" for p, s in self.alternatives[:3])
        return (
            f"推荐: {self.provider} (综合得分={self.score:.4f})\n"
            f"  优化目标: {self.goal.value}\n"
            f"  理由: {self.reason}\n"
            f"  备选: {alt_str}"
        )


# ──────────────────────────────────────────
#  权重配置
# ──────────────────────────────────────────

_GOAL_WEIGHTS: Dict[OptimizationGoal, Dict[str, float]] = {
    OptimizationGoal.QUALITY: {
        "quality": 0.50,
        "latency": 0.15,
        "cost": 0.10,
        "stability": 0.25,
    },
    OptimizationGoal.LATENCY: {
        "quality": 0.20,
        "latency": 0.45,
        "cost": 0.10,
        "stability": 0.25,
    },
    OptimizationGoal.COST: {
        "quality": 0.20,
        "latency": 0.10,
        "cost": 0.45,
        "stability": 0.25,
    },
    OptimizationGoal.BALANCED: {
        "quality": 0.30,
        "latency": 0.25,
        "cost": 0.20,
        "stability": 0.25,
    },
    OptimizationGoal.STABILITY: {
        "quality": 0.15,
        "latency": 0.15,
        "cost": 0.15,
        "stability": 0.55,
    },
}


# ──────────────────────────────────────────
#  推荐器
# ──────────────────────────────────────────

class Recommender:
    """最优匹配推荐器

    基于多维度指标推荐最优 Provider。
    支持 5 种优化目标：质量/延迟/成本/均衡/稳定性。
    """

    def __init__(
        self,
        min_samples: int = 3,
        min_success_rate: float = 0.8,
    ):
        self._metrics: Dict[str, ProviderMetrics] = {}
        self._min_samples = min_samples
        self._min_success_rate = min_success_rate

    def add_metrics(self, provider: str, metrics: ProviderMetrics) -> None:
        """添加 Provider 指标"""
        issues = metrics.validate()
        if issues:
            raise ValueError(f"指标校验失败: {issues}")
        self._metrics[provider] = metrics

    def add_metrics_from_runs(
        self,
        provider: str,
        latencies_ms: List[float],
        quality_scores: List[float],
        success_count: int,
        total_count: int,
        cost_per_1k: float = 0.0,
    ) -> None:
        """从运行数据构建指标

        Args:
            provider:       Provider 名称
            latencies_ms:   延迟列表
            quality_scores: 质量评分列表
            success_count:  成功次数
            total_count:    总次数
            cost_per_1k:    每千 Token 成本
        """
        if not latencies_ms:
            return

        avg_lat = sum(latencies_ms) / len(latencies_ms)
        sorted_lat = sorted(latencies_ms)
        p99_idx = min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)
        p99_lat = sorted_lat[p99_idx]

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        success_rate = success_count / total_count if total_count > 0 else 0

        metrics = ProviderMetrics(
            provider=provider,
            quality_score=round(avg_quality, 4),
            avg_latency_ms=round(avg_lat, 2),
            p99_latency_ms=round(p99_lat, 2),
            cost_per_1k_tokens=cost_per_1k,
            success_rate=round(success_rate, 4),
            n_samples=total_count,
        )
        self.add_metrics(provider, metrics)

    def recommend(
        self,
        goal: OptimizationGoal = OptimizationGoal.BALANCED,
        *,
        max_latency_ms: float | None = None,
        max_cost_per_1k: float | None = None,
        min_quality: float | None = None,
    ) -> Recommendation:
        """推荐最优 Provider

        Args:
            goal:            优化目标
            max_latency_ms:  最大延迟约束
            max_cost_per_1k: 最大成本约束
            min_quality:     最低质量约束

        Returns:
            Recommendation

        Raises:
            ValueError: 无可用 Provider
        """
        if not self._metrics:
            raise ValueError("无可用 Provider 指标")

        weights = _GOAL_WEIGHTS[goal]
        candidates: Dict[str, Dict[str, float]] = {}
        warnings: List[str] = []

        for name, m in self._metrics.items():
            # 约束过滤
            if m.n_samples < self._min_samples:
                warnings.append(f"{name}: 样本不足 ({m.n_samples}<{self._min_samples})")
                continue

            if m.success_rate < self._min_success_rate:
                warnings.append(f"{name}: 成功率过低 ({m.success_rate:.2%})")
                continue

            if max_latency_ms and m.avg_latency_ms > max_latency_ms:
                warnings.append(f"{name}: 延迟超限 ({m.avg_latency_ms:.1f}ms>{max_latency_ms}ms)")
                continue

            if max_cost_per_1k and m.cost_per_1k_tokens > max_cost_per_1k:
                warnings.append(f"{name}: 成本超限")
                continue

            if min_quality and m.quality_score < min_quality:
                warnings.append(f"{name}: 质量不足 ({m.quality_score:.3f}<{min_quality})")
                continue

            # 归一化评分（0-1，越高越好）
            quality_score = m.quality_score
            latency_score = self._normalize_latency(m.avg_latency_ms)
            cost_score = self._normalize_cost(m.cost_per_1k_tokens)
            stability_score = m.success_rate

            candidates[name] = {
                "quality": quality_score,
                "latency": latency_score,
                "cost": cost_score,
                "stability": stability_score,
            }

        if not candidates:
            # 降级：忽略约束
            for name, m in self._metrics.items():
                candidates[name] = {
                    "quality": m.quality_score,
                    "latency": self._normalize_latency(m.avg_latency_ms),
                    "cost": self._normalize_cost(m.cost_per_1k_tokens),
                    "stability": m.success_rate,
                }
            warnings.append("所有 Provider 均不满足约束，已降级推荐")

        # 加权求和
        scores: Dict[str, Tuple[float, Dict[str, float]]] = {}
        for name, dims in candidates.items():
            total = sum(dims[k] * weights[k] for k in weights)
            scores[name] = (total, dims)

        # 排序
        ranked = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)

        best_name, (best_score, best_dims) = ranked[0]
        alternatives = [(name, score) for name, (score, _) in ranked[1:]]

        # 生成理由
        reason = self._generate_reason(best_name, best_dims, goal, weights)

        return Recommendation(
            provider=best_name,
            score=round(best_score, 6),
            goal=goal,
            breakdown={k: round(v, 4) for k, v in best_dims.items()},
            reason=reason,
            alternatives=[(n, round(s, 6)) for n, s in alternatives],
            warnings=warnings,
        )

    def rank_all(
        self,
        goal: OptimizationGoal = OptimizationGoal.BALANCED,
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """排名所有 Provider

        Returns:
            [(provider, score, breakdown), ...] 按分数降序
        """
        if not self._metrics:
            return []

        weights = _GOAL_WEIGHTS[goal]
        results: List[Tuple[str, float, Dict[str, float]]] = []

        for name, m in self._metrics.items():
            dims = {
                "quality": m.quality_score,
                "latency": self._normalize_latency(m.avg_latency_ms),
                "cost": self._normalize_cost(m.cost_per_1k_tokens),
                "stability": m.success_rate,
            }
            total = sum(dims[k] * weights[k] for k in weights)
            results.append((name, round(total, 6), {k: round(v, 4) for k, v in dims.items()}))

        return sorted(results, key=lambda x: x[1], reverse=True)

    @property
    def providers(self) -> List[str]:
        """已注册的 Provider 列表"""
        return list(self._metrics.keys())

    # ── 归一化 ──

    @staticmethod
    def _normalize_latency(latency_ms: float) -> float:
        """延迟归一化（越低越好 → 归一化后越高越好）"""
        if latency_ms <= 0:
            return 1.0
        # 使用反比例: 1 / (1 + latency/1000)
        return 1.0 / (1.0 + latency_ms / 1000.0)

    @staticmethod
    def _normalize_cost(cost_per_1k: float) -> float:
        """成本归一化（越低越好 → 归一化后越高越好）"""
        if cost_per_1k <= 0:
            return 1.0
        return 1.0 / (1.0 + cost_per_1k / 0.01)

    # ── 理由生成 ──

    @staticmethod
    def _generate_reason(
        name: str,
        dims: Dict[str, float],
        goal: OptimizationGoal,
        weights: Dict[str, float],
    ) -> str:
        """生成推荐理由"""
        best_dim = max(weights, key=lambda k: dims[k] * weights[k])
        dim_names = {
            "quality": "质量",
            "latency": "延迟",
            "cost": "成本",
            "stability": "稳定性",
        }
        return (
            f"在「{goal.value}」目标下，{name} 综合得分最高，"
            f"优势维度为{dim_names.get(best_dim, best_dim)} "
            f"(得分={dims[best_dim]:.4f})"
        )


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    # ── 测试 1: 质量优先 ──
    rec = Recommender(min_samples=1)
    rec.add_metrics("openai", ProviderMetrics(
        provider="openai", quality_score=0.95, avg_latency_ms=500,
        cost_per_1k_tokens=0.03, success_rate=0.99, n_samples=10,
    ))
    rec.add_metrics("anthropic", ProviderMetrics(
        provider="anthropic", quality_score=0.85, avg_latency_ms=300,
        cost_per_1k_tokens=0.02, success_rate=0.98, n_samples=10,
    ))
    result = rec.recommend(OptimizationGoal.QUALITY)
    assert_eq("质量优先", result.provider, "openai")

    # ── 测试 2: 延迟优先 ──
    result = rec.recommend(OptimizationGoal.LATENCY)
    assert_eq("延迟优先", result.provider, "anthropic")

    # ── 测试 3: 成本优先 ──
    result = rec.recommend(OptimizationGoal.COST)
    assert_eq("成本优先", result.provider, "anthropic")

    # ── 测试 4: 稳定性优先 ──
    result = rec.recommend(OptimizationGoal.STABILITY)
    assert_eq("稳定性优先", result.provider, "openai")

    # ── 测试 5: 均衡 ──
    result = rec.recommend(OptimizationGoal.BALANCED)
    assert_eq("均衡-有结果", result.provider in ("openai", "anthropic"), True)

    # ── 测试 6: 约束过滤 ──
    result = rec.recommend(OptimizationGoal.BALANCED, max_latency_ms=400)
    assert_eq("延迟约束", result.provider, "anthropic")

    # ── 测试 7: 备选 ──
    assert_eq("备选-非空", len(result.alternatives) > 0, True)

    # ── 测试 8: 理由 ──
    assert_eq("理由-非空", len(result.reason) > 0, True)

    # ── 测试 9: 排名 ──
    ranking = rec.rank_all(OptimizationGoal.QUALITY)
    assert_eq("排名-2个", len(ranking), 2)
    assert_eq("排名-顺序", ranking[0][0], "openai")

    # ── 测试 10: 样本不足 ──
    rec2 = Recommender(min_samples=5)
    rec2.add_metrics("test", ProviderMetrics(
        provider="test", quality_score=0.9, n_samples=2,
    ))
    result = rec2.recommend(OptimizationGoal.BALANCED)
    assert_eq("样本不足-有警告", len(result.warnings) > 0, True)

    # ── 测试 11: 成功率过低 ──
    rec3 = Recommender(min_samples=1, min_success_rate=0.9)
    rec3.add_metrics("bad", ProviderMetrics(
        provider="bad", quality_score=0.5, success_rate=0.5, n_samples=10,
    ))
    result = rec3.recommend(OptimizationGoal.BALANCED)
    assert_eq("成功率-有警告", len(result.warnings) > 0, True)

    # ── 测试 12: 指标校验 ──
    try:
        rec.add_metrics("invalid", ProviderMetrics(
            provider="invalid", quality_score=1.5,
        ))
        assert_eq("校验-应报错", False, True)
    except ValueError:
        assert_eq("校验-报错", True, True)

    # ── 测试 13: add_metrics_from_runs ──
    rec4 = Recommender(min_samples=1)
    rec4.add_metrics_from_runs(
        provider="openai",
        latencies_ms=[100, 150, 200, 250, 300],
        quality_scores=[0.9, 0.85, 0.92, 0.88, 0.91],
        success_count=5,
        total_count=5,
        cost_per_1k=0.03,
    )
    assert_eq("from_runs-已注册", "openai" in rec4.providers, True)

    # ── 测试 14: 4个Provider ──
    rec5 = Recommender(min_samples=1)
    rec5.add_metrics("openai", ProviderMetrics(provider="openai", quality_score=0.9, avg_latency_ms=500, cost_per_1k_tokens=0.03, success_rate=0.99, n_samples=10))
    rec5.add_metrics("anthropic", ProviderMetrics(provider="anthropic", quality_score=0.88, avg_latency_ms=400, cost_per_1k_tokens=0.025, success_rate=0.98, n_samples=10))
    rec5.add_metrics("aliyun", ProviderMetrics(provider="aliyun", quality_score=0.82, avg_latency_ms=200, cost_per_1k_tokens=0.008, success_rate=0.97, n_samples=10))
    rec5.add_metrics("huawei", ProviderMetrics(provider="huawei", quality_score=0.80, avg_latency_ms=250, cost_per_1k_tokens=0.006, success_rate=0.96, n_samples=10))

    result = rec5.recommend(OptimizationGoal.BALANCED)
    assert_eq("4Provider-有结果", result.provider in rec5.providers, True)
    ranking = rec5.rank_all(OptimizationGoal.BALANCED)
    assert_eq("4Provider-排名4", len(ranking), 4)

    print(f"\nRecommender 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
