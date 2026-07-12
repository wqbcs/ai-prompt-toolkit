# 统计分析引擎设计

## 1. 架构总览

### 1.1 数据流图

```
┌──────────────┐     ┌───────────────┐     ┌──────────────────┐
│  TaskResult  │────▶│  Data         │────▶│  Normality       │
│  (原始结果)  │     │  Preprocessor │     │  Test            │
└──────────────┘     └───────────────┘     │  (Shapiro-Wilk)  │
                                           └────────┬─────────┘
                                                    │
                                    ┌───────────────┼───────────────┐
                                    │ 正态+大样本   │               │ 非正态/小样本
                                    ▼               │               ▼
                           ┌──────────────┐         │      ┌──────────────┐
                           │  t检验        │         │      │ Mann-Whitney │
                           │  (双样本)     │         │      │ U检验        │
                           └──────┬───────┘         │      └──────┬───────┘
                                  │                 │             │
                                  ▼                 ▼             ▼
                           ┌─────────────────────────────────────────┐
                           │         Effect Size Calculator          │
                           │         (Cohen's d / r)                 │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │         Confidence Interval Calculator  │
                           │         (均值差异 / 中位数差异)          │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │         Statistical Report Builder      │
                           └─────────────────────────────────────────┘
```

### 1.2 自动选择规则

```
IF 样本量 ≥ 30 AND Shapiro-Wilk p-value ≥ 0.05
  → 使用 t检验 (参数检验)
ELSE
  → 使用 Mann-Whitney U检验 (非参数检验)
```

---

## 2. 数据预处理

### 2.1 接口定义

```typescript
interface MetricValue {
  testCaseId: string;
  providerId: string;
  modelId: string;
  metricName: string;
  value: number;
  timestamp: string;
}

interface SampleGroup {
  label: string;
  providerId: string;
  modelId: string;
  values: number[];
  mean: number;
  median: number;
  stdDev: number;
  min: number;
  max: number;
  sampleSize: number;
}

interface NormalityTestResult {
  statistic: number;
  pValue: number;
  isNormal: boolean;
  method: "shapiro-wilk" | "anderson-darling";
}

class DataPreprocessor {
  extractMetric(results: TaskResult[], metricName: string): MetricValue[] {
    return results
      .filter(r => r.status === "success")
      .map(r => {
        const value = this.resolveMetric(r, metricName);
        return {
          testCaseId: r.testCaseId,
          providerId: r.providerId,
          modelId: r.modelId,
          metricName,
          value,
          timestamp: r.timestamp
        };
      })
      .filter(m => !isNaN(m.value));
  }

  groupByProvider(metrics: MetricValue[]): Map<string, SampleGroup> {
    const groups = new Map<string, number[]>();

    for (const m of metrics) {
      const key = `${m.providerId}:${m.modelId}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(m.value);
    }

    const result = new Map<string, SampleGroup>();
    for (const [key, values] of groups) {
      const [providerId, modelId] = key.split(":");
      const sorted = [...values].sort((a, b) => a - b);
      const n = values.length;
      const mean = values.reduce((a, b) => a + b, 0) / n;
      const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (n - 1);

      result.set(key, {
        label: key,
        providerId,
        modelId,
        values,
        mean,
        median: this.median(sorted),
        stdDev: Math.sqrt(variance),
        min: sorted[0],
        max: sorted[n - 1],
        sampleSize: n
      });
    }

    return result;
  }

  private resolveMetric(result: TaskResult, metricName: string): number {
    switch (metricName) {
      case "latency": return result.totalLatencyMs;
      case "promptTokens": return result.response?.usage.promptTokens || 0;
      case "completionTokens": return result.response?.usage.completionTokens || 0;
      case "totalTokens": return result.response?.usage.totalTokens || 0;
      default:
        if (result.response?.metadata?.[metricName] !== undefined) {
          return Number(result.response.metadata[metricName]);
        }
        return NaN;
    }
  }

  private median(sorted: number[]): number {
    const n = sorted.length;
    if (n % 2 === 0) {
      return (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
    }
    return sorted[Math.floor(n / 2)];
  }
}
```

---

## 3. 正态性检验

### 3.1 Shapiro-Wilk检验实现

```typescript
class ShapiroWilkTest {
  private static readonly COEFFICIENTS: number[][] = [
    [],
    [],
    [0.7071],
    [0.7071, 0.0000],
    [0.6872, 0.1677],
    [0.6646, 0.2413],
    [0.6431, 0.2806, 0.0875],
    [0.6233, 0.3031, 0.1401],
    [0.6052, 0.3164, 0.1743],
    [0.5888, 0.3244, 0.1976],
    [0.5739, 0.3291, 0.2141],
  ];

  test(sample: number[]): NormalityTestResult {
    const n = sample.length;

    if (n < 3) {
      return { statistic: 1, pValue: 1, isNormal: true, method: "shapiro-wilk" };
    }

    if (n > 5000) {
      return this.andersonDarlingTest(sample);
    }

    const sorted = [...sample].sort((a, b) => a - b);
    const mean = sorted.reduce((a, b) => a + b, 0) / n;

    const s2 = sorted.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0);

    let b = 0;
    const m = Math.floor(n / 2);

    for (let i = 0; i < m; i++) {
      const a = this.getCoefficient(n, i);
      b += a * (sorted[n - 1 - i] - sorted[i]);
    }

    const W = (b * b) / s2;
    const pValue = this.approximatePValue(W, n);

    return {
      statistic: W,
      pValue,
      isNormal: pValue >= 0.05,
      method: "shapiro-wilk"
    };
  }

  private getCoefficient(n: number, i: number): number {
    if (n <= 10 && ShapiroWilkTest.COEFFICIENTS[n]) {
      return ShapiroWilkTest.COEFFICIENTS[n][i] || 0;
    }
    return this.approximateCoefficient(n, i);
  }

  private approximateCoefficient(n: number, i: number): number {
    const m = Math.floor(n / 2);
    const j = i + 1;
    return Math.sqrt((j - 0.375) / (n + 0.25)) * 2;
  }

  private approximatePValue(W: number, n: number): number {
    if (W >= 1) return 1;

    const mu = 1 - 0.5 / n;
    const sigma = 1 / Math.sqrt(n);

    const z = (W - mu) / sigma;
    const p = 0.5 * (1 + this.erf(z / Math.sqrt(2)));

    return Math.max(0, Math.min(1, p));
  }

  private erf(x: number): number {
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;

    const sign = x >= 0 ? 1 : -1;
    x = Math.abs(x);

    const t = 1.0 / (1.0 + p * x);
    const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

    return sign * y;
  }

  private andersonDarlingTest(sample: number[]): NormalityTestResult {
    const n = sample.length;
    const sorted = [...sample].sort((a, b) => a - b);
    const mean = sorted.reduce((a, b) => a + b, 0) / n;
    const stdDev = Math.sqrt(sorted.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n);

    let A2 = 0;
    for (let i = 0; i < n; i++) {
      const z = (sorted[i] - mean) / stdDev;
      const phi = 0.5 * (1 + this.erf(z / Math.sqrt(2)));
      const phiRev = 0.5 * (1 + this.erf((sorted[n - 1 - i] - mean) / Math.sqrt(2)));
      A2 += (2 * (i + 1) - 1) * (Math.log(phi) + Math.log(1 - phiRev));
    }

    A2 = -n - A2 / n;
    A2 = A2 * (1 + 0.75 / n + 2.25 / (n * n));

    const pValue = this.adPValue(A2);

    return {
      statistic: A2,
      pValue,
      isNormal: pValue >= 0.05,
      method: "anderson-darling"
    };
  }

  private adPValue(A2: number): number {
    if (A2 >= 0.6) return Math.exp(1.2937 - 5.709 * A2 + 0.0186 * A2 * A2);
    if (A2 >= 0.34) return Math.exp(0.9177 - 4.279 * A2 - 1.38 * A2 * A2);
    if (A2 > 0.2) return 1 - Math.exp(-8.318 + 42.796 * A2 - 59.938 * A2 * A2);
    return 1;
  }
}
```

---

## 4. t检验实现

### 4.1 Welch's t检验（双样本，不假设等方差）

```typescript
interface TTestResult {
  statistic: number;
  degreesOfFreedom: number;
  pValue: number;
  significant: boolean;
  confidenceLevel: number;
  method: "welch-t-test";
  meanDifference: number;
  standardError: number;
}

class WelchtTest {
  private alpha: number;

  constructor(alpha: number = 0.05) {
    this.alpha = alpha;
  }

  test(groupA: SampleGroup, groupB: SampleGroup): TTestResult {
    const nA = groupA.sampleSize;
    const nB = groupB.sampleSize;
    const meanA = groupA.mean;
    const meanB = groupB.mean;
    const varA = Math.pow(groupA.stdDev, 2);
    const varB = Math.pow(groupB.stdDev, 2);

    const meanDiff = meanA - meanB;
    const se = Math.sqrt(varA / nA + varB / nB);

    const t = meanDiff / se;

    const df = this.welchDegreesOfFreedom(varA, nA, varB, nB);

    const pValue = this.twoTailedPValue(t, df);

    return {
      statistic: t,
      degreesOfFreedom: df,
      pValue,
      significant: pValue < this.alpha,
      confidenceLevel: 1 - this.alpha,
      method: "welch-t-test",
      meanDifference: meanDiff,
      standardError: se
    };
  }

  private welchDegreesOfFreedom(varA: number, nA: number, varB: number, nB: number): number {
    const num = Math.pow(varA / nA + varB / nB, 2);
    const denom = Math.pow(varA / nA, 2) / (nA - 1) + Math.pow(varB / nB, 2) / (nB - 1);
    return num / denom;
  }

  private twoTailedPValue(t: number, df: number): number {
    const x = df / (df + t * t);
    return this.incompleteBeta(df / 2, 0.5, x);
  }

  private incompleteBeta(a: number, b: number, x: number): number {
    if (x < 0 || x > 1) return 0;
    if (x === 0) return 0;
    if (x === 1) return 1;

    const lnBeta = this.logGamma(a) + this.logGamma(b) - this.logGamma(a + b);
    const prefix = Math.exp(Math.log(x) * a + Math.log(1 - x) * b - lnBeta);

    if (x < (a + 1) / (a + b + 2)) {
      return prefix * this.betaContinuedFraction(a, b, x) / a;
    }

    return 1 - prefix * this.betaContinuedFraction(b, a, 1 - x) / b;
  }

  private betaContinuedFraction(a: number, b: number, x: number): number {
    const maxIterations = 200;
    const epsilon = 1e-10;

    let qab = a + b;
    let qap = a + 1;
    let qam = a - 1;

    let c = 1;
    let d = 1 - qab * x / qap;
    if (Math.abs(d) < 1e-30) d = 1e-30;
    d = 1 / d;
    let h = d;

    for (let m = 1; m <= maxIterations; m++) {
      const m2 = 2 * m;

      let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
      d = 1 + aa * d;
      if (Math.abs(d) < 1e-30) d = 1e-30;
      c = 1 + aa / c;
      if (Math.abs(c) < 1e-30) c = 1e-30;
      d = 1 / d;
      h *= d * c;

      aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
      d = 1 + aa * d;
      if (Math.abs(d) < 1e-30) d = 1e-30;
      c = 1 + aa / c;
      if (Math.abs(c) < 1e-30) c = 1e-30;
      d = 1 / d;
      const del = d * c;
      h *= del;

      if (Math.abs(del - 1) < epsilon) break;
    }

    return h;
  }

  private logGamma(x: number): number {
    const cof = [
      76.18009172947146, -86.50532032941677, 24.01409824083091,
      -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5
    ];

    let y = x;
    let tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    let ser = 1.000000000190015;

    for (let j = 0; j < 6; j++) {
      ser += cof[j] / ++y;
    }

    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }
}
```

---

## 5. Mann-Whitney U检验实现

### 5.1 非参数检验

```typescript
interface MannWhitneyResult {
  statisticU: number;
  statisticU2: number;
  zScore: number;
  pValue: number;
  significant: boolean;
  confidenceLevel: number;
  method: "mann-whitney-u";
  effectSizeR: number;
  medianDifference: number;
}

class MannWhitneyUTest {
  private alpha: number;

  constructor(alpha: number = 0.05) {
    this.alpha = alpha;
  }

  test(groupA: SampleGroup, groupB: SampleGroup): MannWhitneyResult {
    const nA = groupA.sampleSize;
    const nB = groupB.sampleSize;

    const ranked = this.rankSamples(groupA.values, groupB.values);

    const R1 = ranked.ranksA.reduce((a, b) => a + b, 0);
    const R2 = ranked.ranksB.reduce((a, b) => a + b, 0);

    const U1 = R1 - (nA * (nA + 1)) / 2;
    const U2 = R2 - (nB * (nB + 1)) / 2;

    const mu = (nA * nB) / 2;
    const sigma = Math.sqrt((nA * nB * (nA + nB + 1)) / 12 - this.tieCorrection(ranked.ties, nA + nB));

    const z = (U1 - mu) / sigma;
    const pValue = this.twoTailedZPValue(z);

    const effectSizeR = Math.abs(z) / Math.sqrt(nA + nB);

    const medianDiff = this.hodgesLehmannEstimate(groupA.values, groupB.values);

    return {
      statisticU: U1,
      statisticU2: U2,
      zScore: z,
      pValue,
      significant: pValue < this.alpha,
      confidenceLevel: 1 - this.alpha,
      method: "mann-whitney-u",
      effectSizeR,
      medianDifference: medianDiff
    };
  }

  private rankSamples(sampleA: number[], sampleB: number[]): {
    ranksA: number[];
    ranksB: number[];
    ties: Map<number, number>;
  } {
    const combined: Array<{ value: number; group: "A" | "B"; index: number }> = [
      ...sampleA.map((v, i) => ({ value: v, group: "A" as const, index: i })),
      ...sampleB.map((v, i) => ({ value: v, group: "B" as const, index: i }))
    ];

    combined.sort((a, b) => a.value - b.value);

    const ranks = new Array(combined.length);
    let i = 0;
    const ties = new Map<number, number>();

    while (i < combined.length) {
      let j = i;
      while (j < combined.length && combined[j].value === combined[i].value) {
        j++;
      }

      const avgRank = (i + 1 + j) / 2;
      const tieCount = j - i;

      if (tieCount > 1) {
        ties.set(combined[i].value, tieCount);
      }

      for (let k = i; k < j; k++) {
        ranks[k] = avgRank;
      }

      i = j;
    }

    const ranksA = new Array(sampleA.length);
    const ranksB = new Array(sampleB.length);

    for (let k = 0; k < combined.length; k++) {
      if (combined[k].group === "A") {
        ranksA[combined[k].index] = ranks[k];
      } else {
        ranksB[combined[k].index] = ranks[k];
      }
    }

    return { ranksA, ranksB, ties };
  }

  private tieCorrection(ties: Map<number, number>, n: number): number {
    let correction = 0;
    for (const count of ties.values()) {
      correction += (Math.pow(count, 3) - count) / 12;
    }
    return correction / (n * (n - 1));
  }

  private twoTailedZPValue(z: number): number {
    return 2 * (1 - this.standardNormalCDF(Math.abs(z)));
  }

  private standardNormalCDF(x: number): number {
    return 0.5 * (1 + this.erf(x / Math.sqrt(2)));
  }

  private erf(x: number): number {
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;
    const sign = x >= 0 ? 1 : -1;
    x = Math.abs(x);
    const t = 1.0 / (1.0 + p * x);
    const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return sign * y;
  }

  private hodgesLehmannEstimate(sampleA: number[], sampleB: number[]): number {
    const differences: number[] = [];
    for (const a of sampleA) {
      for (const b of sampleB) {
        differences.push(a - b);
      }
    }
    differences.sort((a, b) => a - b);
    const n = differences.length;
    if (n % 2 === 0) {
      return (differences[n / 2 - 1] + differences[n / 2]) / 2;
    }
    return differences[Math.floor(n / 2)];
  }
}
```

---

## 6. Cohen's d效果量

### 6.1 效果量计算

```typescript
interface EffectSizeResult {
  cohensD: number;
  interpretation: "negligible" | "small" | "medium" | "large" | "very_large";
  rEquivalent: number;
  varianceExplained: number;
  method: "cohens-d";
}

class EffectSizeCalculator {
  calculate(groupA: SampleGroup, groupB: SampleGroup): EffectSizeResult {
    const nA = groupA.sampleSize;
    const nB = groupB.sampleSize;
    const varA = Math.pow(groupA.stdDev, 2);
    const varB = Math.pow(groupB.stdDev, 2);

    const pooledStdDev = Math.sqrt(((nA - 1) * varA + (nB - 1) * varB) / (nA + nB - 2));

    const d = (groupA.mean - groupB.mean) / pooledStdDev;

    const r = d / Math.sqrt(d * d + 4);

    const rSquared = r * r;

    return {
      cohensD: d,
      interpretation: this.interpretD(d),
      rEquivalent: r,
      varianceExplained: rSquared,
      method: "cohens-d"
    };
  }

  private interpretD(d: number): EffectSizeResult["interpretation"] {
    const absD = Math.abs(d);
    if (absD < 0.2) return "negligible";
    if (absD < 0.5) return "small";
    if (absD < 0.8) return "medium";
    if (absD < 1.2) return "large";
    return "very_large";
  }
}
```

### 6.2 Cohen's d解释标准

| |d| 范围 | 解释       | 实际含义                           |
|------------|------------|------------------------------------|
| < 0.2      | 可忽略     | 两组几乎无差异                     |
| 0.2 - 0.5  | 小效果     | 差异存在但不太明显                 |
| 0.5 - 0.8  | 中等效果   | 差异明显可感知                     |
| 0.8 - 1.2  | 大效果     | 差异显著                           |
| > 1.2      | 极大效果   | 差异非常显著，几乎无重叠           |

---

## 7. 置信区间计算

### 7.1 接口定义

```typescript
interface ConfidenceIntervalResult {
  estimate: number;
  lowerBound: number;
  upperBound: number;
  confidenceLevel: number;
  method: "t-distribution" | "bootstrap" | "hodges-lehmann";
}

class ConfidenceIntervalCalculator {
  private alpha: number;

  constructor(alpha: number = 0.05) {
    this.alpha = alpha;
  }

  meanDifferenceCI(groupA: SampleGroup, groupB: SampleGroup): ConfidenceIntervalResult {
    const meanDiff = groupA.mean - groupB.mean;
    const seA = Math.pow(groupA.stdDev, 2) / groupA.sampleSize;
    const seB = Math.pow(groupB.stdDev, 2) / groupB.sampleSize;
    const se = Math.sqrt(seA + seB);

    const df = this.welchDF(
      Math.pow(groupA.stdDev, 2), groupA.sampleSize,
      Math.pow(groupB.stdDev, 2), groupB.sampleSize
    );

    const tCrit = this.tCritical(df, this.alpha / 2);
    const margin = tCrit * se;

    return {
      estimate: meanDiff,
      lowerBound: meanDiff - margin,
      upperBound: meanDiff + margin,
      confidenceLevel: 1 - this.alpha,
      method: "t-distribution"
    };
  }

  bootstrapCI(
    groupA: SampleGroup,
    groupB: SampleGroup,
    statisticFn: (a: number[], b: number[]) => number,
    iterations: number = 10000
  ): ConfidenceIntervalResult {
    const observed = statisticFn(groupA.values, groupB.values);
    const bootstrapStats: number[] = [];

    for (let i = 0; i < iterations; i++) {
      const sampleA = this.resample(groupA.values);
      const sampleB = this.resample(groupB.values);
      bootstrapStats.push(statisticFn(sampleA, sampleB));
    }

    bootstrapStats.sort((a, b) => a - b);
    const lowerIdx = Math.floor(iterations * (this.alpha / 2));
    const upperIdx = Math.floor(iterations * (1 - this.alpha / 2));

    return {
      estimate: observed,
      lowerBound: bootstrapStats[lowerIdx],
      upperBound: bootstrapStats[upperIdx],
      confidenceLevel: 1 - this.alpha,
      method: "bootstrap"
    };
  }

  private resample(values: number[]): number[] {
    const n = values.length;
    const result: number[] = [];
    for (let i = 0; i < n; i++) {
      result.push(values[Math.floor(Math.random() * n)]);
    }
    return result;
  }

  private welchDF(varA: number, nA: number, varB: number, nB: number): number {
    const num = Math.pow(varA / nA + varB / nB, 2);
    const denom = Math.pow(varA / nA, 2) / (nA - 1) + Math.pow(varB / nB, 2) / (nB - 1);
    return num / denom;
  }

  private tCritical(df: number, alpha: number): number {
    if (df > 30) return this.zCritical(alpha);

    const z = this.zCritical(alpha);
    const g1 = 0.25 * (z * z * z + z);
    const g2 = 0.0102 * z * (z * z * z * z * z + 2.4 * z * z * z + 5.2 * z);

    return z + g1 / df + g2 / (df * df);
  }

  private zCritical(alpha: number): number {
    const p = 1 - alpha;
    const t = Math.sqrt(-2 * Math.log(1 - (1 - p) * 2));
    const c0 = 2.515517;
    const c1 = 0.802853;
    const c2 = 0.010328;
    const d1 = 1.432788;
    const d2 = 0.189269;
    const d3 = 0.001308;

    return t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t);
  }
}
```

---

## 8. 自动选择与统计报告

### 8.1 自动选择器

```typescript
interface StatisticalTestResult {
  testMethod: "welch-t-test" | "mann-whitney-u";
  normalityResult: NormalityTestResult;
  testResult: TTestResult | MannWhitneyResult;
  effectSize: EffectSizeResult;
  confidenceInterval: ConfidenceIntervalResult;
  selectionReason: string;
}

class StatisticalTestSelector {
  private normalityTest: ShapiroWilkTest;
  private tTest: WelchtTest;
  private mannWhitney: MannWhitneyUTest;
  private effectSizeCalc: EffectSizeCalculator;
  private ciCalc: ConfidenceIntervalCalculator;
  private alpha: number;

  constructor(alpha: number = 0.05) {
    this.alpha = alpha;
    this.normalityTest = new ShapiroWilkTest();
    this.tTest = new WelchtTest(alpha);
    this.mannWhitney = new MannWhitneyUTest(alpha);
    this.effectSizeCalc = new EffectSizeCalculator();
    this.ciCalc = new ConfidenceIntervalCalculator(alpha);
  }

  compare(groupA: SampleGroup, groupB: SampleGroup): StatisticalTestResult {
    const normalityA = this.normalityTest.test(groupA.values);
    const normalityB = this.normalityTest.test(groupB.values);
    const combinedNormal = normalityA.isNormal && normalityB.isNormal;
    const largeSample = groupA.sampleSize >= 30 && groupB.sampleSize >= 30;

    const useParametric = combinedNormal && largeSample;

    let selectionReason: string;
    let testResult: TTestResult | MannWhitneyResult;
    let ciResult: ConfidenceIntervalResult;

    if (useParametric) {
      selectionReason = `两组数据均通过正态性检验(A: p=${normalityA.pValue.toFixed(4)}, B: p=${normalityB.pValue.toFixed(4)})且样本量充足(A: n=${groupA.sampleSize}, B: n=${groupB.sampleSize})，使用Welch's t检验`;
      testResult = this.tTest.test(groupA, groupB);
      ciResult = this.ciCalc.meanDifferenceCI(groupA, groupB);
    } else {
      const reasons: string[] = [];
      if (!combinedNormal) reasons.push("正态性检验未通过");
      if (!largeSample) reasons.push("样本量不足(n<30)");
      selectionReason = `${reasons.join("，")}，使用Mann-Whitney U检验`;
      testResult = this.mannWhitney.test(groupA, groupB);
      ciResult = this.ciCalc.bootstrapCI(groupA, groupB, (a, b) => {
        const medA = a.sort((x, y) => x - y);
        const medB = b.sort((x, y) => x - y);
        const mA = medA[Math.floor(medA.length / 2)];
        const mB = medB[Math.floor(medB.length / 2)];
        return mA - mB;
      });
    }

    const effectSize = this.effectSizeCalc.calculate(groupA, groupB);

    return {
      testMethod: useParametric ? "welch-t-test" : "mann-whitney-u",
      normalityResult: { ...normalityA, isNormal: combinedNormal },
      testResult,
      effectSize,
      confidenceInterval: ciResult,
      selectionReason
    };
  }
}
```

### 8.2 统计报告示例

```json
{
  "testMethod": "welch-t-test",
  "selectionReason": "两组数据均通过正态性检验(A: p=0.3421, B: p=0.2876)且样本量充足(A: n=50, B: n=50)，使用Welch's t检验",
  "normalityResult": {
    "statistic": 0.9734,
    "pValue": 0.3125,
    "isNormal": true,
    "method": "shapiro-wilk"
  },
  "testResult": {
    "statistic": 3.8421,
    "degreesOfFreedom": 95.7,
    "pValue": 0.0002,
    "significant": true,
    "confidenceLevel": 0.95,
    "method": "welch-t-test",
    "meanDifference": 145.3,
    "standardError": 37.82
  },
  "effectSize": {
    "cohensD": 0.768,
    "interpretation": "medium",
    "rEquivalent": 0.359,
    "varianceExplained": 0.129,
    "method": "cohens-d"
  },
  "confidenceInterval": {
    "estimate": 145.3,
    "lowerBound": 70.23,
    "upperBound": 220.37,
    "confidenceLevel": 0.95,
    "method": "t-distribution"
  }
}
```

---

## 9. 性能目标

| 指标                  | 目标值        | 测量方法                        |
|-----------------------|---------------|---------------------------------|
| 正态性检验耗时        | < 50ms        | 1000样本的Shapiro-Wilk          |
| t检验耗时             | < 5ms         | 双样本各50的Welch's t检验        |
| Mann-Whitney U耗时    | < 10ms        | 双样本各50的U检验               |
| Bootstrap CI耗时      | < 500ms       | 10000次迭代的Bootstrap置信区间   |
| 效果量计算耗时        | < 1ms         | Cohen's d计算                   |
| 完整统计报告生成      | < 600ms       | 从原始数据到完整报告             |
| 数值精度              | < 1e-10 误差  | 与R/SciPy参考实现对比           |
