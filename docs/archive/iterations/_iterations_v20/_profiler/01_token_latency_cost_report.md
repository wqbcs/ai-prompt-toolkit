# Q2-01~04 提示词性能分析器

> **迭代**：v20-Q2-01~04 | **日期**：2026-07-12

---

## 一、Token消耗分析器（Q2-01）

### 1.1 Token计数器

```typescript
interface TokenAnalyzer {
  countTokens(text: string, model: string): TokenCount;
  analyzeBySection(prompt: string): SectionTokenReport[];
  analyzeTrend(history: TokenRecord[]): TokenTrendReport;
  aggregateByTemplate(records: TokenRecord[]): TemplateAggregate[];
}

interface TokenCount {
  input_tokens: number;
  output_tokens_estimated: number;
  total_tokens_estimated: number;
  character_count: number;
  word_count: number;
  token_efficiency: number;
}

interface SectionTokenReport {
  section_type: string;
  section_name: string;
  token_count: number;
  percentage: number;
  variables: string[];
}

interface TokenTrendReport {
  period: string;
  trend_direction: 'increasing' | 'stable' | 'decreasing';
  change_rate: number;
  projection: number;
  alert_threshold: number;
  is_alert: boolean;
}

interface TemplateAggregate {
  template_name: string;
  avg_input_tokens: number;
  avg_output_tokens: number;
  avg_total_cost: number;
  usage_count: number;
  efficiency_score: number;
}

interface TokenRecord {
  timestamp: string;
  template_name: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}
```

### 1.2 Token分析报告

```
┌──────────────────────────────────────────────────────┐
│              Token 消耗分析报告                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│  总Token消耗：12,450                                  │
│  ├── 输入Token：8,200 (65.9%)                        │
│  └── 输出Token：4,250 (34.1%)                        │
│                                                      │
│  分段分析：                                           │
│  ┌────────────┬────────┬──────┬────────┐             │
│  │ 段落       │ Token  │ 占比 │ 变量数 │             │
│  ├────────────┼────────┼──────┼────────┤             │
│  │ @system    │ 2,100  │ 25.6%│ 3      │             │
│  │ @context   │ 1,800  │ 22.0%│ 5      │             │
│  │ @constraint│ 1,500  │ 18.3%│ 2      │             │
│  │ @example   │ 1,200  │ 14.6%│ 4      │             │
│  │ @output    │ 800    │ 9.8% │ 1      │             │
│  │ 其他       │ 800    │ 9.8% │ 0      │             │
│  └────────────┴────────┴──────┴────────┘             │
│                                                      │
│  优化建议：                                           │
│  ⚠ @context段可压缩15%（移除冗余描述）                 │
│  ⚠ @example段可精简（3个示例→2个）                    │
│  ✓ 预估节省：~800 Token/次                           │
└──────────────────────────────────────────────────────┘
```

---

## 二、延迟分析器（Q2-02）

### 2.1 延迟指标

```typescript
interface LatencyAnalyzer {
  measureLatency(request: PromptRequest): LatencyMetrics;
  analyzeDistribution(records: LatencyRecord[]): LatencyDistribution;
  detectAnomalies(records: LatencyRecord[]): AnomalyReport[];
  compareModels(records: LatencyRecord[]): ModelComparison;
}

interface LatencyMetrics {
  total_latency_ms: number;
  ttft_ms: number;
  generation_speed_tps: number;
  network_latency_ms: number;
  processing_latency_ms: number;
  queue_wait_ms: number;
}

interface LatencyDistribution {
  p50_ms: number;
  p90_ms: number;
  p95_ms: number;
  p99_ms: number;
  max_ms: number;
  min_ms: number;
  stddev_ms: number;
}

interface AnomalyReport {
  timestamp: string;
  metric: string;
  expected_value: number;
  actual_value: number;
  deviation_percent: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  possible_cause: string;
}

interface ModelComparison {
  model_name: string;
  avg_ttft_ms: number;
  avg_total_ms: number;
  avg_tps: number;
  p99_ms: number;
  cost_per_1k_tokens: number;
  cost_efficiency: number;
  recommendation: string;
}
```

### 2.2 延迟分布可视化

```
延迟分布直方图 (ms)
  200 |                    ██
  180 |                  ████
  160 |                ██████
  140 |              ████████
  120 |            ██████████
  100 |          ████████████
   80 |        ██████████████
   60 |      ████████████████
   40 |    ██████████████████
   20 |  ████████████████████
   0  |██████████████████████
      0  200  400  600  800  1000  1200  1400  1600

  P50: 450ms | P90: 820ms | P99: 1350ms | TTFT: 180ms | Speed: 42 tps
```

---

## 三、成本估算引擎（Q2-03）

### 3.1 模型定价表

```typescript
interface ModelPricing {
  model_id: string;
  provider: string;
  input_price_per_1m: number;
  output_price_per_1m: number;
  currency: string;
  updated_at: string;
}

const MODEL_PRICING: ModelPricing[] = [
  { model_id: 'gpt-4o', provider: 'openai', input_price_per_1m: 2.50, output_price_per_1m: 10.00, currency: 'USD', updated_at: '2026-07-12' },
  { model_id: 'gpt-4o-mini', provider: 'openai', input_price_per_1m: 0.15, output_price_per_1m: 0.60, currency: 'USD', updated_at: '2026-07-12' },
  { model_id: 'claude-3.5-sonnet', provider: 'anthropic', input_price_per_1m: 3.00, output_price_per_1m: 15.00, currency: 'USD', updated_at: '2026-07-12' },
  { model_id: 'qwen-max', provider: 'alibaba', input_price_per_1m: 1.60, output_price_per_1m: 6.40, currency: 'CNY', updated_at: '2026-07-12' },
  { model_id: 'deepseek-chat', provider: 'deepseek', input_price_per_1m: 0.14, output_price_per_1m: 0.28, currency: 'CNY', updated_at: '2026-07-12' },
];

interface CostEstimator {
  estimateSingle(request: PromptRequest, model: string): CostEstimate;
  estimateBatch(requests: PromptRequest[], model: string): BatchCostEstimate;
  estimateMonthly(usage_pattern: UsagePattern, model: string): MonthlyCostEstimate;
  compareModels(usage_pattern: UsagePattern): ModelCostComparison[];
  checkBudget(estimate: CostEstimate, budget: Budget): BudgetCheckResult;
}

interface CostEstimate {
  input_cost: number;
  output_cost_estimated: number;
  total_cost_estimated: number;
  currency: string;
  confidence: number;
  breakdown: {
    section_type: string;
    token_count: number;
    cost: number;
  }[];
}

interface MonthlyCostEstimate {
  daily_cost_avg: number;
  monthly_cost_estimated: number;
  peak_day_cost: number;
  cost_by_template: Record<string, number>;
  cost_trend: 'increasing' | 'stable' | 'decreasing';
  savings_potential: number;
  savings_recommendations: string[];
}

interface BudgetCheckResult {
  within_budget: boolean;
  budget_remaining: number;
  budget_used_percent: number;
  projected_overrun: number;
  recommended_actions: string[];
}

interface BudgetAlert {
  threshold_percent: number;
  notification_type: 'email' | 'webhook' | 'slack';
  recipients: string[];
  message_template: string;
}
```

### 3.2 成本报告示例

```
┌──────────────────────────────────────────────────────┐
│              成本估算报告                               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  模型：gpt-4o | 货币：USD                             │
│                                                      │
│  单次估算：                                           │
│  ├── 输入成本：$0.0205 (8,200 tokens × $2.50/1M)     │
│  ├── 输出成本：$0.0425 (4,250 tokens × $10.00/1M)    │
│  └── 总成本：$0.0630                                  │
│                                                      │
│  月度估算（1000次/天）：                                │
│  ├── 日均成本：$63.00                                 │
│  ├── 月度成本：$1,890.00                              │
│  └── 峰值日成本：$94.50                               │
│                                                      │
│  模型对比：                                           │
│  ┌──────────────┬──────────┬──────────┬─────────┐    │
│  │ 模型         │ 月成本   │ 节省     │ 性能    │    │
│  ├──────────────┼──────────┼──────────┼─────────┤    │
│  │ gpt-4o       │ $1,890   │ 基准     │ ★★★★★  │    │
│  │ gpt-4o-mini  │ $113     │ -94%     │ ★★★☆☆  │    │
│  │ claude-3.5   │ $2,835   │ +50%     │ ★★★★★  │    │
│  │ qwen-max     │ ¥7,680   │ -42%*    │ ★★★★☆  │    │
│  │ deepseek     │ ¥530     │ -94%*    │ ★★★☆☆  │    │
│  └──────────────┴──────────┴──────────┴─────────┘    │
│  * CNY按7.2汇率折算                                   │
│                                                      │
│  优化建议：                                           │
│  💡 非核心场景使用gpt-4o-mini，月省$1,777             │
│  💡 @context段压缩后可省15% Token                     │
│  💡 设置$2000/月预算告警                              │
└──────────────────────────────────────────────────────┘
```

---

## 四、性能报告生成器（Q2-04）

### 4.1 报告格式

```typescript
interface PerformanceReportGenerator {
  generateMarkdown(data: PerformanceData): string;
  generateHtml(data: PerformanceData): string;
  generateJson(data: PerformanceData): string;
  generateDashboard(data: PerformanceData): string;
}

interface PerformanceData {
  report_id: string;
  generated_at: string;
  template_name: string;
  model: string;
  token_analysis: TokenCount;
  latency_analysis: LatencyMetrics;
  cost_analysis: CostEstimate;
  optimization_suggestions: OptimizationSuggestion[];
  comparison_with_baseline: BaselineComparison;
}

interface OptimizationSuggestion {
  id: string;
  category: 'token' | 'latency' | 'cost';
  priority: 'high' | 'medium' | 'low';
  description: string;
  estimated_savings: {
    tokens?: number;
    latency_ms?: number;
    cost_usd?: number;
  };
  implementation_effort: 'trivial' | 'easy' | 'moderate' | 'hard';
  risk_level: 'none' | 'low' | 'medium' | 'high';
}

interface BaselineComparison {
  baseline_version: string;
  current_version: string;
  token_change_percent: number;
  latency_change_percent: number;
  cost_change_percent: number;
  regression_detected: boolean;
}
```

### 4.2 优化建议引擎

```typescript
class OptimizationEngine {
  analyze(prompt: string, metrics: PerformanceData): OptimizationSuggestion[] {
    const suggestions: OptimizationSuggestion[] = [];

    // Token优化
    if (metrics.token_analysis.input_tokens > 4000) {
      suggestions.push({
        id: 'opt-001',
        category: 'token',
        priority: 'high',
        description: '输入Token超过4000，建议压缩@context段',
        estimated_savings: { tokens: Math.round(metrics.token_analysis.input_tokens * 0.15) },
        implementation_effort: 'easy',
        risk_level: 'low',
      });
    }

    // 延迟优化
    if (metrics.latency_analysis.ttft_ms > 2000) {
      suggestions.push({
        id: 'opt-002',
        category: 'latency',
        priority: 'high',
        description: '首Token延迟超过2秒，建议简化系统角色描述',
        estimated_savings: { latency_ms: 500 },
        implementation_effort: 'moderate',
        risk_level: 'medium',
      });
    }

    // 成本优化
    if (metrics.cost_analysis.total_cost_estimated > 0.10) {
      suggestions.push({
        id: 'opt-003',
        category: 'cost',
        priority: 'medium',
        description: '单次成本超过$0.10，建议评估是否可使用更轻量模型',
        estimated_savings: { cost_usd: metrics.cost_analysis.total_cost_estimated * 0.6 },
        implementation_effort: 'easy',
        risk_level: 'low',
      });
    }

    return suggestions.sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
  }
}
```

---

## 五、验收项

- [x] Token消耗分析器（计数/分段分析/趋势/聚合）
- [x] Token分析报告（含优化建议）
- [x] 延迟分析器（TTFT/TPS/分布/异常检测/模型对比）
- [x] 延迟分布可视化
- [x] 成本估算引擎（5模型定价/单次/批量/月度/预算告警）
- [x] 成本报告（含模型对比）
- [x] 性能报告生成器（Markdown/HTML/JSON/Dashboard）
- [x] 优化建议引擎（Token/延迟/成本三维优化）
