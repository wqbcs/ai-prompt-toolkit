# 最优匹配推荐器设计

## 1. 架构总览

### 1.1 数据流图

```
┌──────────────────┐     ┌──────────────────┐
│  StatisticalTest │────▶│  Recommender      │
│  Results         │     │  Engine           │
└──────────────────┘     └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
           ┌──────────────┐ ┌──────────┐ ┌──────────────┐
           │  WinRate     │ │ Composite│ │  Exclusion   │
           │  Recommender │ │ Score    │ │  Filter      │
           │  (胜率+显著) │ │Recommender│ │  (排除规则)  │
           └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                  │              │              │
                  └──────────────┼──────────────┘
                                 ▼
                    ┌──────────────────────┐
                    │  Reason Generator    │
                    │  (推荐理由生成)       │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Recommendation      │
                    │  Report              │
                    └──────────────────────┘
```

### 1.2 核心流程

```
统计结果 → 排除规则过滤 → 胜率计算 → 综合评分 → 排序 → 生成推荐理由 → 推荐报告
```

---

## 2. 推荐器接口定义

### 2.1 核心类型

```typescript
interface CandidateModel {
  providerId: string;
  modelId: string;
  displayName: string;
  sampleGroup: SampleGroup;
  statisticalResult: StatisticalTestResult;
  costEstimate: CostEstimate;
  latencyStats: {
    mean: number;
    p50: number;
    p95: number;
  };
}

interface Recommendation {
  rank: number;
  candidate: CandidateModel;
  mode: "win_rate" | "composite";
  score: number;
  confidence: "high" | "medium" | "low";
  reasons: RecommendationReason[];
  warnings: string[];
  excluded: boolean;
  exclusionReason?: string;
}

interface RecommendationReason {
  category: "quality" | "cost" | "latency" | "significance" | "stability";
  description: string;
  weight: number;
  supporting_data: Record<string, number>;
}

interface RecommendationReport {
  id: string;
  suiteId: string;
  timestamp: string;
  mode: "win_rate" | "composite";
  recommendations: Recommendation[];
  bestPick: Recommendation;
  summary: string;
  exclusions: ExclusionRecord[];
  metadata: {
    candidateCount: number;
    excludedCount: number;
    significanceLevel: number;
    minimumSampleSize: number;
  };
}

interface ExclusionRecord {
  providerId: string;
  modelId: string;
  reason: string;
  rule: ExclusionRule;
  details: string;
}

interface ExclusionRule {
  type: "unstable" | "insufficient_sample" | "high_error_rate" | "timeout_excessive" | "cost_overrun";
  threshold: number;
  description: string;
}
```

---

## 3. 胜率+显著性推荐模式

### 3.1 胜率计算

```typescript
interface WinRateResult {
  providerId: string;
  modelId: string;
  wins: number;
  losses: number;
  ties: number;
  totalComparisons: number;
  winRate: number;
  significantWins: number;
  significantWinRate: number;
}

class WinRateRecommender {
  private alpha: number;
  private statisticalSelector: StatisticalTestSelector;

  constructor(alpha: number = 0.05) {
    this.alpha = alpha;
    this.statisticalSelector = new StatisticalTestSelector(alpha);
  }

  rank(candidates: CandidateModel[]): Recommendation[] {
    const pairs = this.generatePairs(candidates);
    const results = this.computePairwiseWinRates(pairs, candidates);

    const rankings = candidates.map(candidate => {
      const result = results.get(`${candidate.providerId}:${candidate.modelId}`)!;
      const score = result.significantWinRate;

      return {
        rank: 0,
        candidate,
        mode: "win_rate" as const,
        score,
        confidence: this.assessConfidence(result),
        reasons: this.generateWinRateReasons(candidate, result),
        warnings: this.generateWinRateWarnings(candidate, result),
        excluded: false
      };
    });

    rankings.sort((a, b) => b.score - a.score);
    rankings.forEach((r, i) => r.rank = i + 1);

    return rankings;
  }

  private generatePairs(candidates: CandidateModel[]): [CandidateModel, CandidateModel][] {
    const pairs: [CandidateModel, CandidateModel][] = [];
    for (let i = 0; i < candidates.length; i++) {
      for (let j = i + 1; j < candidates.length; j++) {
        pairs.push([candidates[i], candidates[j]]);
      }
    }
    return pairs;
  }

  private computePairwiseWinRates(
    pairs: [CandidateModel, CandidateModel][],
    candidates: CandidateModel[]
  ): Map<string, WinRateResult> {
    const results = new Map<string, WinRateResult>();

    for (const candidate of candidates) {
      const key = `${candidate.providerId}:${candidate.modelId}`;
      results.set(key, {
        providerId: candidate.providerId,
        modelId: candidate.modelId,
        wins: 0,
        losses: 0,
        ties: 0,
        totalComparisons: 0,
        winRate: 0,
        significantWins: 0,
        significantWinRate: 0
      });
    }

    for (const [a, b] of pairs) {
      const comparison = this.statisticalSelector.compare(a.sampleGroup, b.sampleGroup);
      const keyA = `${a.providerId}:${a.modelId}`;
      const keyB = `${b.providerId}:${b.modelId}`;
      const resultA = results.get(keyA)!;
      const resultB = results.get(keyB)!;

      resultA.totalComparisons += 1;
      resultB.totalComparisons += 1;

      if (comparison.testResult.significant) {
        const meanDiff = comparison.testResult.meanDifference
          ?? comparison.testResult.medianDifference
          ?? (a.sampleGroup.mean - b.sampleGroup.mean);

        if (meanDiff > 0) {
          resultA.wins += 1;
          resultA.significantWins += 1;
          resultB.losses += 1;
        } else if (meanDiff < 0) {
          resultB.wins += 1;
          resultB.significantWins += 1;
          resultA.losses += 1;
        } else {
          resultA.ties += 1;
          resultB.ties += 1;
        }
      } else {
        if (a.sampleGroup.mean > b.sampleGroup.mean) {
          resultA.wins += 1;
          resultB.losses += 1;
        } else if (a.sampleGroup.mean < b.sampleGroup.mean) {
          resultB.wins += 1;
          resultA.losses += 1;
        } else {
          resultA.ties += 1;
          resultB.ties += 1;
        }
      }
    }

    for (const result of results.values()) {
      result.winRate = result.totalComparisons > 0
        ? result.wins / result.totalComparisons
        : 0;
      result.significantWinRate = result.totalComparisons > 0
        ? result.significantWins / result.totalComparisons
        : 0;
    }

    return results;
  }

  private assessConfidence(result: WinRateResult): "high" | "medium" | "low" {
    if (result.totalComparisons < 2) return "low";
    if (result.significantWinRate > 0.7 && result.totalComparisons >= 3) return "high";
    if (result.significantWinRate > 0.4) return "medium";
    return "low";
  }

  private generateWinRateReasons(candidate: CandidateModel, result: WinRateResult): RecommendationReason[] {
    const reasons: RecommendationReason[] = [];

    reasons.push({
      category: "significance",
      description: `显著胜率 ${(result.significantWinRate * 100).toFixed(1)}% (${result.significantWins}/${result.totalComparisons}对比较达到统计显著性)`,
      weight: 0.4,
      supporting_data: {
        significantWinRate: result.significantWinRate,
        significantWins: result.significantWins,
        totalComparisons: result.totalComparisons
      }
    });

    reasons.push({
      category: "quality",
      description: `整体胜率 ${(result.winRate * 100).toFixed(1)}% (胜${result.wins} / 负${result.losses} / 平${result.ties})`,
      weight: 0.3,
      supporting_data: {
        winRate: result.winRate,
        wins: result.wins,
        losses: result.losses,
        ties: result.ties
      }
    });

    if (candidate.statisticalResult.effectSize.cohensD > 0.5) {
      reasons.push({
        category: "quality",
        description: `效果量 Cohen's d=${candidate.statisticalResult.effectSize.cohensD.toFixed(3)} (${candidate.statisticalResult.effectSize.interpretation})`,
        weight: 0.3,
        supporting_data: {
          cohensD: candidate.statisticalResult.effectSize.cohensD,
          varianceExplained: candidate.statisticalResult.effectSize.varianceExplained
        }
      });
    }

    return reasons;
  }

  private generateWinRateWarnings(candidate: CandidateModel, result: WinRateResult): string[] {
    const warnings: string[] = [];

    if (result.totalComparisons < 2) {
      warnings.push("对比次数不足，胜率可能不可靠");
    }

    if (result.winRate > 0.5 && result.significantWinRate < 0.2) {
      warnings.push("虽有胜率但多数对比未达统计显著性，结果可能因随机性产生");
    }

    return warnings;
  }
}
```

---

## 4. 综合评分推荐模式

### 4.1 多维度评分

```typescript
interface ScoringWeights {
  quality: number;
  cost: number;
  latency: number;
  stability: number;
}

class CompositeScoreRecommender {
  private weights: ScoringWeights;

  constructor(weights?: Partial<ScoringWeights>) {
    this.weights = {
      quality: 0.4,
      cost: 0.25,
      latency: 0.2,
      stability: 0.15,
      ...weights
    };
  }

  rank(candidates: CandidateModel[]): Recommendation[] {
    const scored = candidates.map(candidate => {
      const qualityScore = this.computeQualityScore(candidate);
      const costScore = this.computeCostScore(candidate, candidates);
      const latencyScore = this.computeLatencyScore(candidate, candidates);
      const stabilityScore = this.computeStabilityScore(candidate);

      const compositeScore =
        qualityScore * this.weights.quality +
        costScore * this.weights.cost +
        latencyScore * this.weights.latency +
        stabilityScore * this.weights.stability;

      return {
        rank: 0,
        candidate,
        mode: "composite" as const,
        score: compositeScore,
        confidence: this.assessCompositeConfidence(candidate, qualityScore, costScore, latencyScore, stabilityScore),
        reasons: this.generateCompositeReasons(candidate, qualityScore, costScore, latencyScore, stabilityScore),
        warnings: this.generateCompositeWarnings(candidate, qualityScore, costScore, latencyScore, stabilityScore),
        excluded: false
      };
    });

    scored.sort((a, b) => b.score - a.score);
    scored.forEach((r, i) => r.rank = i + 1);

    return scored;
  }

  private computeQualityScore(candidate: CandidateModel): number {
    const effectSize = Math.abs(candidate.statisticalResult.effectSize.cohensD);
    const significance = candidate.statisticalResult.testResult.significant ? 1 : 0;

    const normalizedEffect = Math.min(1, effectSize / 1.2);

    return 0.6 * normalizedEffect + 0.4 * significance;
  }

  private computeCostScore(candidate: CandidateModel, allCandidates: CandidateModel[]): number {
    const costs = allCandidates.map(c => c.costEstimate.totalCost);
    const maxCost = Math.max(...costs);
    const minCost = Math.min(...costs);

    if (maxCost === minCost) return 1;

    const normalized = 1 - (candidate.costEstimate.totalCost - minCost) / (maxCost - minCost);
    return Math.max(0, Math.min(1, normalized));
  }

  private computeLatencyScore(candidate: CandidateModel, allCandidates: CandidateModel[]): number {
    const latencies = allCandidates.map(c => c.latencyStats.mean);
    const maxLatency = Math.max(...latencies);
    const minLatency = Math.min(...latencies);

    if (maxLatency === minLatency) return 1;

    const normalized = 1 - (candidate.latencyStats.mean - minLatency) / (maxLatency - minLatency);
    return Math.max(0, Math.min(1, normalized));
  }

  private computeStabilityScore(candidate: CandidateModel): number {
    const cv = candidate.sampleGroup.stdDev / candidate.sampleGroup.mean;
    const normalized = Math.max(0, 1 - cv);
    return normalized;
  }

  private assessCompositeConfidence(
    candidate: CandidateModel,
    quality: number,
    cost: number,
    latency: number,
    stability: number
  ): "high" | "medium" | "low" {
    const scores = [quality, cost, latency, stability];
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    const min = Math.min(...scores);

    if (avg > 0.7 && min > 0.5) return "high";
    if (avg > 0.4 && min > 0.2) return "medium";
    return "low";
  }

  private generateCompositeReasons(
    candidate: CandidateModel,
    qualityScore: number,
    costScore: number,
    latencyScore: number,
    stabilityScore: number
  ): RecommendationReason[] {
    const reasons: RecommendationReason[] = [];

    reasons.push({
      category: "quality",
      description: `质量评分 ${(qualityScore * 100).toFixed(1)}/100 (效果量d=${candidate.statisticalResult.effectSize.cohensD.toFixed(3)}, ${candidate.statisticalResult.testResult.significant ? "统计显著" : "未达显著"})`,
      weight: this.weights.quality,
      supporting_data: { qualityScore, cohensD: candidate.statisticalResult.effectSize.cohensD }
    });

    reasons.push({
      category: "cost",
      description: `成本评分 ${(costScore * 100).toFixed(1)}/100 (预估费用 ${candidate.costEstimate.currency} ${candidate.costEstimate.totalCost.toFixed(4)})`,
      weight: this.weights.cost,
      supporting_data: { costScore, totalCost: candidate.costEstimate.totalCost }
    });

    reasons.push({
      category: "latency",
      description: `延迟评分 ${(latencyScore * 100).toFixed(1)}/100 (均值${candidate.latencyStats.mean.toFixed(0)}ms, P95=${candidate.latencyStats.p95.toFixed(0)}ms)`,
      weight: this.weights.latency,
      supporting_data: { latencyScore, meanMs: candidate.latencyStats.mean, p95Ms: candidate.latencyStats.p95 }
    });

    const cv = candidate.sampleGroup.stdDev / candidate.sampleGroup.mean;
    reasons.push({
      category: "stability",
      description: `稳定性评分 ${(stabilityScore * 100).toFixed(1)}/100 (变异系数CV=${(cv * 100).toFixed(1)}%)`,
      weight: this.weights.stability,
      supporting_data: { stabilityScore, cv }
    });

    return reasons;
  }

  private generateCompositeWarnings(
    candidate: CandidateModel,
    qualityScore: number,
    costScore: number,
    latencyScore: number,
    stabilityScore: number
  ): string[] {
    const warnings: string[] = [];

    if (qualityScore < 0.3) {
      warnings.push("质量评分过低，该模型可能不适合当前场景");
    }
    if (costScore < 0.3) {
      warnings.push("成本较高，大规模部署时需注意预算控制");
    }
    if (latencyScore < 0.3) {
      warnings.push("延迟较高，可能影响用户体验");
    }
    if (stabilityScore < 0.5) {
      warnings.push("稳定性不足，输出波动较大");
    }
    if (qualityScore > 0.7 && costScore < 0.3) {
      warnings.push("质量与成本存在权衡，需确认是否可接受高成本");
    }

    return warnings;
  }
}
```

---

## 5. 排除规则

### 5.1 排除规则定义

```typescript
interface ExclusionConfig {
  minSampleSize: number;
  maxErrorRate: number;
  maxTimeoutRate: number;
  maxCoefficientOfVariation: number;
  maxCostPerRequest: number;
}

const DEFAULT_EXCLUSION_CONFIG: ExclusionConfig = {
  minSampleSize: 10,
  maxErrorRate: 0.2,
  maxTimeoutRate: 0.1,
  maxCoefficientOfVariation: 0.5,
  maxCostPerRequest: 1.0
};

class ExclusionFilter {
  private config: ExclusionConfig;

  constructor(config?: Partial<ExclusionConfig>) {
    this.config = { ...DEFAULT_EXCLUSION_CONFIG, ...config };
  }

  filter(candidates: CandidateModel[]): {
    passed: CandidateModel[];
    excluded: ExclusionRecord[];
  } {
    const passed: CandidateModel[] = [];
    const excluded: ExclusionRecord[] = [];

    for (const candidate of candidates) {
      const exclusions = this.evaluateExclusions(candidate);

      if (exclusions.length > 0) {
        excluded.push(...exclusions);
      } else {
        passed.push(candidate);
      }
    }

    return { passed, excluded };
  }

  private evaluateExclusions(candidate: CandidateModel): ExclusionRecord[] {
    const exclusions: ExclusionRecord[] = [];
    const key = `${candidate.providerId}:${candidate.modelId}`;

    if (candidate.sampleGroup.sampleSize < this.config.minSampleSize) {
      exclusions.push({
        providerId: candidate.providerId,
        modelId: candidate.modelId,
        reason: "样本量不足",
        rule: {
          type: "insufficient_sample",
          threshold: this.config.minSampleSize,
          description: `样本量低于最小要求 ${this.config.minSampleSize}`
        },
        details: `当前样本量: ${candidate.sampleGroup.sampleSize}, 最低要求: ${this.config.minSampleSize}`
      });
    }

    const cv = candidate.sampleGroup.stdDev / candidate.sampleGroup.mean;
    if (cv > this.config.maxCoefficientOfVariation) {
      exclusions.push({
        providerId: candidate.providerId,
        modelId: candidate.modelId,
        reason: "输出不稳定",
        rule: {
          type: "unstable",
          threshold: this.config.maxCoefficientOfVariation,
          description: `变异系数超过阈值 ${this.config.maxCoefficientOfVariation}`
        },
        details: `当前CV: ${(cv * 100).toFixed(1)}%, 阈值: ${(this.config.maxCoefficientOfVariation * 100).toFixed(1)}%`
      });
    }

    if (candidate.costEstimate.totalCost > this.config.maxCostPerRequest) {
      exclusions.push({
        providerId: candidate.providerId,
        modelId: candidate.modelId,
        reason: "单请求成本过高",
        rule: {
          type: "cost_overrun",
          threshold: this.config.maxCostPerRequest,
          description: `单请求成本超过上限 ${this.config.maxCostPerRequest}`
        },
        details: `当前成本: ${candidate.costEstimate.currency} ${candidate.costEstimate.totalCost.toFixed(4)}, 上限: ${this.config.maxCostPerRequest}`
      });
    }

    return exclusions;
  }
}
```

### 5.2 排除规则矩阵

| 规则类型           | 阈值(默认) | 判定条件                    | 严重级别 |
|--------------------|-----------|-----------------------------|---------|
| insufficient_sample | n < 10    | 样本量不足                  | 必须排除 |
| unstable           | CV > 0.5  | 变异系数过大                | 必须排除 |
| high_error_rate    | > 20%     | 错误率过高                  | 必须排除 |
| timeout_excessive  | > 10%     | 超时率过高                  | 必须排除 |
| cost_overrun       | > $1.0    | 单请求成本超上限            | 警告     |

---

## 6. 推荐理由生成

### 6.1 ReasonGenerator

```typescript
class ReasonGenerator {
  generateReport(
    recommendations: Recommendation[],
    exclusions: ExclusionRecord[],
    mode: "win_rate" | "composite"
  ): RecommendationReport {
    const validRecs = recommendations.filter(r => !r.excluded);
    const bestPick = validRecs[0] || recommendations[0];

    return {
      id: `rec-${Date.now()}`,
      suiteId: "",
      timestamp: new Date().toISOString(),
      mode,
      recommendations,
      bestPick,
      summary: this.generateSummary(bestPick, validRecs, exclusions),
      exclusions,
      metadata: {
        candidateCount: recommendations.length,
        excludedCount: exclusions.length,
        significanceLevel: 0.05,
        minimumSampleSize: 10
      }
    };
  }

  private generateSummary(
    bestPick: Recommendation,
    validRecs: Recommendation[],
    exclusions: ExclusionRecord[]
  ): string {
    const parts: string[] = [];

    parts.push(
      `推荐模型: ${bestPick.candidate.displayName} ` +
      `(${bestPick.candidate.providerId}/${bestPick.candidate.modelId})`
    );
    parts.push(`推荐模式: ${bestPick.mode === "win_rate" ? "胜率+显著性" : "综合评分"}`);
    parts.push(`综合得分: ${(bestPick.score * 100).toFixed(1)}/100`);
    parts.push(`置信度: ${bestPick.confidence}`);

    if (bestPick.reasons.length > 0) {
      parts.push("推荐理由:");
      for (const reason of bestPick.reasons) {
        parts.push(`  - [${reason.category}] ${reason.description}`);
      }
    }

    if (bestPick.warnings.length > 0) {
      parts.push("注意事项:");
      for (const warning of bestPick.warnings) {
        parts.push(`  - ⚠ ${warning}`);
      }
    }

    if (exclusions.length > 0) {
      parts.push(`已排除 ${exclusions.length} 个候选模型:`);
      for (const exc of exclusions) {
        parts.push(`  - ${exc.providerId}/${exc.modelId}: ${exc.reason} (${exc.details})`);
      }
    }

    if (validRecs.length > 1) {
      parts.push(`备选方案: ${validRecs.slice(1, 3).map(r =>
        `${r.candidate.displayName} (得分${(r.score * 100).toFixed(1)})`
      ).join(", ")}`);
    }

    return parts.join("\n");
  }
}
```

---

## 7. 完整推荐示例

### 7.1 输入数据

3个候选模型对比测试结果:

| 模型              | 平均延迟 | P95延迟 | 预估成本(USD) | 样本量 | Cohen's d | 显著性 |
|-------------------|---------|---------|---------------|--------|-----------|--------|
| GPT-4o            | 1250ms  | 2100ms  | 0.0342        | 50     | 0.76      | 是     |
| Claude Sonnet 4   | 980ms   | 1650ms  | 0.0450        | 50     | 0.82      | 是     |
| Qwen-Max          | 2100ms  | 3800ms  | 0.0082        | 48     | 0.31      | 否     |

### 7.2 胜率模式推荐结果

```json
{
  "id": "rec-1720773600000",
  "mode": "win_rate",
  "bestPick": {
    "rank": 1,
    "candidate": {
      "providerId": "anthropic",
      "modelId": "claude-sonnet-4-20250514",
      "displayName": "Claude Sonnet 4"
    },
    "score": 1.0,
    "confidence": "high",
    "reasons": [
      {
        "category": "significance",
        "description": "显著胜率 100.0% (2/2对比较达到统计显著性)",
        "weight": 0.4,
        "supporting_data": { "significantWinRate": 1.0, "significantWins": 2, "totalComparisons": 2 }
      },
      {
        "category": "quality",
        "description": "整体胜率 100.0% (胜2 / 负0 / 平0)",
        "weight": 0.3,
        "supporting_data": { "winRate": 1.0, "wins": 2, "losses": 0, "ties": 0 }
      },
      {
        "category": "quality",
        "description": "效果量 Cohen's d=0.820 (large)",
        "weight": 0.3,
        "supporting_data": { "cohensD": 0.82, "varianceExplained": 0.144 }
      }
    ],
    "warnings": []
  },
  "summary": "推荐模型: Claude Sonnet 4 (anthropic/claude-sonnet-4-20250514)\n推荐模式: 胜率+显著性\n综合得分: 100.0/100\n置信度: high\n推荐理由:\n  - [significance] 显著胜率 100.0% (2/2对比较达到统计显著性)\n  - [quality] 整体胜率 100.0% (胜2 / 负0 / 平0)\n  - [quality] 效果量 Cohen's d=0.820 (large)\n备选方案: GPT-4o (得分50.0)"
}
```

### 7.3 综合评分模式推荐结果

```json
{
  "id": "rec-1720773600000",
  "mode": "composite",
  "bestPick": {
    "rank": 1,
    "candidate": {
      "providerId": "anthropic",
      "modelId": "claude-sonnet-4-20250514",
      "displayName": "Claude Sonnet 4"
    },
    "score": 0.812,
    "confidence": "high",
    "reasons": [
      {
        "category": "quality",
        "description": "质量评分 86.7/100 (效果量d=0.820, 统计显著)",
        "weight": 0.4,
        "supporting_data": { "qualityScore": 0.867, "cohensD": 0.82 }
      },
      {
        "category": "cost",
        "description": "成本评分 48.1/100 (预估费用 USD 0.0450)",
        "weight": 0.25,
        "supporting_data": { "costScore": 0.481, "totalCost": 0.045 }
      },
      {
        "category": "latency",
        "description": "延迟评分 85.2/100 (均值980ms, P95=1650ms)",
        "weight": 0.2,
        "supporting_data": { "latencyScore": 0.852, "meanMs": 980, "p95Ms": 1650 }
      },
      {
        "category": "stability",
        "description": "稳定性评分 92.3/100 (变异系数CV=7.7%)",
        "weight": 0.15,
        "supporting_data": { "stabilityScore": 0.923, "cv": 0.077 }
      }
    ],
    "warnings": []
  },
  "recommendations": [
    { "rank": 1, "candidate": { "displayName": "Claude Sonnet 4" }, "score": 0.812 },
    { "rank": 2, "candidate": { "displayName": "GPT-4o" }, "score": 0.685 },
    { "rank": 3, "candidate": { "displayName": "Qwen-Max" }, "score": 0.423 }
  ]
}
```

---

## 8. 性能目标

| 指标                    | 目标值       | 测量方法                          |
|-------------------------|-------------|-----------------------------------|
| 胜率计算耗时            | < 100ms     | 10个候选模型的成对比较             |
| 综合评分计算耗时        | < 50ms      | 10个候选模型的多维评分             |
| 排除过滤耗时            | < 10ms      | 10个候选模型的规则过滤             |
| 推荐理由生成耗时        | < 20ms      | 包含5个候选模型的报告生成          |
| 完整推荐报告生成        | < 200ms     | 从统计结果到完整推荐报告           |
| 评分归一化精度          | ±0.001      | 评分值域[0,1]的精度               |
| 推荐稳定性              | 100%        | 相同输入输出一致                   |
