# 并行执行引擎设计

## 1. 架构总览

### 1.1 数据流图

```
┌─────────────────────────────────────────────────────────┐
│                    ParallelEngine                        │
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Test      │───▶│ Task         │───▶│ Promise      │  │
│  │ Scheduler │    │ Dispatcher   │    │ .allSettled  │  │
│  └──────────┘    └──────┬───────┘    └──────┬───────┘  │
│                         │                    │          │
│              ┌──────────▼────────┐  ┌───────▼────────┐ │
│              │  Concurrency      │  │  Result         │ │
│              │  Controller       │  │  Collector      │ │
│              │  (信号量/队列)    │  │  (错误隔离)     │ │
│              └──────────┬────────┘  └───────┬────────┘ │
│                         │                    │          │
│              ┌──────────▼────────┐  ┌───────▼────────┐ │
│              │  Timeout          │  │  Progress       │ │
│              │  & Retry          │  │  Tracker        │ │
│              │  (指数退避)       │  │  (实时进度)     │ │
│              └───────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.2 核心流程

```
TestSuite → 任务拆分 → 并发调度(Promise.allSettled) → 错误隔离 → 结果收集 → 聚合报告
```

---

## 2. ParallelEngine接口定义

### 2.1 核心类型

```typescript
interface TestCase {
  id: string;
  name: string;
  provider: Provider;
  request: ProviderRequest;
  expectedBehavior?: ExpectedBehavior;
  retries: number;
  timeoutMs: number;
  metadata?: Record<string, unknown>;
}

interface ExpectedBehavior {
  contains?: string[];
  notContains?: string[];
  regexMatches?: string[];
  jsonSchema?: object;
  customValidator?: string;
}

interface TestSuite {
  id: string;
  name: string;
  description: string;
  testCases: TestCase[];
  config: ExecutionConfig;
}

interface ExecutionConfig {
  maxConcurrency: number;
  globalTimeoutMs: number;
  retryPolicy: RetryConfig;
  failFast: boolean;
  continueOnError: boolean;
  progressCallback?: (progress: ExecutionProgress) => void;
}

interface ExecutionProgress {
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  inFlightTasks: number;
  estimatedRemainingMs: number;
  phase: "initializing" | "executing" | "collecting" | "finalizing";
}

interface TaskResult {
  testCaseId: string;
  testCaseName: string;
  providerId: string;
  modelId: string;
  status: "success" | "failed" | "timeout" | "skipped";
  response?: ProviderResponse;
  error?: TaskError;
  attempts: number;
  totalLatencyMs: number;
  timestamp: string;
}

interface TaskError {
  type: "network" | "timeout" | "rate_limit" | "validation" | "provider" | "unknown";
  message: string;
  statusCode?: number;
  retryable: boolean;
  stack?: string;
}

interface ExecutionReport {
  suiteId: string;
  suiteName: string;
  status: "completed" | "partial" | "failed" | "aborted";
  results: TaskResult[];
  summary: ExecutionSummary;
  config: ExecutionConfig;
  startTime: string;
  endTime: string;
  totalDurationMs: number;
}

interface ExecutionSummary {
  totalTasks: number;
  successCount: number;
  failedCount: number;
  timeoutCount: number;
  skippedCount: number;
  averageLatencyMs: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  p99LatencyMs: number;
  totalTokensUsed: number;
  estimatedCost: CostEstimate;
}
```

### 2.2 ParallelEngine类

```typescript
class ParallelEngine {
  private concurrencyController: ConcurrencyController;
  private timeoutManager: TimeoutManager;
  private retryPolicy: ExponentialBackoffRetryPolicy;
  private progressTracker: ProgressTracker;
  private resultCollector: ResultCollector;

  constructor(config: ExecutionConfig) {
    this.concurrencyController = new SemaphoreConcurrencyController(config.maxConcurrency);
    this.timeoutManager = new TimeoutManager(config.globalTimeoutMs);
    this.retryPolicy = new ExponentialBackoffRetryPolicy(config.retryPolicy);
    this.progressTracker = new ProgressTracker(config.progressCallback);
    this.resultCollector = new ResultCollector();
  }

  async execute(suite: TestSuite): Promise<ExecutionReport> {
    const startTime = new Date().toISOString();
    this.progressTracker.start(suite.testCases.length);

    try {
      const results = await this.dispatchAll(suite.testCases, suite.config);
      const endTime = new Date().toISOString();

      return {
        suiteId: suite.id,
        suiteName: suite.name,
        status: this.determineStatus(results, suite.config),
        results,
        summary: this.buildSummary(results),
        config: suite.config,
        startTime,
        endTime,
        totalDurationMs: Date.now() - new Date(startTime).getTime()
      };
    } finally {
      this.timeoutManager.clearAll();
      this.progressTracker.finalize();
    }
  }

  private async dispatchAll(testCases: TestCase[], config: ExecutionConfig): Promise<TaskResult[]> {
    const tasks = testCases.map(tc => this.executeTask(tc, config));

    const settled = await Promise.allSettled(tasks);

    return settled.map((result, index) => {
      if (result.status === "fulfilled") {
        return result.value;
      }
      return {
        testCaseId: testCases[index].id,
        testCaseName: testCases[index].name,
        providerId: testCases[index].provider.providerId,
        modelId: testCases[index].request.modelId,
        status: "failed" as const,
        error: {
          type: "unknown" as const,
          message: result.reason?.message || "未知错误",
          retryable: false
        },
        attempts: 0,
        totalLatencyMs: 0,
        timestamp: new Date().toISOString()
      };
    });
  }

  private async executeTask(testCase: TestCase, config: ExecutionConfig): Promise<TaskResult> {
    await this.concurrencyController.acquire();
    const taskStartTime = Date.now();
    let lastError: TaskError | null = null;
    let attempts = 0;

    try {
      for (let attempt = 0; attempt <= testCase.retries; attempt++) {
        attempts = attempt + 1;

        try {
          const response = await Promise.race([
            testCase.provider.invoke(testCase.request),
            this.timeoutManager.createTimeout(testCase.timeoutMs, testCase.id)
          ]);

          this.progressTracker.recordCompletion(true);
          this.concurrencyController.release();

          return {
            testCaseId: testCase.id,
            testCaseName: testCase.name,
            providerId: testCase.provider.providerId,
            modelId: testCase.request.modelId,
            status: "success",
            response,
            attempts,
            totalLatencyMs: Date.now() - taskStartTime,
            timestamp: new Date().toISOString()
          };
        } catch (error) {
          lastError = this.classifyError(error);

          if (!lastError.retryable || attempt === testCase.retries) {
            break;
          }

          const delay = this.retryPolicy.calculateDelay(attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }

      this.progressTracker.recordCompletion(false);
      this.concurrencyController.release();

      return {
        testCaseId: testCase.id,
        testCaseName: testCase.name,
        providerId: testCase.provider.providerId,
        modelId: testCase.request.modelId,
        status: lastError?.type === "timeout" ? "timeout" : "failed",
        error: lastError || { type: "unknown", message: "未知错误", retryable: false },
        attempts,
        totalLatencyMs: Date.now() - taskStartTime,
        timestamp: new Date().toISOString()
      };
    } catch (fatalError) {
      this.concurrencyController.release();
      this.progressTracker.recordCompletion(false);
      throw fatalError;
    }
  }

  private classifyError(error: unknown): TaskError {
    if (error instanceof TimeoutError) {
      return { type: "timeout", message: error.message, retryable: true };
    }
    if (error instanceof RateLimitError) {
      return { type: "rate_limit", message: error.message, statusCode: 429, retryable: true };
    }
    if (error instanceof HttpError) {
      return {
        type: "provider",
        message: error.message,
        statusCode: error.statusCode,
        retryable: error.statusCode >= 500
      };
    }
    if (error instanceof NetworkError) {
      return { type: "network", message: error.message, retryable: true };
    }
    return { type: "unknown", message: String(error), retryable: false };
  }

  private determineStatus(results: TaskResult[], config: ExecutionConfig): ExecutionReport["status"] {
    const allSuccess = results.every(r => r.status === "success");
    const anySuccess = results.some(r => r.status === "success");

    if (allSuccess) return "completed";
    if (anySuccess) return "partial";
    if (config.failFast) return "aborted";
    return "failed";
  }

  private buildSummary(results: TaskResult[]): ExecutionSummary {
    const latencies = results
      .filter(r => r.status === "success")
      .map(r => r.totalLatencyMs)
      .sort((a, b) => a - b);

    const successResults = results.filter(r => r.status === "success");
    const totalTokens = successResults.reduce(
      (sum, r) => sum + (r.response?.usage.totalTokens || 0), 0
    );

    return {
      totalTasks: results.length,
      successCount: results.filter(r => r.status === "success").length,
      failedCount: results.filter(r => r.status === "failed").length,
      timeoutCount: results.filter(r => r.status === "timeout").length,
      skippedCount: results.filter(r => r.status === "skipped").length,
      averageLatencyMs: latencies.length > 0
        ? latencies.reduce((a, b) => a + b, 0) / latencies.length
        : 0,
      p50LatencyMs: this.percentile(latencies, 50),
      p95LatencyMs: this.percentile(latencies, 95),
      p99LatencyMs: this.percentile(latencies, 99),
      totalTokensUsed: totalTokens,
      estimatedCost: { promptCost: 0, completionCost: 0, totalCost: 0, currency: "USD" }
    };
  }

  private percentile(sorted: number[], p: number): number {
    if (sorted.length === 0) return 0;
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }
}
```

---

## 3. 并发调度机制

### 3.1 Promise.allSettled调度

```typescript
interface ConcurrencyController {
  acquire(): Promise<void>;
  release(): void;
  getAvailable(): number;
  getActive(): number;
}

class SemaphoreConcurrencyController implements ConcurrencyController {
  private available: number;
  private maxConcurrency: number;
  private waitQueue: Array<{ resolve: () => void }>;

  constructor(maxConcurrency: number) {
    this.maxConcurrency = maxConcurrency;
    this.available = maxConcurrency;
    this.waitQueue = [];
  }

  async acquire(): Promise<void> {
    if (this.available > 0) {
      this.available -= 1;
      return;
    }

    return new Promise<void>(resolve => {
      this.waitQueue.push({ resolve });
    });
  }

  release(): void {
    if (this.waitQueue.length > 0) {
      const next = this.waitQueue.shift()!;
      this.available += 0;
      next.resolve();
    } else {
      this.available += 1;
    }
  }

  getAvailable(): number {
    return this.available;
  }

  getActive(): number {
    return this.maxConcurrency - this.available;
  }
}
```

### 3.2 批量调度策略

```typescript
interface BatchStrategy {
  batch(testCases: TestCase[], batchSize: number): TestCase[][];
}

class StreamingBatchStrategy implements BatchStrategy {
  batch(testCases: TestCase[], batchSize: number): TestCase[][] {
    const batches: TestCase[][] = [];
    for (let i = 0; i < testCases.length; i += batchSize) {
      batches.push(testCases.slice(i, i + batchSize));
    }
    return batches;
  }
}

class PriorityBatchStrategy implements BatchStrategy {
  batch(testCases: TestCase[], batchSize: number): TestCase[][] {
    const sorted = [...testCases].sort((a, b) => {
      const priorityA = a.metadata?.priority as number || 0;
      const priorityB = b.metadata?.priority as number || 0;
      return priorityB - priorityA;
    });

    const batches: TestCase[][] = [];
    for (let i = 0; i < sorted.length; i += batchSize) {
      batches.push(sorted.slice(i, i + batchSize));
    }
    return batches;
  }
}
```

---

## 4. 超时与重试策略

### 4.1 超时管理

```typescript
class TimeoutManager {
  private globalTimeoutMs: number;
  private activeTimers: Map<string, NodeJS.Timeout>;

  constructor(globalTimeoutMs: number) {
    this.globalTimeoutMs = globalTimeoutMs;
    this.activeTimers = new Map();
  }

  createTimeout(timeoutMs: number, taskId: string): Promise<never> {
    return new Promise((_, reject) => {
      const timer = setTimeout(() => {
        this.activeTimers.delete(taskId);
        reject(new TimeoutError(`任务 ${taskId} 超时 (${timeoutMs}ms)`));
      }, Math.min(timeoutMs, this.globalTimeoutMs));

      this.activeTimers.set(taskId, timer);
    });
  }

  clearTask(taskId: string): void {
    const timer = this.activeTimers.get(taskId);
    if (timer) {
      clearTimeout(timer);
      this.activeTimers.delete(taskId);
    }
  }

  clearAll(): void {
    for (const timer of this.activeTimers.values()) {
      clearTimeout(timer);
    }
    this.activeTimers.clear();
  }
}
```

### 4.2 指数退避重试

```
重试延迟 = min(baseDelay × 2^attempt + jitter, maxDelay)

示例 (baseDelay=1000ms, maxDelay=30000ms):
  第1次重试: ~1000ms  (750ms ~ 1250ms with jitter)
  第2次重试: ~2000ms  (1500ms ~ 2500ms with jitter)
  第3次重试: ~4000ms  (3000ms ~ 5000ms with jitter)
  第4次重试: ~8000ms  (6000ms ~ 10000ms with jitter)
  第5次重试: ~16000ms (12000ms ~ 20000ms with jitter)
```

### 4.3 可重试条件矩阵

| 错误类型      | 状态码  | 可重试 | 最大重试次数 | 退避策略       |
|---------------|---------|--------|-------------|----------------|
| 网络错误      | -       | 是     | 3           | 指数退避       |
| 速率限制      | 429     | 是     | 5           | 指数退避+Retry-After |
| 服务端错误    | 500     | 是     | 3           | 指数退避       |
| 网关错误      | 502/503 | 是     | 3           | 指数退避       |
| 超时          | -       | 是     | 2           | 固定延迟       |
| 认证失败      | 401/403 | 否     | 0           | -              |
| 参数错误      | 400     | 否     | 0           | -              |
| 内容过滤      | -       | 否     | 0           | -              |

---

## 5. 错误隔离机制

### 5.1 隔离原则

```
1. 单个任务失败不影响其他任务执行
2. 错误信息完整保留，不吞没异常细节
3. 部分失败时仍可生成完整报告
4. failFast模式除外（全局中止）
```

### 5.2 ResultCollector

```typescript
class ResultCollector {
  private results: TaskResult[];
  private errors: TaskError[];

  constructor() {
    this.results = [];
    this.errors = [];
  }

  addResult(result: TaskResult): void {
    this.results.push(result);
    if (result.status !== "success" && result.error) {
      this.errors.push(result.error);
    }
  }

  getResults(): TaskResult[] {
    return [...this.results];
  }

  getErrors(): TaskError[] {
    return [...this.errors];
  }

  getByProvider(providerId: string): TaskResult[] {
    return this.results.filter(r => r.providerId === providerId);
  }

  getByStatus(status: TaskResult["status"]): TaskResult[] {
    return this.results.filter(r => r.status === status);
  }

  getSuccessRate(): number {
    if (this.results.length === 0) return 0;
    return this.results.filter(r => r.status === "success").length / this.results.length;
  }
}
```

---

## 6. 进度追踪

### 6.1 ProgressTracker

```typescript
class ProgressTracker {
  private totalTasks: number;
  private completedTasks: number;
  private failedTasks: number;
  private startTime: number;
  private callback?: (progress: ExecutionProgress) => void;
  private latencies: number[];

  constructor(callback?: (progress: ExecutionProgress) => void) {
    this.callback = callback;
    this.completedTasks = 0;
    this.failedTasks = 0;
    this.latencies = [];
  }

  start(totalTasks: number): void {
    this.totalTasks = totalTasks;
    this.startTime = Date.now();
    this.emit();
  }

  recordCompletion(success: boolean, latencyMs?: number): void {
    this.completedTasks += 1;
    if (!success) this.failedTasks += 1;
    if (latencyMs !== undefined) this.latencies.push(latencyMs);
    this.emit();
  }

  getProgress(): ExecutionProgress {
    const elapsed = Date.now() - this.startTime;
    const avgLatency = this.latencies.length > 0
      ? this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length
      : 0;
    const remainingTasks = this.totalTasks - this.completedTasks;
    const estimatedRemainingMs = remainingTasks * avgLatency;

    return {
      totalTasks: this.totalTasks,
      completedTasks: this.completedTasks,
      failedTasks: this.failedTasks,
      inFlightTasks: this.totalTasks - this.completedTasks,
      estimatedRemainingMs,
      phase: this.determinePhase()
    };
  }

  finalize(): void {
    this.emit();
  }

  private determinePhase(): ExecutionProgress["phase"] {
    if (this.completedTasks === 0) return "initializing";
    if (this.completedTasks < this.totalTasks) return "executing";
    if (this.completedTasks === this.totalTasks) return "finalizing";
    return "executing";
  }

  private emit(): void {
    if (this.callback) {
      this.callback(this.getProgress());
    }
  }
}
```

### 6.2 进度输出格式

```
[12:30:45] 执行中 | ████████░░░░░░░░ 53% | 完成 8/15 | 失败 1 | 剩余 ~12s
[12:30:48] 执行中 | ████████████░░░░ 80% | 完成 12/15 | 失败 1 | 剩余 ~5s
[12:30:51] 完成   | ████████████████ 100% | 完成 15/15 | 失败 1 | 耗时 18s
```

---

## 7. 完整执行示例

### 7.1 测试套件定义

```typescript
const suite: TestSuite = {
  id: "suite-ab-test-v1",
  name: "GPT-4o vs Claude Sonnet 客服场景对比",
  description: "对比两个模型在客服场景下的响应质量",
  testCases: [
    {
      id: "tc-001",
      name: "退款咨询 - GPT-4o",
      provider: new OpenAIProvider(openaiConfig),
      request: {
        modelId: "gpt-4o",
        messages: [
          { role: "system", content: "你是客服助手" },
          { role: "user", content: "我想退款，订单号是12345" }
        ],
        temperature: 0.3,
        maxTokens: 512
      },
      retries: 2,
      timeoutMs: 30000
    },
    {
      id: "tc-002",
      name: "退款咨询 - Claude Sonnet",
      provider: new AnthropicProvider(anthropicConfig),
      request: {
        modelId: "claude-sonnet-4-20250514",
        messages: [
          { role: "system", content: "你是客服助手" },
          { role: "user", content: "我想退款，订单号是12345" }
        ],
        temperature: 0.3,
        maxTokens: 512
      },
      retries: 2,
      timeoutMs: 30000
    }
  ],
  config: {
    maxConcurrency: 5,
    globalTimeoutMs: 120000,
    retryPolicy: { maxRetries: 3, baseDelayMs: 1000, maxDelayMs: 30000, backoffMultiplier: 2, retryableStatusCodes: [429, 500, 502, 503, 504], jitterFactor: 0.25 },
    failFast: false,
    continueOnError: true
  }
};
```

### 7.2 执行与结果

```typescript
const engine = new ParallelEngine(suite.config);
const report = await engine.execute(suite);

console.log(`状态: ${report.status}`);
console.log(`成功: ${report.summary.successCount}/${report.summary.totalTasks}`);
console.log(`P95延迟: ${report.summary.p95LatencyMs}ms`);
console.log(`Token消耗: ${report.summary.totalTokensUsed}`);
```

---

## 8. 性能目标

| 指标                    | 目标值              | 测量方法                        |
|-------------------------|---------------------|---------------------------------|
| 引擎初始化耗时          | < 10ms              | 构造函数到就绪                  |
| 任务调度开销            | < 1ms/任务          | 单任务入队到开始执行            |
| 并发调度效率            | > 95%               | 实际并发数/配置并发数            |
| 100任务执行吞吐         | > 10 任务/s         | 100任务完成总耗时                |
| 内存占用(100任务)       | < 50MB              | 100并发任务的增量内存            |
| 错误隔离零泄漏          | 100%                | 单任务错误不影响其他任务         |
| 进度追踪精度            | ±1 任务             | 进度计数与实际完成数偏差          |
